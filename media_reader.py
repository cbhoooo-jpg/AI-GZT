# -*- coding: utf-8 -*-
"""
媒体读取核心模块（read_media 工具的后端底座）

职责:
    1. 媒体参数读取:统一从 config.json 的 tool_output 节读取媒体参数，缺键用本模块默认值兜底
    2. 图片三级降级转码:像素级缩放 → 质量级降档 → 兜底只返元信息（永不截断像素、永不 OOM）
    3. 请求级媒体登记表:工具层登记像素，消息构造层取用后清空（供补插 user 多模态消息）
    4. 视频探测与抽帧接口（阶段B 实现，本阶段仅占位；ffmpeg 缺失时返回明确文字，绝不静默失败）

依赖:
    - PIL(Pillow):图片解码与缩放（项目已有依赖）
    - numpy:阶段B 帧差计算（向量化，比纯 PIL 快 10 倍以上）
    - ffmpeg/ffprobe:阶段B 视频抽帧（随包内置，缺失时明确提示）

铁律:
    - 纯新增文件，不修改 llm_client.image_to_base64（保护 chat 附件直传链路零回归）
    - 所有阈值来自配置，禁止硬编码魔法数字
    - 任何失败都必须抛出可读异常或返回带原因的结果，禁止静默失败
"""
import base64
import io
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

# 配置路径解析:与 llm_client.py / api_server.py 完全对齐（打包环境=EXE同级，开发环境=脚本所在目录）
if getattr(sys, "frozen", False):
    CONFIG_PATH = os.path.join(os.path.dirname(sys.executable), "config.json")
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# 媒体参数默认值（config.json 的 tool_output 节缺键时兜底，与执行步骤文件第四章一致）
MEDIA_DEFAULTS: Dict[str, Any] = {
    # 图片参数（阶段A 使用）
    "media_image_max_edge": 1568,                   # 长边像素上限，超了等比缩放
    "media_image_max_size_mb": 1.0,                 # 单图体积上限（MB）
    "media_image_quality_steps": [85, 75, 60, 45],  # JPEG 质量逐档，达标即停
    "media_total_max_mb": 2.0,                      # 单次读取附件总体积红线（MB）
    # 视频抽帧参数（阶段B 使用·五道闸门）
    "video_window_seconds": 60,                     # 默认时间窗（秒）
    "video_frame_interval": 10,                     # 抽帧间隔（秒）
    "video_max_frames": 8,                          # 最大帧数硬顶
    "video_frame_max_edge": 1024,                   # 单帧长边上限
    "video_frame_max_kb": 200,                      # 单帧体积上限（KB）
    "video_total_max_mb": 2.0,                      # 帧附件总体积红线（MB）
    # 停滞段分析参数（阶段B 使用）
    "static_scan_fps": 1.0,                         # 停滞扫描采样频率（每秒取帧数）
    "static_mad_threshold": 2.0,                    # 静止判定阈值（MAD）
    "static_min_duration": 3.0,                     # 最短静止时长（秒）
    "smart_sampling": True,                         # 抽帧是否跳过静止段
    "static_dominant_ratio": 0.95,                  # 静止占比超此值→降级文字+1帧代表帧
}


def _load_raw_config() -> Dict[str, Any]:
    """读取 config.json 原始内容;任何异常都返回空字典，不阻断主流程"""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception as e:
        print(f"⚠️ [media_reader] 读取配置失败，使用默认值: {e}")
        return {}


def get_media_config() -> Dict[str, Any]:
    """
    媒体参数统一读取入口

    数据来源优先级:config.json 的 tool_output 节 > 本模块 MEDIA_DEFAULTS 兜底
    :return: 已补全全部默认键的媒体参数字典
    """
    cfg = dict(MEDIA_DEFAULTS)
    raw = _load_raw_config()
    tool_output = raw.get("tool_output") or {}
    for key in MEDIA_DEFAULTS.keys():
        value = tool_output.get(key)
        if value is not None and value != "":
            cfg[key] = value
    return cfg


# ==================== 请求级媒体登记表 ====================
# 用途:工具层读图/抽帧成功后登记像素，消息构造层一次性取用后清空（避免跨轮泄漏）
# 结构:[{"kind": "image" | "video_frame", "path": 文件路径, "b64": base64像素, "meta": 元信息}, ...]
_MEDIA_REGISTRY: List[Dict[str, Any]] = []


