# -*- coding: utf-8 -*-
"""
background_task_manager.py —— 后台任务管理器（长命令后台任务机制 · 第2层，P1）

职责:
    接管 exec_cmd 在等待窗口内未跑完、被"自动提升"的命令进程:
      - 不终止进程，登记为后台任务继续运行，对话当轮立即释放；
      - 守护线程轮询进程状态，自然结束/硬超时/手动取消三态收尾；
      - 结束后推送 SSE 事件（P2 卡片消费），并把结果放入按会话的待读队列，
        供下一轮 chat() 开始时 drain_pending 自动回灌给模型；
      - 提供 query / cancel / read_logs / list_session 供 AI 工具与 HTTP 接口调用。

设计约束:
    - 零对 api_server 的硬导入（避免循环导入）；SSE 推送通过 set_sse_pusher 注入回调；
    - 任务进程由 command_runner.start_command 创建，本管理器只持有句柄、不重建进程；
    - 独立守护线程持有任务生命周期，与聊天请求线程解耦——新对话的停止信号
      （CHAT_STOP_SIGNALS）只作用于聊天线程，不会误杀后台任务；
    - 终态任务保留 TTL 后清理，注册表不无限膨胀。

状态机:
    background_running ──自然结束 rc==0──> success
                      ──自然结束 rc!=0──> failed
                      ──用户 cancel─────> cancelled
                      ──硬超时到点──────> timeout_killed
"""

import os
import time
import threading
import datetime

import command_runner

# ---- 默认阈值（P1 先内置；P2 再下沉 config.json 的 bg_task 节点 + 设置页）----
DEFAULT_HARD_TIMEOUT = 1800      # 单任务最大运行秒数（30 分钟），到点递归杀树
DEFAULT_TTL_SECONDS = 60 * 60    # 终态任务在注册表保留时长（60 分钟）
DEFAULT_POLL_INTERVAL = 2        # 守护线程轮询间隔（秒）
DEFAULT_MAX_CONCURRENT = 5       # 同一会话允许同时后台运行的任务上限
TAIL_LINES = 200                 # 收尾/回灌默认读取的日志尾部行数


