# -*- coding: utf-8 -*-
"""
video_editor_core.py — 独立视频剪辑工具 · 剪辑内核
功能:ffmpeg 定位、视频探测、时间解析、裁剪、拼接、SRT 解析/生成、
      edge-tts 字幕转语音、时间轴对齐混音、字幕烧录合成。
仅依赖 imageio-ffmpeg（绿色 ffmpeg）；配音功能另需 edge-tts（联网）。
"""
import os
import re
import sys
import shutil
import subprocess
import tempfile
import datetime

# Windows 下隐藏 ffmpeg 子进程黑色控制台窗口（复用录屏插件同款标志）
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


class EditorError(Exception):
    """业务异常，消息可直接展示给用户"""


def find_ffmpeg():
    """定位 ffmpeg:优先 imageio-ffmpeg 绿色二进制，其次系统 PATH"""
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise EditorError("未找到 ffmpeg，请先执行:pip install imageio-ffmpeg")


def run_ffmpeg(args, total_duration=None, progress_cb=None, stage="处理"):
    """执行 ffmpeg 命令，通过 -progress 管道实时解析进度百分比。"""
    ff = find_ffmpeg()
    err_path = os.path.join(tempfile.gettempdir(), "ve_ff_err_%d.log" % os.getpid())
    cmd = [ff, "-y", "-hide_banner"] + args + ["-progress", "pipe:1", "-nostats"]
    with open(err_path, "w", encoding="utf-8", errors="ignore") as errf:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=errf,
            creationflags=CREATE_NO_WINDOW, bufsize=1,
            universal_newlines=True, encoding="utf-8", errors="ignore")
        for raw in proc.stdout:  # 逐行读进度，避免管道阻塞
            line = raw.strip()
            if line.startswith(("out_time_ms=", "out_time_us=")):
                try:
                    us = int(line.split("=", 1)[1])
                    sec = us / 1_000_000.0  # ffmpeg 的 out_time_ms 实际单位也是微秒
                    if progress_cb and total_duration:
                        progress_cb(stage, min(99, int(sec / total_duration * 100)))
                except ValueError:
                    pass
            elif line == "progress=end" and progress_cb:
                progress_cb(stage, 100)
        code = proc.wait()
    err = ""
    try:
        with open(err_path, "r", encoding="utf-8", errors="ignore") as f:
            err = f.read()
    finally:
        try:
            os.remove(err_path)
        except OSError:
            pass
    if code != 0:
        raise EditorError("ffmpeg 执行失败（%s）:\n%s" % (stage, (err or "无错误输出")[-400:]))


def parse_time(text):
    """支持 40 / 1:23 / 00:01:23 / 1:23.5 三种写法，返回秒（float）"""
    text = str(text).strip()
    if not text:
        raise EditorError("时间不能为空")
    parts = text.split(":")
    try:
        if len(parts) == 1:
            return float(parts[0])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except ValueError:
        pass
    raise EditorError("时间格式无法识别:%s（支持 40 / 1:23 / 00:01:23）" % text)


def fmt_srt_time(sec):
    """秒 -> SRT 时间码 HH:MM:SS,mmm"""
    sec = max(0.0, float(sec))
    ms = int(round((sec - int(sec)) * 1000))
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def probe_video(path):
    """解析 ffmpeg -i 输出，返回时长/分辨率/帧率/有无音轨（imageio-ffmpeg 无 ffprobe）"""
    if not os.path.isfile(path):
        raise EditorError("文件不存在:%s" % path)
    proc = subprocess.run([find_ffmpeg(), "-hide_banner", "-i", path],
                          stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                          creationflags=CREATE_NO_WINDOW)
    text = proc.stderr.decode("utf-8", errors="ignore")
    info = {"path": path, "duration": 0.0, "width": 0, "height": 0,
            "fps": 0.0, "has_audio": "Audio:" in text,
            "size": os.path.getsize(path)}
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if m:
        info["duration"] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    m = re.search(r"(\d{2,5})x(\d{2,5})", text)
    if m:
        info["width"], info["height"] = int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d+(?:\.\d+)?)\s+fps", text)
    if m:
        info["fps"] = float(m.group(1))
    return info


def unique_output(src_path, suffix):
    """生成与源同目录、带功能后缀与时间戳的输出路径，绝不覆盖源文件"""
    directory = os.path.dirname(os.path.abspath(src_path))
    base = os.path.splitext(os.path.basename(src_path))[0]
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(directory, "%s_%s_%s.mp4" % (base, suffix, ts))
# ============================ 视频裁剪 ============================

