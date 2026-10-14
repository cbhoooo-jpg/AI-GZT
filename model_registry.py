# -*- coding: utf-8 -*-
"""多模型客户端注册表（阶段3）:按 slot 管理 9 个独立 LLM 客户端，替代全局单例。"""
import os
import sys
import json
import threading
from typing import Dict, Any, Optional, List

if getattr(sys, 'frozen', False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_CONFIG_PATH = os.path.join(_BASE_DIR, "models_config.json")

# 运行时默认值（可由 models_config.json 顶层 runtime 节覆盖，不硬编码）
_DEFAULT_RUNTIME = {"max_concurrency": 3, "retry": 1}

_clients: Dict[int, Dict[str, Any]] = {}
_clients_lock = threading.Lock()
_sem: Optional[threading.Semaphore] = None
_sem_limit: int = 0
_sem_lock = threading.Lock()


def load_models_config() -> Dict[str, Any]:
    """读取 models_config.json 全文；缺失/损坏时返回安全默认结构"""
    if not os.path.exists(MODELS_CONFIG_PATH):
        return {"version": 1, "models": [], "runtime": dict(_DEFAULT_RUNTIME)}
    try:
        with open(MODELS_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"[ModelRegistry] models_config.json 解析失败: {e}")
        return {"version": 1, "models": [], "runtime": dict(_DEFAULT_RUNTIME)}


def get_runtime() -> Dict[str, Any]:
    """读取 runtime 节（并发上限/重试次数），缺失字段用默认值兜底"""
    runtime = load_models_config().get("runtime") or {}
    result = dict(_DEFAULT_RUNTIME)
    if isinstance(runtime, dict):
        for k in ("max_concurrency", "retry"):
            v = runtime.get(k)
            if isinstance(v, int) and v >= 0:
                result[k] = v
    return result


def get_slot_config(slot: int) -> Dict[str, Any]:
    """读取指定槽位的完整配置；未找到时返回空字典"""
    data = load_models_config()
    for m in data.get("models", []) or []:
        if isinstance(m, dict):
            try:
                if int(m.get("slot", 0)) == int(slot):
                    return m
            except (TypeError, ValueError):
                continue
    return {}


def _config_signature(cfg: Dict[str, Any]) -> str:
    """生成槽位配置指纹（用于判断缓存客户端是否需要重建）"""
    keys = ("api_url", "model_name", "api_key", "timeout")
    return json.dumps({k: cfg.get(k) for k in keys}, sort_keys=True, ensure_ascii=False)


def _build_client(cfg: Dict[str, Any]):
    """按槽位配置构造独立客户端（函数内延迟导入 openai/httpx，打包安全；trust_env=False 禁用系统代理）"""
    api_key = cfg.get("api_key", "")
    base_url = str(cfg.get("api_url", "") or "").rstrip("/")
    if base_url.endswith("/chat/completions"):
        base_url = base_url[: -len("/chat/completions")]
    timeout = cfg.get("timeout", 200)
    try:
        timeout_val = int(timeout)
    except (TypeError, ValueError):
        timeout_val = 200
    from openai import OpenAI
    import httpx
    http_client = httpx.Client(timeout=timeout_val, trust_env=False)
    return OpenAI(api_key=api_key, base_url=base_url, http_client=http_client)


def get_client(slot: int):
    """按 slot 返回独立客户端（惰性创建 + 缓存 + 锁保护）；配置变更时自动重建"""
    slot = int(slot)
    cfg = get_slot_config(slot)
    signature = _config_signature(cfg)
    with _clients_lock:
        cached = _clients.get(slot)
        if cached and cached.get("signature") == signature and cached.get("client") is not None:
            return cached["client"]
    client = _build_client(cfg)
    with _clients_lock:
        _clients[slot] = {
            "client": client,
            "signature": signature,
            "model_name": cfg.get("model_name", ""),
        }
    return client


def invalidate(slot: int) -> None:
    """清除指定槽位缓存（保存配置后调用，热更新范围隔离）"""
    try:
        slot = int(slot)
    except (TypeError, ValueError):
        return
    with _clients_lock:
        _clients.pop(slot, None)


def invalidate_all() -> None:
    """清除全部槽位缓存"""
    with _clients_lock:
        _clients.clear()


def list_roles() -> List[Dict[str, Any]]:
    """返回已填写 persona_name 的槽位（与 /api/models/roles 现有 GET 口径一致）"""
    data = load_models_config()
    roles: List[Dict[str, Any]] = []
    for m in data.get("models", []) or []:
        if isinstance(m, dict) and m.get("persona_name"):
            roles.append({"slot": m.get("slot"), "persona_name": m.get("persona_name", "")})
    return roles


def get_semaphore() -> threading.Semaphore:
    """返回并发信号量（上限来自 runtime.max_concurrency，变更时自动重建）"""
    global _sem, _sem_limit
    limit = int(get_runtime().get("max_concurrency", 3))
    if limit <= 0:
        limit = 3
    with _sem_lock:
        if _sem is None or _sem_limit != limit:
            _sem = threading.Semaphore(limit)
            _sem_limit = limit
        return _sem