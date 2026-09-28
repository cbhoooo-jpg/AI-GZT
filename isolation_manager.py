# -*- coding: utf-8 -*-
"""
项目信息隔离管理模块（isolation_manager.py）

功能:
    作为"项目信息隔离"清单的唯一读写入口，解决项目运行时产生大量临时文件、
    导致项目手册第二/三章文件明细与注入 AI 上下文的项目文件树"信息无上限膨胀"的问题。

设计原则:
    1. 单向注入:本模块负责隔离清单的磁盘读写，读取后通过
       file_filter_config.set_isolation_context() 把隔离上下文注入统一过滤模块，
       所有扫盘链路（上下文注入/手册同步/RAG索引）自动共享该内存态，调用方零侵入。
    2. 零 IO 复用:file_filter_config 保持纯配置模块（自身不做任何文件读写），
       磁盘路径策略与落盘职责全部收敛在本模块。
    3. 相对路径存储:清单只存"相对仓库根"的路径（统一小写、/ 分隔、无首尾斜杠），
       跨机器、跨盘符稳定；隔离某目录时其全部子孙路径由前缀匹配自动命中。
    4. 只建议不自动:文件数超阈值时仅返回建议标记，由前端提示用户手动隔离，
       避免系统误判导致正常代码被屏蔽。
"""
import os
import json
import sys

# 统一过滤模块:隔离上下文注入到这里，所有扫盘链路共享同一模块对象（含子线程）
import file_filter_config

# 隔离配置文件默认内容（用户可手工编辑 isolation_config.json 调整）
DEFAULT_CONFIG = {
    "enabled": True,           # 隔离功能总开关
    "suggest_threshold": 300,  # 单个目录条目数超过该值时前端提示"建议隔离"
    "paths": []                # 隔离路径清单（相对仓库根，统一小写、/ 分隔）
}