def trim_video(src, start_text, end_text, precise=False, output=None, progress_cb=None):
    """裁剪片段。precise=False 流拷贝秒出；True 重编码帧级精确。"""
    info = probe_video(src)
    start, end = parse_time(start_text), parse_time(end_text)
    if start < 0 or end <= start:
        raise EditorError("时间区间不合法:开始 %.2f 秒，结束 %.2f 秒" % (start, end))
    if end > info["duration"] + 0.5:
        raise EditorError("结束时间超过视频时长（%.1f 秒）" % info["duration"])
    output = output or unique_output(src, "裁剪")
    duration = end - start
    if not precise:
        # 流拷贝裁剪: -ss/-t 均置于 -i 后(输出侧)。
        # 实测(imageio-ffmpeg 自带 ffmpeg):若 -ss 放 -i 前,输出侧 -t 会按
        # 原始时间轴计算(选 5~35 秒、-t 30 实际截到原始 35 秒处),成片 35 秒、
        # 时间戳带 5 秒偏移,播放器以黑屏填补片头。输出侧 -ss/-t 实测成片正好
        # 30.000 秒、时间戳归零;切点自动对齐到请求点之后最近关键帧。
        # 代价:ffmpeg 需从头 demux 到切点(不解码,长视频仍远快于重编码)。
        args = ["-i", src,
                "-ss", "%.3f" % start, "-t", "%.3f" % duration,
                "-c", "copy", "-avoid_negative_ts", "make_zero",
                "-movflags", "+faststart", output]
        run_ffmpeg(args, total_duration=duration, progress_cb=progress_cb, stage="快速裁剪")
    else:
        args = ["-i", src, "-ss", "%.3f" % start, "-t", "%.3f" % duration,
                "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                "-pix_fmt", "yuv420p"]
        args += ["-c:a", "aac", "-b:a", "128k"] if info["has_audio"] else ["-an"]
        args += ["-movflags", "+faststart", output]
        run_ffmpeg(args, total_duration=duration, progress_cb=progress_cb, stage="精确裁剪")
    return output


# ============================ 视频拼接 ============================

def concat_videos(paths, compatible=False, output_dir=None, progress_cb=None):
    """按给定顺序拼接多个视频。compatible=False 流拷贝；True 统一规格重编码。"""
    if len(paths) < 2:
        raise EditorError("拼接至少需要 2 个视频")
    for p in paths:
        if not os.path.isfile(p):
            raise EditorError("文件不存在:%s" % p)
    out_dir = output_dir or os.path.dirname(os.path.abspath(paths[0]))
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output = os.path.join(out_dir, "视频拼接_%s.mp4" % ts)

    if not compatible:
        # concat demuxer 流拷贝:参数一致时秒出
        list_path = os.path.join(tempfile.gettempdir(), "ve_concat_%d.txt" % os.getpid())
        with open(list_path, "w", encoding="utf-8") as f:
            for p in paths:
                f.write("file '%s'\n" % os.path.abspath(p).replace("\\", "/").replace("'", "'\\''"))
        try:
            args = ["-f", "concat", "-safe", "0", "-i", list_path,
                    "-c", "copy", "-movflags", "+faststart", output]
            run_ffmpeg(args, progress_cb=progress_cb, stage="快速拼接")
            return output
        except EditorError:
            if not os.path.isfile(output) or os.path.getsize(output) == 0:
                raise EditorError("快速拼接失败:各视频编码参数可能不一致，请改用「兼容拼接」")
        finally:
            try:
                os.remove(list_path)
            except OSError:
                pass

    # 兼容拼接:统一分辨率（缩放补黑边）/帧率/像素格式/采样率，缺音轨补静音
    infos = [probe_video(p) for p in paths]
    w, h = infos[0]["width"] or 1280, infos[0]["height"] or 720
    if w % 2:
        w -= 1
    if h % 2:
        h -= 1
    total = sum(i["duration"] for i in infos) or None
    args = []
    for p in paths:
        args += ["-i", p]
    fc = []
    for idx, info in enumerate(infos):
        fc.append("[%d:v]scale=%d:%d:force_original_aspect_ratio=decrease,"
                  "pad=%d:%d:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p[v%d]"
                  % (idx, w, h, w, h, idx))
        if info["has_audio"]:
            fc.append("[%d:a]aresample=44100,aformat=channel_layouts=stereo[a%d]" % (idx, idx))
        else:
            fc.append("anullsrc=r=44100:cl=stereo[a%d]" % idx)
    fc.append("".join("[v%d][a%d]" % (i, i) for i in range(len(paths)))
              + "concat=n=%d:v=1:a=1[vout][aout]" % len(paths))
    args += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]",
             "-c:v", "libx264", "-preset", "medium", "-crf", "23",
             "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", output]
    run_ffmpeg(args, total_duration=total, progress_cb=progress_cb, stage="兼容拼接")
    return output


