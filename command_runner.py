# -*- coding: utf-8 -*-
"""
command_runner.py —— 进程树命令执行器（长命令后台任务机制 · 第1层，P0）

功能:
    对上层屏蔽 Windows 进程树与管道细节，统一提供"启动—等待—查日志—终止"四个原语，
    根治 subprocess.run(shell=True, timeout=) 在 Windows 下的两类缺陷:
      1. 超时后库内 kill() 只杀直接子进程 cmd.exe，bat 派生的孙进程（pip/python 等）
         仍持有继承来的 stdout/stderr 管道写句柄，导致库内部无超时 communicate() 永久阻塞；
      2. 未重定向 stdin，bat 中 pause / set /p 在无控制台的打包环境永久等待输入。

方案:
    - Popen + CREATE_NEW_PROCESS_GROUP，每个任务独立进程组；
    - stdin=DEVNULL（pause/set /p 立即收到 EOF 跳过）；
    - stdout/stderr 合并直接写任务专属日志文件，不走管道继承，从根上消除管道阻塞；
    - wait_or_promote 仅用 proc.poll() 非阻塞轮询，永不调用无超时 communicate()；
    - terminate_tree 用 taskkill /F /T /PID 递归终止整棵进程树，且幂等可重复调用。

被调用方:
    api_server.py 的 exec_cmd 工具分支、/api/task/submit 的 run_command 分支；
    P1 阶段起被 background_task_manager.py 复用。

零项目内依赖，可直接 `python -c "import command_runner"` 独立自检。
"""

import os
import sys
import time
import signal
import subprocess
from dataclasses import dataclass
from typing import Optional

# Windows:新建独立进程组标志，终止时只按本任务根 PID 递归 /T，不误杀其他任务
CREATE_NEW_PROCESS_GROUP = 0x00000200

# 任务日志根目录（复用项目现有 tool_outputs 目录约定）
# 路径策略与 api_server.py 完全一致:
#   打包(frozen)环境 → exe 同级目录/tool_outputs/bg_tasks（用户数据不进 _internal，卸载升级不丢失）
#   源码开发环境     → 脚本所在目录/tool_outputs/bg_tasks
if getattr(sys, "frozen", False):
    _LOG_BASE = os.path.dirname(sys.executable)
else:
    _LOG_BASE = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(_LOG_BASE, "tool_outputs", "bg_tasks")

# 默认单任务日志上限（2MB），收尾时超限只保留尾部，防止安装日志撑爆磁盘
DEFAULT_LOG_MAX_BYTES = 2 * 1024 * 1024


@dataclass
class CommandHandle:
    """单个命令进程的句柄与元数据（上层不直接操作 proc 字段以外的进程细节）"""
    task_id: str
    cmd: str
    cwd: Optional[str]
    log_path: str
    proc: subprocess.Popen
    started_at: float
    log_file: object = None
    log_max_bytes: int = DEFAULT_LOG_MAX_BYTES
    status: str = "running"  # running / finished / terminated


def _ensure_log_dir():
    """确保日志目录存在（首次启动自动创建）"""
    os.makedirs(LOG_DIR, exist_ok=True)


def start_command(cmd, cwd=None, task_id=None, log_max_bytes=DEFAULT_LOG_MAX_BYTES):
    """
    启动命令（原语1:启动）。

    参数:
        cmd: 命令字符串（与现状一致，shell=True 执行）
        cwd: 工作目录，None 表示继承
        task_id: 任务ID，仅用于日志文件命名；不传则生成 tmp_ 前缀临时ID
        log_max_bytes: 单日志上限字节数
    返回:
        CommandHandle
    异常:
        启动失败（如 FileNotFoundError）向上抛出，由调用方转成工具错误结果
    """
    _ensure_log_dir()
    if not task_id:
        task_id = "tmp_%s_%06d" % (time.strftime("%Y%m%d%H%M%S"),
                                   int.from_bytes(os.urandom(3), "big") % 1000000)
    log_path = os.path.join(LOG_DIR, task_id + ".log")
    log_file = open(log_path, "wb")

    popen_kwargs = dict(
        shell=True,
        stdin=subprocess.DEVNULL,      # 根治 pause / set /p 输入型挂死
        stdout=log_file,               # 输出直接落盘，孙进程不继承管道
        stderr=subprocess.STDOUT,      # 合并标准错误，顺序与控制台一致
        cwd=cwd,
    )
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = CREATE_NEW_PROCESS_GROUP
    else:
        # 非 Windows:独立会话，终止时可整组 kill（预留跨平台）
        popen_kwargs["start_new_session"] = True

    try:
        proc = subprocess.Popen(cmd, **popen_kwargs)
    except Exception:
        log_file.close()
        raise

    return CommandHandle(
        task_id=task_id, cmd=cmd, cwd=cwd, log_path=log_path,
        proc=proc, started_at=time.time(), log_file=log_file,
        log_max_bytes=log_max_bytes,
    )


