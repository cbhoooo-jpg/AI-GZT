# -*- coding: utf-8 -*-
"""任务编排器（阶段4）—— 6 态状态机 + 自适应角色池 + 会话隔离 + 三条硬终止。

设计口径（来自《前端重构与多模型交互改造方案》§4.4 / §9）:
  1. 6 态:0 待派发 → 1 开发中 → 2 待审查 → 3 审查中 → 4 待裁决 → 5 已闭环/已驳回;
  2. 三条硬终止:① 回炉 ≤2 次;② 单任务总超时 30 分钟;③ 审查不可用 → 主控降级自审(显式标注);
  3. 会话隔离:主会话 sessions/main.json 永久保留;一任务一次级会话 tasks/T-XXX/dev.json + review.json;
  4. 标记头:派发 [主控派发|目标:X|任务 #T-XXX|轮次 N/M];回报 [模型回报|来自:X|任务 #T-XXX|第 N 轮];
  5. 三档压缩:L1 最近 3 条原文 / L2 第 4~10 条压单行 / L3 更早不注入;用户插话永不压缩;
  6. 落盘文件永不截断:裁剪只作用于「注入视图」,不改落盘文件。

打包安全:顶层零重依赖导入（openai / httpx 由 model_registry 内部延迟导入）;
调用入口统一走 llm_client.chat_with（自带信号量 + 重试 + 超时）。
"""
import os
import re
import sys
import json
import time
import threading
from typing import Dict, Any, Optional, List, Callable

if getattr(sys, "frozen", False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SESSIONS_DIR = os.path.join(_BASE_DIR, "sessions")
TASKS_DIR = os.path.join(SESSIONS_DIR, "tasks")
MAIN_SESSION_NAME = "main.json"

# ---------------- 状态定义 ----------------
# 【2026-10-13 瘦身】6 态精简为 3 态（保留数值不动，兼容历史 meta）
STATE_DISPATCH_PENDING = 0
STATE_DEV_RUNNING = 1
STATE_CLOSED = 5  # 数值沿用 5，历史 meta 里的 state=5 仍可正确识别为"已闭环"

STATE_NAMES = {
    STATE_DISPATCH_PENDING: "待派发",
    STATE_DEV_RUNNING: "开发中",
    STATE_CLOSED: "已闭环",
}
TERMINAL_STATES = ("已闭环", "已驳回", "已中止", "超时中止")

# 硬终止默认参数（可由 models_config.json 顶层 runtime 节覆盖,不硬编码）
_DEFAULT_LIMITS = {"max_rework": 2, "task_timeout_sec": 1800, "sub_session_rounds": 6}

# ---------------- 标记头模板（P0:主模型区分"用户说的"与"模型说的"的唯一依据） ----------------
DISPATCH_HEADER_TPL = "[主控派发|目标:{target}|任务 #{task_id}|轮次 {round_no}/{round_total}]"
REPORT_HEADER_TPL = "[模型回报|来自:{sender}|任务 #{task_id}|第 {round_no} 轮]"
USER_HEADER_TPL = "[用户消息|会话:{session}|任务 #{task_id}]"

# ---------------- 三档压缩参数 ----------------
L1_RAW_COUNT = 3
L2_SINGLE_COUNT = 10

# ---------------- 模块级状态 ----------------
_IO_LOCK = threading.RLock()
_TASK_LOCK = threading.RLock()
_SSE_PUSHER: Optional[Callable[[str, dict], None]] = None
_SSE_LOCK = threading.Lock()
_PROBE_CACHE: Dict[int, Dict[str, Any]] = {}
_PROBE_TTL = 300  # 探针结果缓存秒数

# ============================ 会话层（原子写 + 单写锁） ============================

def _ensure_dirs() -> None:
    """确保 sessions/ 与 sessions/tasks/ 存在"""
    try:
        os.makedirs(TASKS_DIR, exist_ok=True)
    except Exception as e:
        print(f"[Orchestrator] 创建会话目录失败: {e}")

def _safe_name(name: Any) -> str:
    """防路径穿越:仅保留字母/数字/下划线/短横线"""
    keep = [ch for ch in str(name or "") if ch.isalnum() or ch in ("_", "-")]
    return "".join(keep) or "default"

def _atomic_write_json(path: str, data: Any) -> None:
    """原子写:先写 .tmp 再 os.replace,避免写入中断导致文件截断"""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

class SessionWriter:
    """会话文件读写:单例写锁（RLock）+ 原子写;读也加锁"""

    _lock = _IO_LOCK

    @classmethod
    def read(cls, path: str, default: Any = None) -> Any:
        with cls._lock:
            if not os.path.exists(path):
                return default
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[Orchestrator] 会话读取失败 {path}: {e}")
                return default

    @classmethod
    def write(cls, path: str, data: Any) -> None:
        with cls._lock:
            _atomic_write_json(path, data)

    @classmethod
    def append(cls, path: str, msg: dict) -> dict:
        """追加一条消息（读-改-写在同一把锁内,覆盖"追加 + 触发唤醒",落盘文件永不截断）"""
        with cls._lock:
            data = cls.read(path, default=None)
            if not isinstance(data, dict):
                data = {"messages": []}
            if not isinstance(data.get("messages"), list):
                data["messages"] = []
            item = dict(msg or {})
            item.setdefault("ts", time.time())
            data["messages"].append(item)
            data["updated_at"] = item["ts"]
            _atomic_write_json(path, data)
            return data

def main_session_path() -> str:
    """主会话文件（永久保留,禁止清空/截断）"""
    return os.path.join(SESSIONS_DIR, MAIN_SESSION_NAME)

def task_dir(task_id: str) -> str:
    """单个任务的次级会话目录"""
    return os.path.join(TASKS_DIR, _safe_name(task_id))

def task_file(task_id: str, kind: str) -> str:
    """次级会话文件（dev / review / meta）"""
    return os.path.join(task_dir(task_id), f"{_safe_name(kind)}.json")
# ---------------- 次级记忆持久化（对齐主模型 latest_chat_history_{项目}.json） ----------------

def _clean_name(name: Any) -> str:
    """文件名净化:与 api_server.get_project_history_file 同源同正则"""
    keep = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5_-]', "_", str(name or ""))
    return keep or "default"


def secondary_history_path(slot: int, project_name: str = "") -> str:
    """次级记忆持久化文件:{BASE}/latest_secondary_history_{项目}_{角色}.json

    - 命名对齐主模型 latest_chat_history_{项目}.json;含角色维度,避免角色串台;
    - 项目名净化与 api_server.get_project_history_file 同源;
    - 角色名取该槽位 persona_name,缺失回退 slot{N}。
    """
    proj = _clean_name(project_name or "default")
    role = ""
    try:
        from model_registry import get_slot_config
        cfg = get_slot_config(int(slot)) or {}
        role = str(cfg.get("persona_name", "") or "").strip()
    except Exception:
        role = ""
    if not role:
        role = f"slot{int(slot)}"
    return os.path.join(_BASE_DIR, f"latest_secondary_history_{proj}_{_clean_name(role)}.json")


