# -*- coding: utf-8 -*-
"""
Python 符号定位器（ast_symbol_index.py）

功能:
    给 AI 提供"知道符号名 -> 文件 + 起止行 + 签名 + 完整源码"的精确定位能力，
    走 AST 静态解析，零向量编码、零网络请求，毫秒级、结果 100% 准确，
    与 rag_search（模糊语义兜底）形成分工。

设计要点:
    1. 零重依赖:只依赖标准库 + file_filter_config（统一黑名单），
       不 import rag_manager，避免拖入 numpy/faiss/torch 等大体积依赖链；
    2. 仓库路径自读 config.json，读法与 rag_manager.get_repository_path 完全一致
       （含 PyInstaller 打包环境兼容分支）；
    3. 扫描范围:.py 文件，目录/文件过滤复用 file_filter_config 统一黑名单；
    4. 缓存策略:按文件 mtime 失效的内存缓存，不落盘（实时扫描极快，落盘反而引入行号失效坑）；
    5. 提取范围:顶层类、顶层函数、类内方法；补 AsyncFunctionDef、不过滤私有符号；
       嵌套函数不收录（避免深层嵌套噪声）。

对外函数:
    locate_symbol(symbol, file=None, with_content=True) -> dict  # 唯一 AI 可见入口
    clear_cache() -> None                                        # 调试用，清空缓存
"""

import os
import ast
import json
import sys

# 文件扫描噪音过滤统一配置（虚拟环境/打包产物/.git/缓存目录等），与 RAG 扫盘链路复用同一黑名单
import file_filter_config


# ==================== 仓库路径读取（轻量版，与 rag_manager 完全对齐） ====================

def get_repository_path() -> str:
    """动态获取当前配置的仓库路径。

    与 rag_manager.get_repository_path 读法完全一致（含 PyInstaller 兼容分支），
    但不依赖 rag_manager 模块，避免拖入 numpy/faiss/torch 等大体积依赖。
    """
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.json")
    default_repo = os.path.normpath(os.path.join(base_dir, "仓库文件夹")).replace("\\", "/")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            repo_path = config.get("repository_path", default_repo)
            return os.path.normpath(repo_path).replace("\\", "/")
        except Exception as e:
            print(f"[ASTIndex] 读取仓库路径配置失败，使用默认路径: {str(e)}")
    return default_repo


# ==================== 源码读取（编码异常兜底） ====================

def _read_text_with_fallback(abs_path):
    """读取源码文本，UTF-8 解码失败时忽略异常字符兜底。"""
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


# ==================== 位置/签名提取（辅助） ====================

def _node_start_line(node):
    """节点起始行:有装饰器时取装饰器首行（不丢 @ 行），否则取 def/class 行。"""
    start = node.lineno
    deco = getattr(node, "decorator_list", None)
    if deco:
        start = min(start, deco[0].lineno)
    return start


def _signature_from_node(node, lines):
    """截取 def/class 那一整行作为签名（不跨行拼接，稳准）。"""
    idx = node.lineno - 1
    if 0 <= idx < len(lines):
        return lines[idx].strip()
    return ""
# ==================== 符号条目提取（AST） ====================

def _extract_docstring(node):
    """安全提取 docstring（ast.get_docstring 在非模块/类/函数节点上会抛错）。"""
    try:
        return ast.get_docstring(node) or ""
    except Exception:
        return ""


def _end_line_of(node, next_symbol_line, total_lines):
    """节点结束行:优先 end_lineno，缺失时回退到"下一个符号行-1"或文件末行。"""
    end = getattr(node, "end_lineno", None)
    if end:
        return end
    if next_symbol_line is not None and next_symbol_line > node.lineno:
        return next_symbol_line - 1
    return total_lines


def _collect_node(node, lines, parent_class, class_range, top_symbols, next_symbol_line):
    """把单个 AST 节点转换为符号条目字典，追加到 top_symbols。

    parent_class 不为空时视为类内方法（qualified_name 用 Class.method 形式）。
    """
    is_async = isinstance(node, ast.AsyncFunctionDef)
    if isinstance(node, ast.ClassDef):
        node_type = "class"
    elif is_async:
        node_type = "async_function" if parent_class is None else "async_method"
    else:
        node_type = "function" if parent_class is None else "method"

    qualified_name = f"{parent_class}.{node.name}" if parent_class else node.name
    start_line = _node_start_line(node)
    end_line = _end_line_of(node, next_symbol_line, len(lines))

    # 类内方法的所属类区间
    entry_class_range = None
    if parent_class and class_range:
        entry_class_range = {
            "name": class_range["name"],
            "start_line": class_range["start_line"],
            "end_line": class_range["end_line"],
        }

    top_symbols.append({
        "symbol": node.name,
        "qualified_name": qualified_name,
        "type": node_type,
        "start_line": start_line,
        "end_line": end_line,
        "decorators": [
            (getattr(d, "id", None) or getattr(d, "attr", "") or "")
            for d in getattr(node, "decorator_list", []) if d is not None
        ],
        "signature": _signature_from_node(node, lines),
        "docstring": _extract_docstring(node),
        "class_range": entry_class_range,
    })


def _parse_file(abs_path):
    """解析单个 .py 文件，返回该文件内所有符号条目列表（含坐标）。

    语法错误跳过、读取异常兜底，不中断全量扫描。
    """
    try:
        source = _read_text_with_fallback(abs_path)
    except Exception:
        return []
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    lines = source.splitlines()
    entries = []
    # 顶层类、顶层函数/异步函数
    for node in tree.body:
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if isinstance(node, ast.ClassDef):
            start_line = _node_start_line(node)
            end_line = getattr(node, "end_lineno", len(lines))
            class_range = {"name": node.name, "start_line": start_line, "end_line": end_line}
            _collect_node(node, lines, None, None, entries, None)
            # 类内方法（仅一层）
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    _collect_node(sub, lines, node.name, class_range, entries, None)
        else:
            _collect_node(node, lines, None, None, entries, None)
    return entries