def register_media(kind: str, path: str, b64: str, meta: Optional[Dict[str, Any]] = None) -> bool:
    """
    登记一个媒体项（图片 / 视频帧）

    :param kind: 类型，"image" 或 "video_frame"
    :param path: 媒体文件路径（用于文字说明）
    :param b64: base64 像素数据;为空表示只拿到元信息（第三级兜底），不登记
    :param meta: 元信息字典（尺寸/格式/是否压缩等）
    :return: 是否登记成功
    """
    if not b64:
        return False
    _MEDIA_REGISTRY.append({
        "kind": kind,
        "path": path,
        "b64": b64,
        "meta": meta or {},
    })
    return True


def take_media() -> List[Dict[str, Any]]:
    """
    取出当前请求登记的全部媒体项，并清空登记表

    :return: 媒体项列表（可能为空列表，调用方需判空跳过）
    """
    global _MEDIA_REGISTRY
    items = list(_MEDIA_REGISTRY)
    _MEDIA_REGISTRY = []
    return items


def clear_media() -> None:
    """强制清空登记表（异常兜底使用;正常流程由 take_media 完成清空）"""
    global _MEDIA_REGISTRY
    _MEDIA_REGISTRY = []


def peek_media_count() -> int:
    """只读查询当前登记数量，供测试与日志使用（不改变登记表状态）"""
    return len(_MEDIA_REGISTRY)


# ==================== 图片三级降级转码 ====================

# PIL 打不开的真实缺口:heic/heif（需 pillow-heif）、avif（需 pillow-avif-plugin）、svg（无解码器）、相机 RAW（需 rawpy）
UNSUPPORTED_HINT = (
    "该图片格式 PIL 无法解码（常见于 heic/heif、avif、svg、相机 RAW），"
    "建议先转换为 PNG/JPG 后再读取"
)


