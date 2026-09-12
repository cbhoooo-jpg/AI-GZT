# -*- coding: utf-8 -*-
"""
屏幕录制插件（本地操作类）V1.0

能力:
1. mss 抓屏（多屏/高DPI坐标已由 screenshot_tool.py 验证）+ tkinter 全屏遮罩鼠标框选；
2. 原始帧经管道直喂 imageio-ffmpeg 自带的 ffmpeg，libx264 编码输出
   H.264/yuv420p/faststart 标准 MP4（B站、腾讯视频可直接上传）；
3. 对话控制:start（开始录屏）/ stop（停止录屏）/ status（录屏状态）。

架构说明（重要）:
主程序 api_server 每次调用插件都会重新 import 模块并同步执行 run()，录制状态无法
驻留内存。因此真正的录制运行在独立子进程（python main.py --record 参数.json）中，
启动器与录制进程通过 runtime/status.json 与 runtime/stop.flag 通信。

V1 边界:只录画面不录声音（参赛视频后期用 edge-tts 配音对齐）；麦克风/系统声混入列 V2。

命令行自测:
  python main.py selftest           # 录主屏 3 秒，产物 runtime/selftest.mp4
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import mss

# Windows 下抓屏线程初始化 COM，规避 mss 的 RPC_E_WRONG_THREAD(0x8001010d)
try:
    import pythoncom
    _HAS_PYTHONCOM = True
except Exception:
    _HAS_PYTHONCOM = False

# 主程序注入的合并配置（默认配置+用户配置）；命令行自测时为空字典
plugin_config = {}

PLUGIN_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = PLUGIN_DIR / "runtime"        # 状态文件/标志/自测产物目录（不入库）
STATUS_FILE = RUNTIME_DIR / "status.json"
STOP_FLAG = RUNTIME_DIR / "stop.flag"
PAUSE_FLAG = RUNTIME_DIR / "pause.flag"   # 存在即暂停:录制进程停止抓帧但不退出，删除即继续

# 默认录制参数（均可被插件配置页或调用参数覆盖，业务逻辑中不再硬编码其他阈值）
DEFAULT_FPS = 20                            # 默认帧率（参赛演示建议 30）
DEFAULT_CRF = 23                            # x264 画质，数值越小越清晰体积越大
DEFAULT_PRESET = "veryfast"                 # x264 编码预设
DEFAULT_MAX_SECONDS = 1800                  # 防遗忘自动停止:30 分钟
X264_PRESETS = {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium"}

# Windows 子进程统一标志:控制台由 pythonw 启动时进程没有控制台，若不加此标志，
# 系统会为每个子进程（ffmpeg/tasklist 等）新建黑色控制台窗口——
# 轮询时表现为屏幕每 0.8 秒规律闪烁，录制时 ffmpeg 黑窗还会被 mss 录进成片导致整段黑屏
_SUBPROCESS_FLAGS = 0x08000000 if os.name == "nt" else 0   # CREATE_NO_WINDOW


def cfg(key, default):
    """读取主程序注入的插件配置，空值回退默认。"""
    val = plugin_config.get(key, default)
    return val if val not in (None, "") else default


def find_ffmpeg():
    """定位 ffmpeg:优先 imageio-ffmpeg 自带绿色二进制，其次系统 PATH，均无返回 None。"""
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).exists():
            return exe
    except Exception:
        pass
    return shutil.which("ffmpeg")


def _even(n):
    """宽高对齐偶数像素（yuv420p 像素格式的硬要求，奇数宽高会编码失败）。"""
    n = max(2, int(n))
    return n - (n % 2)
# ===== 录制区域选择（tkinter 全屏遮罩，方案复用 screenshot_tool.py） =====
try:
    import tkinter as tk
    _HAS_TK = True
except Exception:
    _HAS_TK = False


class RegionSelector:
    """跨所有显示器的半透明遮罩，鼠标拖拽框选录制区域；ESC 取消、回车取全屏。"""

    def __init__(self):
        self.start = None
        self.end = None
        self.selecting = False
        self.rect = None              # 选中结果 (x, y, w, h)，取消为 None
        self.masks = []
        self.canvases = []
        self.root = None

    def _make_mask(self, x, y, w, h):
        win = tk.Toplevel()
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.5)
        win.config(bg="black")
        win.cursor = "cross"
        cvs = tk.Canvas(win, width=w, height=h, bg="black", highlightthickness=0)
        cvs.pack(fill=tk.BOTH, expand=True)
        self.canvases.append(cvs)
        cvs.bind("<ButtonPress-1>", lambda e, ww=win: self._press(e, ww))
        cvs.bind("<B1-Motion>", self._drag)
        cvs.bind("<ButtonRelease-1>", self._release)
        win.bind("<KeyPress>", self._key)
        win.focus_set()
        return win

    def _press(self, event, win):
        if not self.selecting:
            self.selecting = True
            gx = win.winfo_x() + event.x
            gy = win.winfo_y() + event.y
            self.start = self.end = (gx, gy)

    def _drag(self, event):
        if not self.selecting:
            return
        top = event.widget.winfo_toplevel()
        self.end = (top.winfo_x() + event.x, top.winfo_y() + event.y)
        for cvs in self.canvases:
            cvs.delete("sel")
            top = cvs.winfo_toplevel()
            l = min(self.start[0], self.end[0]) - top.winfo_x()
            t = min(self.start[1], self.end[1]) - top.winfo_y()
            r = max(self.start[0], self.end[0]) - top.winfo_x()
            b = max(self.start[1], self.end[1]) - top.winfo_y()
            cvs.create_rectangle(l, t, r, b, outline="#1677ff", width=2,
                                 fill="#1677ff", stipple="gray25", tags="sel")

    def _release(self, event):
        if not self.selecting:
            return
        self.selecting = False
        x1, y1 = self.start
        x2, y2 = self.end
        x, y = min(x1, x2), min(y1, y2)
        w, h = abs(x2 - x1), abs(y2 - y1)
        if w < 10 or h < 10:      # 选区过小视为取消
            self._close()
            self.rect = None
            return
        self.rect = (x, y, w, h)
        self._close()

    def _key(self, event):
        if event.keysym == "Escape":
            self.rect = None
            self._close()
        elif event.keysym in ("Return", "KP_Enter"):
            from screeninfo import get_monitors
            ms = get_monitors()
            x0 = min(m.x for m in ms)
            y0 = min(m.y for m in ms)
            x1 = max(m.x + m.width for m in ms)
            y1 = max(m.y + m.height for m in ms)
            self.rect = (x0, y0, x1 - x0, y1 - y0)
            self._close()

    def _close(self):
        for win in self.masks:
            try:
                win.destroy()
            except Exception:
                pass
        self.masks.clear()
        self.canvases.clear()
        if self.root:
            self.root.quit()
            self.root.destroy()
            self.root = None

    def select(self):
        """弹出遮罩并阻塞等待选择，返回 (x, y, w, h) 或 None（用户取消）。"""
        if not _HAS_TK:
            raise RuntimeError("当前环境缺少 tkinter，无法弹出框选遮罩，请改用全屏录制。")
        from screeninfo import get_monitors
        self.rect = None
        self.root = tk.Tk()
        self.root.withdraw()
        for m in get_monitors():
            self.masks.append(self._make_mask(m.x, m.y, m.width, m.height))
        self.root.mainloop()
        return self.rect


def resolve_region(mode, monitor_index=0):
    """解析录制区域。

    mode: full=主屏全屏（默认）；region=鼠标框选；monitor_N=第 N 个显示器。
    返回 mss monitor 字典 {"left","top","width","height"}，宽高已对齐偶数。
    """
    with mss.mss() as sct:
        monitors = sct.monitors          # [0]=虚拟全屏, [1]=主屏, [2..]=副屏
        if mode == "region":
            rect = RegionSelector().select()
            if not rect:
                return None              # 用户取消框选
            x, y, w, h = rect
            return {"left": x, "top": y, "width": _even(w), "height": _even(h)}
        if mode.startswith("monitor"):
            idx = monitor_index or int(mode.split("_")[-1] or "1")
            idx = max(1, min(idx, len(monitors) - 1))
            mon = dict(monitors[idx])
        else:
            mon = dict(monitors[1])      # 默认主屏
        mon["width"] = _even(mon["width"])
        mon["height"] = _even(mon["height"])
        return mon
# ===== 状态文件读写（启动器与录制子进程的唯一通信媒介） =====
def write_status(data: dict):
    """原子写状态文件:先写临时文件再替换，避免读取方读到半截 JSON。"""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATUS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATUS_FILE)


def read_status():
    """读取录制状态；文件不存在或损坏时返回 idle 状态。"""
    try:
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"recording": False, "state": "idle"}


def is_process_alive(pid):
    """判断进程是否存活（仅查询，不杀进程）。

    Windows 下用 ctypes 直接调 OpenProcess，不再启动 tasklist 子进程——
    控制台由 pythonw 启动时没有控制台，tasklist 每次执行都会闪一个黑窗，
    而本函数被控制台每 0.8 秒轮询调用，表现为屏幕规律闪烁。
    """
    if not pid:
        return False
    try:
        if os.name == "nt":
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
            if not handle:
                return False
            kernel32.CloseHandle(handle)
            return True
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def record_loop(region, out_path, fps, crf, preset, max_seconds):
    """录制主循环（运行在独立子进程中）。

    流程:拉起 ffmpeg 子进程 → 按 1/fps 节奏抓屏 → BGRA 原始帧直喂管道 →
    检测 stop.flag / 达到最大时长 → 关闭管道等待 ffmpeg 封装完成 → 更新状态。
    """
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        write_status({"recording": False, "state": "error",
                      "error": "未找到 ffmpeg，请先安装 imageio-ffmpeg 依赖。"})
        return

    w, h = region["width"], region["height"]
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pixel_format", "bgra",
        "-video_size", f"{w}x{h}", "-framerate", str(fps),
        "-i", "pipe:0",
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(out_path),
    ]

    # paused:是否暂停中；content_seconds:成片内容时长（不含暂停）；paused_seconds:累计暂停时长
    status = {"recording": True, "state": "recording", "output": str(out_path),
              "width": w, "height": h, "fps": fps,
              "started_at": time.time(), "frames": 0, "pid": os.getpid(),
              "paused": False, "pause_started_at": None,
              "content_seconds": 0.0, "paused_seconds": 0.0}
    write_status(status)

    proc = None
    err_tail = ""
    try:
        if _HAS_PYTHONCOM:
            pythoncom.CoInitialize()      # 抓屏线程 COM 初始化
        # 必须带 CREATE_NO_WINDOW:录制子进程由 pythonw 控制台拉起时没有控制台，
        # 否则系统给 ffmpeg 新建黑色控制台窗口（置顶），该窗口会被 mss 录进成片导致整段黑屏
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                creationflags=_SUBPROCESS_FLAGS)
        frame_interval = 1.0 / fps
        with mss.mss() as sct:
            while True:
                # 停止指令优先（墙钟时间检测，暂停期间也能立即响应停止）
                if STOP_FLAG.exists():
                    break
                # 防遗忘自动停止按“成片内容时长”计时，暂停的时间不计入
                if status["content_seconds"] >= max_seconds:
                    break

                # ===== 暂停/继续:pause.flag 存在则停帧等待，不喂任何数据给 ffmpeg =====
                # ffmpeg 帧时间戳由帧序隐含，暂停期间不写帧，成片天然无空白段，恢复即续录
                if PAUSE_FLAG.exists():
                    if not status.get("paused"):
                        status["paused"] = True
                        status["pause_started_at"] = time.time()
                        status["state"] = "paused"
                        write_status(status)
                    time.sleep(0.2)
                    continue
                if status.get("paused"):
                    status["paused_seconds"] += round(
                        time.time() - status.pop("pause_started_at"), 2)
                    status["paused"] = False
                    status["state"] = "recording"
                    write_status(status)

                t0 = time.time()
                img = sct.grab(region)
                # 分辨率异常保护:只写入与声明尺寸一致的帧
                if img.width == w and img.height == h:
                    proc.stdin.write(img.bgra)
                    status["frames"] += 1
                    status["content_seconds"] = round(status["frames"] / fps, 1)
                    if status["frames"] % fps == 0:   # 约每秒落一次状态
                        write_status(status)
                # 帧节奏控制:补齐到下一帧时刻，既不超频也不堆积
                dt = time.time() - t0
                if dt < frame_interval:
                    time.sleep(frame_interval - dt)
    except Exception as e:
        err_tail = str(e)
    finally:
        # 优雅关闭管道并等待 ffmpeg 写完 moov，超时则强杀（强杀会导致 MP4 不可播）
        if proc is not None:
            try:
                if proc.stdin:
                    proc.stdin.close()
            except Exception:
                pass
            try:
                proc.wait(timeout=15)
            except Exception:
                proc.kill()
        try:
            STOP_FLAG.unlink(missing_ok=True)
            PAUSE_FLAG.unlink(missing_ok=True)
        except Exception:
            pass
        if _HAS_PYTHONCOM:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

    elapsed = time.time() - status["started_at"]
    ok = Path(out_path).exists() and Path(out_path).stat().st_size > 0
    if not ok:
        stderr_txt = ""
        try:
            if proc is not None and proc.stderr:
                stderr_txt = proc.stderr.read().decode("utf-8", "ignore")[-300:]
        except Exception:
            pass
        write_status({"recording": False, "state": "error",
                      "error": f"录制失败:{err_tail or stderr_txt or '未生成有效文件'}"})
        return

    status.update({"recording": False, "state": "finished",
                   "elapsed_seconds": round(elapsed, 1),
                   "content_seconds": round(status.get("content_seconds", 0.0), 1),
                   "paused_seconds": round(status.get("paused_seconds", 0.0), 1),
                   "file_size": round(Path(out_path).stat().st_size / 1024 / 1024, 2)})
    write_status(status)


def _build_output_path():
    """生成输出文件路径:配置目录优先，其次系统“视频”目录，文件名带时间戳不覆盖。"""
    out_dir = cfg("output_dir", "")
    if not out_dir:
        out_dir = str(Path.home() / "Videos" / "AI智能助手录屏")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = time.strftime("screen_recorder_%Y%m%d_%H%M%S") + ".mp4"
    return out_dir / name
def probe_video_seconds(video_path):
    """用 ffmpeg -i 输出解析视频时长（秒）；失败返回 None。"""
    import re
    ffmpeg = find_ffmpeg()
    if not ffmpeg or not Path(video_path).exists():
        return None
    try:
        p = subprocess.run([ffmpeg, "-hide_banner", "-i", str(video_path)],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="ignore", timeout=20,
                           creationflags=_SUBPROCESS_FLAGS)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", p.stderr or "")
        if m:
            h, mnt, sec = m.groups()
            return int(h) * 3600 + int(mnt) * 60 + float(sec)
    except Exception:
        return None
    return None


def speed_up_video(src_path, target_seconds=None, factor=None):
    """成片变速压缩:内容完整不裁剪，仅通过 setpts 改变播放时长。

    典型场景:实际录制 60 秒，指定压到 40 秒 → 自动按 1.5 倍速重编码。
    target_seconds:目标成片秒数（与 factor 二选一，优先 target_seconds）。
    factor:显式倍速（>1 加速、<1 减速）。
    返回 (输出路径 or None, 说明文本)。
    """
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        return None, "未找到 ffmpeg，无法变速（请安装 imageio-ffmpeg 依赖）。"
    src = Path(src_path)
    if not src.exists():
        return None, f"源视频不存在:{src_path}"

    src_dur = probe_video_seconds(src)
    if not src_dur:
        return None, "无法解析源视频时长，变速中止。"

    # 计算倍速:目标秒数模式 = 源时长 / 目标时长；夹取到 setpts 安全区间 [0.25, 4.0]
    SPEED_MIN, SPEED_MAX = 0.25, 4.0
    if target_seconds:
        factor = src_dur / max(0.1, float(target_seconds))
    if factor is None:
        return None, "未指定目标秒数或倍速。"
    factor = max(SPEED_MIN, min(SPEED_MAX, float(factor)))
    if abs(factor - 1.0) < 0.01:
        return None, f"源视频 {src_dur:.1f} 秒，与目标基本一致，无需变速。"

    tag = f"{int(round(target_seconds))}s" if target_seconds else f"{factor:g}x"
    out_path = src.with_name(src.stem + f"_加速_{tag}.mp4")
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src),
        "-filter:v", f"setpts=PTS/{factor:.6f}",   # V1 无音轨；帧序重排，内容不丢
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(out_path),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="ignore",
                       creationflags=_SUBPROCESS_FLAGS)
    if p.returncode != 0 or not out_path.exists():
        return None, f"变速失败:{(p.stderr or '未知错误')[-300:]}"

    new_dur = probe_video_seconds(out_path) or 0
    return str(out_path), (f"✅ 变速完成:{src_dur:.1f} 秒 → {new_dur:.1f} 秒"
                           f"（{factor:.2f} 倍速，内容完整无裁剪），文件:{out_path}")
# ===== 插件对话入口:start / stop / status =====
def _spawn_recorder(mode, monitor_index, out_path, fps, crf, preset, max_seconds):
    """拉起独立录制子进程（非阻塞），返回子进程 PID。"""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    STOP_FLAG.unlink(missing_ok=True)
    param_file = RUNTIME_DIR / "record_params.json"
    param_file.write_text(json.dumps({
        "mode": mode, "monitor_index": monitor_index, "out_path": str(out_path),
        "fps": fps, "crf": crf, "preset": preset, "max_seconds": max_seconds,
    }, ensure_ascii=False), encoding="utf-8")
    log_file = open(RUNTIME_DIR / "record_child.log", "wb")
    # CREATE_NO_WINDOW:录制子进程本身不弹黑框（不影响 tkinter 框选遮罩正常显示）
    proc = subprocess.Popen(
        [sys.executable, str(PLUGIN_DIR / "main.py"), "--record", str(param_file)],
        cwd=str(PLUGIN_DIR), stdin=subprocess.DEVNULL,
        stdout=log_file, stderr=subprocess.STDOUT,
        creationflags=_SUBPROCESS_FLAGS)
    return proc.pid


def _parse_int(value, default, lo, hi):
    """安全解析整数参数并夹取到合法区间。"""
    try:
        return max(lo, min(hi, int(float(value))))
    except Exception:
        return default


def _detect_mode(params):
    """从显式参数与自然语言 query 中识别录制范围与显示器序号。"""
    import re
    mode = str(params.get("mode", "")).strip().lower()
    query = str(params.get("query", ""))
    if not mode:
        if any(k in query for k in ("框选", "选区", "选择区域", "自定义区域", "拖拽", "框一块")):
            mode = "region"
        else:
            m = re.search(r"第?\s*(\d+)\s*个?(?:显示器|屏幕|monitor)", query)
            if "副屏" in query:
                mode, idx = "monitor", 2
            elif m:
                mode, idx = "monitor", int(m.group(1))
            else:
                mode, idx = "full", 1
    else:
        idx = _parse_int(params.get("monitor_index", 1), 1, 1, 16)
        if mode.isdigit():
            mode, idx = "monitor", int(mode)
    monitor_index = idx if mode == "monitor" else 0
    return mode, monitor_index


def _status_text(st):
    """把状态字典格式化为给用户看的文本。"""
    state = st.get("state", "idle")
    if state == "recording":
        return (f"🔴 正在录屏中:成片内容 {st.get('content_seconds', 0):.0f} 秒、"
                f"约 {st.get('frames', 0)} 帧，"
                f"分辨率 {st.get('width')}x{st.get('height')}@{st.get('fps')}fps，"
                f"输出文件 {st.get('output')}")
    if state == "paused":
        return (f"⏸ 已暂停:已录内容 {st.get('content_seconds', 0):.0f} 秒，"
                f"说/点「继续」恢复录制，「停止录屏」结束并保存。")
    if state == "starting" or st.get("recording"):
        return "🔴 录屏正在启动/框选中……"
    if state == "finished":
        ps = st.get('paused_seconds', 0)
        pause_txt = f"，暂停 {ps:.0f} 秒" if ps else ""
        return (f"✅ 录屏已结束:{st.get('output')}，"
                f"成片时长 {st.get('content_seconds', st.get('elapsed_seconds'))} 秒"
                f"{pause_txt}，大小 {st.get('file_size', 0):.2f} MB")
    if state == "canceled":
        return "已取消:未选择录制区域。"
    if state == "error":
        return f"❌ 录屏出错:{st.get('error', '未知错误')}"
    return "⚪ 当前没有进行中的录屏。"


def run(params: dict = None):
    """插件主入口:由主程序以全新模块实例同步调用，支持 start/stop/status。"""
    params = params or {}
    query = str(params.get("query", ""))
    action = str(params.get("action", "")).strip().lower()
    if not action:
        # 注意“暂停”含“停”字，必须先于 stop 判断，否则会被误判为结束
        if "暂停" in query:
            action = "pause"
        elif "继续" in query or "恢复" in query:
            action = "resume"
        elif "变速" in query or "加速" in query or "压缩到" in query or "压到" in query:
            action = "speed"
        elif "停" in query:
            action = "stop"
        elif "状态" in query or "进度" in query:
            action = "status"
        else:
            action = "start"

    st = read_status()
    alive = is_process_alive(st.get("pid")) and st.get("state") in ("recording", "paused")

    if action == "status":
        return _status_text(st)

    if action == "pause":
        if st.get("state") != "recording" or not is_process_alive(st.get("pid")):
            return "当前没有正在录制的录屏，无需暂停。"
        PAUSE_FLAG.touch()
        time.sleep(0.5)
        return "⏸ 已暂停录屏（录制进程保留，画面不写入成片），说/点「继续录屏」恢复。"

    if action == "resume":
        if st.get("state") != "paused":
            return "当前录屏不处于暂停状态，无需继续。"
        try:
            PAUSE_FLAG.unlink(missing_ok=True)
        except Exception:
            pass
        time.sleep(0.5)
        return "▶ 已继续录屏，新画面接续写入同一文件。"

    if action == "stop":
        if st.get("state") not in ("recording", "starting", "paused") \
                or not is_process_alive(st.get("pid")):
            return "当前没有进行中的录屏，无需停止。"
        # 暂停态下停止:先解除暂停标志，让录制进程立刻响应停止，避免等待 0.2s 轮询
        try:
            PAUSE_FLAG.unlink(missing_ok=True)
        except Exception:
            pass
        STOP_FLAG.touch()
        for _ in range(30):                          # 最多等待 15 秒封装
            time.sleep(0.5)
            st = read_status()
            if st.get("state") in ("finished", "error", "canceled"):
                break
        return _status_text(st)

    if action == "speed":
        # 成片变速:优先显式参数 target_seconds/factor，其次从 query 解析“压到40秒/1.5倍速”
        import re
        target = params.get("target_seconds")
        factor = params.get("factor")
        if not target and not factor:
            m = re.search(r"(\d+(?:\.\d+)?)\s*秒", query)
            if m:
                target = float(m.group(1))
            else:
                m2 = re.search(r"(\d+(?:\.\d+)?)\s*倍", query)
                if m2:
                    factor = float(m2.group(1))
        src = params.get("video_path") or st.get("output")
        if not src:
            return ("请先完成一次录屏，或明确指定要变速的视频。说法示例:"
                    "「把刚才的录屏压缩到40秒」「1.5倍速处理」。")
        _, msg = speed_up_video(src, target_seconds=target, factor=factor)
        return msg

    if action == "start":
        if alive:
            return "已有一段录屏正在进行中，请先说「停止录屏」结束当前录制，再开始新的录制。\n" + _status_text(st)
        if not find_ffmpeg():
            return ("❌ 缺少 ffmpeg:请在插件市场为本插件安装依赖 imageio-ffmpeg，"
                    "或执行 pip install imageio-ffmpeg==0.5.1 后重试。")
        mode, monitor_index = _detect_mode(params)
        fps = _parse_int(params.get("fps", cfg("fps", DEFAULT_FPS)), DEFAULT_FPS, 5, 60)
        crf = _parse_int(params.get("crf", cfg("crf", DEFAULT_CRF)), DEFAULT_CRF, 0, 40)
        preset = str(params.get("preset", cfg("preset", DEFAULT_PRESET))).strip()
        if preset not in X264_PRESETS:
            preset = DEFAULT_PRESET
        max_seconds = _parse_int(cfg("max_seconds", DEFAULT_MAX_SECONDS),
                                 DEFAULT_MAX_SECONDS, 10, 8 * 3600)
        out_path = _build_output_path()
        write_status({"recording": True, "state": "starting"})
        pid = _spawn_recorder(mode, monitor_index, out_path, fps, crf, preset, max_seconds)
        if mode == "region":
            return (f"🎬 框选遮罩已弹出，请在屏幕上拖拽选择要录制的区域（ESC 取消、回车全屏），"
                    f"选好后自动开始录制，文件将保存到 {out_path}。说「停止录屏」结束。")
        for _ in range(20):                          # 全屏/指定显示器:等待真正进入录制
            time.sleep(0.25)
            st = read_status()
            if st.get("state") in ("recording", "error"):
                break
        head = f"🎬 已开始录屏（{ '第'+str(monitor_index)+'个显示器' if mode=='monitor' else '主屏全屏'}，{fps}fps），文件:{out_path}。说「停止录屏」结束。"
        if st.get("state") == "error":
            return f"❌ 录屏启动失败:{st.get('error')}"
        return head

    return (f"不支持的操作:{action}（可用:start 开始 / pause 暂停 / "
            f"resume 继续 / stop 结束并保存 / status 状态 / speed 成片变速）")
# ===== 插件生命周期（主程序约定） =====
def init(config: dict = None):
    """插件安装/启用/配置修改时调用:校验关键依赖并返回初始化结果。"""
    global plugin_config
    if config:
        plugin_config = config
    missing = []
    try:
        import mss  # noqa: F401
    except Exception:
        missing.append("mss")
    if not find_ffmpeg():
        missing.append("imageio-ffmpeg")
    if missing:
        return {"success": False,
                "message": "屏幕录制依赖缺失:" + "、".join(missing) +
                           "，请在插件市场安装依赖后重启插件。"}
    return {"success": True, "message": "屏幕录制插件初始化成功，可对话说「开始录屏」。"}


def uninstall():
    """插件卸载时清理运行时状态文件（保留用户已录制的视频）。"""
    try:
        for f in (STATUS_FILE, STOP_FLAG, PAUSE_FLAG, RUNTIME_DIR / "record_params.json",
                  RUNTIME_DIR / "record_child.log"):
            if f.exists():
                f.unlink()
    except Exception:
        pass
    return {"success": True, "message": "屏幕录制插件已卸载，已清理运行时状态。"}


# ===== 命令行入口:录制子进程 / 真机自测 =====
def _child_main(param_path):
    """录制子进程入口:读取参数文件 → 解析区域 → 进入录制循环。"""
    p = json.loads(Path(param_path).read_text(encoding="utf-8"))
    region = resolve_region(p["mode"], p.get("monitor_index", 0))
    if not region:                       # 用户在框选遮罩按了 ESC
        write_status({"recording": False, "state": "canceled"})
        return
    record_loop(region, p["out_path"], int(p["fps"]), int(p["crf"]),
                p["preset"], int(p["max_seconds"]))


def _selftest():
    """真机自测:录主屏 3 秒，输出 runtime/selftest.mp4，用于验证整条编码链路。"""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    region = resolve_region("full")
    out = RUNTIME_DIR / "selftest.mp4"
    out.unlink(missing_ok=True)
    print(f"[selftest] 录制主屏 {region['width']}x{region['height']} 共 3 秒 ...")
    record_loop(region, str(out), fps=15, crf=23, preset="veryfast", max_seconds=3)
    st = read_status()
    if st.get("state") == "finished" and out.exists():
        print(f"[selftest] 成功:{out}，{st.get('elapsed_seconds')}s，"
              f"{st.get('file_size', 0)/1024:.0f} KB")
    else:
        print(f"[selftest] 失败:{st}")


if __name__ == "__main__":
    # Windows 控制台默认 GBK，统一切 UTF-8，避免 emoji/中文输出崩溃
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if len(sys.argv) >= 3 and sys.argv[1] == "--record":
        _child_main(sys.argv[2])
    elif len(sys.argv) >= 2 and sys.argv[1] == "selftest":
        _selftest()
    else:
        print("用法:python main.py selftest（录主屏3秒自测）；"
              "录制子进程由插件自动以 --record 参数.json 拉起。")