def _now_text():
    """人类可读时间戳（日志/文案用）"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class BackgroundTaskManager:
    """后台任务注册表 + 单一守护监控线程（进程内单例）"""

    def __init__(self):
        self._tasks = {}                       # task_id -> 任务字典
        self._pending = {}                     # session_id -> [已完成任务字典, ...] 待回灌
        self._lock = threading.RLock()
        self._sse_pusher = None                # 注入的 push_sse_message(session_id, payload) 回调
        self._monitor = None
        self._started = False

    # ---------- 生命周期 ----------

    def start(self):
        """启动唯一守护监控线程（幂等）"""
        with self._lock:
            if self._started:
                return
            self._started = True
            self._monitor = threading.Thread(
                target=self._monitor_loop, name="bg-task-monitor", daemon=True)
            self._monitor.start()

    def set_sse_pusher(self, pusher):
        """注入 SSE 推送回调，签名 pusher(session_id, payload:dict)"""
        self._sse_pusher = pusher

    def shutdown(self):
        """进程退出兜底:递归终止所有仍在运行的后台任务（atexit 调用）"""
        with self._lock:
            running = [t for t in self._tasks.values()
                       if t["status"] == "background_running"]
        for t in running:
            try:
                command_runner.terminate_tree(t["handle"])
            except Exception:
                pass

    # ---------- 注册（提升）----------

    def _gen_task_id(self):
        return "bg_%s_%06d" % (time.strftime("%Y%m%d_%H%M%S"),
                               int.from_bytes(os.urandom(3), "big") % 1000000)

    def register_and_promote(self, handle, command, session_id):
        """
        将一个已在运行、等待窗口内未结束的 CommandHandle 登记为后台任务。
        返回 task_id；同会话运行数超限时返回 None（调用方回退到 P0 硬杀）。
        """
        self.start()
        with self._lock:
            running_count = sum(
                1 for t in self._tasks.values()
                if t["session_id"] == session_id and t["status"] == "background_running")
            if running_count >= DEFAULT_MAX_CONCURRENT:
                return None
            task_id = self._gen_task_id()
            task = {
                "task_id": task_id,
                "command": command,
                "session_id": session_id,
                "status": "background_running",
                "start_time": handle.started_at,
                "end_time": None,
                "returncode": None,
                "log_path": handle.log_path,
                "tail": command_runner.read_tail(handle, TAIL_LINES),
                "handle": handle,
            }
            self._tasks[task_id] = task
        self._push(session_id, {"type": "bg_task_promoted", "task_id": task_id,
                                "command": command,
                                "start_time": task["start_time"]})
        return task_id

    # ---------- 查询 / 日志 / 列表 ----------

    def _get_owned(self, task_id, session_id):
        t = self._tasks.get(task_id)
        if t and t["session_id"] == session_id:
            return t
        return None

    def query(self, task_id, session_id):
        """返回任务快照字典；不存在/不属本会话返回 None"""
        with self._lock:
            t = self._get_owned(task_id, session_id)
            if not t:
                return None
            return {k: v for k, v in t.items() if k != "handle"}

    def read_logs(self, task_id, session_id, lines=200):
        with self._lock:
            t = self._get_owned(task_id, session_id)
            if not t:
                return None
            handle = t["handle"]
        return command_runner.read_tail(handle, max(1, min(int(lines), 2000)))

    def list_session(self, session_id):
        """列出某会话全部任务（不含进程句柄），按开始时间升序"""
        with self._lock:
            items = [dict({k: v for k, v in t.items() if k != "handle"})
                     for t in self._tasks.values() if t["session_id"] == session_id]
        items.sort(key=lambda x: x["start_time"])
        return items
    # ---------- 手动取消 ----------

    def cancel(self, task_id, session_id):
        """
        递归终止指定后台任务，返回任务快照；任务不存在/不属本会话返回 None。
        若任务已处于终态，不重复处理，直接返回快照。
        """
        with self._lock:
            t = self._get_owned(task_id, session_id)
            if not t:
                return None
            if t["status"] != "background_running":
                return {k: v for k, v in t.items() if k != "handle"}
            t["status"] = "cancelled"
            t["end_time"] = time.time()
            handle = t["handle"]

        # 杀树在锁外执行（taskkill 可能耗时），避免阻塞监控线程
        command_runner.terminate_tree(handle)
        with self._lock:
            t["returncode"] = handle.proc.returncode
            t["tail"] = command_runner.read_tail(handle, TAIL_LINES)
            snap = {k: v for k, v in t.items() if k != "handle"}
            self._enqueue_locked(snap)
        self._push(t["session_id"], {"type": "bg_task_cancelled",
                                     "task_id": task_id})
        return snap

    # ---------- 跨轮回灌 ----------

    def _enqueue_locked(self, snap):
        """调用方必须持有 self._lock"""
        q = self._pending.setdefault(snap["session_id"], [])
        # 同一任务只回灌一次（监控线程与 cancel 可能竞争）
        if not any(x["task_id"] == snap["task_id"] for x in q):
            q.append(snap)

    def drain_pending(self, session_id):
        """取出并清空某会话的全部已完成任务快照，按开始时间升序返回"""
        with self._lock:
            q = self._pending.pop(session_id, None)
        return sorted(q, key=lambda x: x["start_time"]) if q else []

    # ---------- 监控线程 ----------

    def _monitor_loop(self):
        """2 秒轮询:自然结束收尾、硬超时杀树、终态 TTL 清理"""
        while True:
            time.sleep(DEFAULT_POLL_INTERVAL)
            try:
                self._scan()
            except Exception:
                # 监控线程绝不能因单个任务异常退出
                pass

    def _scan(self):
        now = time.time()
        to_finish = []
        to_timeout = []
        to_clean = []
        with self._lock:
            for tid, t in self._tasks.items():
                st = t["status"]
                if st == "background_running":
                    if now - t["start_time"] >= DEFAULT_HARD_TIMEOUT:
                        to_timeout.append(t)
                    else:
                        to_finish.append(t)
                elif st in ("success", "failed", "cancelled", "timeout_killed"):
                    if t["end_time"] and now - t["end_time"] >= DEFAULT_TTL_SECONDS:
                        to_clean.append(tid)
            for tid in to_clean:
                self._tasks.pop(tid, None)

        for t in to_finish:
            rc = t["handle"].proc.poll()
            if rc is not None:
                self._finalize_natural(t, rc)

        for t in to_timeout:
            self._finalize_timeout(t)

    def _finalize_natural(self, t, rc):
        with self._lock:
            if t["status"] != "background_running":
                return
            t["status"] = "success" if rc == 0 else "failed"
            t["end_time"] = time.time()
            t["returncode"] = rc
            # 自然结束不经过 terminate_tree:显式关闭日志句柄并按上限截断，避免句柄泄漏
            command_runner.finalize_finished(t["handle"])
            t["tail"] = command_runner.read_tail(t["handle"], TAIL_LINES)
            snap = {k: v for k, v in t.items() if k != "handle"}
            self._enqueue_locked(snap)
        ev = "bg_task_done"
        self._push(t["session_id"], {"type": ev, "task_id": t["task_id"],
                                     "returncode": rc, "status": t["status"]})

    def _finalize_timeout(self, t):
        with self._lock:
            if t["status"] != "background_running":
                return
            t["status"] = "timeout_killed"
            t["end_time"] = time.time()
            handle = t["handle"]
        command_runner.terminate_tree(handle)
        with self._lock:
            t["returncode"] = handle.proc.returncode
            t["tail"] = command_runner.read_tail(handle, TAIL_LINES)
            snap = {k: v for k, v in t.items() if k != "handle"}
            self._enqueue_locked(snap)
        self._push(t["session_id"], {"type": "bg_task_timeout_killed",
                                     "task_id": t["task_id"]})

    # ---------- SSE 注入 ----------

    def _push(self, session_id, payload):
        pusher = self._sse_pusher
        if pusher:
            try:
                pusher(session_id, payload)
            except Exception:
                pass

    # ---------- 文案构造（供工具分支复用，严格对齐详细方案 §6.5）----------

    @staticmethod
    def _fmt_duration(seconds):
        seconds = int(seconds)
        if seconds < 60:
            return "%d秒" % seconds
        return "%d分%02d秒" % (seconds // 60, seconds % 60)

    def build_promote_text(self, task_id, command, timeout):
        """提升当轮返回给模型的结构化文案（§6.5 ①-⑤行为约束 + 两个工具用法）"""
        return (
            "🟢 命令已自动提升为后台运行（等待窗口内未结束，未被终止）\n"
            "任务ID:{tid}\n"
            "命令:{cmd}\n"
            "提升时间:{ts}\n"
            "\n"
            "【重要】这条命令仍在后台真实执行，请严格遵守:\n"
            "① 不要重复执行同一条命令；\n"
            "② 当轮不要等待结果，直接告知用户命令已转后台继续跑，可继续处理其他对话；\n"
            "③ 后续轮次如需结果，调用 query_background_task 工具（参数 task_id 传上述任务ID）查询状态与日志尾部；\n"
            "④ 若用户要求停止，调用 cancel_background_task 工具（参数 task_id）递归终止整棵进程树；\n"
            "⑤ 自然结束后，系统会在下一轮对话开始时把真实退出码、耗时、日志尾部自动告知你（完成回灌），无需盲目轮询。"
        ).format(tid=task_id, cmd=command, ts=_now_text())

    def build_query_text(self, snap, tail):
        """query_background_task 返回给模型的文案，按状态如实区分"""
        st = snap["status"]
        cmd = snap["command"]
        tid = snap["task_id"]
        if st == "background_running":
            elapsed = self._fmt_duration(time.time() - snap["start_time"])
            return (
                "🔵 后台任务仍在运行\n"
                "任务ID:{tid}\n命令:{cmd}\n已运行:{elapsed}\n"
                "日志尾部:\n{tail}\n"
                "请告知用户任务仍在执行；如需停止可调用 cancel_background_task。"
            ).format(tid=tid, cmd=cmd, elapsed=elapsed, tail=tail or "(暂无输出)")

        duration = self._fmt_duration(snap["end_time"] - snap["start_time"]) \
            if snap["end_time"] else "未知"
        head = {
            "success": "✅ 后台任务已成功结束（真实结果，可继续后续步骤）",
            "failed": "❌ 后台任务执行失败（退出码≠0，禁止编造成功，请据日志排查）",
            "cancelled": "🛑 后台任务已被用户手动终止（整棵进程树递归结束）",
            "timeout_killed": "⏱️ 后台任务超过硬超时{ht}秒，已被系统递归终止整棵进程树".format(
                ht=DEFAULT_HARD_TIMEOUT),
        }.get(st, "❓ 后台任务状态未知:{0}".format(st))
        return (
            "{head}\n"
            "任务ID:{tid}\n命令:{cmd}\n退出码:{rc}\n总耗时:{dur}\n"
            "日志尾部（最后{n}行）:\n{tail}\n"
            "完整日志路径:{log}"
        ).format(head=head, tid=tid, cmd=cmd, rc=snap["returncode"],
                 dur=duration, tail=tail or "(无输出)", n=TAIL_LINES,
                 log=snap["log_path"])

    def build_cancel_text(self, snap, tail):
        """cancel_background_task 返回文案"""
        if not snap:
            return None
        return (
            "🛑 已递归终止后台任务整棵进程树（用户手动终止）\n"
            "任务ID:{tid}\n命令:{cmd}\n终止前退出码:{rc}\n"
            "终止前日志尾部:\n{tail}"
        ).format(tid=snap["task_id"], cmd=snap["command"],
                 rc=snap["returncode"], tail=tail or "(无输出)")

    def build_pending_notice(self, snap):
        """下一轮 chat() 开始时注入给模型的完成通知（user 角色）"""
        st = snap["status"]
        duration = self._fmt_duration(snap["end_time"] - snap["start_time"]) \
            if snap["end_time"] else "无需"
        verdict = {
            "success": "✅ 成功结束（退出码0）——这是真实结果，可据此继续后续步骤",
            "failed": "❌ 执行失败（退出码≠0）——禁止编造成功，请据日志排查后决定是否重试",
            "cancelled": "🛑 已被用户手动终止",
            "timeout_killed": "⏱️ 超过硬超时{0}秒被系统递归终止".format(DEFAULT_HARD_TIMEOUT),
        }.get(st, "❓ 状态未知")
        return (
            "【后台任务完成回灌】你之前提升到后台的一条命令已结束:\n"
            "任务ID:{tid}\n命令:{cmd}\n状态:{verdict}\n"
            "总耗时:{dur}\n日志尾部（最后{n}行）:\n{tail}\n"
            "请结合该真实结果向用户汇报或继续任务；若为失败请如实说明，不要假装成功。"
        ).format(tid=snap["task_id"], cmd=snap["command"], verdict=verdict,
                 dur=duration, tail=snap["tail"] or "(无输出)", n=TAIL_LINES)


# 进程内单例
background_task_manager = BackgroundTaskManager()

import atexit
atexit.register(background_task_manager.shutdown)