def _get_program_dir() -> str:
    """获取程序目录:打包环境为 exe 同级目录，开发环境为脚本所在目录

    与 config.json 的路径策略完全一致，保证多模块读写同一份配置文件。
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _get_config_path() -> str:
    """获取隔离配置文件绝对路径（与 config.json 同目录）"""
    return os.path.join(_get_program_dir(), "isolation_config.json")


def get_repository_root() -> str:
    """获取当前配置的仓库根目录（统一/分隔、反斜杠已转换）

    优先读取 config.json 的 repository_path；读取失败时回退到程序目录下的"仓库文件夹"。
    """
    program_dir = _get_program_dir()
    config_path = os.path.join(program_dir, "config.json")
    default_repo = os.path.join(program_dir, "仓库文件夹")
    repo_path = default_repo
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            repo_path = cfg.get("repository_path") or default_repo
        except Exception as e:
            print(f"⚠️ 隔离模块读取仓库路径配置失败，使用默认路径:{str(e)}")
    return os.path.normpath(repo_path).replace("\\", "/")


def _normalize_path(rel_path: str) -> str:
    """标准化隔离路径:反斜杠转/、统一小写、去除首尾空白与首尾斜杠"""
    if not rel_path:
        return ""
    return str(rel_path).strip().replace("\\", "/").lower().strip("/")


def load_config() -> dict:
    """读取隔离配置文件

    文件不存在或解析失败时，自动写入默认配置并返回默认值，保证功能开箱可用。
    :return: 配置字典 {enabled, suggest_threshold, paths}
    """
    config_path = _get_config_path()
    if not os.path.exists(config_path):
        # 首次运行:落盘默认配置，方便用户手工编辑
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 字段兜底:缺失字段用默认值补齐，防止用户手工删改后 KeyError
        merged = dict(DEFAULT_CONFIG)
        if isinstance(data, dict):
            merged.update({k: v for k, v in data.items() if k in DEFAULT_CONFIG})
        if not isinstance(merged.get("paths"), list):
            merged["paths"] = []
        # 统一标准化存量路径，兼容用户手工编辑时写入的 Windows 反斜杠/大写
        merged["paths"] = [_normalize_path(p) for p in merged["paths"] if _normalize_path(p)]
        return merged
    except Exception as e:
        print(f"⚠️ 隔离配置解析失败，使用默认配置:{str(e)}")
        return dict(DEFAULT_CONFIG)


def save_config(data: dict) -> bool:
    """原子写入隔离配置文件:先写临时文件再 os.replace，避免半写状态

    :param data: 完整配置字典
    :return: 是否写入成功
    """
    config_path = _get_config_path()
    tmp_path = config_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, config_path)
        return True
    except Exception as e:
        print(f"⚠️ 隔离配置写入失败:{str(e)}")
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return False


def list_paths() -> dict:
    """查询当前隔离清单与阈值配置（供接口/前端展示）

    :return: {"enabled": bool, "suggest_threshold": int, "paths": [...]}
    """
    cfg = load_config()
    return {
        "enabled": cfg.get("enabled", True),
        "suggest_threshold": cfg.get("suggest_threshold", 300),
        "paths": list(cfg.get("paths", [])),
    }


def add_path(rel_path: str) -> dict:
    """把指定路径加入隔离清单（目录则整棵子树由前缀匹配自动命中）

    :param rel_path: 相对仓库根的路径或绝对路径（内部自动转相对路径）
    :return: 最新清单
    """
    normalized = _to_repo_relative(rel_path)
    if not normalized:
        return list_paths()
    cfg = load_config()
    paths = list(cfg.get("paths", []))
    if normalized not in paths:
        paths.append(normalized)
    cfg["paths"] = sorted(set(paths))
    save_config(cfg)
    refresh_injection()
    return list_paths()


def remove_path(rel_path: str) -> dict:
    """从隔离清单移除指定路径

    同时清理其所有子路径，避免残留悬挂项导致"已解除却仍被拦截"。
    :param rel_path: 相对仓库根的路径或绝对路径
    :return: 最新清单
    """
    normalized = _to_repo_relative(rel_path)
    cfg = load_config()
    if normalized:
        prefix = normalized + "/"
        cfg["paths"] = [
            p for p in cfg.get("paths", [])
            if p != normalized and not p.startswith(prefix)
        ]
        save_config(cfg)
        refresh_injection()
    return list_paths()


def _to_repo_relative(path: str) -> str:
    """把入参统一转成"相对仓库根"的标准化相对路径

    支持两种入参:①前端传来的仓库相对路径（如"项目A/output"）；
    ②绝对路径（如"D:/AI仓库文件夹/项目A/output"），自动剥离仓库根前缀。
    """
    if not path:
        return ""
    raw = str(path).strip().replace("\\", "/")
    repo_root = get_repository_root().replace("\\", "/").lower()
    lower_raw = raw.lower()
    # 绝对路径:剥离仓库根前缀，得到相对路径
    if lower_raw == repo_root:
        return ""
    if lower_raw.startswith(repo_root + "/"):
        raw = raw[len(repo_root) + 1:]
    elif os.path.isabs(raw):
        # 非本仓库的绝对路径:尝试用 relpath 兜底（跨盘符时返回原值，此处直接放弃）
        try:
            rel = os.path.relpath(raw, get_repository_root())
            if rel.startswith(".."):
                return ""
            raw = rel
        except ValueError:
            return ""
    return _normalize_path(raw)


def refresh_injection() -> None:
    """把磁盘上的隔离清单注入统一过滤模块（内存态）

    调用时机:①程序启动时；②清单每次变更后。
    所有扫盘链路 import 的是同一个 file_filter_config 模块对象，
    因此注入一次即全部生效（含 auto_sync_monitor 子线程）。
    """
    cfg = load_config()
    repo_root = get_repository_root()
    if not cfg.get("enabled", True):
        # 总开关关闭:注入空清单，等价于不隔离
        file_filter_config.set_isolation_context(repo_root, [])
        return
    file_filter_config.set_isolation_context(repo_root, cfg.get("paths", []))


def check_suggest(total_count: int) -> bool:
    """根据阈值判断是否需要提示用户"建议隔离"

    :param total_count: 当前目录下的条目数
    :return: True 表示超过阈值，建议前端提示隔离（只提示，不自动执行）
    """
    cfg = load_config()
    if not cfg.get("enabled", True):
        return False
    try:
        threshold = int(cfg.get("suggest_threshold", 300))
    except (TypeError, ValueError):
        threshold = 300
    return total_count > threshold