def _prepare_image(image_path: str, max_edge: int) -> Tuple[Image.Image, Dict[str, Any]]:
    """
    图片预处理:解码 + 第一级像素级缩放（永不截断像素，只做等比缩放）

    :param image_path: 图片文件路径
    :param max_edge: 长边像素上限
    :return: (缩放后的图像副本, 元信息字典)
    :raises FileNotFoundError: 文件不存在
    :raises ValueError: 解码失败（格式不支持或文件损坏）
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图片文件不存在: {image_path}")

    orig_bytes = os.path.getsize(image_path)
    meta: Dict[str, Any] = {
        "path": image_path,
        "original_size_mb": round(orig_bytes / (1024 * 1024), 3),
        "compressed": False,
        "degrade_level": 0,   # 0=未降级 1=像素级 2=质量级 3=兜底只返元信息
        "degrade_reason": "",
    }

    try:
        with Image.open(image_path) as img:
            img.load()
            src_format = (img.format or "JPEG").upper()
            src_width, src_height = img.size
            meta["format"] = src_format.lower()
            meta["width"], meta["height"] = src_width, src_height
            work = img.copy()
    except Exception as e:
        raise ValueError(f"图片解码失败:{UNSUPPORTED_HINT}｜路径: {image_path}｜原因: {e}")

    # 第一级:像素级缩放（仅长边超限时触发，按像素比例等比，绝不拉伸变形）
    long_edge = max(src_width, src_height)
    if long_edge > max_edge:
        scale = max_edge / float(long_edge)
        new_size = (max(1, int(src_width * scale)), max(1, int(src_height * scale)))
        work = work.resize(new_size, Image.Resampling.LANCZOS)
        meta["compressed"] = True
        meta["degrade_level"] = 1
        meta["resized_to"] = f"{new_size[0]}x{new_size[1]}"

    return work, meta


def media_image_to_base64(
    image_path: str,
    max_edge: Optional[int] = None,
    max_size_mb: Optional[float] = None,
    quality_steps: Optional[List[int]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    图片三级降级转码（read_media 图片分支的唯一入口）

    第一级（像素级）:长边超 media_image_max_edge 时等比缩放（见 _prepare_image）
    第二级（质量级）:缩放后体积仍超 media_image_max_size_mb 时，按 quality_steps 逐档降质，卡进上限即停
    第三级（兜底）:仍超限则返回空像素 + 元信息与超限原因（不载入像素，永不 OOM、永不爆 token）

    :param image_path: 图片文件路径
    :param max_edge: 长边上限，默认取配置 media_image_max_edge
    :param max_size_mb: 单图体积上限（MB），默认取配置 media_image_max_size_mb
    :param quality_steps: JPEG 质量档位列表，默认取配置 media_image_quality_steps
    :return: (base64 字符串或空串, 元信息字典;空串表示已降级为纯元信息)
    :raises FileNotFoundError: 文件不存在
    :raises ValueError: 解码或编码失败（格式不支持）
    """
    cfg = get_media_config()
    if max_edge is None:
        max_edge = int(cfg.get("media_image_max_edge", 1568))
    if max_size_mb is None:
        max_size_mb = float(cfg.get("media_image_max_size_mb", 1.0))
    if not quality_steps:
        quality_steps = list(cfg.get("media_image_quality_steps") or [85, 75, 60, 45])

    work, meta = _prepare_image(image_path, max_edge)
    limit_bytes = int(max_size_mb * 1024 * 1024)
    has_alpha = work.mode in ("RGBA", "LA", "P")

    def _encode(fmt: str, quality: Optional[int] = None) -> bytes:
        """按指定格式编码到内存;JPEG 走有损质量档，PNG 走无损优化"""
        buf = io.BytesIO()
        if fmt == "png":
            work.save(buf, format="PNG", optimize=True)
        else:
            work.convert("RGB").save(buf, format="JPEG", quality=int(quality or 85), optimize=True)
        return buf.getvalue()

    # 初始尝试:带透明通道保留 PNG 无损;其余走 JPEG 首档质量
    try:
        if has_alpha:
            best_bytes, best_format = _encode("png"), "png"
        else:
            best_bytes, best_format = _encode("jpeg", quality_steps[0]), "jpeg"
    except Exception as e:
        raise ValueError(f"图片编码失败:{UNSUPPORTED_HINT}｜路径: {image_path}｜原因: {e}")

    # 第二级:体积超限 → 转 JPEG 按质量档逐档降，达标即停
    if len(best_bytes) > limit_bytes:
        for q in quality_steps:
            candidate = _encode("jpeg", q)
            best_bytes, best_format = candidate, "jpeg"
            meta["compressed"] = True
            meta["degrade_level"] = max(int(meta.get("degrade_level", 0)), 2)
            if len(candidate) <= limit_bytes:
                meta["degrade_reason"] = f"体积超限，JPEG 质量降至 {q}"
                break
        else:
            meta["degrade_reason"] = f"体积超限，已降至最低质量档 {quality_steps[-1]}"

    # 第三级:兜底——仍超限则只返元信息，不载入像素
    if len(best_bytes) > limit_bytes:
        meta["final_size_mb"] = round(len(best_bytes) / (1024 * 1024), 3)
        meta["degrade_level"] = 3
        meta["degrade_reason"] = (
            f"图片过大:缩放+降质后仍 {meta['final_size_mb']}MB，"
            f"超过单图上限 {max_size_mb}MB；已仅返回元信息，可先压缩或裁剪后再读取"
        )
        return "", meta

    meta["final_size_mb"] = round(len(best_bytes) / (1024 * 1024), 3)
    meta["mime"] = "image/png" if best_format == "png" else "image/jpeg"
    return base64.b64encode(best_bytes).decode("utf-8"), meta


# ==================== 视频接口（阶段B 实现，本阶段仅占位） ====================

# 视频扩展名集合（一级粗分流，仅做路由用途;真实判定以 ffprobe 探测成功为准）
VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".mkv", ".avi", ".flv", ".wmv", ".webm", ".m4v",
    ".ts", ".m2ts", ".mpg", ".mpeg", ".3gp", ".vob", ".asf", ".ogv", ".rmvb",
}

# ffmpeg/ffprobe 探测缓存（None=尚未探测;空串=探测失败;其他=可执行文件绝对路径）
_FFMPEG_CACHED: Optional[str] = None
_FFPROBE_CACHED: Optional[str] = None