def _strip_naked_tool_json(text: str) -> str:
    """【M1·根因修复·对齐主模型】剥离"无标记包裹的裸工具调用对象"文本块。

    背景:工具/插件模板会以「双下划线模板版本字段 + name + parameters」这种
    无中文标记的裸对象形态出现在模型输出里;现有净化只认「工具调用开始…结束」
    中文标记块 → 裸对象两头都抓不到,会被原样落盘、原样派发给次级对话。
    实现（2026-10-14 对齐主链路加固版，FIX-INTERRUPT-001-EXEC1）:
      ① 定位模板版本字段 → 向前取最近左花括号作为候选对象起点；
      ② 候选起点必须与字段同行且距离 ≤200 字符，跨行/过远一律视为正文引用 → 跳过不删；
      ③ 向后逐字符做括号配对（感知引号与反斜杠转义）；
      ④ 配对失败 → 跳过不删（旧实现此处从起点截到末尾，是"首轮之后内容全丢"的根因）；
      ⑤ 待删区间若跨轮次/工具结果边界（含「第N轮交互」或「工具执行结果」）→ 跳过不删；
      ⑥ 用 search_from 游标单调推进，跳过时不回头，避免死循环。
    最后收敛多余空行，避免历史里出现大片空白。
    本函数与 api_server.py 同名函数行为对齐（两文件互不 import 耦合）。
    """
    if not text:
        return text
    key = '"__template_version"'
    out = str(text)
    search_from = 0   # 搜索游标:跳过时不回头，避免死循环
    guard = 0
    while guard < 500:
        guard += 1
        pos = out.find(key, search_from)
        if pos < 0:
            break
        start = out.rfind("{", 0, pos)
        # 约束1:候选起点必须存在、与字段同行、且距离 ≤200 字符，否则视为正文引用 → 跳过不删
        if start < 0 or "\n" in out[start:pos] or (pos - start) > 200:
            search_from = pos + len(key)
            continue
        depth = 0
        in_str = False
        esc = False
        end = -1
        for i in range(start, len(out)):
            ch = out[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        # 约束2:配对失败 → 跳过不删（宁可留残留，绝不截断后续内容）
        if end < 0:
            search_from = pos + len(key)
            continue
        segment = out[start:end]
        # 约束3:待删区间跨轮次/工具结果边界 → 说明锚定到了正文，跳过不删
        if ("【第" in segment and "轮交互】" in segment) or "工具执行结果" in segment:
            search_from = pos + len(key)
            continue
        out = out[:start] + out[end:]
        search_from = start   # 删除成功后从删除点继续搜索后续残留
    while "\n\n\n" in out:
        out = out.replace("\n\n\n", "\n\n")
    return out.strip()
def _load_secondary_history(slot: int, project_name: str = "") -> List[dict]:
    """读次级记忆(越界/损坏静默返回 [],兼容 list 与 {"messages":[...]} 两种结构)"""
    path = secondary_history_path(slot, project_name)
    data = SessionWriter.read(path, default=None)
    if isinstance(data, list):
        return [m for m in data if isinstance(m, dict)]
    if isinstance(data, dict) and isinstance(data.get("messages"), list):
        return [m for m in data["messages"] if isinstance(m, dict)]
    return []


def _purify_secondary_text(text: str) -> str:
    """次级记忆落盘前净化（完全对齐主模型 api_server.py L2955-2996 的 9 条正则）

    - 触发时机:只在 _run_task 收尾拼装「用户问:…\n回答:…」落盘 content 前调用;
    - 当轮不剥离保证:当轮流式（ai_output_stream / ai_reasoning）完全不经过本函数,
      前端实时显示原样不受影响;只有落盘进记忆文件时才做净化;
    - 与主模型逐字同构:①轮次标记 ②工具调用原文块 ③空行收敛 ④裸工具JSON
      ⑤read_file 成功 ⑥read_file 失败 ⑦编辑/写入/创建/删除/重命名 ⑧RAG 检索 ⑨命令输出;
    - 目的:防止大文件、长命令、编辑内容撑爆模型上下文窗口（与主模型口径完全一致）。
    """
    if not text:
        return text
    import re
    out = str(text)
    # ① 去掉「第N轮交互 / AI输出:」轮次标记（只留正文,多轮之间自然换行）
    out = re.sub(r'【第\d+轮交互】\s*\n?AI输出[::]\s*', '', out)
    # ② 去掉工具调用原文块(写明"工具调用"字样的整块内容),工具执行结果摘要行仍保留
    out = re.sub(r'【工具调用[^\n]*】[\s\S]*?【工具调用[^\n]*】\s*', '', out)
    # ③ 收敛连续空行,避免历史里出现大片空白
    out = re.sub(r'\n{3,}', '\n\n', out).strip()
    # ④ 剥离"无标记包裹的裸工具调用对象"(模板版本字段形态)
    out = _strip_naked_tool_json(out)
    # ⑤ 读取文件成功 → 摘要(兼容全角/半角冒号,覆盖当前项目/全局/白名单/仓库根/全路径/跨目录)
    out = re.sub(
        r'🔹 指令\d+执行结果[::]✅ 读取(?:当前项目文件|全局文件|全局白名单文件|仓库根目录文件|文件)成功[::](.+?)\n[\s\S]*?(?=\n🔹 指令|\n【第|\Z)',
        r'🔹 执行结果:✅ 读取文件「\1」成功，完整内容已在对话中返回，可随时重新调用查看',
        out
    )
    # ⑥ 读取文件失败 → 摘要(替换长错误栈)
    out = re.sub(
        r'🔹 指令\d+执行结果[::]❌ 读取(?:当前项目文件|全局文件|全局白名单文件|仓库根目录文件|项目文件|仓库文件|文件)失败[::](.+?)\n[\s\S]*?(?=\n🔹 指令|\n【第|\Z)',
        r'🔹 执行结果:❌ 读取文件「\1」失败，可重新调用工具查看详细错误信息',
        out
    )
    # ⑦ 文件编辑/写入/创建/删除/重命名 → 摘要(避免大段 JSON/代码存入记忆)
    out = re.sub(
        r'🔹 指令\d+执行结果[::]✅ (?:edit_file|write_file|create_file|delete_file|rename_file)操作成功[::](.+?)\n[\s\S]*?(?=\n🔹 指令|\n【第|\Z)',
        r'🔹 执行结果:✅ \1操作成功，操作详情可查看操作日志',
        out
    )
    # ⑧ RAG 检索 → 摘要(避免大段检索结果占满记忆)
    out = re.sub(
        r'🔹 指令\d+执行结果[::]✅ 代码检索结果[::]\n[\s\S]*?(?=\n🔹 指令|\n【第|\Z)',
        r'🔹 执行结果:✅ 代码检索完成，匹配结果已在对话中返回，可随时重新检索',
        out
    )
    # ⑨ 命令执行 → 摘要(避免大段终端输出存入记忆)
    out = re.sub(
        r'🔹 指令\d+执行结果[::]✅ 命令执行成功[::]命令[::].+?标准输出[::][\s\S]*?(?=\n🔹 指令|\n【第|\Z)',
        r'🔹 执行结果:✅ 命令执行成功，输出结果已在对话中返回',
        out
    )
    return out


def strip_tool_result_blocks(text: str) -> str:
    """展示净化:剥离次级落盘串里的「工具执行结果:…」段（只给前端展示用，记忆文件保留完整串）

    - 触发场景:api_server 的 /api/orch/secondary_history 返回前调用（展示净化，非落盘净化）；
    - 与落盘解耦:本函数只读不改，_append_secondary_msg 落盘内容与 _purify_secondary_text 均不受影响；
    - 切分规则:逐行扫描，行首（去前导空白后）命中「工具执行结果:」→ 进入丢弃态，
      该行与后续"带前导空白"的续行（工具输出的多行结果）一并丢弃；
      遇到"非缩进且非空"的行（视为下一段 AI 正文）→ 退出丢弃态并保留该行；
    - 目的:前端只看到 AI 正文，不再把「工具执行结果:…」铺上屏（口径:拼接内容只进记忆文件）。
    """
    _t = str(text or "")
    if not _t or "工具执行结果:" not in _t:
        return _t
    _kept: List[str] = []
    _dropping = False
    for _line in _t.split("\n"):
        if _line.strip().startswith("工具执行结果:"):
            _dropping = True
            continue
        if _dropping:
            if _line.strip() and not _line[:1].isspace():
                _dropping = False
            else:
                continue
        _kept.append(_line)
    return "\n".join(_kept).strip()


def _append_secondary_msg(slot: int, project_name: str, content: str) -> None:
    """追加一条次级记忆(结构与主模型 latest_chat_history_{项目}.json 逐字同构)

    - 外层结构:纯数组 [{"content": str, "timestamp": 毫秒 int}],与主模型完全一致;
    - 条目粒度:1 条 = 1 轮(用户问 + 回答,必要时追加"工具执行结果:"段),不再拆成两条;
    - content 拼装由调用方负责(如 f"用户问:{ask}\\n回答:{answer}"),本函数只做落盘;
    - 条数上限 = max_chat_rounds(1 条 = 1 轮),与主模型口径一致;
    - 复用 SessionWriter 底座:单写锁(_IO_LOCK 为 RLock,read 可重入) + 原子写(_atomic_write_json)。
    - 兼容:文件内既有旧结构({"messages":[...]})时由 _load_secondary_history 归一读出,
      回写统一为新格式(纯数组),老条目靠回读侧兼容识别,不丢历史。
    """
    path = secondary_history_path(slot, project_name)
    rounds = 10
    try:
        from model_registry import get_slot_config
        cfg = get_slot_config(int(slot)) or {}
        rounds = int(cfg.get("max_chat_rounds", 0) or 0) or 10
    except Exception:
        rounds = 10
    with _IO_LOCK:
        msgs = _load_secondary_history(slot, project_name)
        item = {"content": str(content or ""), "timestamp": int(time.time() * 1000)}
        msgs.append(item)
        limit = max(1, int(rounds))
        if len(msgs) > limit:
            msgs = msgs[-limit:]
        _atomic_write_json(path, msgs)

# ============================ 角色池（自适应） ============================

def _limits() -> Dict[str, int]:
    """硬终止参数:runtime 节可覆盖（max_rework / task_timeout_sec / sub_session_rounds）"""
    result = dict(_DEFAULT_LIMITS)
    try:
        from model_registry import load_models_config
        runtime = (load_models_config() or {}).get("runtime") or {}
        if isinstance(runtime, dict):
            for k in list(result.keys()):
                v = runtime.get(k)
                if isinstance(v, int) and v >= 0:
                    result[k] = v
    except Exception as e:
        print(f"[Orchestrator] 读取 runtime 失败,用默认值: {e}")
    return result


# 任务目录清理默认参数（可由 tasks_config.json 覆盖,不硬编码）
_DEFAULT_TASKS_CONFIG = {
    "max_task_dirs": 100,
    "prune_on_create": True,
}

def _tasks_config() -> Dict[str, Any]:
    """任务目录清理参数:tasks_config.json 可覆盖（缺失走默认）

    【2026-10-13 新增】与 _limits() 同构:先 copy 默认值 → try 读文件 → 异常打印回退。
    按用户拍板 Q6:独立配置文件（与 memory_config.json 同级），前端可改。
    """
    result: Dict[str, Any] = dict(_DEFAULT_TASKS_CONFIG)
    try:
        cfg_path = os.path.join(_BASE_DIR, "tasks_config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f) or {}
            if isinstance(cfg, dict):
                v = cfg.get("max_task_dirs")
                if isinstance(v, int) and v > 0:
                    result["max_task_dirs"] = v
                v = cfg.get("prune_on_create")
                if isinstance(v, bool):
                    result["prune_on_create"] = v
    except Exception as e:
        print(f"[Orchestrator] 读取 tasks_config 失败,用默认值: {e}")
    return result


# 上下文截断默认参数（可由 config.json 的 orchestrator.context_limits 节覆盖,不硬编码）
_DEFAULT_CONTEXT_LIMITS = {
    "secondary_summary": 400,
    "review_dev_report": 12000,
    "judge_dev_report": 8000,
    "judge_review_opinion": 8000,
    "decide_dev_report": 8000,
}

def _context_limits() -> Dict[str, int]:
    """上下文截断参数:config.json 的 orchestrator.context_limits 节可覆盖（缺失走默认）"""
    result = dict(_DEFAULT_CONTEXT_LIMITS)
    try:
        cfg_path = os.path.join(_BASE_DIR, "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f) or {}
            section = (cfg.get("orchestrator") or {}).get("context_limits") or {}
            if isinstance(section, dict):
                for k in list(result.keys()):
                    v = section.get(k)
                    if isinstance(v, int) and v > 0:
                        result[k] = v
    except Exception as e:
        print(f"[Orchestrator] 读取 context_limits 失败,用默认值: {e}")
    return result


def probe_slot(slot: int, force: bool = False) -> tuple:
    """极短探针（不阻断主流程）:复用 chat_with,结果带 TTL 缓存,避免每次派发都烧 token"""
    now = time.time()
    cached = _PROBE_CACHE.get(int(slot))
    if cached and not force and (now - cached.get("ts", 0)) < _PROBE_TTL:
        return cached.get("ok", False), cached.get("msg", "")
    ok, msg = False, ""
    try:
        from llm_client import chat_with
        resp = chat_with(int(slot), [{"role": "user", "content": "ping"}],
                         temperature=0.0, max_tokens=64)
        try:
            content = resp["choices"][0]["message"]["content"] or ""
            reasoning = resp["choices"][0]["message"].get("reasoning_content", "") or ""
        except Exception:
            content = str(resp)[:100]
            reasoning = ""
        # 兼容推理型模型:max_tokens 16→64 给正式输出留空间;reasoning_content 非空也视为可用
        ok = bool(str(content).strip()) or bool(str(reasoning).strip())
        msg = "可用" if ok else "返回为空"
    except Exception as e:
        ok, msg = False, str(e)[:150]
    _PROBE_CACHE[int(slot)] = {"ok": ok, "msg": msg, "ts": now}
    return ok, msg

def build_role_pool(with_probe: bool = False) -> List[Dict[str, Any]]:
    """自适应角色池:api_url + model_name + api_key + persona_name 全非空即入池。

    代码不判断角色含义 → 由主控读清单自主分发（与"角色匹配自适应"口径一致）。
    """
    try:
        from model_registry import load_models_config
        data = load_models_config() or {}
    except Exception as e:
        print(f"[Orchestrator] 读取模型配置失败: {e}")
        return []
    pool: List[Dict[str, Any]] = []
    for m in data.get("models", []) or []:
        if not isinstance(m, dict):
            continue
        needed = ("api_url", "model_name", "api_key", "persona_name")
        if any(not str(m.get(k, "") or "").strip() for k in needed):
            continue
        try:
            slot_no = int(m.get("slot", 0) or 0)
        except (TypeError, ValueError):
            continue
        pool.append({
            "slot": slot_no,
            "display_name": str(m.get("display_name", "") or f"模型{slot_no}"),
            "model_name": str(m.get("model_name", "") or ""),
            "persona_name": str(m.get("persona_name", "") or ""),
            "available": True,
        })
    pool.sort(key=lambda x: x["slot"])
    if with_probe:
        for item in pool:
            ok, _msg = probe_slot(item["slot"])
            item["available"] = bool(ok)
    return pool

def match_role_slot(pool: List[Dict[str, Any]], keyword: str,
                    exclude: Optional[List[int]] = None) -> Optional[int]:
    """兜底:按人设名 / 显示名子串就近匹配（仅当主控未给或给错槽位时使用,不静默乱派）"""
    kw = str(keyword or "").strip()
    if not kw:
        return None
    skip = set(int(x) for x in (exclude or []))
    for item in pool:
        if item["slot"] in skip or not item.get("available", True):
            continue
        if kw in item["persona_name"] or kw in item["display_name"]:
            return int(item["slot"])
    return None

def pool_brief(pool: List[Dict[str, Any]]) -> str:
    """生成交给主控的《可用角色清单》文本"""
    if not pool:
        return "(空:无可用角色)"
    lines = []
    for item in pool:
        flag = "可用" if item.get("available", True) else "上次失败"
        lines.append(f"- 槽位{item['slot']} | {item['display_name']} | 人设:{item['persona_name']} | {flag}")
    return "\n".join(lines)

# ============================ 标记头与三档压缩 ============================

def dispatch_header(target: str, task_id: str, round_no: int, round_total: int) -> str:
    """派发标记头:目标槽位 + 任务号 + 轮次"""
    return DISPATCH_HEADER_TPL.format(target=target, task_id=task_id,
                                      round_no=round_no, round_total=round_total)

def report_header(sender: str, task_id: str, round_no: int) -> str:
    """回报标记头:来源 + 任务号 + 轮次"""
    return REPORT_HEADER_TPL.format(sender=sender, task_id=task_id, round_no=round_no)

def _l2_compress(msg: dict) -> str:
    """L2:中段消息压成单行摘要"""
    content = str(msg.get("content", "") or "")
    head = content.split("\n", 1)[0][:80]
    who = msg.get("header", "") or msg.get("role", "")
    return f"[历史摘要] {who} {head}".strip()

def build_main_context(session_id: str, task_id: str = "") -> List[dict]:
    """三档压缩后的「注入视图」（不改落盘文件;用户插话永不压缩）"""
    data = SessionWriter.read(main_session_path(), default={"messages": []})
    msgs = list((data or {}).get("messages") or []) if isinstance(data, dict) else []
    if not msgs:
        return []
    tail = msgs[-L2_SINGLE_COUNT:]
    head_set = set(id(x) for x in tail[-L1_RAW_COUNT:])
    view: List[dict] = []
    for m in tail:
        if not isinstance(m, dict):
            continue
        if id(m) in head_set:
            continue
        if m.get("role") == "user":
            view.append({"role": "user", "content": str(m.get("content", ""))})
        else:
            view.append({"role": "system", "content": _l2_compress(m)})
    for m in tail[-L1_RAW_COUNT:]:
        if not isinstance(m, dict):
            continue
        view.append({"role": m.get("role", "assistant"), "content": str(m.get("content", ""))})
    return view
# ============================ 状态机层（6 态 + 三条硬终止） ============================

def _task_meta_path(task_id: str) -> str:
    return task_file(task_id, "meta")

def _new_task_id() -> str:
    """按 tasks/ 现有目录生成 T-XXX 序号（单调递增，永不复用）

    【2026-10-13 编号机制改造·按用户拍板 Q5】:
      原算法「从 1 找最小空号」在目录出现空洞时会复用编号（同一 #T-XXX 指向过
      两个不同任务，日志/前端排障无法区分）；本次改为「扫描现存目录取 max + 1」，
      保证:
        - 编号单调递增，永不复用（删任意旧目录后新号仍向下走）；
        - 4 位编号（T-1000）自动兼容（f-string 的 :03d 是"至少 3 位"，非"截断到 3 位"）；
        - 整条链路（目录路径 / 消息头 / get_task / 反解 int(parts[1])）对编号长度零假设。
    """
    _ensure_dirs()
    max_seq = 0
    try:
        for name in os.listdir(TASKS_DIR):
            parts = str(name).split("-")
            if len(parts) == 2 and parts[0] == "T":
                try:
                    seq = int(parts[1])
                    if seq > max_seq:
                        max_seq = seq
                except (TypeError, ValueError):
                    continue
    except Exception:
        pass
    return f"T-{max_seq + 1:03d}"

def _prune_old_tasks() -> int:
    """惰性清理 sessions/tasks/ 目录（按用户拍板 Q1~Q4）

    - 上限:目录总数 > max_task_dirs 时触发（只删至上限）；
    - 只清终态:meta.state_name ∈ TERMINAL_STATES（"已闭环"/"已驳回"/"已中止"/"超时中止"）；
      **进行中任务永不清理**（硬约束 Q3）；
    - 排序:按 meta.created_at 升序（最旧优先删）；
    - 动作:shutil.rmtree 整个目录（不归档 —— Q2 拍板:档案=缓存，直接删）；
    - 保护:以下情形直接返回 0:
        ① prune_on_create=false（配置开关关闭）；
        ② 扫描目录失败；
        ③ 目录数 ≤ 上限（最常见路径）；
        ④ 全部为进行中（无法清则临时超限，等终态后回收）；
    - 返回:实际删除的目录数（仅用于日志打印，不参与逻辑）。
    """
    cfg = _tasks_config()
    if not cfg.get("prune_on_create", True):
        return 0
    limit = int(cfg.get("max_task_dirs", 100) or 100)
    if limit <= 0:
        return 0
    _ensure_dirs()
    terminal_items = []
    total = 0
    try:
        for name in os.listdir(TASKS_DIR):
            dir_path = os.path.join(TASKS_DIR, name)
            if not os.path.isdir(dir_path):
                continue
            total += 1
            meta = SessionWriter.read(os.path.join(dir_path, "meta.json"), default=None)
            if not isinstance(meta, dict):
                continue
            if meta.get("state_name") not in TERMINAL_STATES:
                continue
            try:
                ts = float(meta.get("created_at") or 0)
            except (TypeError, ValueError):
                ts = 0.0
            terminal_items.append((ts, str(name), dir_path))
    except Exception as e:
        print(f"[Orchestrator] 清理任务目录:扫描失败,跳过: {e}")
        return 0
    if total <= limit:
        return 0
    terminal_items.sort(key=lambda x: x[0])
    need = total - limit
    removed = 0
    for _ts, _name, _path in terminal_items:
        if removed >= need:
            break
        try:
            import shutil as _shutil
            _shutil.rmtree(_path, ignore_errors=True)
            removed += 1
            print(f"[Orchestrator] 任务目录清理:删除终态目录 {_name}（超过上限 {limit}）")
        except Exception as e:
            print(f"[Orchestrator] 任务目录清理:删除 {_name} 失败: {e}")
    return removed


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """读取任务 meta 快照"""
    meta = SessionWriter.read(_task_meta_path(task_id), default=None)
    return meta if isinstance(meta, dict) else None

def create_task(requirement: str, session_id: str = "default",
                project_name: str = "default") -> Dict[str, Any]:
    """建任务:落 meta + 空的 dev/review 次级会话,入 [0] 待派发

    - project_name（新增,可选）:任务归属项目名，次级对话按「项目 × 槽位」双维度隔离；
      不传 → 视为 default（向后兼容旧调用）；旧任务 meta 无此字段同样视为 default。
    """
    _ensure_dirs()
    limits = _limits()
    with _TASK_LOCK:
        # 【2026-10-13 新增】惰性清理:建任务时按 tasks_config.json 上限滚动删除最旧终态目录
        #   （用户拍板 Q4）；清理在编号分配之前，保证扫到的目录列表即为本次分配依据；
        #   同一把 _TASK_LOCK 内 → 与编号分配 + 落盘互斥，无并发窗口；
        #   双 try/except 保护:调用点包一层 + 函数内已包一层，清理永不影响建任务主流程。
        try:
            _prune_old_tasks()
        except Exception as e:
            print(f"[Orchestrator] 清理任务目录失败,不影响建任务: {e}")
        task_id = _new_task_id()
        now = time.time()
        meta: Dict[str, Any] = {
            "task_id": task_id,
            "session_id": _safe_name(session_id),
            "project_name": str(project_name or "default"),
            "requirement": str(requirement or ""),
            "state": STATE_DISPATCH_PENDING,
            "state_name": STATE_NAMES[STATE_DISPATCH_PENDING],
            # 【2026-10-13 D 项修正·回滚保留】以下两字段并非"只写不读":
            #   · rework_count → _push_state 内 SSE payload["rework"] + list_tasks 列表字段
            #   · degraded_review → _push_state 内 SSE payload["degraded"] + list_tasks 列表字段
            #   剃除会让前端静默失真（回炉数恒 0 / 降级恒 False），故回滚保留。
            "rework_count": 0,
            "degraded_review": False,
            "dev_slot": None,
            "created_at": now,
            "updated_at": now,
            "deadline_at": now + limits["task_timeout_sec"],
            "history": [{"ts": now, "state": STATE_NAMES[STATE_DISPATCH_PENDING], "note": "任务创建"}],
        }
        # 仅落 meta（状态机依赖）；dev/review 旧会话文件已废弃，不再生成，杜绝新旧双写
        SessionWriter.write(_task_meta_path(task_id), meta)
    _push_state(task_id, meta)
    return meta

def advance(task_id: str, state: int, note: str = "",
            state_name: Optional[str] = None, **extra) -> Dict[str, Any]:
    """统一流转入口:更新 state + 追加 history + SSE 推送"""
    with _TASK_LOCK:
        meta = get_task(task_id) or {"task_id": task_id, "session_id": "default", "history": []}
        meta["state"] = state
        meta["state_name"] = state_name or STATE_NAMES.get(state, str(state))
        meta["updated_at"] = time.time()
        for k, v in extra.items():
            meta[k] = v
        meta.setdefault("history", []).append({
            "ts": meta["updated_at"],
            "state": meta["state_name"],
            "note": str(note or ""),
        })
        # 【2026-10-13 瘦身】history 限长保留最近 20 条，防止任务 meta 无限增长（原"只写不读"的元凶）
        HISTORY_MAX = 20
        if len(meta["history"]) > HISTORY_MAX:
            meta["history"] = meta["history"][-HISTORY_MAX:]
        SessionWriter.write(_task_meta_path(task_id), meta)
    _push_state(task_id, meta)
    return meta

def finalize(task_id: str, name: str, note: str = "") -> Dict[str, Any]:
    """走终态:已闭环 / 已驳回 / 已中止 / 超时中止（state 统一记 5,state_name 区分）"""
    if name not in TERMINAL_STATES:
        name = "已中止"
    return advance(task_id, STATE_CLOSED, note=note,
                   state_name=name, terminal=True)

# ============================ SSE 推送（复用 background_task_manager 同构范式） ============================

def set_sse_pusher(pusher: Optional[Callable[[str, dict], None]]) -> None:
    """注入 SSE 回调,签名与 push_sse_message(session_id, data) 同构"""
    global _SSE_PUSHER
    with _SSE_LOCK:
        _SSE_PUSHER = pusher


# 主控上下文追加器（由 api_server 启动时注入，避免 orchestrator 反向 import api_server 造成循环依赖）
_MAIN_INJECTOR: Optional[Callable[[str, str], None]] = None


def set_main_injector(injector: Optional[Callable[[str, str], None]]) -> None:
    """注入「主控上下文追加器」回调（签名:injector(text, sender)）

    - orchestrator 不 import api_server（避免循环依赖），改用回调注入（同 set_sse_pusher 先例）;
    - api_server 注入后，次级 @主控 的内容会被追加到 latest_chat_history_{项目}.json，
      主控模型下一轮 load_global_history 即可读到（真正送给主模型，而非只到前端）。
    """
    global _MAIN_INJECTOR
    with _SSE_LOCK:
        _MAIN_INJECTOR = injector


# 主控唤醒器（由 api_server 启动时注入；次级 @主控 后触发一次主控模型调用）
# 【2026-10-13 新增】按用户口径 S1:走 /api/chat 主链路自调用，与人手对话上下文天然同源。
_MAIN_WAKER: Optional[Callable[[str, str, str], None]] = None


def set_main_waker(waker: Optional[Callable[[str, str, str], None]]) -> None:
    """注入「主控唤醒器」回调（签名:waker(text, sender, task_id)）

    - 与 set_main_injector 完全同构:orchestrator 不 import httpx/api_server，改用回调注入;
    - api_server 注入后，次级 @主控 将真正触发一次主控模型调用（走 /api/chat 主链路）;
    - 按用户口径:不设链路深度上限，防无限续接完全交给主控提示词判断;失败仅打印，不重试。
    """
    global _MAIN_WAKER
    with _SSE_LOCK:
        _MAIN_WAKER = waker


def _push_state(task_id: str, meta: Dict[str, Any]) -> None:
    """任务状态每次流转推一条;推送失败不影响主流程"""
    with _SSE_LOCK:
        pusher = _SSE_PUSHER
    if not pusher:
        return
    payload = {
        "type": "task_state_changed",
        "task_id": task_id,
        "state": meta.get("state_name", ""),
        "rework": meta.get("rework_count", 0),
        "degraded": bool(meta.get("degraded_review")),
        "terminal": bool(meta.get("terminal")) or meta.get("state_name") in TERMINAL_STATES,
    }
    try:
        pusher(meta.get("session_id", "default"), payload)
    except Exception as e:
        print(f"[Orchestrator] SSE 推送失败: {e}")

def push_secondary_summary(session_id: str, text: str) -> None:
    """次级状态摘要推送（方案 §4.6）"""
    with _SSE_LOCK:
        pusher = _SSE_PUSHER
    if not pusher or not text:
        return
    try:
        pusher(session_id or "default", {"type": "secondary_summary", "content": str(text)[:_context_limits()["secondary_summary"]]})
    except Exception as e:
        print(f"[Orchestrator] 次级摘要推送失败: {e}")

# push_to_main（次级→主控回流）已按用户口径移除:系统不再把次级输出搬回主对话,也不再冒充用户写主会话

def push_secondary_event(session_id: str, etype: str, content: str,
                         slot: Optional[int] = None,
                         project: str = "") -> None:
    """次级对话页业务事件推送（对齐 1.vue 的 dispatch / report type）

    - 派发 → type=dispatch；开发/审查回报 → type=report；
    - slot（B-2 新增,可选）:事件归属的次级槽位号,前端据此过滤本页事件（旧调用不传→向后兼容）；
    - 通道隔离（新增）:有 slot → 推 sec_{slot} 独立通道（与主控 default 物理隔离，杜绝串台）；
      etype=secondary_to_main（次级→主控通知）例外强制走 default，主控页才能显示「来自XX的消息」；
      无 slot 的旧调用 → 保持原 key（向后兼容，零回归）；
    - 推送失败只打印，绝不影响主流程。
    """
    with _SSE_LOCK:
        pusher = _SSE_PUSHER
    if not pusher:
        return
    payload: Dict[str, Any] = {"type": str(etype or "report"), "content": str(content or "")}
    if slot is not None:
        try:
            payload["slot"] = int(slot)
        except Exception:
            pass
    # 目标通道（Step 1 新增 + 方案C 项目维度）:次级事件走 sec_{slot}_{project} 独立分包。
    # 【方案C·根因修复·跨项目串台】原实现通道键仅为 sec_{slot}，项目A 与 项目B 物理上是同一条通道:
    #   项目A 派发 → 写入 SESSION_LAST_OUTPUT["sec_2"]；切到项目B → B 页连的仍是 sec_2
    #   → 后端把 A 的残留快照回放给 B 页 → 用户看到"两个项目的次级对话页面都显示同一内容"。
    #   现改为通道键 = sec_{slot}_{project}，与前端 URL `/api/chat/stream/sec_{slot}_{project}` 严格对应，
    #   项目 A 与 项目 B 物理上是两条独立通道 + 各自独立快照，串台从根上消除。
    #   项目名归一化:空值统一回 default，与前端 secProjectName() 的口径严格一致
    #   （前端 localStorage 无值时也返回 'default'，两端拼接出的通道键字符串完全相同）。
    _chan = session_id or "default"
    if str(etype or "") == "secondary_to_main":
        _chan = "default"
    elif slot is not None:
        try:
            _proj = str(project or "").strip() or "default"
            _chan = f"sec_{int(slot)}_{_proj}"
        except Exception:
            _chan = session_id or "default"
    try:
        pusher(_chan, payload)
    except Exception as e:
        print(f"[Orchestrator] 次级业务推送失败: {e}")


def push_secondary_to_main(session_id: str, sender: str, text: str, task_id: str = "",
                           slot: int = 0) -> None:
    """次级 → 主控通知（仅当次级输出里 @主控/@玲珑 时调用）

    - 【2026-10-13 头像接入】新增 slot 参数（可选，默认 0 = 旧调用零副作用）:
      前端 PageO0x2f.vue 的 senderIcon() 需按槽位切图（slot 2~9 → model_{slot}.png），
      而本函数原 payload 只带 sender（人设名），slot 5~9 人设名为空 → 无法反查，
      故在此透传真实槽位号，保证 8 张头像全部可用。
    - 条件触发:正文必须含 @主控 或主控人设名，否则直接返回（不打扰主模型）;
    - 做三件事:①推 secondary_to_main 事件（主对话页显示「来自XX的消息」）;
      ②追加写编排自身主会话（main_session_path，供编排内部回溯）;
      ③调用 api_server 注入的 main_waker，走 /api/chat 主链路自调用，
        把回报作为"一条用户提交"打进主控模型（与人手对话上下文天然同源）—— 这一步才真正唤醒主控;
    - 【2026-10-13 去重】原 main_injector 预写已删:它与唤醒时 /api/chat 的落盘功能重叠，
      会造成主控下轮读到双份回报，故只留唤醒一步。
    - 按用户口径:唤醒必须成功（失败即架构失效，只修复不留兜底）;不设深度上限，防无限续接交给主控提示词。
    """
    body = str(text or "").strip()
    if not body:
        return
    try:
        _pool = build_role_pool()
        _main = _main_slot(_pool)
        _names = ["主控"]
        for _it in (_pool or []):
            if _main is not None and int(_it.get("slot", 0) or 0) == int(_main):
                if str(_it.get("persona_name", "") or "").strip():
                    _names.append(str(_it.get("persona_name", "")).strip())
        _hit = any(("@" + _n) in body for _n in _names if _n)
    except Exception:
        _hit = False
    if not _hit:
        return
    payload = {"type": "secondary_to_main", "sender": str(sender or ""),
               "content": body, "task_id": str(task_id or ""),
               "slot": int(slot or 0)}
    with _SSE_LOCK:
        pusher = _SSE_PUSHER
    if pusher:
        try:
            pusher(session_id or "default", payload)
        except Exception as e:
            print(f"[Orchestrator] 次级→主控通知推送失败: {e}")
    try:
        SessionWriter.append(main_session_path(), {
            "role": "user",
            "header": f"[来自{sender}|任务 #{task_id}]",
            "content": body,
        })
    except Exception as e:
        print(f"[Orchestrator] 次级→主控通知写主会话失败: {e}")
    # ④ 【2026-10-13 新增】真正唤醒主控模型（唯一投递路径；旧 ③ injector 预写已删，避免重复落盘）:
    #    调用 api_server 注入的唤醒器，走 /api/chat 主链路自调用（与人手对话上下文天然同源）;
    #    按用户口径:唤醒必须成功（失败即架构失效，只修复不留兜底）;不设深度上限，回到主控提示词判断。
    try:
        waker = _MAIN_WAKER
    except NameError:
        waker = None
    if waker:
        try:
            waker(body, str(sender or ""), str(task_id or ""))
        except Exception as e:
            print(f"[Orchestrator] 次级→主控 唤醒主控模型失败: {e}")

# ============================ 模型调用与角色路由 ============================

def _call_model_ex(slot: int, messages: List[dict],
                   temperature: float = 0.5,
                   max_tokens: Optional[int] = None):
    """扩展调用入口:额外返回模型「真思考」（reasoning_content），与主控 api_server 同源同口径

    - 返回 (content, reasoning) 二元组；非推理型模型 reasoning 为空串（前端不渲染空思考气泡）;
    - 与 _call_model 共用 llm_client.chat_with（信号量 + 重试 + 动态超时全部不变）;
    - 新增本函数是为了「次级窗口=用户与模型聊天」里的 AI思考过程 能拿到真思考，
      而不是像之前那样拿正文（含工具调用块）冒充思考。
    """
    from llm_client import chat_with
    resp = chat_with(int(slot), messages, temperature=temperature, max_tokens=max_tokens)
    try:
        msg = resp["choices"][0]["message"]
    except Exception:
        return str(resp), ""
    content = str(msg.get("content") or "")
    reasoning = str(msg.get("reasoning_content") or "")
    return content, reasoning


def _call_model(slot: int, messages: List[dict],
                temperature: float = 0.5, max_tokens: Optional[int] = None) -> str:
    """统一调用入口（复用 llm_client.chat_with:自带信号量 + 重试 + 动态超时）

    - 保持原签名与返回值（只返回正文），旧调用零回归；内部复用 _call_model_ex 丢弃真思考。
    """
    return _call_model_ex(slot, messages, temperature=temperature, max_tokens=max_tokens)[0]


def _call_model_stream(slot: int, messages: List[dict],
                       on_reasoning=None, on_content=None,
                       temperature: float = 0.5,
                       max_tokens: Optional[int] = None):
    """流式调用入口（对齐主控 api_server /api/chat 的 stream 口径）

    - 优先走 llm_client.chat_with(stream=True):逐 delta 回调 on_reasoning / on_content，
      让次级窗口具备与主对话页一致的"逐字流式"观感，延迟显著小于整段返回;
    - 返回 (content, reasoning) 完整串（供上层落盘 / 工具块解析）;
    - 兼容兜底:若 stream 初始化失败或中途异常 → 自动降级为 _call_model_ex 整段调用，
      保证功能永不丢失（宁可无流式，不可无输出）。

    参数:
    - on_reasoning(text_chunk): 真思考增量回调（可能被调用多次）
    - on_content(text_chunk):   正文增量回调（可能被调用多次）
    """
    from llm_client import chat_with
    full_content = ""
    full_reasoning = ""
    try:
        stream_resp = chat_with(int(slot), messages, temperature=temperature,
                                max_tokens=max_tokens, stream=True)
        # 兼容 llm_client 在无配置/异常时直接返回 dict（非生成器）的分支:直接降级整段
        if isinstance(stream_resp, dict) or not hasattr(stream_resp, "__iter__"):
            raise RuntimeError("stream 初始化失败（返回非迭代对象）")
        for chunk in stream_resp:
            try:
                choice = (chunk.get("choices") or [None])[0] or {}
                delta = choice.get("delta") or {}
                r = str(delta.get("reasoning_content") or "")
                c = str(delta.get("content") or "")
            except Exception:
                continue
            if r:
                full_reasoning += r
                if on_reasoning:
                    try:
                        on_reasoning(r)
                    except Exception:
                        pass
            if c:
                full_content += c
                if on_content:
                    try:
                        on_content(c)
                    except Exception:
                        pass
        return full_content, full_reasoning
    except Exception as e:
        # 已收到部分增量（流式中途异常）→ 不降级整段，直接返回已收内容，避免"部分流式 + 整段"重复
        if full_content or full_reasoning:
            print(f"[Orchestrator] 流式中途异常，返回已收到的部分内容: {str(e)[:150]}")
            return full_content, full_reasoning
        # 完全未收到任何增量（stream 初始化失败等）→ 降级为整段调用（行为与改造前一致，保证输出不丢）
        print(f"[Orchestrator] 流式调用失败，降级为整段返回: {str(e)[:150]}")
        return _call_model_ex(slot, messages, temperature=temperature, max_tokens=max_tokens)


def _main_slot(pool: List[Dict[str, Any]]) -> Optional[int]:
    """主控槽位:优先人设名含「主控」/「玲珑」,其次槽位 1,最后池内第一个"""
    for item in pool:
        if ("主控" in item["persona_name"]) or ("玲珑" in item["persona_name"]):
            return int(item["slot"])
    for item in pool:
        if int(item["slot"]) == 1:
            return 1
    return int(pool[0]["slot"]) if pool else None

def _route_by_main(meta: Dict[str, Any], pool: List[Dict[str, Any]], purpose: str,
                   keyword: str, exclude: Optional[List[int]] = None) -> Optional[int]:
    """角色路由:主控自主分发优先,失败转人设名子串兜底（两种都失败返回 None → 前置拦截）"""
    skip = [int(x) for x in (exclude or [])]
    valid = [int(it["slot"]) for it in pool if it.get("available", True) and int(it["slot"]) not in skip]
    if not valid:
        return None
    main = _main_slot(pool)
    if main is not None and main not in skip:
        prompt = (
            f"你是任务统筹中枢,当前任务 #{meta.get('task_id', '')}。\n"
            f"可用角色清单:\n{pool_brief(pool)}\n"
            f"请为「{purpose}」选择最合适的槽位。只输出一个数字槽位号,不要任何解释。"
        )
        try:
            txt = _call_model(main, [{"role": "user", "content": prompt}],
                              temperature=0.0, max_tokens=16)
            for n in re.findall(r"\d+", txt or ""):
                if int(n) in valid:
                    return int(n)
        except Exception as e:
            print(f"[Orchestrator] 主控路由失败,转兜底匹配: {e}")
    return match_role_slot(pool, keyword, exclude=skip)

def extract_dispatch_mentions(text: str, pool: List[Dict[str, Any]]) -> Optional[int]:
    """从主模型回复提取首个派发 @角色 → 槽位号（甲-2 / 甲-2a）

    - 跳过标记头行（以 [ 开头），只扫正文；
    - 排除主控自身槽位（复用 _main_slot，零硬编码）；
    - 一轮回复只取第一个命中的派发 mention；
    - 【行首派发·防误派发】只认「行首 @角色」（line 已 strip，等价于允许前置 0~N 空格/Tab）:
      句中提及（如"当前可用:@开发、@审查"）一律不算派发；
      一旦命中，照旧「整段投递」（需求描述不丢，派发行为与改动前完全一致）。
    """
    body = str(text or "")
    if not body or not pool:
        return None
    main_slot = _main_slot(pool)
    exclude = [int(main_slot)] if main_slot is not None else []
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith("["):
            continue
        # 【行首派发·防误派发】只认「行首 @角色」（strip 后即行首，等价于允许前置 0~N 空格/Tab）；
        #   句中提及（如"当前可用:@开发、@审查"）一律不算派发 —— 根治系统误派发。
        #   命中后本行 @角色 之后仍可跟需求描述，整段文本照旧投递（需求内容不丢）。
        m = re.match(r"@([\u4e00-\u9fa5A-Za-z0-9_]+)", line)
        if not m:
            continue
        kw = m.group(1).strip()
        if not kw:
            continue
        slot = match_role_slot(pool, kw, exclude=exclude)
        if slot is not None:
            return slot
    return None

# ============================ 提示词构造 ============================

def _build_tool_context(slot: Optional[int] = None) -> str:
    """次级可用插件清单（复用主控同源数据源 tool_template_manager.get_merged_tool_list）

    - 严格照 api_server 主控口径:仅对带 plugin_config 的模板生成插件描述；
    - 内置工具（read_file/edit_file/...）已由槽位 fixed_prompt_1 覆盖，此处不重复。
    - 【插件按槽位过滤】enabled_plugins 缺失/非list/空数组 → 全量注入（口径与主控逐字对齐）。
    """
    try:
        from tool_template_manager import ToolTemplateManager
        merged = ToolTemplateManager.get_merged_tool_list() or {}
    except Exception as e:
        print(f"[Orchestrator] 工具清单读取失败: {e}")
        return ""
    # 【按槽位过滤】读该槽位 enabled_plugins；缺失/非list/空数组一律全量，防误清空致模型裸奔
    try:
        from model_registry import get_slot_config as _get_slot_cfg_tool
        _tool_cfg = (_get_slot_cfg_tool(int(slot)) or {}) if slot is not None else {}
    except Exception:
        _tool_cfg = {}
    _enabled_plugins = _tool_cfg.get("enabled_plugins")
    if isinstance(_enabled_plugins, list) and len(_enabled_plugins) > 0:
        _allowed_plugins = set(str(x) for x in _enabled_plugins)
        _filtered_merged = {}
        for _tid, _tpl in merged.items():
            _pid = str(((_tpl or {}).get("plugin_config") or {}).get("plugin_id", _tid))
            if _pid in _allowed_plugins or str(_tid) in _allowed_plugins:
                _filtered_merged[_tid] = _tpl
        merged = _filtered_merged
    plugin_desc: List[str] = []
    for _tool_id, template in (merged or {}).items():
        if not isinstance(template, dict):
            continue
        cfg = template.get("plugin_config")
        if not isinstance(cfg, dict):
            continue
        param_desc_list = []
        for param in (cfg.get("parameters") or []):
            required_tag = "必填" if param.get("required", False) else "可选"
            param_desc_list.append(
                f"{param.get('name', '')}（{required_tag}，{param.get('description', '')}）")
        params_desc = "；".join(param_desc_list)
        trigger_words = "、".join(cfg.get("trigger_words", []) or [])
        plugin_desc.append(
            f"【插件】工具名:{cfg.get('plugin_id', _tool_id)}，名称:{cfg.get('name', '')}，"
            f"描述:{cfg.get('description', '')}，参数要求:{params_desc}，"
            f"触发关键词:{trigger_words}，调用时工具名称必须填写工具名！"
        )
    if not plugin_desc:
        return ""
    return "\n【可用插件列表】\n" + "\n".join(plugin_desc)

def _build_role_system(slot: int) -> str:
    """次级模型自身配置（人设 + 3 固定提示 + 插件清单），复用主控同源数据源"""
    try:
        from model_registry import get_slot_config
        cfg = get_slot_config(int(slot)) or {}
    except Exception as e:
        print(f"[Orchestrator] 次级配置读取失败: {e}")
        return ""
    parts: List[str] = []
    persona_name = str(cfg.get("persona_name", "") or "")
    persona_prompt = str(cfg.get("persona_prompt", "") or "").strip()
    if persona_prompt:
        parts.append(
            f"========== 模型人设（{persona_name or cfg.get('display_name', '')}）==========\n"
            f"{persona_prompt}\n=================================="
        )
    for fk in ("fixed_prompt_1", "fixed_prompt_2", "fixed_prompt_3"):
        fv = str(cfg.get(fk, "") or "").strip()
        if fv:
            parts.append(fv)
    tool_ctx = _build_tool_context(int(slot))
    if tool_ctx.strip():
        parts.append(tool_ctx.strip())
    # 项目上下文（A 方案:次级自注入；格式与主控逐字一致）
    proj_ctx = _build_project_context()
    if proj_ctx.strip():
        parts.append(proj_ctx.strip())
    return "\n".join(parts)

def _build_project_context() -> str:
    """当前开发项目上下文（复刻主控 api_server 逐字同格式）

    - A 方案:次级自注入 —— 延迟 import api_server 读 CURRENT_PROJECT（破循环依赖，同 set_sse_pusher 先例）；
    - 键名与主控完全一致:project_name / project_root / file_list；
    - 文件清单超过 100 条自动截断（与主控同口径）；
    - 任何异常静默降级返回空串，绝不阻断派发。
    """
    try:
        import api_server as _api
        cp = _api.CURRENT_PROJECT or {}
        if not cp.get("project_name"):
            return ""
        project_root = os.path.normpath(cp["project_root"]).replace("\\", "/")
        file_list = cp.get("file_list", []) or []
        abs_file_list = []
        for rel_path in file_list:
            abs_path = os.path.normpath(os.path.join(project_root, rel_path)).replace("\\", "/")
            abs_file_list.append(abs_path)
        ctx = "\n========== 当前开发项目上下文 ==========\n"
        ctx += f"当前开发项目名称:{cp['project_name']}\n"
        ctx += f"项目根目录完整绝对路径:{project_root}\n"
        ctx += "项目文件清单（均为标准化绝对路径，可直接调用文件操作工具使用）:\n"
        if not abs_file_list:
            ctx += "✅ 当前为全局状态，如要进行项目开发请提醒用户选择相关项目，工作台使用项目隔离记忆方式\n"
        else:
            if len(abs_file_list) > 100:
                ctx += "\n".join([f"- {p}" for p in abs_file_list[:100]])
                ctx += "\n... 文件过多，仅显示前100个，可调用get_project_tree获取完整目录树\n"
            else:
                ctx += "\n".join([f"- {p}" for p in abs_file_list]) + "\n"
        ctx += "💡 以上所有文件路径均为标准化绝对路径，统一使用/分隔符，可直接调用文件操作工具使用，无需自行拼接路径\n"
        ctx += "==================================\n"
        return ctx
    except Exception as e:
        print(f"[Orchestrator] 项目上下文构造失败(已忽略): {str(e)[:120]}")
        return ""

def _build_secondary_history(slot: Optional[int] = None, project_name: str = "") -> List[dict]:
    """次级会话历史（读单文件 latest_secondary_history_项目_角色.json，取最近 N 轮原文 + 逐条时间戳）

    - 存储结构（本轮改造）:纯数组 [{"content": "用户问:…\\n回答:…", "timestamp": 毫秒}],
      与主模型 latest_chat_history_{项目}.json 逐字同构（1 条 = 1 轮）;
    - 回读拆分:content 按 "\\n回答:" 拆成 user/assistant 两条供模型上下文;
      若 content 里无 "\\n回答:" 标记（老格式记忆）→ 按 role 原样透传（向后兼容，老文件可读）;
    - 过程消息过滤（A1 口径）:think（真思考）/ ai（含工具调用块的正文）/ tool（已废弃）
      仅用于前端展示，不进入下一轮模型上下文 —— 否则模型会重复看到自己的思考与工具调用原文，
      导致上下文膨胀与自我复读；真正需要跨任务保留的只有 dispatch（user）与 report（assistant）。
    - 轮数口径:1 轮 = 1 条（user+assistant 合并落盘），回读时拆成 2 条，
      实际进入上下文条数上限 = 该槽位 max_chat_rounds（缺省 10）× 2；
    - 时间戳口径:与主控逐条时间戳一致，前缀 [YYYY-MM-DD HH:MM]；
      ts 由 SessionWriter.append 自动补（秒级 float），兼容毫秒（>1e11 自动 /1000），缺失用当前时间兜底；
    - 三档压缩（L1/L2）已按口径弃用，不再生成「[历史摘要]」条目。
    """
    rounds = 10
    if slot is not None:
        try:
            from model_registry import get_slot_config as _get_cfg_hist
            _hcfg = _get_cfg_hist(int(slot)) or {}
            rounds = int(_hcfg.get("max_chat_rounds", 0) or 0) or 10
        except Exception:
            rounds = 10
    raw = _load_secondary_history(int(slot or 0), str(project_name or ""))
    if not raw:
        return []
    now_ts = time.time()

    def _fmt_ts(_v) -> str:
        """时间戳归一:兼容秒(float) / 毫秒 int(>1e11 自动 /1000)，缺失用当前时间兜底"""
        try:
            _n = float(_v or now_ts)
        except Exception:
            _n = now_ts
        if _n > 1e11:
            _n = _n / 1000.0
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(_n))

    # 归一化:1 条 = 1 轮(用户问 + 回答)
    #   - 新格式（纯数组 + f"用户问:…\n回答:…"）:按主模型口径拆成 user / assistant 两条;
    #   - 老格式（{role, content, ts, header, msg_type}）:无 "\n回答:" 标记 → 按 role 原样透传,
    #     保证历史文件向后兼容可读（老记忆不丢）;
    #   - 展示型过程消息（老格式遗留 msg_type=think/ai/tool）:仍过滤,不进入下一轮模型上下文。
    norm: List[dict] = []
    for m in raw:
        if not isinstance(m, dict):
            continue
        if str(m.get("msg_type") or "") in ("think", "ai", "tool"):
            continue
        _c = str(m.get("content", "") or "")
        _ts_str = _fmt_ts(m.get("timestamp") or m.get("ts"))
        if "\n回答:" in _c:
            _ask_raw, _ans_raw = _c.split("\n回答:", 1)
            _ask = _ask_raw[len("用户问:"):] if _ask_raw.startswith("用户问:") else _ask_raw
            _ans = _ans_raw[len("回答:"):] if _ans_raw.startswith("回答:") else _ans_raw
            norm.append({"role": "user", "content": f"[{_ts_str}] {_ask}"})
            norm.append({"role": "assistant", "content": f"[{_ts_str}] {_ans}"})
        else:
            norm.append({
                "role": str(m.get("role") or "assistant"),
                "content": f"[{_ts_str}] {_c}",
            })
    if not norm:
        return []
    # 1 轮 = user + assistant 两条，取尾部 rounds*2 条
    return norm[-(rounds * 2):]

def _build_secondary_messages(slot: int, project_name: str, prompt: str) -> List[dict]:
    """次级调用消息体:system（模型自身配置） + 历史（单文件持久化） + 本轮 prompt

    - 必须在「本轮 prompt 落盘之前」调用，避免本轮 prompt 在历史中重复出现。
    """
    messages: List[dict] = []
    sys_text = _build_role_system(slot)
    if sys_text.strip():
        messages.append({"role": "system", "content": sys_text})
    messages.extend(_build_secondary_history(slot, project_name))
    messages.append({"role": "user", "content": str(prompt)})
    return messages

def _build_dev_prompt(meta: Dict[str, Any]) -> str:
    """开发派发提示词（原样派发:直接给主控回复原文,不加派发标识/轮次标记/任何包装）

    【2026-10-13 瘦身】原 round_no/round_total/last_review 三参已删:
    - round_no / round_total:函数体内从未使用（化石形参）；
    - last_review:调用点（_run_task）定义为空串后从无赋值（永远为空）—— 回炉流程已删，
      "上一轮审查驳回意见"这条分支永远走不到，一并删除。
    """
    return str(meta.get("requirement", "") or "")

def _build_review_prompt(meta: Dict[str, Any], dev_report: str, round_no: int,
                         round_total: int, degraded: bool = False) -> str:
    """审查派发提示词（只含派发标识 + 原始需求 + 开发回报,不加任何命令式内容）"""
    lines = [
        dispatch_header("审查", meta.get("task_id", ""), round_no, round_total),
        f"原始需求:{meta.get('requirement', '')}",
        "【开发回报】",
        str(dev_report)[:_context_limits()["review_dev_report"]],
    ]
    return "\n".join(lines)

# _ask_main_judge（主控裁决）已按用户口径移除:系统不再让代码驱动主控裁决


# _rule_parse_dev_status（C1-B规则兜底）已按用户口径移除:系统不替主控改判


# _ask_main_decide_review（主控三态决策）已按用户口径移除:系统不再驱动主控判断"继续开发/转审查/闭环"


# ========================================================================
# A1:次级工具执行循环（与主控 api_server /api/chat 工具循环同源、同口径）
# ------------------------------------------------------------------------
# 设计要点:
#   1) 检测/解析口径与主控一致（成对标记 + 编辑专用通道 + 通用通道）;
#   2) 执行层延迟 import api_server 复用主控模块级函数,非另起一套;
#   3) 同步阻塞实现（次级运行在后台线程,无事件循环）;
#   4) 循环上限读取「该模型自己的」max_reply_rounds（预设 20）。
# 注意:源码中以常量拼接成对标记,避免写入时被上层标记解析误截断。
# ========================================================================
_TC_OPEN = "【工具调用" + "开始】"
_TC_CLOSE = "【工具调用" + "结束】"
_TOOL_BLOCK_RE = re.compile(re.escape(_TC_OPEN) + r"(.*?)" + re.escape(_TC_CLOSE), re.S)
# 全角冒号常量(源码以 chr 构造,规避写入通道把全角冒号吞成半角冒号)
_FC = chr(0xFF1A)
# 冒号分隔正则片段:匹配全角冒号或半角冒号
_FC_SEP = "[" + _FC + ":]"
# 通用通道参数名白名单（与主控 ALL_PARAM_NAMES 同口径）
_TOOL_PARAM_NAMES = {"file_name", "operation", "target_block", "content", "gzt_anchor",
                     "gzt_newtext", "path", "is_dir", "old_path", "new_name", "query", "cmd"}
# 修改类工具（防死循环与回填口径，与主控保持一致）
_TOOL_MODIFY_TOOLS = {"edit_file", "create_file", "delete_file", "rename_file", "write_file"}


def _tool_param_names(tool_name: str) -> set:
    """参数名白名单:内置工具 + 动态加载插件参数（与主控口径一致）"""
    names = set(_TOOL_PARAM_NAMES)
    if tool_name == "read_file":
        names.update({"start_line", "end_line"})
    if tool_name == "locate_symbol":
        names.update({"symbol", "file", "with_content"})
    try:
        import api_server as _api
        cfg = _api.tool_template_manager.get_plugin_config(tool_name)
        if cfg:
            names.update([p["name"] for p in cfg.get("parameters", [])])
    except Exception:
        pass
    return names


def _tool_parse_params(tool_name: str, params_str: str) -> Dict[str, Any]:
    """解析参数列表文本 -> params（复刻主控口径:编辑专用通道 + 通用通道）"""
    params: Dict[str, Any] = {}
    raw = str(params_str or "")

    # ---- 编辑专用通道:长内容工具 100% 稳定优先，杜绝内容误截断 ----
    if tool_name in ("edit_file", "create_file"):
        try:
            norm = raw.replace(_FC, ":", 50)
            if tool_name == "edit_file":
                m = re.search(r'^[ \t]*file_name' + _FC_SEP + r'[ \t]*(.*?)(?=\n[ \t]*(operation|gzt_anchor|gzt_newtext|target_block|content)' + _FC_SEP + r'|\Z)', norm, re.S | re.M)
                if m:
                    params["file_name"] = m.group(1).strip()
                m = re.search(r'^[ \t]*operation' + _FC_SEP + r'[ \t]*(.*?)(?=\n[ \t]*(gzt_anchor|gzt_newtext|target_block|content)' + _FC_SEP + r'|\Z)', norm, re.S | re.M)
                if m:
                    params["operation"] = m.group(1).strip()
                m = re.search(r'^[ \t]*gzt_anchor' + _FC_SEP + r'[ \t]*(.*?)(?=\n[ \t]*gzt_newtext' + _FC_SEP + r'|\Z)', norm, re.S | re.M)
                if m:
                    v = m.group(1)
                    if v.startswith("\n"):
                        v = v[1:]
                    params["gzt_anchor"] = v.rstrip("\n")
                m = re.search(r'^[ \t]*gzt_newtext' + _FC_SEP + r'(.*)', norm, re.S | re.M)
                if m:
                    v = m.group(1)
                    if v.startswith("\n"):
                        v = v[1:]
                    params["gzt_newtext"] = v.rstrip("\n")
                if "file_name" in params and "operation" in params:
                    if params.get("operation") in ("insert_start", "insert_end") or "gzt_anchor" in params:
                        return params
            elif tool_name == "create_file":
                m = re.search(r'^[ \t]*path' + _FC_SEP + r'[ \t]*(.*?)(?=\n[ \t]*(is_dir|gzt_newtext|content)' + _FC_SEP + r')', norm, re.S | re.M)
                if m:
                    params["path"] = m.group(1).strip()
                m = re.search(r'^[ \t]*is_dir' + _FC_SEP + r'[ \t]*(.*?)(?=\n[ \t]*(?:gzt_newtext|content)' + _FC_SEP + r'|$)', norm, re.S | re.M)
                if m:
                    params["is_dir"] = m.group(1).strip().lower() in ("true", "1", "yes")
                m = re.search(r'^[ \t]*(?:gzt_newtext|content)' + _FC_SEP + r'[ \t]*(.*)', norm, re.S | re.M)
                if m:
                    v = m.group(1)
                    if v.startswith("\n"):
                        v = v[1:]
                    params["gzt_newtext"] = v.rstrip()
                if "path" in params:
                    return params
        except Exception:
            params = {}

    # ---- 通用通道:顶格参数名切分,内容原样保留（含换行/缩进） ----
    names = _tool_param_names(tool_name)
    cur_name = None
    cur_val: List[str] = []
    for line in raw.split("\n"):
        check_line = line
        for pn in names:
            if line.lstrip().startswith(pn + _FC):
                check_line = line.replace(_FC, ":", 1)
                break
        if (not line.startswith((" ", "\t"))) and ":" in check_line.strip():
            k = check_line.split(":", 1)[0].strip()
            if k in names and k not in params:
                if cur_name is not None:
                    params[cur_name] = "\n".join(cur_val).rstrip("\n")
                cur_name = k
                cur_val = [check_line.split(":", 1)[1]]
                continue
        if cur_name is not None:
            cur_val.append(line)
    if cur_name is not None:
        params[cur_name] = "\n".join(cur_val).rstrip("\n")

    # ---- 统一后置:类型归一（与主控口径一致） ----
    if tool_name == "edit_file" and params.get("operation") == "delete":
        params.setdefault("content", "")
    if "is_dir" in params and isinstance(params["is_dir"], str):
        params["is_dir"] = params["is_dir"].strip().lower() == "true"
    for k, v in list(params.items()):
        if k in ("content", "target_block", "gzt_newtext", "gzt_anchor") or not isinstance(v, str):
            continue
        vs = v.strip()
        if vs and (vs[0] in '{["0123456789-tfn' or vs in ("true", "false", "null")):
            try:
                import json as _json
                pv = _json.loads(vs)
                if not isinstance(pv, str):
                    params[k] = pv
            except Exception:
                pass
    return params


def _tool_parse_blocks(text: str) -> List[Dict[str, Any]]:
    """从模型输出文本解析工具调用块 -> [{name, params}, ...]（与主控检测口径一致）"""
    blocks: List[Dict[str, Any]] = []
    for raw in _TOOL_BLOCK_RE.findall(str(text or "")):
        body = raw.strip()
        m = re.search(r'工具名称' + _FC_SEP + r'\s*(\w+)', body)
        if not m:
            continue
        name = m.group(1).strip()
        pm = re.search(r'参数列表' + _FC_SEP + r'\s*(.*)', body, re.S)
        if not pm:
            continue
        blocks.append({"name": name, "params": _tool_parse_params(name, pm.group(1))})
    return blocks


def _call_model_with_tools(slot: int, messages: List[dict], session_id: str,
                           max_rounds: int = 20, temperature: float = 0.5,
                           max_tokens: Optional[int] = None,
                           task_id: str = "", kind: str = "dev",
                           history_out: Optional[List[str]] = None,
                           project: str = "") -> str:
    """A1:次级工具执行循环（与主控 api_server /api/chat 同源同口径）

    流程:调模型 → 检测工具块 → 执行 → 回填 messages → 再调模型 → 无工具即结束
    - 所有次级槽位共用本函数（只传各自 slot），行为完全一致;
    - max_rounds 读取「该模型自己的」max_reply_rounds（预设 20）;
    - 执行器为同步阻塞实现（次级运行在后台线程，无事件循环）;
    - 返回最后一轮 AI 原文（即任务总结，2a 口径）;
    - task_id/kind（新增,可选）:传值后 think/tool 过程消息会同步落盘到次级会话文件，
      让晚打开/切项目后的历史回读也能看到完整过程（不传 → 不落盘，旧调用零回归）。
    - history_out（新增,可选）:传值后按「轮」累积记忆落盘片段（每轮 AI 正文原文 +
      每轮工具执行结果「工具执行结果:…」段），由调用方 _run_task 收尾时按主模型
      latest_chat_history_{项目}.json 口径一次性拼装「用户问:…\n回答:…」落盘;
      不传（旧调用）→ 零影响，行为与改造前完全一致。
    """
    conv: List[dict] = list(messages or [])
    accumulated: List[str] = []
    total = max(1, int(max_rounds or 1))
    for round_no in range(1, total + 1):
        # 流式改造:逐 delta 实时推送真思考 + 正文，让次级窗口具备与主对话页一致的逐字流式观感
        # 说明:
        #   ① 回调 on_reasoning → ai_reasoning（真思考，来自 delta.reasoning_content）
        #   ② 回调 on_content   → ai_output_stream（正文，含工具调用指令块）
        #   ③ 中间轮与最终轮统一走流式（此前只有中间轮整段推、最终轮靠 report 整段 → 无流式感）
        #   ④ 降级兜底:若模型端不支持 stream 或中途异常，_call_model_stream 自动回退整段调用，
        #      此时回调不会触发 → 由下方「回调未产生增量」分支补推一次，保证前端不空白。
        _reason_buf: List[str] = []
        _content_buf: List[str] = []

        def _on_reasoning_chunk(chunk: str) -> None:
            if not chunk:
                return
            _reason_buf.append(chunk)
            try:
                # 【方案C·串台修复】透传 project → 通道键带项目维度，项目A 与 项目B 物理隔离
                push_secondary_event(session_id, "ai_reasoning", chunk, slot=slot, project=project)
            except Exception as _e:
                print(f"[Orchestrator] ai_reasoning 推送失败(忽略): {str(_e)[:120]}")

        def _on_content_chunk(chunk: str) -> None:
            if not chunk:
                return
            _content_buf.append(chunk)
            try:
                # 【方案C·串台修复】透传 project → 通道键带项目维度
                push_secondary_event(session_id, "ai_output_stream", chunk, slot=slot, project=project)
            except Exception as _e:
                print(f"[Orchestrator] ai_output_stream 推送失败(忽略): {str(_e)[:120]}")

        try:
            # 流式入口:同一次调用里同时拿到「正文 + 真思考」（避免为拿思考再调一次模型）
            text, reasoning = _call_model_stream(
                slot, conv,
                on_reasoning=_on_reasoning_chunk, on_content=_on_content_chunk,
                temperature=temperature, max_tokens=max_tokens,
            )
        except Exception as e:
            accumulated.append(f"❌ 模型调用失败:{str(e)[:200]}")
            break
        cur = str(text or "")
        reasoning = str(reasoning or "")
        # 降级兜底:若流式回调未产生任何增量（模型端不支持 stream / 中途异常已降级整段），
        # 则在此补推一次整段，保证前端一定能看到本轮内容。
        if reasoning and not _reason_buf:
            try:
                # 【方案C·串台修复】透传 project → 通道键带项目维度
                push_secondary_event(session_id, "ai_reasoning", reasoning, slot=slot, project=project)
            except Exception as _e:
                print(f"[Orchestrator] ai_reasoning 补推失败(忽略): {str(_e)[:120]}")
        if cur and not _content_buf:
            try:
                # 【方案C·串台修复】透传 project → 通道键带项目维度
                push_secondary_event(session_id, "ai_output_stream", cur, slot=slot, project=project)
            except Exception as _e:
                print(f"[Orchestrator] ai_output_stream 补推失败(忽略): {str(_e)[:120]}")
        # 【需求2·分气泡】本轮 AI 正文收尾 → 补推 ai_output 终态事件（对齐主对话页 PageO0x2f.vue L908-916 口径）:
        #   前端收到 ai_output 后显式置空 roundThinkMsg / roundAiMsg 指针,
        #   下一轮流式（ai_output_stream）自然落到新气泡 —— 与主对话页分轮机制 100% 同构。
        #   工具执行结果按用户口径不推前端 → 用户看到的一轮一轮分气泡 = 纯 AI 输出内容。
        #   与 report 事件不冲突:前端 report 分支优先用 streamedThisTurn 判重,不会重复 push。
        if cur:
            try:
                # 【方案C·串台修复】透传 project → 通道键带项目维度
                push_secondary_event(session_id, "ai_output", cur, slot=slot, project=project)
            except Exception as _e:
                print(f"[Orchestrator] ai_output 终态推送失败(忽略): {str(_e)[:120]}")
        # 过程消息（think / ai）按决策3不再落盘；SSE 实时推送已在上方完成，前端显示不受影响。
        if cur:
            accumulated.append(cur)
            # 记忆文件累积（可选）:调用方传 history_out 时，把每轮 AI 正文原文累积下来，
            # 供 _run_task 收尾时按主模型口径拼装「用户问:…\n回答:…」一次性落盘。
            # 不传（旧调用）→ 零影响，SSE 实时推送与返回值语义均不变。
            if history_out is not None:
                history_out.append(cur)
        # 【2026-10-12 根因修复·次级通道补全器接入】
        # 根因:玲珑派发的开发任务走本函数，与主控 /api/chat 是两条物理隔离链路;
        #   而工具块补全器此前只存在于 api_server 的 /api/chat 内，本链路零兜底:
        #   模型漏写结束标记时，下方 _TOOL_BLOCK_RE.findall 抓不到该块 →
        #   _tool_parse_blocks 返回空 → if not blocks 直接 break（误判"无工具调用"）→
        #   工具不执行、文件不写入、任务中断。这是"主链路改了、任务链未改"的真实根因。
        # 做法:解析前先补全（复用 api_server 同一份实现，两端永远同一把尺子）;
        #   仅补"结束标记"、不猜任何内容;无补足时原样返回，零行为变更;
        #   遇新开始标记先就地闭合旧块 —— 连续多块均未闭合的场景也能正确拆块。
        # 注意:上方 SSE 已按原文推送、history_out 已按原文落盘 —— 前端显示与记忆不受影响。
        try:
            import api_server as _api_ac
            _cur_fixed, _ac_pad = _api_ac._autoclose_tool_blocks(cur)
            if _ac_pad > 0:
                print(f"[Orchestrator] 检测到本轮回复中有 {_ac_pad} 个工具块缺少结束标记，"
                      f"已在解析前自动补全（仅补标记，不补内容）")
                cur = _cur_fixed
        except Exception as _e_ac:
            print(f"[Orchestrator] 工具块补全失败(忽略，按原文解析): {str(_e_ac)[:120]}")
        blocks = _tool_parse_blocks(cur)
        if not blocks:
            # 【2026-10-13 根因修复·取消静默闭环】
            # 原「无块即 break」把「解析失败/输出截断」当成了「模型已收尾」:
            #   模型输出半截工具块（只有开始标记、缺名称/参数/结束标记）时，
            #   工具结果永远回灌不到模型（下方 conv.append(user) 回灌走不到），任务被静默当完成。
            # 按用户口径:闭环只能由「模型自己不再调工具、给出总结」体现，代码不得代判。
            #   ① 输出里无开始标记 → 真·模型已给总结 → 正常结束（唯一合法闭环出口）;
            #   ② 输出里有开始标记但块不完整 → 截断异常，非闭环;回灌纠错提示让模型重发。
            if _TC_OPEN in str(cur or ""):
                print(f"[Orchestrator] 第 {round_no} 轮检测到工具调用块不完整（有开始标记、无完整内容），"
                      f"已回灌纠错提示要求模型重发")
                conv.append({"role": "assistant", "content": cur})
                conv.append({"role": "user", "content": (
                    "⚠️【系统提示】你上一条回复中的工具调用块不完整:缺少"
                    "「工具名称」/「参数列表」/「" + _TC_CLOSE + "」中的一项或多项，系统无法执行。"
                    "请重新完整输出该工具调用块（四部分必须齐全），不要输出任何额外解释。")})
                continue
            break  # 真·无工具调用 → 模型已给总结，正常结束（唯一合法闭环出口）
        # 回填 assistant 本轮到对话（与主控 messages.append 口径一致）
        conv.append({"role": "assistant", "content": cur})
        # 依次执行本轮所有工具
        results: List[str] = []
        for idx, blk in enumerate(blocks):
            name = str(blk.get("name") or "").strip()
            params = blk.get("params") or {}
            if not name:
                results.append("❌ 工具指令解析失败:缺少工具名称字段")
                continue
            try:
                res = _execute_tool_sync(name, params, session_id)
            except Exception as e:
                res = f"❌ 工具执行异常:{str(e)[:200]}"
            results.append(f"🔹 指令{idx + 1}执行结果:{res}")
        # 记忆文件累积（可选）:本轮工具执行结果按主模型口径追加为「工具执行结果:…」段，
        # 与 api_server 主模型 structured_content 的写法逐字同构（Q4=A 恢复落盘）。
        # 不传（旧调用）→ 零影响，工具结果仍只在本任务内存对话 conv 中回填给模型。
        if history_out is not None and results:
            history_out.append("工具执行结果:" + "\n".join(results))
        conv.append({"role": "user", "content": "\n".join(results)})
        # A6 补插:媒体像素只能落在 user 角色多模态消息内（工具角色不接受 image_url 块）
        # 与主控 api_server 完全同源（同一 media_reader 登记表 + 同一总量闸门），无登记则零开销跳过
        try:
            import media_reader as _mr2
            _pend2 = _mr2.take_media()
            if _pend2:
                _cfg2 = _mr2.get_media_config()
                _lim2 = int(float(_cfg2.get("media_total_max_mb", 2.0)) * 1024 * 1024)
                _keep2, _used2, _drop2 = [], 0, 0
                for _it in _pend2:
                    _b2 = int(len(_it.get("b64", "")) * 3 / 4)
                    if _keep2 and _used2 + _b2 > _lim2:
                        _drop2 += 1
                        continue
                    _keep2.append(_it)
                    _used2 += _b2
                _ln2 = [f"📎 本次读取 {len(_pend2)} 项媒体，随本消息传入 {len(_keep2)} 项:"]
                _blk2 = [{"type": "text", "text": ""}]
                for _i2, _it in enumerate(_keep2, 1):
                    _m2 = _it.get("meta") or {}
                    _k2 = "图片" if _it.get("kind") == "image" else "视频帧"
                    _ln2.append(f"{_i2}. [{_k2}] {_it.get('path')}｜{_m2.get('width')}x{_m2.get('height')}｜{_m2.get('final_size_mb')}MB")
                    _blk2.append({"type": "image_url", "image_url": {"url": f"data:{_m2.get('mime', 'image/jpeg')};base64,{_it.get('b64')}"}})
                if _drop2:
                    _ln2.append(f"⚠️ 受总量上限 {_cfg2.get('media_total_max_mb')}MB 限制，已裁剪 {_drop2} 项未传入")
                _blk2[0]["text"] = "\n".join(_ln2)
                conv.append({"role": "user", "content": _blk2})
        except Exception as _e2:
            print(f"[Orchestrator] 媒体像素补插失败(忽略): {str(_e2)[:120]}")
        # 说明（A1 口径）:工具执行结果不单独推送/落盘 —— 主对话页从未有此独立节点，
        #   工具结果仅在本任务的「内存对话 conv」中回填给模型，供其继续下一轮决策。
        #   这样次级窗口 100% 与主对话页一致:主控原话 → AI真思考(折叠) → AI正文(含工具调用原文) → 最终回报。
        # 剩余轮次=1 时注入强制收尾提示（与主控 L2603-2610 同口径）
        if total - round_no == 1:
            conv.append({"role": "user", "content": (
                "🛑【系统强制提示】工具调用轮次即将用完，仅剩1次回复机会。"
                "下一轮禁止再出现任何工具调用标记，必须立即停止调用工具并直接输出当前任务的阶段性总结:"
                "①已完成的内容与执行结果；②未完成的事项明确告知，顺延到下一轮任务中执行。")})
    return (accumulated[-1] if accumulated else "").strip()


def _slot_max_rounds(slot: int, default: int = 20) -> int:
    """读取「该模型自己的」max_reply_rounds（与主控 api_server 同源同口径,预设 20）"""
    try:
        from model_registry import get_slot_config
        cfg = get_slot_config(int(slot)) or {}
        return max(1, int(cfg.get("max_reply_rounds", default) or default))
    except Exception:
        return max(1, int(default))


def _execute_tool_sync(tool_name: str, params: Dict[str, Any], session_id: str) -> str:
    """A1:次级工具执行器（同步阻塞,与主控 api_server /api/chat 工具分支同源同口径）

    覆盖:只读类（get_project_tree/read_file/rag_search/locate_symbol）+ 执行类（exec_cmd）
    + 后台任务（query_background_task/cancel_background_task）+ 修改类与插件（见后续批次）。
    公共函数走延迟 import api_server 复用与主控同源（get_real_physical_path/is_path_forbidden/
    add_operation_log/add_file_operation_log/truncate_tool_output/build_simple_tree 及
    command_runner/background_task_manager/rag_manager/ast_symbol_index 等单例）。
    环境差异适配:req.session_id → 入参 session_id;push_sse_message(req.session_id,..) →
    _api.push_sse_message(session_id,..);次级运行在后台线程（无事件循环）,不用 asyncio.create_task。
    """
    import api_server as _api
    try:
        if tool_name == "get_project_tree":
            cp = _api.CURRENT_PROJECT
            if cp["project_root"]:
                root_path = cp["project_root"]
                root_name = cp["project_name"]
                root_tag = "current_project"
            else:
                root_path = _api.REPOSITORY_PATH
                root_name = "仓库根目录"
                root_tag = "repo_root"
            tree_children, path_map = _api.build_simple_tree(root_path, tag=root_tag)
            root_abs_path = os.path.normpath(root_path).replace("\\", "/")
            path_map[""] = {
                "abs_path": root_abs_path,
                "tag": root_tag,
                "is_dir": True
            }
            tree_data = {root_name: tree_children}
            return_data = {
                "tree": tree_data,
                "path_map": path_map,
                "tip": "💡 所有文件/文件夹的绝对路径已在path_map中给出，直接使用abs_path字段调用文件操作工具即可，无需自行拼接路径，路径已统一标准化为/分隔符"
            }
            exec_result = f"✅ 文件列表读取成功:{json.dumps(return_data, ensure_ascii=False, indent=2)}"
            _api.add_operation_log("文件操作", f"✅ 文件列表读取成功，共返回{len(path_map)}个路径条目")
            return _api.truncate_tool_output("get_project_tree", 1, exec_result)

        elif tool_name == "read_file":
            file_name = str(params.get("file_name", "") or "").strip()
            raw_start_line = params.get("start_line")
            raw_end_line = params.get("end_line")
            if isinstance(raw_start_line, str) and not raw_start_line.strip():
                raw_start_line = None
            if isinstance(raw_end_line, str) and not raw_end_line.strip():
                raw_end_line = None
            page_start, page_end = None, None
            if raw_start_line is not None or raw_end_line is not None:
                try:
                    is_start_wild = isinstance(raw_start_line, str) and raw_start_line.strip() == "*"
                    is_end_wild = isinstance(raw_end_line, str) and raw_end_line.strip() == "*"
                    if is_start_wild and is_end_wild:
                        page_start, page_end = None, None
                    else:
                        if raw_start_line is None or raw_end_line is None:
                            raise ValueError("必须同时提供start_line和end_line")
                        page_start = 1 if is_start_wild else int(raw_start_line)
                        page_end = 10 ** 12 if is_end_wild else int(raw_end_line)
                        if page_start < 1 or page_end < page_start:
                            raise ValueError("行号范围非法")
                except (TypeError, ValueError):
                    return "❌ 参数错误:read_file翻页参数非法，start_line/end_line必须同时为正整数且end_line>=start_line（行号从1开始）；需要完整读取文件时显式传start_line=*和end_line=*（可规避翻页参数被自动补全导致的超界错误），请修正参数后重试"
            target_file_path = _api.get_real_physical_path(file_name)
            if not target_file_path:
                return f"❌ 路径为空:{file_name}"
            forbidden, reason = _api.is_path_forbidden(target_file_path)
            if forbidden:
                _api.add_file_operation_log("read", file_name, "fail", reason)
                return f"⚠️ {reason}，禁止读取"
            if not os.path.exists(target_file_path):
                err_msg = f"❌ 文件不存在:{file_name}（标准化后路径:{target_file_path}）\n⚠️ 分析工具调用失败原因:\n1. 指令执行错误（路径拼写错误/文件不存在），请向用户说明并执行一次重试；\n2. 工作台系统错误无法执行或者已经执行第二次重试，请停止任务执行并向用户说明，给出可能性分析。"
                _api.add_operation_log("文件操作", f"❌ 读取文件失败:{file_name}，文件不存在")
                return err_msg
            if not os.path.isfile(target_file_path):
                err_msg = f"❌ 路径是文件夹不是文件:{file_name}（标准化后路径:{target_file_path}）\n⚠️ 分析工具调用失败原因:\n1. 指令执行错误（路径指向文件夹而非文件），请向用户说明并执行一次重试；\n2. 工作台系统错误无法执行或者已经执行第二次重试，请停止任务执行并向用户说明，给出可能性分析。"
                _api.add_operation_log("文件操作", f"❌ 读取文件失败:{file_name}，路径是文件夹")
                return err_msg
            try:
                # A6 收口:图片读取统一走 media_reader（与 api_server 完全同源，杜绝两处实现与文案漂移）
                # 像素由登记表承载，由 orchestrator 消息组装处补插 user 多模态消息送达模型
                import media_reader as _mr
                _IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif", ".ico", ".psd", ".tga", ".pcx", ".dds", ".qoi", ".icns"}
                file_ext = os.path.splitext(target_file_path)[1].lower()
                if file_ext in _IMG_EXTS:
                    try:
                        media_b64, media_meta = _mr.media_image_to_base64(target_file_path)
                    except Exception as e:
                        return f"❌ 图片读取失败:{file_name}（绝对路径:{target_file_path}）\n原因:{e}\n💡 heic/avif/svg/相机RAW 等格式 PIL 无法解码，请先转换为 PNG/JPG 后再读取。"
                    cp = _api.CURRENT_PROJECT
                    if cp["project_root"] and target_file_path.startswith(os.path.normpath(cp["project_root"]).replace("\\", "/")):
                        log_msg = f"✅ 读取当前项目图片文件成功:{file_name}（绝对路径:{target_file_path}）"
                    else:
                        log_msg = f"✅ 读取图片文件成功:{file_name}（绝对路径:{target_file_path}）"
                    _mtip = f"📸 {media_meta.get('width')}x{media_meta.get('height')}｜格式 {media_meta.get('format')}｜原始 {media_meta.get('original_size_mb')}MB｜输出 {media_meta.get('final_size_mb')}MB"
                    if not media_b64:
                        # 第三级兜底:只返元信息文字，不登记像素
                        _api.add_operation_log("文件操作", log_msg)
                        return f"{log_msg}\n{_mtip}\n⚠️ {media_meta.get('degrade_reason')}"
                    _mr.register_media("image", target_file_path, media_b64, media_meta)
                    _api.add_operation_log("文件操作", log_msg)
                    return f"{log_msg}\n{_mtip}\n💡 图片像素已随本消息传入，可直接识别其中的文字、场景、物体与图表，无需再次读取。"
                elif file_ext in _mr.VIDEO_EXTENSIONS:
                    # 视频分支（阶段B）:ffprobe 探测 → 停滞段扫描 → 五道闸门智能抽帧 → 逐帧三级降级 → 登记像素
                    # 与主控 api_server 完全同源（同一 media_reader + 同一登记表），像素由上层补插逻辑送达模型
                    _vres = _mr.extract_video_frames(target_file_path, None, None)
                    if _vres.get("ok"):
                        _vframes = _vres.get("frames") or []
                        _vstamps = [f.get("timestamp") for f in _vframes if isinstance(f, dict)]
                        log_msg = f"✅ 读取视频文件成功:{file_name}（绝对路径:{target_file_path}）"
                        _api.add_operation_log("文件操作", log_msg)
                        return (
                            f"{log_msg}\n{_vres.get('report') or _vres.get('message')}\n"
                            f"💡 已抽取 {len(_vframes)} 帧（时间戳(s): {_vstamps}），帧像素已随本消息传入，可直接识别画面内容，无需再次读取。"
                        )
                    return f"⚠️ 视频读取暂不可用:{file_name}\n{_vres.get('message')}"
                with open(target_file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if page_start is not None:
                    all_lines = content.split("\n")
                    total_lines = len(all_lines)
                    if page_start > total_lines:
                        _api.add_operation_log("文件操作", f"⚠️ 翻页超出文件末尾:{file_name}，共{total_lines}行")
                        return f"❌ 参数错误:start_line={page_start}超出文件总行数{total_lines}，请用1-{total_lines}范围内的行号重新读取"
                    seg_start = max(1, page_start)
                    seg_end = min(page_end, total_lines)
                    sliced = "\n".join(all_lines[seg_start - 1:seg_end])
                    cp = _api.CURRENT_PROJECT
                    if cp["project_root"] and target_file_path.startswith(os.path.normpath(cp["project_root"]).replace("\\", "/")):
                        page_log_msg = f"✅ 读取当前项目文件成功:{file_name}（绝对路径:{target_file_path}）"
                    else:
                        page_log_msg = f"✅ 读取文件成功:{file_name}（绝对路径:{target_file_path}）"
                    step = seg_end - seg_start + 1
                    prev_tip = f"上一段start_line={max(1, seg_start - step)}&end_line={seg_start - 1}" if seg_start > 1 else "已是文件开头"
                    next_tip = f"下一段start_line={seg_end + 1}&end_line={min(total_lines, seg_end + step)}" if seg_end < total_lines else "已是文件末尾"
                    _api.add_operation_log("文件操作", page_log_msg + f"，翻页第{seg_start}-{seg_end}行/共{total_lines}行")
                    return (f"{page_log_msg}\n📄 文件共{total_lines}行，当前显示第{seg_start}-{seg_end}行\n"
                            f"📍 翻页提示:{prev_tip}；{next_tip}\n内容:\n{sliced}\n"
                            f"📢 以上为文件第{seg_start}-{seg_end}行片段，需要其他段落用start_line/end_line继续翻页；根据读取信息执行下一步指令（注意:修改指令代码缩进要和原文匹配）。")
                cp = _api.CURRENT_PROJECT
                if cp["project_root"] and target_file_path.startswith(os.path.normpath(cp["project_root"]).replace("\\", "/")):
                    log_msg = f"✅ 读取当前项目文件成功:{file_name}（绝对路径:{target_file_path}）"
                    return_msg = f"✅ 读取当前项目文件成功:{file_name}（绝对路径:{target_file_path}）\n内容:\n{content}\n📢 这是文件完整内容，根据用户需求后给予反馈信息:\n 1. 用户要求读取文件，给出文件结构化说明，无需进行下一步操作；\n 2. 执行一轮修复任务当中（如果本轮任务已经完成直接给出任务完成说明），根据读取信息给出修复说明，并执行下一个指令（注意:修改指令代码缩进要和原文匹配） 。"
                else:
                    log_msg = f"✅ 读取文件成功:{file_name}（绝对路径:{target_file_path}）"
                    return_msg = f"✅ 读取文件成功:{file_name}（绝对路径:{target_file_path}）\n内容:\n{content}\n📢 这是文件完整内容，根据用户需求后给予反馈信息:\n 1. 用户要求读取文件，给出文件结构化说明，无需进行下一步操作；\n 2. 执行一轮修复任务当中（如果本轮任务已经完成直接给出任务完成说明），根据读取信息给出修复说明，并执行下一个指令（注意:修改指令代码缩进要和原文匹配）。"
                _api.add_operation_log("文件操作", log_msg)
                return return_msg
            except Exception as e:
                err_msg = f"❌ 读取文件失败:{file_name}（绝对路径:{target_file_path}），错误:{str(e)}\n⚠️ 分析工具调用失败原因:\n1. 指令执行错误（文件权限不足/文件被占用），请向用户说明并执行一次重试；\n2. 工作台系统错误无法执行或者已经执行第二次重试，请停止任务执行并向用户说明，给出可能性分析。"
                _api.add_operation_log("文件操作", f"❌ 读取文件失败:{file_name}，错误:{str(e)}", "error")
                return err_msg

        elif tool_name == "rag_search":
            query = str(params.get("query", "") or "").strip()
            cp = _api.CURRENT_PROJECT
            current_project = cp["project_name"] if cp["project_name"] else None
            results = _api.rag_manager.search(query, project_name=current_project)
            exec_result = f"✅ 代码检索结果:\n"
            _api.add_operation_log("文件操作", f"✅ 代码检索结果:\n")
            for res in results:
                file_abs_path = _api.get_real_physical_path(res['file_name'])
                res['abs_path'] = file_abs_path
                exec_result += f"📄 文件:{res['file_name']}（绝对路径:{file_abs_path}）\n```\n{res['content']}\n```\n"
                _api.add_operation_log("文件操作", f"📄 文件:{res['file_name']}（绝对路径:{file_abs_path}）\n```\n{res['content']}\n```\n")
            exec_result += "\n💡 检索结果已自动补全文件绝对路径，直接使用abs_path字段调用文件操作工具即可，无需自行拼接路径"
            return _api.truncate_tool_output("rag_search", 1, exec_result)

        elif tool_name == "locate_symbol":
            symbol = str(params.get("symbol", "") or "").strip()
            file_arg = str(params.get("file", "") or "").strip()
            with_content = params.get("with_content", True)
            if isinstance(with_content, str):
                with_content = with_content.strip().lower() not in ("false", "0", "no", "")
            locate_result = _api.ast_symbol_index.locate_symbol(symbol, file=file_arg or None, with_content=bool(with_content))
            if not locate_result.get("found"):
                exec_result = f"❌ 未定位到符号「{symbol}」:{locate_result.get('message', '')}"
                _api.add_operation_log("文件操作", exec_result, "error")
                return exec_result
            exec_result = f"✅ 符号定位结果（共 {locate_result['match_count']} 处，匹配方式:{locate_result.get('match_type')}）:\n"
            _api.add_operation_log("文件操作", f"✅ 符号定位结果:{symbol}\n")
            for m in locate_result["matches"]:
                header = (f"📄 符号:{m['qualified_name']}（类型:{m['type']}）\n"
                          f"   文件:{m['file']}（绝对路径:{m['abs_path']}）\n"
                          f"   行号:{m['start_line']}-{m['end_line']}\n"
                          f"   签名:{m['signature']}\n")
                exec_result += header
                _api.add_operation_log("文件操作", header)
                if m.get("content"):
                    exec_result += f"```\n{m['content']}\n```\n"
            exec_result += "\n💡 已补齐文件绝对路径与精确行号:可直接用 read_file（start_line/end_line）读取，或用 edit_file（signature 整行作锚点）精确修改"
            return _api.truncate_tool_output("locate_symbol", 1, exec_result)

        elif tool_name == "exec_cmd":
            cmd = str(params.get("cmd", "") or "").strip()
            exec_result = ""
            lower_cmd = cmd.lower()
            # 【2026-10-12 调整】按用户要求取消 & 命令拼接拦截，仅保留危险程序段首匹配保护。
            is_dangerous = _api._contains_dangerous_command(cmd)
            if is_dangerous:
                exec_result = "❌ 禁止执行危险命令，仅允许执行查询类命令"
                _api.add_operation_log("AI执行命令", exec_result, "error")
                return exec_result
            try:
                _exec_timeout = int(_api._get_tool_output_config().get("exec_cmd_timeout", 60))
            except Exception:
                _exec_timeout = 60
            try:
                _tmp_task_id = "tmp_%s_%06d" % (time.strftime("%Y%m%d%H%M%S"),
                                                 int.from_bytes(os.urandom(3), "big") % 1000000)
                _handle = _api.command_runner.start_command(cmd, cwd=None, task_id=_tmp_task_id)
                _wait_r = _api.command_runner.wait_or_promote(_handle, _exec_timeout)
                if _wait_r.get("finished"):
                    _output = _api.command_runner.read_tail(_handle, lines=100000)
                    _rc = _wait_r.get("returncode")
                    if _rc == 0:
                        exec_result = f"✅ 命令执行成功:命令:{cmd} 标准输出:{_output} "
                        _api.add_operation_log("AI执行命令", f"执行命令成功:{cmd}")
                    else:
                        exec_result = (f"❌ 命令执行失败:命令:{cmd}，返回码:{_rc}\n"
                                      f"输出（标准输出与标准错误按控制台顺序合并）:{_output}\n"
                                      f"⚠️ 请根据返回码和错误信息分析失败原因、修正命令后重试，不要重复执行完全相同的失败命令")
                        _api.add_operation_log("AI执行命令", f"❌ 命令执行失败:{cmd}，返回码:{_rc}，错误:{_output[:200]}", "error")
                else:
                    _bg_enabled = True
                    try:
                        _bg_enabled = bool(_api.load_config().get("bg_task", {}).get("enabled", True))
                    except Exception:
                        _bg_enabled = True
                    _bg_tid = None
                    if _bg_enabled:
                        _bg_tid = _api.background_task_manager.background_task_manager.register_and_promote(
                            _handle, cmd, session_id)
                    if _bg_tid:
                        exec_result = _api.background_task_manager.background_task_manager.build_promote_text(
                            _bg_tid, cmd, _exec_timeout)
                        _api.add_operation_log("AI执行命令", f"🟢 命令已提升后台运行[{_bg_tid}]:{cmd}", "warning")
                    else:
                        _api.command_runner.terminate_tree(_handle)
                        exec_result = (f"⏱️ 命令执行超时（超过{_exec_timeout}秒未结束），系统已递归终止整棵进程树（taskkill /F /T，cmd及其子进程、孙进程一并结束）:{cmd}\n"
                                      f"终止前输出（最后200行）:{_wait_r.get('tail', '')}\n"
                                      f"建议:①缩小输出范围（加过滤条件/head/tail/Select-Object -First等）；"
                                      f"②改用read_file的start_line/end_line分页读取文件；"
                                      f"③确属长耗时命令，可在配置tool_output.exec_cmd_timeout调大超时秒数")
                        _api.add_operation_log("AI执行命令", f"⏱️ 命令执行超时（{_exec_timeout}秒）已递归终止进程树:{cmd}", "warning")
            except Exception as e:
                exec_result = f"❌ 命令执行失败:{str(e)}向用户说明执行指令后得到结构化信息"
                _api.add_operation_log("AI执行命令", f"❌ 命令执行失败:{str(e)}")
            return _api.truncate_tool_output("exec_cmd", 1, exec_result)

        elif tool_name == "query_background_task":
            _bg_tid = str(params.get("task_id", "") or "").strip()
            _snap = _api.background_task_manager.background_task_manager.query(_bg_tid, session_id)
            if not _snap:
                exec_result = f"❌ 未找到属于当前会话的后台任务:{_bg_tid}（请核对任务ID，或该任务已过保留期被清理）"
            else:
                _tail = _api.background_task_manager.background_task_manager.read_logs(_bg_tid, session_id, 200)
                exec_result = _api.background_task_manager.background_task_manager.build_query_text(_snap, _tail)
            return exec_result

        elif tool_name == "cancel_background_task":
            _bg_tid = str(params.get("task_id", "") or "").strip()
            _snap = _api.background_task_manager.background_task_manager.cancel(_bg_tid, session_id)
            if not _snap:
                exec_result = f"❌ 未找到属于当前会话的后台任务:{_bg_tid}，无法取消（请核对任务ID）"
            else:
                _tail = _api.background_task_manager.background_task_manager.read_logs(_bg_tid, session_id, 200)
                exec_result = _api.background_task_manager.background_task_manager.build_cancel_text(_snap, _tail)
                _api.add_operation_log("AI执行命令", f"🛑 用户手动终止后台任务[{_bg_tid}]")
            return exec_result

        elif tool_name == "write_file":
            file_name = str(params.get("file_name", "") or "").strip()
            content = params.get("content", "")
            write_path = _api.get_real_physical_path(file_name)
            forbidden, reason = _api.is_path_forbidden(write_path)
            if forbidden:
                _api.add_file_operation_log("write", file_name, "fail", reason)
                return f"⚠️ {reason}，禁止写入"
            try:
                os.makedirs(os.path.dirname(write_path), exist_ok=True)
                with open(write_path, "w", encoding="utf-8") as f:
                    f.write(content)
                write_abs_path = _api.get_real_physical_path(write_path)
                _api.add_operation_log("文件操作", f"✅ 写入文件成功:{file_name}，绝对路径:{write_abs_path}")
                cp = _api.CURRENT_PROJECT
                if cp["project_root"] and write_path.startswith(os.path.normpath(cp["project_root"]).replace("\\", "/")):
                    rel_file_name = os.path.relpath(write_path, cp["project_root"]).replace("\\", "/")
                    if rel_file_name not in cp["file_list"]:
                        cp["file_list"].append(rel_file_name)
                    try:
                        _api.project_manual_manager.update_manual_detail_table(cp["manual_path"])
                    except Exception:
                        pass
                    _api.update_current_project_file_list()
                try:
                    _api.rag_manager.add_file(write_path)
                except Exception:
                    pass
                try:
                    _api.broadcast_file_change()
                except Exception:
                    pass
                return f"✅ 写入文件成功:{file_name}（绝对路径:{write_abs_path}）"
            except Exception as e:
                _api.add_operation_log("文件操作", f"❌ 写入文件失败:{str(e)}，路径:{write_path}", "error")
                return f"❌ 写入文件失败:{str(e)}，路径:{write_path}"

        elif tool_name == "create_file":
            path = str(params.get("path", "") or "").strip()
            raw_is_dir = params.get("is_dir", False)
            if isinstance(raw_is_dir, str):
                is_dir = raw_is_dir.strip().lower() == "true"
            else:
                is_dir = bool(raw_is_dir)
            content = params.get("gzt_newtext") or params.get("content", "")
            create_path = _api.get_real_physical_path(path)
            forbidden, reason = _api.is_path_forbidden(create_path)
            if forbidden:
                _api.add_file_operation_log("create", path, "fail", reason)
                return f"⚠️ {reason}，禁止创建"
            if os.path.exists(create_path):
                _api.add_file_operation_log("create", path, "fail", "路径已存在")
                return f"❌ 创建失败:路径【{path}】已存在（标准化后路径:{create_path}）"
            try:
                if is_dir:
                    os.makedirs(create_path, exist_ok=True)
                    create_abs_path = _api.get_real_physical_path(create_path)
                    _api.add_operation_log("文件操作", f"✅ 文件夹创建成功:{path}，绝对路径:{create_abs_path}")
                    exec_result = f"✅ 文件夹创建成功:{path}（绝对路径:{create_abs_path}）"
                else:
                    os.makedirs(os.path.dirname(create_path), exist_ok=True)
                    with open(create_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    create_abs_path = _api.get_real_physical_path(create_path)
                    if content:
                        _api.add_operation_log("文件操作", f"✅ 文件创建+写入成功:{path}，绝对路径:{create_abs_path}")
                        exec_result = f"✅ 文件创建+写入成功:{path}（绝对路径:{create_abs_path}），共写入{len(content)}字符"
                    else:
                        _api.add_operation_log("文件操作", f"✅ 空文件创建成功:{path}，绝对路径:{create_abs_path}")
                        exec_result = f"✅ 空文件创建成功:{path}（绝对路径:{create_abs_path}）"
                cp = _api.CURRENT_PROJECT
                if cp["project_root"] and create_path.startswith(os.path.normpath(cp["project_root"]).replace("\\", "/")):
                    try:
                        _api.project_manual_manager.update_manual_detail_table(cp["manual_path"])
                    except Exception:
                        pass
                    _api.update_current_project_file_list()
                try:
                    _api.rag_manager.add_file(create_path)
                except Exception:
                    pass
                try:
                    _api.broadcast_file_change()
                except Exception:
                    pass
                return exec_result
            except Exception as e:
                _api.add_operation_log("文件操作", f"❌ 创建失败:{str(e)}，路径:{create_path}", "error")
                return f"❌ 创建失败:{str(e)}，路径:{create_path}"

        elif tool_name == "delete_file":
            file_name = str(params.get("file_name", "") or "").strip()
            delete_path = _api.get_real_physical_path(file_name)
            forbidden, reason = _api.is_path_forbidden(delete_path)
            if forbidden:
                _api.add_file_operation_log("delete", file_name, "fail", reason)
                return f"⚠️ {reason}，禁止删除"
            if not os.path.exists(delete_path):
                _api.add_file_operation_log("delete", file_name, "fail", "路径不存在")
                return f"❌ 删除失败:路径【{file_name}】不存在（标准化后路径:{delete_path}）"
            try:
                if os.path.isdir(delete_path):
                    import shutil
                    shutil.rmtree(delete_path)
                else:
                    os.remove(delete_path)
                delete_abs_path = _api.get_real_physical_path(delete_path)
                _api.add_operation_log("文件操作", f"✅ 删除成功:{file_name}，绝对路径:{delete_abs_path}")
                cp = _api.CURRENT_PROJECT
                if cp["project_root"] and delete_path.startswith(os.path.normpath(cp["project_root"]).replace("\\", "/")):
                    rel_file_name = os.path.relpath(delete_path, cp["project_root"]).replace("\\", "/")
                    if rel_file_name in cp["file_list"]:
                        cp["file_list"].remove(rel_file_name)
                    try:
                        _api.project_manual_manager.update_manual_detail_table(cp["manual_path"])
                    except Exception:
                        pass
                    _api.update_current_project_file_list()
                try:
                    _api.rag_manager.delete_file(delete_path)
                except Exception:
                    pass
                try:
                    _api.broadcast_file_change()
                except Exception:
                    pass
                return f"✅ 删除成功:{file_name}（绝对路径:{delete_abs_path}）"
            except Exception as e:
                _api.add_operation_log("文件操作", f"❌ 删除失败:{str(e)}，路径:{delete_path}", "error")
                return f"❌ 删除失败:{str(e)}，路径:{delete_path}"

        elif tool_name == "rename_file":
            old_path = str(params.get("old_path", "") or "").strip()
            new_name = str(params.get("new_name", "") or "").strip()
            old_abs_path = _api.get_real_physical_path(old_path)
            new_abs_path = os.path.join(os.path.dirname(old_abs_path), new_name).replace("\\", "/")
            if not os.path.exists(old_abs_path):
                _api.add_file_operation_log("rename", old_path, "fail", "原路径不存在")
                return f"❌ 重命名失败:原路径【{old_path}】不存在（标准化后路径:{old_abs_path}）"
            if os.path.exists(new_abs_path):
                _api.add_file_operation_log("rename", old_path, "fail", "目标路径已存在")
                return f"❌ 重命名失败:目标路径【{new_name}】已存在（标准化后路径:{new_abs_path}）"
            forbidden_old, reason_old = _api.is_path_forbidden(old_abs_path)
            if forbidden_old:
                _api.add_file_operation_log("rename", old_path, "fail", reason_old)
                return f"⚠️ {reason_old}，禁止重命名"
            forbidden_new, reason_new = _api.is_path_forbidden(new_abs_path)
            if forbidden_new:
                _api.add_file_operation_log("rename", old_path, "fail", reason_new)
                return f"⚠️ {reason_new}，目标路径禁止操作"
            try:
                os.rename(old_abs_path, new_abs_path)
                new_abs_path_std = _api.get_real_physical_path(new_abs_path)
                _api.add_operation_log("文件操作", f"✅ 重命名成功:{old_path} → {new_name}，新路径:{new_abs_path_std}")
                cp = _api.CURRENT_PROJECT
                if cp["project_root"] and old_abs_path.startswith(os.path.normpath(cp["project_root"]).replace("\\", "/")):
                    rel_old_path = os.path.relpath(old_abs_path, cp["project_root"]).replace("\\", "/")
                    rel_new_path = os.path.relpath(new_abs_path, cp["project_root"]).replace("\\", "/")
                    if rel_old_path in cp["file_list"]:
                        cp["file_list"].remove(rel_old_path)
                    if rel_new_path not in cp["file_list"]:
                        cp["file_list"].append(rel_new_path)
                    try:
                        _api.project_manual_manager.update_manual_detail_table(cp["manual_path"])
                    except Exception:
                        pass
                    _api.update_current_project_file_list()
                try:
                    _api.rag_manager.delete_file(old_abs_path)
                except Exception:
                    pass
                try:
                    _api.rag_manager.add_file(new_abs_path)
                except Exception:
                    pass
                try:
                    _api.broadcast_file_change()
                except Exception:
                    pass
                return f"✅ 重命名成功:{old_path} → {new_name}（新路径绝对路径:{new_abs_path_std}）"
            except Exception as e:
                _api.add_operation_log("文件操作", f"❌ 重命名失败:{str(e)}，原路径:{old_abs_path}，新路径:{new_abs_path}", "error")
                return f"❌ 重命名失败:{str(e)}，原路径:{old_abs_path}，新路径:{new_abs_path}"

        elif tool_name == "edit_file":
            file_name = str(params.get("file_name", "") or "").strip()
            operation = str(params.get("operation", "") or "").strip()
            target_block = params.get("gzt_anchor") or params.get("target_block", "")
            content = params.get("gzt_newtext") or params.get("content", "")
            formatted_target_block = _api.safe_escape_restore(target_block)
            formatted_content = _api.safe_escape_restore(content)
            if not file_name or not operation:
                return "⚠️ 参数错误:file_name和operation为必填参数"
            allowed_operations = ["delete", "insert_before", "insert_after", "replace", "insert_start", "insert_end"]
            if operation not in allowed_operations:
                return f"⚠️ 不支持的操作类型:{operation}，可选值:{','.join(allowed_operations)}"
            if operation not in ["insert_start", "insert_end"] and not target_block:
                return "⚠️ 参数错误:delete/insert_before/insert_after/replace操作必须传入gzt_anchor参数"
            op_path = _api.get_real_physical_path(file_name)
            forbidden, reason = _api.is_path_forbidden(op_path)
            if forbidden:
                _api.add_file_operation_log(operation, file_name, "fail", reason)
                return f"⚠️ {reason}，禁止操作，请向用户说明"
            cp = _api.CURRENT_PROJECT
            if cp["project_root"] and op_path.startswith(os.path.normpath(cp["project_root"]).replace("\\", "/")):
                rel_file_name = os.path.relpath(op_path, cp["project_root"]).replace("\\", "/")
                if rel_file_name not in cp["file_list"] and os.path.exists(op_path):
                    cp["file_list"].append(rel_file_name)
                    _api.update_current_project_file_list()
            try:
                success, msg = _api.intelligent_file_editor.edit_file(
                    file_path=op_path,
                    operation=operation,
                    target_block=formatted_target_block,
                    content=formatted_content
                )
                if success:
                    if os.path.isabs(file_name):
                        op_abs_path = _api.get_real_physical_path(file_name)
                    else:
                        _base = cp["project_root"] if cp["project_root"] else _api.REPOSITORY_PATH
                        op_abs_path = _api.get_real_physical_path(os.path.relpath(op_path, _base))
                    _api.add_operation_log("文件操作", f"✅ {operation}操作成功:{file_name}，绝对路径:{op_abs_path}")
                    try:
                        _api.rag_manager.add_file(op_path)
                    except Exception:
                        pass
                    _api.update_current_project_file_list()
                    try:
                        _api.broadcast_file_change()
                    except Exception:
                        pass
                    return (f"✅ {operation}操作成功:{file_name}\n{msg}\n"
                            f"📂 文件绝对路径:{op_abs_path}\n操作完成后读取文件确认修改状态")
                else:
                    _api.add_operation_log("文件操作", f"❌ {operation}操作失败:{file_name}，错误:{msg}", "error")
                    return (f"❌ {operation}操作失败:{file_name}\n{msg}\n"
                            f"⚠️ 分析工具调用失败原因:\n"
                            f"1.指令执行错误（锚点错误，:符号大小写错误导致匹配不上或者是锚点内容太少缺少唯一性，锚点内容必须整行），请向用户说明并执行一次重试；\n"
                            f"2. 工作台系统错误无法执行，已经执行第二次重试，请停止任务执行并向用户说明，给出可能性分析。")
            except Exception as e:
                _api.add_operation_log("文件操作", f"❌ 编辑文件异常:{file_name}，错误:{str(e)}", "error")
                return (f"❌ 编辑文件异常:{str(e)}\n"
                        f"⚠️ 分析工具调用失败原因:\n"
                        f"1. 指令执行错误（锚点错误，:符号大小写错误导致匹配不上或者是锚点内容太少缺少唯一性锚点内容必须整行），请向用户说明并执行一次重试；\n"
                        f"2. 工作台系统错误无法执行，已经执行第二次重试，请停止任务执行并向用户说明，给出可能性分析。")

        else:
            # 判断是否是插件（未识别的工具名 -> 动态加载 plugin 目录下的插件）
            try:
                plugin_config = _api.tool_template_manager.get_plugin_config(tool_name)
            except Exception:
                plugin_config = None
            if plugin_config:
                try:
                    params_str = json.dumps(params, ensure_ascii=False)
                    start_log_content = f"🔄 开始执行插件【{plugin_config['name']}({tool_name})】，参数:{params_str}"
                    _api.add_operation_log("插件执行", start_log_content)
                    try:
                        _api.push_sse_message(session_id, {
                            "type": "operation_log",
                            "oper_type": "插件执行",
                            "content": start_log_content,
                            "status": "running",
                            "timestamp": time.time()
                        })
                    except Exception:
                        pass
                    plugin_path = os.path.join(_api.tool_template_manager.PLUGIN_DIR, tool_name, plugin_config["entry"])
                    if not os.path.exists(plugin_path):
                        fail_log_content = f"❌ 执行插件【{plugin_config['name']}】失败:插件入口文件不存在:{plugin_config['entry']}"
                        _api.add_operation_log("插件执行", fail_log_content, "error")
                        try:
                            _api.push_sse_message(session_id, {
                                "type": "operation_log",
                                "oper_type": "插件执行",
                                "content": fail_log_content,
                                "status": "error",
                                "timestamp": time.time()
                            })
                        except Exception:
                            pass
                        return f"❌ 插件入口文件不存在:{plugin_config['entry']}"
                    import importlib.util
                    import sys as _sys
                    plugin_module_name = f"plugin_{tool_name}"
                    if plugin_module_name in _sys.modules:
                        del _sys.modules[plugin_module_name]
                    spec = importlib.util.spec_from_file_location(plugin_module_name, plugin_path)
                    plugin_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(plugin_module)
                    plugin_module.plugin_config = plugin_config["merged_config"]
                    exec_result = plugin_module.run(params)
                    result_str = str(exec_result)
                    success_log_content = f"✅ 执行插件【{plugin_config['name']}】成功，返回结果:{result_str[:200]}{'...' if len(result_str) > 200 else ''}"
                    _api.add_operation_log("插件执行", success_log_content)
                    try:
                        _api.push_sse_message(session_id, {
                            "type": "operation_log",
                            "oper_type": "插件执行",
                            "content": success_log_content,
                            "status": "success",
                            "timestamp": time.time()
                        })
                    except Exception:
                        pass
                    plugin_exec_result = f"✅ 插件执行成功:{tool_name}\n{exec_result}"
                    return _api.truncate_tool_output(tool_name, 1, plugin_exec_result)
                except Exception as e:
                    fail_log_content = f"❌ 执行插件【{plugin_config.get('name', tool_name)}】异常:{str(e)}"
                    _api.add_operation_log("插件执行", fail_log_content, "error")
                    try:
                        _api.push_sse_message(session_id, {
                            "type": "operation_log",
                            "oper_type": "插件执行",
                            "content": fail_log_content,
                            "status": "error",
                            "timestamp": time.time()
                        })
                    except Exception:
                        pass
                    return f"❌ 插件执行失败:{str(e)}"

        # ---- P4-DONE ----
        return f"❌ 未识别的工具:{tool_name}"
    except Exception as e:
        return f"❌ 工具执行异常:{str(e)[:300]}"


# ============================ 任务执行线程（含三条硬终止） ============================

_ABORT_FLAG: Dict[str, bool] = {}

def is_aborted(task_id: str) -> bool:
    return bool(_ABORT_FLAG.get(task_id))

def request_abort(task_id: str) -> Dict[str, Any]:
    """手动中止:置标志 + 走终态「已中止」"""
    meta = get_task(task_id)
    if not meta:
        return {"ok": False, "msg": "任务不存在"}
    if meta.get("state_name") in TERMINAL_STATES:
        return {"ok": False, "msg": f"任务已处于终态:{meta.get('state_name')}"}
    _ABORT_FLAG[task_id] = True
    finalize(task_id, "已中止", "用户手动中止")
    return {"ok": True, "task_id": task_id, "state": "已中止"}

def _run_task(task_id: str, forced_slot: Optional[int] = None) -> None:
    """后台工作线程:派发 → 开发 → 审查 → 裁决,含三条硬终止

    forced_slot 非空时:直接按该槽位派发（甲-2 mention 定槽，跳过路由）；
    为空时:保持原逻辑（_route_by_main 主控自主分发）—— 旧链路零改动。
    """
    meta = get_task(task_id)
    if not meta:
        return
    limits = _limits()
    deadline = float(meta.get("deadline_at") or (time.time() + limits["task_timeout_sec"]))
    pool = build_role_pool(with_probe=True)
    if not pool:
        finalize(task_id, "已驳回", "无可用角色:字段未填全或探针全部失败")
        return

    forced_in_pool = (forced_slot is not None and
                      any(int(it["slot"]) == int(forced_slot) for it in pool))
    forced_available = (forced_in_pool and
                        any(int(it["slot"]) == int(forced_slot) and it.get("available", True) for it in pool))
    if forced_in_pool:
        dev_slot = int(forced_slot)
        if forced_available:
            advance(task_id, STATE_DISPATCH_PENDING, f"主控已选定开发槽位 {dev_slot}", dev_slot=dev_slot)
        else:
            # 显式 @角色 指定槽位时以指定为准:探针失败降级为告警,不驳回
            advance(task_id, STATE_DISPATCH_PENDING,
                    f"主控已选定开发槽位 {dev_slot}（探针未通过,按显式指定继续）", dev_slot=dev_slot)
    else:
        dev_slot = _route_by_main(meta, pool, "开发任务执行", "开发")
        if dev_slot is None:
            finalize(task_id, "已驳回", "无法确定开发槽位,已前置拦截（未派发）")
            return
        advance(task_id, STATE_DISPATCH_PENDING, f"主控已选定开发槽位 {dev_slot}", dev_slot=dev_slot)

    while True:
        if is_aborted(task_id):
            return
        if time.time() > deadline:
            finalize(task_id, "超时中止", f"任务总耗时超过 {limits['task_timeout_sec']} 秒")  # 硬终止②
            return

        # ---- 1 开发中 ----
        advance(task_id, STATE_DEV_RUNNING, f"派发开发（槽位 {dev_slot}）")
        dev_prompt = _build_dev_prompt(meta)
        # 项目名（物理隔离依据）+ 主控人设名（前缀用），取值失败一律回退，不影响派发
        _proj = str(meta.get("project_name", "") or "")
        _mp = "玲珑"
        try:
            _ms = _main_slot(pool)
            for _it in (pool or []):
                if int(_it.get("slot", 0) or 0) == int(_ms or 0):
                    _p = str(_it.get("persona_name", "") or "").strip()
                    if _p:
                        _mp = _p
                    break
        except Exception:
            pass
        dev_messages = _build_secondary_messages(dev_slot, _proj, dev_prompt)
        # 记忆文件 1 轮 = 1 条（与主模型 latest_chat_history_{项目}.json 同构）:
        #   content = f"用户问:主控输出（{人设名}）:{dev_prompt}\n回答:{累积正文+工具结果}"
        #   累积片段由 _call_model_with_tools 通过 history_out 按轮填充（每轮 AI 正文 + "工具执行结果:…" 段）,
        #   调用结束在这里一次性落盘;不再拆成 user/assistant 两条,也不再写 header 字段（重复根因一并切除）。
        _history_parts: List[str] = []
        try:
            dev_report = _call_model_with_tools(dev_slot, dev_messages, meta.get("session_id", "default"),
                                                max_rounds=_slot_max_rounds(dev_slot),
                                                task_id=task_id, kind="dev",
                                                history_out=_history_parts,
                                                # 【方案C·串台修复】透传项目名 → 内部 5 处推送通道键带项目维度
                                                project=_proj)
        except Exception as e:
            finalize(task_id, "已中止", f"开发调用失败:{str(e)[:150]}")
            return
        # 一次性落盘 1 条（1 轮）:结构/字段/时间戳/条目粒度 与主模型逐字同构。
        # 累积片段优先用 history_out（每轮 AI 正文 + "工具执行结果:…" 段）,
        # 若模型端未产生任何中间轮（_history_parts 为空）则回退到最后一轮原文 dev_report,
        # 保证 content 里的"回答:"段永不为空。
        # 【修复·根因】逐片段净化再拼接（原「先 join 再整体净化」会把尾部内容吞掉）:
        #   _history_parts 每项语义独立（每轮 AI 正文 / 每轮「工具执行结果:…」段），
        #   而 _purify_secondary_text 的 ⑤⑥⑦⑧⑨ 条正则均以 (?=…|\Z) 收尾 ——
        #   若先 "\n".join 再整体净化，最后一段工具结果的 \Z 会一路吃到字符串末尾，
        #   把它之后的所有 AI 正文（含最终总结 dev_report）整体替换成一行摘要，
        #   导致次级记忆落盘只剩第一次交互（本次线上缺陷的根因）。
        #   逐段净化后，每段 \Z 只作用于本段尾部，AI 正文与工具结果互不侵蚀。
        # 【需求1·落盘前净化】与主模型 api_server.py L2955-2996 逐字同构:
        #   只作用于「本次落盘的 content」——剥离工具调用原文块 + 长内容(读文件/编辑/RAG/命令)压成摘要;
        #   当轮流式(ai_output_stream / ai_reasoning)不经过本函数 → 前端实时显示原样不受影响。
        #   当轮不剥离、只落盘剥离 → 完全符合用户口径。
        _answer_text = "\n".join(
            [_purify_secondary_text(_p) for _p in _history_parts if _p]
        ) or _purify_secondary_text(str(dev_report or ""))
        _append_secondary_msg(
            dev_slot, _proj,
            f"用户问:主控输出（{_mp}）:{dev_prompt}\n回答:{_answer_text}",
        )
        push_secondary_summary(meta.get("session_id", "default"),
                               f"#{task_id} 开发回报完成:{str(dev_report)[:120]}")
        # 开发回报原样推给开发自己的窗口（不加 [开发回报|任务 #x] 包装）
        # 【方案C·串台修复】透传 _proj → 通道键 sec_{dev_slot}_{项目}，项目A 与 项目B 物理隔离
        push_secondary_event(meta.get("session_id", "default"), "report",
                             str(dev_report or ""), slot=dev_slot, project=_proj)
        # 【修复·根因级】sender 不再硬编码 "开发":按真实派发的开发槽位 dev_slot，
        # 从角色池 pool 里取该槽位的 persona_name（人设名）动态传入，
        # 让主对话页 PageO0x2f.vue 显示「来自<真实角色名>的消息」，
        # 而不是不论派给谁都恒为「来自开发的消息」。
        # · 字段名与 build_role_pool() 出参严格一致（slot / display_name / persona_name / available），
        #   取法复用项目内既有写法 _it.get("persona_name")，不新造字段、不硬编码。
        # · 兜底:槽位不在池中 / persona_name 为空 / 取值异常 → 回退 "开发"，
        #   保证 sender 永不为空 —— 前端 m.role || '次级' 不会退化成"来自次级的消息"。
        # · 只读遍历 pool，不修改任何状态，异常全部吞掉，绝不影响主流程闭环。
        _dev_sender = "开发"
        try:
            for _it in (pool or []):
                if int(_it.get("slot", 0) or 0) == int(dev_slot):
                    _pn = str(_it.get("persona_name", "") or "").strip()
                    if _pn:
                        _dev_sender = _pn
                    break
        except Exception:
            _dev_sender = "开发"
        # 【2026-10-13 根因修复·取消静默闭环】
        # 按用户口径:代码不得替模型判「任务已闭环」——闭环只能由模型自己给出总结（无工具调用）体现。
        #   若 dev_report 里仍残留未闭合工具块开始标记，说明模型输出被截断、且重发至轮次上限
        #   仍未能自愈 → 属「异常中止」而非「已完成」:
        #   ① 强制把异常回报推给主控（报文加 @主控 前缀绕过门控），让主控能感知并决策重派;
        #   ② 任务状态标「已中止」，不再伪标「已闭环」，让排查能一眼区分真完成/假完成。
        # 正常路径（模型给出总结、无残留标记）保持原样:@主控 门控 → 唤醒主控 → 已闭环。
        _abnormal = bool(_TC_OPEN in str(dev_report or ""))
        if _abnormal:
            _warn = ("@主控 " + f"⚠️【任务异常中止】#{task_id}\n"
                     f"任务因「模型输出被截断（工具调用块不完整）」未能完成，请重新派发。\n"
                     f"已输出内容（截断处）:\n{str(dev_report or '')[:800]}")
            push_secondary_to_main(meta.get("session_id", "default"), _dev_sender, _warn, task_id,
                                   slot=dev_slot)
        else:
            # 仅当开发输出里出现 @主控/@玲珑 时，才把该段原样送到主对话窗口通知主模型（不自动唤醒、不自动回复）
            push_secondary_to_main(meta.get("session_id", "default"), _dev_sender, str(dev_report or ""), task_id,
                                   slot=dev_slot)

        # ---- 2 派发结束:自动流水线已按用户口径移除（不再转审查/不再主控决策/不再自动续派/不再主控裁决/不再回炉） ----
        # 开发回报已通过 push_secondary_event(slot=dev_slot) 推到开发自己的窗口,本任务到此结束
        if _abnormal:
            finalize(task_id, "已中止", f"模型输出截断(未完成):#{task_id}")
        else:
            finalize(task_id, "已闭环", f"开发回报完成:#{task_id}")
        return

# ============================ 超时守护（硬终止②,兜住线程外挂） ============================

def tick_timeout() -> List[str]:
    """扫描非终态任务,超过 deadline 的强制「超时中止」;返回被中止的 task_id 列表"""
    _ensure_dirs()
    killed: List[str] = []
    if not os.path.isdir(TASKS_DIR):
        return killed
    now = time.time()
    for name in os.listdir(TASKS_DIR):
        meta = SessionWriter.read(os.path.join(TASKS_DIR, name, "meta.json"), default=None)
        if not isinstance(meta, dict):
            continue
        if meta.get("state_name") in TERMINAL_STATES:
            continue
        if now > float(meta.get("deadline_at", 0) or 0):
            tid = str(meta.get("task_id", name))
            _ABORT_FLAG[tid] = True
            finalize(tid, "超时中止", "守护线程判定总耗时超限")
            killed.append(tid)
    return killed

def start_timeout_guard(interval: int = 30) -> threading.Thread:
    """启动超时守护线程（daemon）"""
    def _loop():
        while True:
            try:
                tick_timeout()
            except Exception as e:
                print(f"[Orchestrator] 超时守护异常: {e}")
            time.sleep(max(5, int(interval or 30)))
    t = threading.Thread(target=_loop, daemon=True, name="orch-timeout-guard")
    t.start()
    return t

# ============================ 对外接口（供 api_server 调用） ============================

def submit_task(requirement: str, session_id: str = "default",
                project_name: str = "default") -> Dict[str, Any]:
    """提交编排任务:建任务 + 异步派发,立即返回 task_id（不阻塞 HTTP）

    - project_name（新增,可选）:任务归属项目名，透传 create_task，实现次级对话按项目隔离；
      不传 → 视为 default（旧调用零回归）。
    """
    req = str(requirement or "").strip()
    if not req:
        return {"ok": False, "msg": "需求不能为空"}
    pool = build_role_pool()
    if not pool:
        return {"ok": False,
                "msg": "无可用角色:请在模型配置页把 api_url / model_name / api_key / persona_name 填全并保存"}
    meta = create_task(req, session_id, project_name)
    SessionWriter.append(main_session_path(), {
        "role": "user",
        "header": USER_HEADER_TPL.format(session=meta["session_id"], task_id=meta["task_id"]),
        "content": req,
    })
    threading.Thread(target=_run_task, args=(meta["task_id"],),
                     daemon=True, name=f"orch-{meta['task_id']}").start()
    return {"ok": True, "task_id": meta["task_id"],
            "state": meta["state_name"], "role_pool": pool}

def submit_by_mention(requirement: str, session_id: str = "default",
                      target_keyword: str = "",
                      forced_slot: Optional[int] = None,
                      project_name: str = "default") -> Dict[str, Any]:
    """按 mention 派发（甲-2）:由 @角色 命中槽位直接定槽，跳过 _route_by_main。

    - project_name（新增,可选）:任务归属项目名，透传 create_task，实现次级对话按项目隔离；
      不传 → 视为 default（旧调用零回归）。

    - forced_slot 优先（通常由 extract_dispatch_mentions 直接给出，一次匹配）；
    - 未给 forced_slot 时按 target_keyword 兜底匹配；
    - T5:不向主会话追加 user 消息（派发由主模型回复触发，避免与回复重复）；
    - 异步起线程，立即返回 task_id（不阻塞 HTTP）。
    """
    req = str(requirement or "").strip()
    if not req:
        return {"ok": False, "msg": "需求不能为空"}
    pool = build_role_pool()
    if not pool:
        return {"ok": False, "msg": "无可用角色:请检查模型配置"}
    forced = int(forced_slot) if forced_slot is not None else match_role_slot(pool, target_keyword)
    if forced is None:
        return {"ok": False, "msg": f"未匹配到角色:{target_keyword or forced_slot}"}
    if not any(int(it["slot"]) == forced and it.get("available", True) for it in pool):
        return {"ok": False, "msg": f"目标槽位不可用:{forced}"}
    meta = create_task(req, session_id, project_name)
    # 原样派发:把主控回复原文整段送进目标模型窗口（不加系统包装头/槽位号/轮次标记）
    # 【方案C·串台修复】透传 project_name → 通道键 sec_{forced}_{项目}，与前端建连 URL 严格对应
    push_secondary_event(meta.get("session_id", "default"), "dispatch", req, slot=forced,
                         project=project_name)
    threading.Thread(target=_run_task, args=(meta["task_id"], forced),
                     daemon=True, name=f"orch-{meta['task_id']}").start()
    return {"ok": True, "task_id": meta["task_id"],
            "state": meta["state_name"], "forced_slot": forced, "role_pool": pool}

def query_task(task_id: str) -> Dict[str, Any]:
    """查询单任务:meta 快照 + 开发/审查次级会话全文"""
    meta = get_task(task_id)
    if not meta:
        return {"ok": False, "msg": "任务不存在"}
    return {
        "ok": True,
        "data": meta,
        "dev": SessionWriter.read(task_file(task_id, "dev"), default={"messages": []}),
        "review": SessionWriter.read(task_file(task_id, "review"), default={"messages": []}),
    }

def list_tasks(session_id: Optional[str] = None) -> Dict[str, Any]:
    """列出会话下全部任务（按 task_id 升序）"""
    _ensure_dirs()
    sid = _safe_name(session_id) if session_id else None
    items: List[Dict[str, Any]] = []
    if os.path.isdir(TASKS_DIR):
        for name in sorted(os.listdir(TASKS_DIR)):
            meta = SessionWriter.read(os.path.join(TASKS_DIR, name, "meta.json"), default=None)
            if not isinstance(meta, dict):
                continue
            if sid and meta.get("session_id") != sid:
                continue
            items.append({k: meta.get(k) for k in
                          ("task_id", "state_name", "rework_count",
                           "degraded_review", "created_at", "updated_at")})
    items.sort(key=lambda x: str(x.get("task_id", "")))
    return {"ok": True, "data": items}

def get_secondary_history(session_id: str = "default", slot: int = 0,
                          project_name: str = "") -> Dict[str, Any]:
    """B-1:次级对话页历史回读（补 SSE 无回溯缺口）

    - project_name（新增,可选）:非空时多筛一层 meta.project_name（「项目 × 槽位」双维度隔离）；
      不传 → 保持原行为（旧调用零回归）；旧任务 meta 无该字段 → 视为 default。

    - 遍历 TASKS_DIR:筛出「meta.session_id == 本会话」且「dev_slot / review_slot == 目标 slot」的任务；
    - 读对应 task_file(task_id, "dev"|"review") 的 messages，按任务 created_at 升序合并；
    - 每条返回 {task_id, kind, role, header, content, created_at}，前端按 role 渲染 dispatch / report。
    """
    sid = _safe_name(session_id) if session_id else "default"
    want = int(slot or 0)
    items: List[Dict[str, Any]] = []
    if want > 0:
        # 直读单文件（物理隔离:文件名含项目名与角色名），不再遍历任务目录筛 meta
        # 翻译层:新格式（纯数组 + f"用户问:…\n回答:…"）→ 拆回前端认识的
        #   {role, content, created_at} 两条（user=左侧派发 / assistant=右侧回报），
        #   老格式（{role, content, ts, header, msg_type}）→ 原样透传，前端渲染规则零改动。
        for m in _load_secondary_history(want, str(project_name or "")):
            if not isinstance(m, dict):
                continue
            _c = str(m.get("content") or "")
            _ts = m.get("timestamp") or m.get("ts") or 0
            if "\n回答:" in _c:
                _ask_raw, _ans_raw = _c.split("\n回答:", 1)
                _ask = _ask_raw[len("用户问:"):] if _ask_raw.startswith("用户问:") else _ask_raw
                _ans = _ans_raw[len("回答:"):] if _ans_raw.startswith("回答:") else _ans_raw
                # 展示净化（方案A·后端剥离）:回读串里可能含「工具执行结果:…」段（落盘时为上下文完整性保留），
                # 这里在送出给前端之前剥掉，保证前端只拿到 AI 正文；
                # 记忆文件 latest_secondary_history_*.json 的落盘内容不受任何影响（口径:拼接内容只进记忆文件）。
                _ans = strip_tool_result_blocks(_ans)
                items.append({
                    "task_id": "",
                    "kind": "dev",
                    "role": "user",
                    "header": "",
                    "content": _ask,
                    "msg_type": "",
                    "created_at": _ts,
                })
                items.append({
                    "task_id": "",
                    "kind": "dev",
                    "role": "assistant",
                    "header": "",
                    "content": _ans,
                    "msg_type": "",
                    "created_at": _ts,
                })
            else:
                items.append({
                    "task_id": "",
                    "kind": "dev",
                    "role": str(m.get("role") or ""),
                    "header": str(m.get("header") or ""),
                    # 展示净化（方案A·后端剥离）:老格式条目同样剥离「工具执行结果:…」段后再送前端
                    "content": strip_tool_result_blocks(_c),
                    "msg_type": str(m.get("msg_type") or ""),
                    "created_at": _ts,
                })
    items.sort(key=lambda x: (x.get("created_at") or 0))
    return {"ok": True, "data": {"session_id": sid, "slot": want, "messages": items}}

def abort_task(task_id: str) -> Dict[str, Any]:
    """中止任务（对外别名）"""
    return request_abort(task_id)

def get_state_machine_summary() -> Dict[str, Any]:
    """状态机说明（供前端/配置页展示）"""
    return {
        "states": [{"code": k, "name": v} for k, v in sorted(STATE_NAMES.items())],
        "terminal": list(TERMINAL_STATES),
        "limits": _limits(),
    }

def get_role_pool_brief() -> Dict[str, Any]:
    """当前角色池快照（供前端展示"谁能接活儿"）"""
    pool = build_role_pool(with_probe=False)
    return {"ok": True, "data": pool, "brief": pool_brief(pool)}