def _decode_output(raw):
    """日志字节解码:优先 UTF-8，失败回退 GBK（沿用项目现有双解码经验）"""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("gbk", errors="replace")


def read_tail(handle, lines=200):
    """
    原语3:读取日志尾部 N 行（供 AI 工具结果与前端卡片展示）。
    日志上限 2MB，整体读取可接受；进程未结束时也可随时调用。
    """
    try:
        if handle.log_file and not handle.log_file.closed:
            handle.log_file.flush()
        with open(handle.log_path, "rb") as f:
            raw = f.read()
        text = _decode_output(raw)
        tail = text.splitlines()[-lines:]
        return "\n".join(tail)
    except FileNotFoundError:
        return ""
    except Exception as e:
        return "[读取日志失败] %s" % e


def wait_or_promote(handle, seconds, poll_interval=0.2):
    """
    原语2:同步等待窗口。

    仅用 proc.poll() 非阻塞轮询，严禁调用无超时 communicate()。
    - 窗口内结束:{"finished": True, "returncode": rc, "tail": 日志尾部}
    - 窗口到仍存活:{"finished": False, "pid": pid, "log_path": ..., "tail": ...}
      进程保持存活、句柄由上层（P0=终止收尾 / P1=任务管理器接管）继续持有。
    """
    deadline = time.time() + max(0, seconds)
    while True:
        rc = handle.proc.poll()
        if rc is not None:
            handle.status = "finished"
            _close_log(handle)
            _truncate_if_oversize(handle)
            return {"finished": True, "returncode": rc,
                    "tail": read_tail(handle)}
        if time.time() >= deadline:
            return {"finished": False, "pid": handle.proc.pid,
                    "log_path": handle.log_path, "tail": read_tail(handle)}
        time.sleep(poll_interval)


def terminate_tree(handle):
    """
    原语4:递归终止整棵进程树，幂等（重复调用/进程已退出均安全）。

    Windows:taskkill /F /T /PID 连子带孙全部结束，再 wait 兜底回收僵尸句柄；
    非 Windows:os.killpg 整组 SIGKILL。
    返回 {"terminated": 本次是否执行了终止, "returncode": 退出码或None}
    """
    proc = handle.proc
    if proc.poll() is not None:
        # 进程已自然结束，无需终止
        _close_log(handle)
        return {"terminated": False, "returncode": proc.returncode}

    pid = proc.pid
    try:
        if sys.platform == "win32":
            # /F 强制 /T 递归终止子树；输出吞掉（中文系统返回 GBK，无需解析）
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           capture_output=True, timeout=15)
        else:
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            proc.wait(timeout=10)
        except Exception:
            # taskkill 已递归杀树，wait 超时仅兜底 kill 根进程
            try:
                proc.kill()
                proc.wait(timeout=5)
            except Exception:
                pass
    finally:
        handle.status = "terminated"
        _close_log(handle)
        _truncate_if_oversize(handle)

    return {"terminated": True, "returncode": proc.returncode}


def _close_log(handle):
    """关闭日志文件句柄（幂等），确保缓冲区落盘"""
    try:
        if handle.log_file and not handle.log_file.closed:
            handle.log_file.flush()
            handle.log_file.close()
    except Exception:
        pass


def _truncate_if_oversize(handle):
    """日志超过上限时只保留尾部并重写，防止长安装日志撑爆磁盘"""
    try:
        if not os.path.exists(handle.log_path):
            return
        size = os.path.getsize(handle.log_path)
        if size <= handle.log_max_bytes:
            return
        with open(handle.log_path, "rb") as f:
            f.seek(max(0, size - handle.log_max_bytes))
            kept = f.read()
        text = _decode_output(kept)
        # 从第一个完整行开始保留，避免截断半行乱码
        nl = text.find("\n")
        if nl != -1:
            text = text[nl + 1:]
        with open(handle.log_path, "wb") as f:
            f.write(("[日志超过 %d 字节，仅保留尾部]\n" % handle.log_max_bytes)
                    .encode("utf-8"))
            f.write(text.encode("utf-8", errors="replace"))
    except Exception:
        # 日志截断失败不影响主流程
        pass