def find_ffmpeg(binary: str = "ffmpeg") -> Optional[str]:
    """
    探测 ffmpeg / ffprobe 可执行文件（结果进程内缓存，避免重复探测）

    探测顺序（与项目打包资源约定对齐）:
        1. 项目内置 bin 目录:打包环境=EXE同级/bin，开发环境=项目根/bin
        2. 系统 PATH

    :param binary: "ffmpeg" 或 "ffprobe"
    :return: 可执行文件绝对路径;未找到返回 None（调用方必须给出明确文字提示，禁止静默失败）
    """
    global _FFMPEG_CACHED, _FFPROBE_CACHED
    cached = _FFMPEG_CACHED if binary == "ffmpeg" else _FFPROBE_CACHED
    if cached is not None:
        return cached or None

    import shutil as _shutil
    exe_name = binary + (".exe" if os.name == "nt" else "")
    root = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else BASE_DIR
    builtin_path = os.path.join(root, "bin", exe_name)

    if os.path.isfile(builtin_path):
        result = builtin_path
    else:
        result = _shutil.which(binary) or ""

    if binary == "ffmpeg":
        _FFMPEG_CACHED = result
    else:
        _FFPROBE_CACHED = result
    return result or None


def _get_cmd_timeout() -> int:
    """复用 tool_output.exec_cmd_timeout 作为 ffmpeg/ffprobe 调用超时（秒）；兜底 60"""
    raw = _load_raw_config()
    to = raw.get("tool_output") or {}
    try:
        t = int(to.get("exec_cmd_timeout") or 0)
    except (TypeError, ValueError):
        t = 0
    return t if t > 0 else 60


def _parse_time_spec(spec: Any) -> Tuple[float, str]:
    """
    解析时间参数:支持纯秒数（"90" / 90）、分:秒（"01:30"）、时:分:秒（"1:30:00"）

    :return: (秒数 float, 错误信息;成功时错误信息为空串)
    """
    if spec is None or spec == "":
        return 0.0, ""
    if isinstance(spec, bool):
        return 0.0, f"时间参数非法:{spec}"
    if isinstance(spec, (int, float)):
        if spec < 0:
            return 0.0, f"时间参数不能为负数:{spec}"
        return float(spec), ""
    s = str(spec).strip()
    if not s:
        return 0.0, ""
    # 纯秒数
    try:
        val = float(s)
        if val < 0:
            return 0.0, f"时间参数不能为负数:{s}"
        return val, ""
    except ValueError:
        pass
    # 分:秒 或 时:分:秒
    parts = s.split(":")
    if len(parts) not in (2, 3):
        return 0.0, f"时间参数格式不支持:{s}（应为 90 或 01:30 或 1:30:00）"
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return 0.0, f"时间参数格式不支持:{s}（应为 90 或 01:30 或 1:30:00）"
    if any(n < 0 for n in nums):
        return 0.0, f"时间参数不能为负数:{s}"
    total = nums[0] * 60 + nums[1] if len(nums) == 2 else nums[0] * 3600 + nums[1] * 60 + nums[2]
    return total, ""