# ==================== 文件扫描（复用统一黑名单） ====================

def _scan_py_files(repo_path):
    """扫描仓库内全部 .py 文件绝对路径，复用 file_filter_config 统一黑名单。"""
    results = []
    if not repo_path or not os.path.isdir(repo_path):
        return results
    for root, dirs, files in os.walk(repo_path):
        file_filter_config.prune_walk_dirs(dirs)
        for name in files:
            if file_filter_config.is_noise_file(name):
                continue
            if not name.lower().endswith(".py"):
                continue
            results.append(os.path.join(root, name))
    return results
# ==================== 索引缓存（按文件 mtime 失效，不落盘） ====================

# key=文件绝对路径，value=(mtime, 条目列表)
_CACHE = {}


def _get_index(repo_path):
    """构建/刷新全仓库符号索引，返回 [(abs_path, entry), ...]。

    缓存按文件 mtime 失效:文件未改动则复用已解析条目，改动才重解析；
    已删除的文件自动从缓存中清除。
    """
    py_files = _scan_py_files(repo_path)
    current_set = set(py_files)
    # 清除已不存在文件的缓存
    for stale in list(_CACHE.keys()):
        if stale not in current_set:
            del _CACHE[stale]

    index = []
    for abs_path in py_files:
        try:
            mtime = os.path.getmtime(abs_path)
        except OSError:
            continue
        cached = _CACHE.get(abs_path)
        if cached is not None and cached[0] == mtime:
            entries = cached[1]
        else:
            entries = _parse_file(abs_path)
            _CACHE[abs_path] = (mtime, entries)
        for entry in entries:
            index.append((abs_path, entry))
    return index


def clear_cache():
    """清空符号索引内存缓存（调试用）。"""
    _CACHE.clear()
# ==================== 对外入口:符号定位 ====================

def _make_result(entry, abs_path, repo_path, with_content):
    """把命中条目组装为返回结构（含完整源码，可选关闭省 token）。"""
    rel_path = os.path.relpath(abs_path, repo_path).replace("\\", "/")
    if not rel_path.startswith(".") and not os.path.isabs(rel_path):
        rel_display = rel_path
    else:
        rel_display = os.path.normpath(abs_path).replace("\\", "/")
    result = {
        "symbol": entry["symbol"],
        "qualified_name": entry["qualified_name"],
        "type": entry["type"],
        "file": rel_display,
        "abs_path": os.path.normpath(abs_path).replace("\\", "/"),
        "start_line": entry["start_line"],
        "end_line": entry["end_line"],
        "decorators": entry["decorators"],
        "signature": entry["signature"],
        "docstring": entry["docstring"],
        "class_range": entry["class_range"],
        "content": "",
    }
    if with_content:
        try:
            source = _read_text_with_fallback(abs_path)
            lines = source.splitlines()
            s = max(0, entry["start_line"] - 1)
            e = min(len(lines), entry["end_line"])
            result["content"] = "\n".join(lines[s:e])
        except Exception:
            result["content"] = ""
    return result


def _match_entries(index, symbol, file):
    """按 精确 > 前缀 > 包含 三级策略匹配符号，file 参数可限定单文件。"""
    file_filter = None
    if file:
        file_filter = os.path.normpath(file).replace("\\", "/").lower()

    def _file_ok(abs_path):
        if file_filter is None:
            return True
        norm = os.path.normpath(abs_path).replace("\\", "/").lower()
        return norm.endswith(file_filter) or os.path.basename(norm) == os.path.basename(file_filter)

    exact, prefix, contains = [], [], []
    for abs_path, entry in index:
        if not _file_ok(abs_path):
            continue
        name = entry["symbol"]
        if name == symbol:
            exact.append((abs_path, entry))
        elif name.startswith(symbol):
            prefix.append((abs_path, entry))
        elif symbol in name:
            contains.append((abs_path, entry))
    if exact:
        return exact, "exact"
    if prefix:
        return prefix, "prefix"
    if contains:
        return contains, "contains"
    return [], "none"


def locate_symbol(symbol, file=None, with_content=True):
    """符号名 -> 文件 + 起止行 + 签名 + 完整源码（AST 静态解析，100% 准、零编码）。

    参数:
        symbol: 要定位的符号名（函数名/类名/方法名）
        file:   可选，限定单个文件（相对路径或文件名，模糊后缀匹配）
        with_content: 是否返回完整源码（默认 True；只查位置时传 False 省 token）

    返回:
        dict，结构见文件头注释与执行步骤文档。
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "found": False,
            "symbol": symbol,
            "match_count": 0,
            "matches": [],
            "message": "symbol 参数为空或非字符串，请传入有效的符号名。",
        }
    symbol = symbol.strip()
    repo_path = get_repository_path()
    if not repo_path or not os.path.isdir(repo_path):
        return {
            "found": False,
            "symbol": symbol,
            "match_count": 0,
            "matches": [],
            "message": f"仓库路径不存在或不可访问: {repo_path}",
        }

    index = _get_index(repo_path)
    matches, match_type = _match_entries(index, symbol, file)
    if not matches:
        return {
            "found": False,
            "symbol": symbol,
            "match_count": 0,
            "matches": [],
            "message": "未找到该符号，可改用 rag_search 或 exec_cmd findstr 检索。",
        }

    results = [_make_result(entry, abs_path, repo_path, with_content) for abs_path, entry in matches]
    return {
        "found": True,
        "symbol": symbol,
        "match_type": match_type,
        "match_count": len(results),
        "matches": results,
    }