# ============================ SRT 字幕 ============================

def parse_srt(path):
    """解析标准 SRT，返回 [{'start':秒,'end':秒,'text':文本}]；自动尝试 UTF-8/GBK"""
    raw = None
    for enc in ("utf-8-sig", "gbk", "utf-8"):
        try:
            with open(path, "r", encoding=enc) as f:
                raw = f.read()
            break
        except UnicodeDecodeError:
            continue
    if raw is None:
        raise EditorError("SRT 文件编码无法识别，请另存为 UTF-8 后重试")
    subs = []
    blocks = re.split(r"\n\s*\n", raw.strip())
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        time_line = lines[1] if re.match(r"\d+$", lines[0]) else lines[0]
        text_lines = lines[2:] if re.match(r"\d+$", lines[0]) else lines[1:]
        m = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)", time_line)
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000.0
        end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000.0
        text = "\n".join(text_lines).strip()
        if text and end > start:
            subs.append({"start": start, "end": end, "text": text})
    if not subs:
        raise EditorError("未从 SRT 中解析到有效字幕条目")
    return subs


def build_srt(subs, path):
    """把字幕条目写成 UTF-8 with BOM 的 SRT（BOM 可避免部分播放器/滤镜乱码）"""
    with open(path, "w", encoding="utf-8-sig") as f:
        for idx, s in enumerate(subs, 1):
            f.write("%d\n%s --> %s\n%s\n\n" % (
                idx, fmt_srt_time(s["start"]), fmt_srt_time(s["end"]), s["text"]))
    return path
# ============================ 字幕转语音（edge-tts） ============================

TTS_VOICES = [
    ("zh-CN-XiaoxiaoNeural", "晓晓（女声，自然亲切，默认）"),
    ("zh-CN-YunxiNeural", "云希（男声，沉稳）"),
    ("zh-CN-YunjianNeural", "云健（男声，磁性解说）"),
    ("zh-CN-XiaoyiNeural", "晓伊（女声，活泼）"),
    ("zh-CN-YunyangNeural", "云扬（男声，新闻播报）"),
]


async def _tts_one(text, voice, rate, pitch, out_path):
    """单条字幕合成 mp3"""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(out_path)


def _parse_version(ver):
    """版本号字符串 -> 数字元组，如 7.2.8 -> (7,2,8)"""
    nums = re.findall(r"\d+", str(ver))
    return tuple(int(x) for x in nums[:3]) if nums else (0, 0, 0)


def _check_edge_tts():
    """导入并校验 edge-tts 版本:6.x 旧令牌算法已被微软服务端拒绝(403)，必须 7.2.8+。"""
    try:
        import edge_tts
    except ImportError:
        raise EditorError("未安装 edge-tts，请先执行:pip install -r requirements.txt")
    ver = getattr(edge_tts, "__version__", "0.0.0")
    if _parse_version(ver) < (7, 2, 8):
        raise EditorError(
            "edge-tts 版本过旧（当前 %s），微软 TTS 服务已拒绝旧版安全令牌（报 403）。\n"
            "请升级后重试:pip install -U \"edge-tts>=7.2.8,<8.0.0\"" % ver)
    return edge_tts


def generate_speech(subs, voice, rate, pitch, work_dir, progress_cb=None):
    """逐条字幕生成配音 mp3，返回 [(mp3路径, 起始毫秒)]。需要联网。单条失败自动重试 1 次。"""
    _check_edge_tts()
    results = []
    for idx, s in enumerate(subs):
        if not s.get("text", "").strip():
            continue
        out_path = os.path.join(work_dir, "tts_%03d.mp3" % idx)
        import asyncio
        last_err = None
        for _attempt in (1, 2):  # 首次失败后重试 1 次，兼容偶发网络抖动
            try:
                asyncio.run(_tts_one(s["text"], voice, rate, pitch, out_path))
                last_err = None
                break
            except Exception as e:
                last_err = e
                msg = str(e)
                # 403/旧令牌被拒属于版本问题，重试无意义，直接给出升级指引
                if "403" in msg or "Invalid response status" in msg or "Sec-MS-GEC" in msg:
                    raise EditorError(
                        "微软 TTS 服务拒绝访问（403 Invalid response status），多为 edge-tts 版本过旧。\n"
                        "请升级后重试:pip install -U \"edge-tts>=7.2.8,<8.0.0\"\n"
                        "原始错误:%s" % msg[:200])
        if last_err is not None:
            raise EditorError("第 %d 条字幕配音失败（已重试 1 次，配音需联网）:%s"
                              % (idx + 1, str(last_err)[:200]))
        if not os.path.isfile(out_path) or os.path.getsize(out_path) == 0:
            raise EditorError("第 %d 条字幕配音生成为空，请检查网络后重试" % (idx + 1))
        results.append((out_path, int(round(s["start"] * 1000))))
        if progress_cb:
            progress_cb("字幕配音", int((idx + 1) / len(subs) * 100))
    if not results:
        raise EditorError("没有可配音的字幕文本")
    return results