def _run_ffprobe(ffprobe_path: str, video_path: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    调用 ffprobe 探测视频元信息（时长 / 分辨率 / 帧率 / 编码）

    :return: (信息字典 或 None, 错误文字;成功时错误文字为空串)
    """
    import subprocess as _sp
    cmd = [
        ffprobe_path, "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,duration,codec_name",
        "-show_entries", "format=duration,size,format_name",
        "-of", "json",
        video_path,
    ]
    try:
        proc = _sp.run(cmd, capture_output=True, timeout=_get_cmd_timeout())
    except _sp.TimeoutExpired:
        return None, "ffprobe 探测超时（视频可能过大或损坏）"
    except Exception as e:
        return None, f"ffprobe 调用失败:{e}"
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode("utf-8", "replace").strip()[:200]
        return None, f"ffprobe 探测失败:{err or '未知原因'}"
    try:
        data = json.loads((proc.stdout or b"").decode("utf-8", "replace") or "{}")
    except Exception as e:
        return None, f"ffprobe 输出解析失败:{e}"
    streams = data.get("streams") or []
    if not streams:
        return None, "未找到视频流（可能不是视频文件或文件损坏）"
    st = streams[0] or {}
    fmt = data.get("format") or {}

    def _f(v: Any) -> float:
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    duration = _f(st.get("duration")) or _f(fmt.get("duration"))
    fps_raw = str(st.get("r_frame_rate") or "0/1")
    try:
        n_s, d_s = fps_raw.split("/")
        fps = float(n_s) / float(d_s) if float(d_s) else 0.0
    except Exception:
        fps = 0.0
    meta = {
        "width": int(st.get("width") or 0),
        "height": int(st.get("height") or 0),
        "fps": round(fps, 3),
        "duration": round(duration, 3),
        "codec": str(st.get("codec_name") or ""),
        "format": str(fmt.get("format_name") or ""),
        "size_mb": round(_f(fmt.get("size")) / (1024 * 1024), 3),
    }
    return meta, ""


def _scan_static_segments(ffmpeg_path: str, video_path: str, start_sec: float, duration_sec: float) -> Dict[str, Any]:
    """
    停滞段扫描:每秒取 1 帧、缩至 64×64 灰度、numpy 向量化 MAD 帧差判静止

    :return: {"ok","message","static_segments","active_segments","static_ratio","scanned_seconds","frame_count"}
    """
    empty = {"ok": False, "message": "", "static_segments": [], "active_segments": [],
             "static_ratio": 0.0, "scanned_seconds": 0.0, "frame_count": 0}
    try:
        import numpy as _np
    except ImportError:
        r = dict(empty)
        r["message"] = "numpy 未安装，停滞段分析不可用（可 pip install numpy 后重试）"
        return r

    import subprocess as _sp
    cfg = get_media_config()
    scan_fps = float(cfg.get("static_scan_fps", 1.0)) or 1.0
    mad_threshold = float(cfg.get("static_mad_threshold", 2.0))
    min_duration = float(cfg.get("static_min_duration", 3.0))

    # -ss / -t 前置到 -i 之前:只解目标段，绝不全片解码
    cmd = [
        ffmpeg_path, "-v", "error", "-nostdin",
        "-ss", f"{max(0.0, start_sec):.3f}",
        "-t", f"{max(0.01, duration_sec):.3f}",
        "-i", video_path,
        "-vf", f"fps={scan_fps},scale=64:64,format=gray",
        "-f", "rawvideo", "-pix_fmt", "gray",
        "-",
    ]
    try:
        proc = _sp.run(cmd, capture_output=True, timeout=_get_cmd_timeout())
    except _sp.TimeoutExpired:
        r = dict(empty)
        r["message"] = "停滞段扫描超时"
        return r
    except Exception as e:
        r = dict(empty)
        r["message"] = f"停滞段扫描调用失败:{e}"
        return r
    if proc.returncode != 0:
        r = dict(empty)
        err = (proc.stderr or b"").decode("utf-8", "replace").strip()[:200]
        r["message"] = f"ffmpeg 扫描失败:{err or '未知原因'}"
        return r

    raw = proc.stdout or b""
    frame_size = 64 * 64
    n = len(raw) // frame_size
    if n < 2:
        return {"ok": True, "message": "", "static_segments": [],
                "active_segments": [{"start": 0.0, "end": round(duration_sec, 3)}],
                "static_ratio": 0.0, "scanned_seconds": round(duration_sec, 3),
                "frame_count": int(n)}

    arr = _np.frombuffer(raw[: n * frame_size], dtype=_np.uint8).reshape(n, frame_size).astype(_np.float32)
    diffs = _np.abs(arr[1:] - arr[:-1]).mean(axis=1)

    step = 1.0 / scan_fps
    static_segs: List[Dict[str, Any]] = []
    active_segs: List[Dict[str, Any]] = []

    # 静止判定:相似边 → 连续区间法
    # 逐帧判定（第 i 帧与前帧相似即算静止）会丢掉区间首帧，1fps 采样下 3s 静止段被削成 2s，
    # 恰好被 min_duration 过滤 → 实测静止段全部漏报。改为把"相似的相邻帧对"聚成连续区间，
    # 帧索引区间 [a, b] 对应时间 [a*step, (b+1)*step]，首尾帧不再丢失。
    similar = (diffs < mad_threshold).astype(_np.int8) if len(diffs) else _np.zeros(0, dtype=_np.int8)
    pad = _np.concatenate([_np.zeros(1, dtype=_np.int8), similar, _np.zeros(1, dtype=_np.int8)])
    edges = _np.where(_np.diff(pad) != 0)[0]
    static_ranges: List[Tuple[float, float]] = []
    for k in range(0, max(0, len(edges) - 1), 2):
        s = int(edges[k]) * step
        e = min((int(edges[k + 1]) + 1) * step, duration_sec)
        if e - s >= min_duration:
            static_ranges.append((s, e))

    # 静止区间之外的部分归入活动段（抽帧落点只取活动段，避开静止画面）
    cursor = 0.0
    for s, e in static_ranges:
        if s - cursor > 1e-6:
            active_segs.append({"start": round(cursor, 2), "end": round(s, 2)})
        static_segs.append({"start": round(s, 2), "end": round(e, 2), "duration": round(e - s, 2)})
        cursor = e
    if duration_sec - cursor > 1e-6:
        active_segs.append({"start": round(cursor, 2), "end": round(duration_sec, 2)})

    static_total = sum(x["duration"] for x in static_segs)
    ratio = (static_total / duration_sec) if duration_sec > 0 else 0.0
    return {
        "ok": True, "message": "",
        "static_segments": static_segs,
        "active_segments": active_segs,
        "static_ratio": round(min(1.0, ratio), 3),
        "scanned_seconds": round(duration_sec, 3),
        "frame_count": int(n),
    }


def _extract_frame_b64(ffmpeg_path: str, video_path: str, timestamp: float,
                       max_edge: int, max_kb: int, quality_steps: List[int]) -> Tuple[str, Dict[str, Any]]:
    """
    抽取单帧 → 三级降级（缩放 → 降质 → 兜底）；临时文件用后即删

    :return: (base64 或空串, 元信息字典;空串表示该帧不可用)
    """
    import subprocess as _sp
    import tempfile as _tf
    tmp_fd, tmp_path = _tf.mkstemp(suffix=".png", prefix="vframe_")
    os.close(tmp_fd)
    try:
        # -ss 前置到 -i 之前:快速定位，只解该帧附近
        cmd = [
            ffmpeg_path, "-v", "error", "-nostdin", "-y",
            "-ss", f"{max(0.0, timestamp):.3f}",
            "-i", video_path,
            "-frames:v", "1",
            tmp_path,
        ]
        try:
            proc = _sp.run(cmd, capture_output=True, timeout=_get_cmd_timeout())
        except _sp.TimeoutExpired:
            return "", {"ok": False, "reason": f"抽帧超时 @ {timestamp:.2f}s"}
        if proc.returncode != 0 or not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
            err = (proc.stderr or b"").decode("utf-8", "replace").strip()[:150]
            return "", {"ok": False, "reason": f"抽帧失败 @ {timestamp:.2f}s: {err or '空输出'}"}
        # 复用图片三级降级（video_frame_max_kb 折算为 MB）
        b64, meta = media_image_to_base64(
            tmp_path,
            max_edge=max_edge,
            max_size_mb=max_kb / 1024.0,
            quality_steps=quality_steps,
        )
        meta["timestamp"] = round(timestamp, 2)
        if not b64:
            meta["ok"] = False
            meta["reason"] = meta.get("degrade_reason") or "单帧降级后仍超限"
        else:
            meta["ok"] = True
        return b64, meta
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def _sample_from_active(active_segments: List[Dict[str, Any]], start_sec: float,
                        window_sec: float, interval: float, max_frames: int) -> List[float]:
    """在活动段内按 interval 抽样，每段至少 1 帧，总帧数 ≤ max_frames（保留首尾）"""
    picks: List[float] = []
    for seg in active_segments:
        s = float(seg.get("start", 0.0))
        e = float(seg.get("end", window_sec))
        if e <= s:
            continue
        seg_len = e - s
        n_in = max(1, int(seg_len // interval))
        # 按 n_in 等分该段、每份中点取样:段内分布均匀，n_in=1 时正好落段中点。
        # 原实现 rel = s + i*interval + interval/2 在 interval > seg_len 时首帧会越界贴段尾，
        # 代表性弱（实测活动段 3-7s、interval=10 时落点 6.95 贴尾，非段中点 5.0）。
        slot = seg_len / float(n_in)
        for i in range(n_in):
            rel = s + (i + 0.5) * slot
            if rel >= e:
                rel = max(s, e - 0.05)
            picks.append(start_sec + rel)
    picks = sorted({round(p, 3) for p in picks})
    if len(picks) > max_frames:
        if max_frames <= 1:
            picks = [picks[len(picks) // 2]]
        else:
            step = (len(picks) - 1) / float(max_frames - 1)
            idxs = sorted({int(round(i * step)) for i in range(max_frames)})
            picks = [picks[k] for k in idxs if 0 <= k < len(picks)]
    return picks


def probe_video(video_path: str) -> Dict[str, Any]:
    """
    视频探测（阶段B 填实;本阶段为占位实现，返回明确文字，不做任何 ffmpeg 调用）

    :param video_path: 视频文件路径
    :return: {"ok": bool, "message": str, "meta": dict}
    """
    if not os.path.exists(video_path):
        return {"ok": False, "message": f"视频文件不存在: {video_path}", "meta": {}}

    ffprobe = find_ffmpeg("ffprobe")
    if ffprobe is None:
        return {
            "ok": False,
            "message": (
                "未检测到 ffprobe，视频信息读取不可用。"
                "请将 ffprobe 放入项目 bin 目录或加入系统 PATH 后重试"
            ),
            "meta": {},
        }

    meta, err = _run_ffprobe(ffprobe, video_path)
    if meta is None:
        return {"ok": False, "message": err or "ffprobe 探测失败", "meta": {}}
    return {"ok": True, "message": "", "meta": meta}


def extract_video_frames(
    video_path: str,
    start: Optional[str] = None,
    duration: Optional[float] = None,
) -> Dict[str, Any]:
    """
    视频抽帧（阶段B 填实;本阶段为占位实现，返回明确文字，不做任何 ffmpeg 调用）

    阶段B 实现要点（详见执行步骤文件第六章 B4）:
        - 五道闸门:时间窗 → 抽帧间隔 → 最大帧数硬顶8 → 单帧上限 → 总量2MB
        - 停滞段分析:每秒取1帧缩至64x64灰度，帧差 MAD<阈值 且持续≥N秒 → 判为静止段
        - 智能抽帧:帧落点只取活动段，每段至少1帧;静止占比超阈值 → 降级为文字报告+1帧
        - 定位参数前置（-ss 放在 -i 之前）只解目标段，绝不全片解码

    :param video_path: 视频文件路径
    :param start: 起始时间，支持 "90" / "01:30" / "1:30:00"
    :param duration: 读取时长（秒），为空则用配置 video_window_seconds
    :return: {"ok": bool, "message": str, "frames": list, "report": str}
    """
    if not os.path.exists(video_path):
        return {"ok": False, "message": f"视频文件不存在: {video_path}", "frames": [], "report": ""}

    ffmpeg = find_ffmpeg("ffmpeg")
    if ffmpeg is None:
        return {
            "ok": False,
            "message": (
                "未检测到 ffmpeg，视频帧读取不可用。"
                "请将 ffmpeg 放入项目 bin 目录或加入系统 PATH 后重试"
            ),
            "frames": [],
            "report": "",
        }
    ffprobe = find_ffmpeg("ffprobe")
    if ffprobe is None:
        return {
            "ok": False,
            "message": (
                "未检测到 ffprobe，视频信息读取不可用。"
                "请将 ffprobe 放入项目 bin 目录或加入系统 PATH 后重试"
            ),
            "frames": [],
            "report": "",
        }

    cfg = get_media_config()

    # 1. 探测视频元信息
    meta, err = _run_ffprobe(ffprobe, video_path)
    if meta is None:
        return {"ok": False, "message": err or "ffprobe 探测失败", "frames": [], "report": ""}

    video_dur = float(meta.get("duration") or 0.0)

    # 2. 时间窗解析（纯秒 / 分:秒 / 时:分:秒）
    start_sec, e1 = _parse_time_spec(start)
    if e1:
        return {"ok": False, "message": e1, "frames": [], "report": ""}
    dur_val, e2 = _parse_time_spec(duration)
    if e2:
        return {"ok": False, "message": e2, "frames": [], "report": ""}
    default_window = float(cfg.get("video_window_seconds", 60))
    window_sec = dur_val if (duration not in (None, "") and dur_val > 0) else default_window
    if video_dur > 0 and start_sec >= video_dur:
        return {"ok": False,
                "message": f"起始时间 {start_sec:.1f}s 超出视频总时长 {video_dur:.1f}s",
                "frames": [], "report": ""}
    if video_dur > 0:
        window_sec = min(window_sec, max(0.0, video_dur - start_sec))
    if window_sec <= 0:
        window_sec = default_window

    # 3. 停滞段扫描（失败不阻断，退化全窗口活动）
    scan = _scan_static_segments(ffmpeg, video_path, start_sec, window_sec)
    if scan.get("ok"):
        static_ratio = float(scan.get("static_ratio", 0.0))
        static_segments = scan.get("static_segments", []) or []
        active_segments = scan.get("active_segments", []) or [{"start": 0.0, "end": window_sec}]
        scan_message = ""
    else:
        static_ratio = 0.0
        static_segments = []
        active_segments = [{"start": 0.0, "end": window_sec}]
        scan_message = str(scan.get("message") or "")

    # 4. 五道闸门 + 抽帧落点选择
    smart = bool(cfg.get("smart_sampling", True))
    max_frames = int(cfg.get("video_max_frames", 8)) or 8
    interval = float(cfg.get("video_frame_interval", 10)) or 10.0
    dominant = float(cfg.get("static_dominant_ratio", 0.95))

    is_static_content = smart and static_ratio >= dominant
    if is_static_content:
        # 静态内容:降级为文字报告 + 单帧代表帧（取窗口中点）
        timestamps = [start_sec + window_sec / 2.0]
    elif smart and static_segments:
        # 智能抽帧:帧落点只取活动段，每段至少 1 帧
        timestamps = _sample_from_active(active_segments, start_sec, window_sec, interval, max_frames)
    else:
        # 全窗口等距抽样
        n = max(1, min(max_frames, int(window_sec / interval) or 1))
        step = window_sec / n
        timestamps = [start_sec + step * (i + 0.5) for i in range(n)]
    if not timestamps:
        timestamps = [start_sec + min(window_sec / 2.0, 1.0)]

    # 5. 逐帧抽取 + 三级降级 + 总量红线
    frame_max_edge = int(cfg.get("video_frame_max_edge", 1024))
    frame_max_kb = int(cfg.get("video_frame_max_kb", 200))
    quality_steps = list(cfg.get("media_image_quality_steps") or [85, 75, 60, 45])
    total_max_mb = float(cfg.get("video_total_max_mb", 2.0))
    total_limit = int(total_max_mb * 1024 * 1024)

    frames: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    total_bytes = 0
    for ts in timestamps:
        b64, fmeta = _extract_frame_b64(ffmpeg, video_path, ts, frame_max_edge, frame_max_kb, quality_steps)
        if not b64:
            skipped.append({"timestamp": round(ts, 2), "reason": fmeta.get("reason", "抽帧失败")})
            continue
        est = len(b64) * 3 // 4  # base64 → 原始字节估算
        if frames and total_bytes + est > total_limit:
            skipped.append({"timestamp": round(ts, 2), "reason": "帧总量超红线，已丢弃后续帧"})
            continue
        total_bytes += est
        frames.append({"b64": b64, "meta": fmeta, "timestamp": round(ts, 2)})

    if not frames:
        msg = "抽帧全部失败或超限，未获得可用帧"
        if scan_message:
            msg += f"；{scan_message}"
        return {"ok": False, "message": msg, "frames": [], "report": ""}

    # 6. 登记为「视频帧」类型（供消息构造层补插 user 多模态消息）
    for fr in frames:
        register_media("video_frame", video_path, fr["b64"],
                       {**fr["meta"], "timestamp": fr["timestamp"]})

    # 7. 生成文字报告（含静止段与帧时间戳）
    lines = [
        f"视频: {os.path.basename(video_path)}",
        f"分辨率: {meta.get('width')}x{meta.get('height')}｜帧率: {meta.get('fps')}｜时长: {meta.get('duration')}s",
        f"读取窗口: 起点 {start_sec:.2f}s，时长 {window_sec:.2f}s",
    ]
    if scan.get("ok"):
        if static_segments:
            segs_txt = "；".join([f"{s['start']}-{s['end']}s({s['duration']}s)" for s in static_segments])
            lines.append(f"静止段: {segs_txt}")
        else:
            lines.append("静止段: 无")
        lines.append(f"静止占比: {static_ratio * 100:.1f}%")
    elif scan_message:
        lines.append(f"停滞扫描未完成: {scan_message}")
    if is_static_content:
        lines.append("判定: 静态内容（静止占比超阈值），已降级为单帧代表帧")
    lines.append(f"实抽帧数: {len(frames)}，时间戳(s): {[f['timestamp'] for f in frames]}")
    if skipped:
        lines.append(f"跳过帧: {skipped}")
    report = "\n".join(lines)

    return {"ok": True, "message": report, "frames": frames, "report": report}


# 模块对外导出清单（供 api_server / orchestrator 统一引用）
__all__ = [
    "get_media_config",
    "register_media",
    "take_media",
    "clear_media",
    "peek_media_count",
    "media_image_to_base64",
    "probe_video",
    "extract_video_frames",
    "find_ffmpeg",
    "VIDEO_EXTENSIONS",
    "MEDIA_DEFAULTS",
]