def _escape_sub_path(path):
    """subtitles 滤镜路径转义:反斜杠转正斜杠、盘符冒号转义"""
    return os.path.abspath(path).replace("\\", "/").replace(":", "\\:")


def render_subtitles(src, subs, output=None, do_tts=False, voice="zh-CN-XiaoxiaoNeural",
                     rate="+0%", pitch="+0Hz", audio_mode="mix", orig_volume=0.3,
                     style=None, progress_cb=None):
    """
    字幕烧录 + 可选配音合成，一次重编码导出 MP4。
    audio_mode: mix=配音+原声混合 / voiceover=配音覆盖原声 / tts_only=仅配音
    style: {fontsize, font_name, primary_colour, outline_colour, outline, alignment, margin_v}
    """
    import time
    info = probe_video(src)
    if not subs:
        raise EditorError("字幕列表为空")
    output = output or unique_output(src, "字幕配音" if do_tts else "字幕")
    style = style or {}
    fontsize = style.get("fontsize", 22)
    font_name = style.get("font_name", "Microsoft YaHei")
    primary = style.get("primary_colour", "&H00FFFFFF")
    outline_c = style.get("outline_colour", "&H00000000")
    outline = style.get("outline", 1.2)
    alignment = 6 if style.get("position") == "top" else 2  # ASS 小键盘位:6顶部 2底部
    margin_v = style.get("margin_v", 30)

    work_dir = tempfile.mkdtemp(prefix="ve_sub_%d_" % int(time.time()))
    try:
        srt_path = os.path.join(work_dir, "subs.srt")
        build_srt(subs, srt_path)
        force_style = ("FontName=%s,Fontsize=%d,PrimaryColour=%s,OutlineColour=%s,"
                       "BorderStyle=1,Outline=%s,Alignment=%d,MarginV=%d"
                       % (font_name, fontsize, primary, outline_c, outline, alignment, margin_v))
        vf = "subtitles='%s':force_style='%s'" % (_escape_sub_path(srt_path), force_style)

        tts_files = []
        if do_tts:
            tts_files = generate_speech(subs, voice, rate, pitch, work_dir, progress_cb)

        args = ["-i", src]
        if do_tts:
            for mp3, _ms in tts_files:
                args += ["-i", mp3]
            need_silent_base = (not info["has_audio"]) or audio_mode in ("voiceover", "tts_only")
            if need_silent_base:
                # 与视频等长的静音底轨，作为 amix duration=first 的时长基准，防止输出变长
                args += ["-f", "lavfi", "-t", "%.3f" % info["duration"],
                         "-i", "anullsrc=r=44100:cl=stereo"]
            n = len(tts_files)
            fc = []
            for i, (_mp3, ms) in enumerate(tts_files):
                fc.append("[%d:a]adelay=%d|%d[d%d]" % (i + 1, ms, ms, i))
            base_idx = n + 1  # 视频占输入 0，配音占 1..n，底轨在 n+1
            if info["has_audio"] and audio_mode == "mix":
                fc.append("[0:a]volume=%.2f[base]" % float(orig_volume))
            else:
                fc.append("[%d:a]volume=0.0[base]" % base_idx)
            fc.append("[base]" + "".join("[d%d]" % i for i in range(n))
                      + "amix=inputs=%d:duration=first:dropout_transition=0,"
                        "aresample=44100[aout]" % (n + 1))
            args += ["-filter_complex", ";".join(fc),
                     "-map", "0:v", "-map", "[aout]"]
        else:
            args += ["-map", "0:v"]
            args += ["-map", "0:a"] if info["has_audio"] else ["-an"]

        args += ["-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                 "-pix_fmt", "yuv420p"]
        if do_tts or info["has_audio"]:
            args += ["-c:a", "aac", "-b:a", "128k"]
        args += ["-movflags", "+faststart", output]
        run_ffmpeg(args, total_duration=info["duration"] or None,
                   progress_cb=progress_cb, stage="合成导出")
        return output
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)