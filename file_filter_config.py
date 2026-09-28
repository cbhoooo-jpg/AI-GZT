# -*- coding: utf-8 -*-
"""
文件过滤统一配置模块（file_filter_config.py）

功能:
    集中管理项目文件扫描时的"噪音文件"过滤规则，供 get_project_tree 工具、
    项目手册生成、RAG 索引构建、备份功能等所有扫盘链路统一复用，
    新增/调整过滤规则只需要修改本文件一处。

背景:
    虚拟环境（.venv/venv/env）、打包产物（dist/build/Output）、Git 数据（.git）、
    依赖目录（node_modules）、缓存目录（__pycache__ 等）均为工具自动生成、
    可随时重建的文件，实测数量可达数万（.venv 4 万+、dist 8 千+），
    若进入 AI 上下文会导致 token 暴涨、有效信号被稀释、浪费用户费用。

过滤规则约定:
    1. 点（.）开头的目录默认排除（工具生成目录的通用约定，如 .git/.venv/.idea），
       但 KEEP_DIR_NAMES 白名单中的真实项目目录（如 .github）保留；
    2. 点（.）开头的文件一律保留（如 .gitignore/.gitattributes 是真实项目文件）；
    3. 目录名/文件名均采用【精确匹配】黑名单，不使用前缀/子串匹配，
       避免误杀 venv_demo.py、my_venv_tools/ 这类正常命名；
    4. 文件按后缀 + 文件名黑名单过滤。
"""

import os

# ==================== 目录黑名单（按目录名精确匹配） ====================
EXCLUDE_DIR_NAMES = frozenset({
    # —— Python 虚拟环境 ——
    '.venv', 'venv', 'env',
    # —— Python 解释器 / 工具缓存 ——
    '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache',
    '.tox', '.eggs', 'htmlcov', '.ipynb_checkpoints',
    # —— 版本控制数据 ——
    '.git', '.svn',
    # —— 前端依赖 ——
    'node_modules',
    # —— IDE / 编辑器配置 ——
    '.idea', '.vscode',
    # —— 构建打包产物 ——
    'dist', 'build', 'Output', 'output',
    # —— 运行期可再生数据（日志 / 备份 / 索引 / 临时目录 / 模型） ——
    'logs', 'log', 'backup', '备份文件夹', 'code_rag',
    'temp', 'tmp', 'models', '.cache', 'gte-small-zh',
})

# 点开头目录中的"真实项目目录"白名单:不参与"点开头目录默认排除"约定
KEEP_DIR_NAMES = frozenset({
    '.github',   # GitHub Actions 工作流 / Issue 模板等项目配置
})

# ==================== 文件后缀黑名单（小写，含点） ====================
EXCLUDE_FILE_EXTS = frozenset({
    '.pyc', '.pyo',   # Python 字节码缓存
    '.log',           # 运行日志
    '.tmp', '.bak',   # 临时 / 备份文件
    '.swp',           # Vim 交换文件
    '.index',         # 向量索引等可再生二进制索引
})

# ==================== 文件名黑名单（统一小写，精确匹配） ====================
EXCLUDE_FILE_NAMES = frozenset({
    'thumbs.db',      # Windows 缩略图缓存
    'desktop.ini',    # Windows 文件夹配置
    '.ds_store',      # macOS 目录元数据
})
# ==================== 文件名后缀片段黑名单（小写，匹配文件名结尾） ====================
# 第三方前端库的压缩产物（如 vue.min.js / element-ui.min.css）:
# os.path.splitext 只能取到最后一个 .js/.css，无法用 EXCLUDE_FILE_EXTS 拦截，
# 故单列此表按"文件名结尾"精确匹配，避免误伤正常的 *.js / *.css 源码文件。
EXCLUDE_FILE_SUFFIXES = frozenset({
    '.min.js', '.min.css',   # 前端压缩库产物
})
# ==================== 判断函数 ====================
def is_noise_dir(dir_name):
    """判断目录名是否为应排除的噪音目录（精确匹配，不做前缀/子串匹配）

    规则:
      1. 白名单目录（KEEP_DIR_NAMES，如 .github）一律保留；
      2. 点（.）开头目录默认排除（工具生成约定，如 .git/.venv/.idea）；
      3. 命中 EXCLUDE_DIR_NAMES 黑名单的目录排除。
    返回 True 表示应排除。
    """
    if not dir_name:
        return False
    # 白名单优先:真实项目配置目录（如 .github）保留
    if dir_name in KEEP_DIR_NAMES:
        return False
    # 点开头目录默认排除（工具生成目录的通用约定）
    if dir_name.startswith('.'):
        return True
    # 黑名单精确匹配
    return dir_name in EXCLUDE_DIR_NAMES


def is_noise_file(file_name):
    """判断文件名是否为应排除的噪音文件（点开头文件一律保留，如 .gitignore）

    规则:
      1. 命中 EXCLUDE_FILE_NAMES 文件名黑名单（统一小写比较）排除；
      2. 文件名结尾命中 EXCLUDE_FILE_SUFFIXES 黑名单（如 .min.js/.min.css）排除；
      3. 后缀命中 EXCLUDE_FILE_EXTS 黑名单排除。
    返回 True 表示应排除。
    """
    if not file_name:
        return False
    lower_name = file_name.lower()
    # 文件名精确匹配黑名单
    if lower_name in EXCLUDE_FILE_NAMES:
        return True
    # 文件名结尾片段黑名单（拦截 .min.js/.min.css 等压缩产物）
    if lower_name.endswith(tuple(EXCLUDE_FILE_SUFFIXES)):
        return True
    # 后缀黑名单（含点，小写）
    ext = os.path.splitext(lower_name)[1]
    if ext in EXCLUDE_FILE_EXTS:
        return True
    return False


def prune_walk_dirs(dirs, root=None):
    """对 os.walk 的 dirs 列表原地剪枝（排除噪音目录 + 动态隔离路径，阻止递归进入）

    用法:
        for root, dirs, files in os.walk(path):
            prune_walk_dirs(dirs, root)   # 必须在处理 files 前调用
            ...
    :param dirs: os.walk 第二个返回值（原地修改实现剪枝）
    :param root: 当前遍历的绝对目录路径；传入后叠加"动态隔离"判断。
                 不传 root 时行为与历史版本完全一致（向后兼容旧调用点）。
    返回被排除的目录名列表，便于调用方统计或打印日志。
    """
    removed = []
    kept = []
    for d in dirs:
        # 静态噪音目录黑名单（精确匹配）
        if is_noise_dir(d):
            removed.append(d)
            continue
        # 动态隔离路径:命中隔离目录时整棵子树跳过（前缀匹配）
        if root and is_isolated_path(os.path.join(root, d)):
            removed.append(d)
            continue
        kept.append(d)
    # os.walk 通过原地修改 dirs 实现剪枝
    dirs[:] = kept
    return removed


# ==================== 动态"项目信息隔离"上下文（内存态，由 isolation_manager 注入） ====================
# 说明:
#   本模块保持"零 IO"纯配置定位，自身不读取任何配置文件；
#   磁盘上的隔离清单由 isolation_manager.py 负责读写，
#   并在【程序启动时】与【清单变更时】调用 set_isolation_context() 注入到这里。
#   由于所有扫盘链路 import 的是同一个模块对象（含 auto_sync_monitor 子线程），
#   注入一次即全局生效，调用方无需改动任何判断逻辑。
_ISOLATION_CTX = {
    "repo_root": "",    # 仓库根目录绝对路径（标准化:反斜杠转/、小写、无尾斜杠）
    "paths": set(),     # 隔离路径集合（相对仓库根、小写、/ 分隔、无首尾斜杠）
}


def set_isolation_context(repo_root, paths):
    """注入动态隔离上下文（由 isolation_manager.refresh_injection 调用）

    :param repo_root: 仓库根目录（绝对路径）
    :param paths: 隔离路径列表（相对路径或绝对路径，内部统一标准化）
    """
    global _ISOLATION_CTX
    root = str(repo_root or "").replace("\\", "/").rstrip("/").lower()
    norm_paths = set()
    for p in (paths or []):
        np = _normalize_isolation_path(p)
        if np:
            norm_paths.add(np)
    _ISOLATION_CTX = {"repo_root": root, "paths": norm_paths}


def _normalize_isolation_path(path):
    """内部工具:把单条隔离路径标准化为"相对仓库根、小写、/ 分隔、无首尾斜杠"

    兼容三种入参:①相对路径（项目A/output）；②带仓库根的绝对路径；③反斜杠/大写形式。
    特别处理:入参等于仓库根时返回空串（不允许隔离整个仓库，防止手册二/三章被清空）。
    """
    if not path:
        return ""
    raw = str(path).strip().replace("\\", "/")
    root = _ISOLATION_CTX.get("repo_root", "")
    lower_raw = raw.lower()
    if root:
        if lower_raw == root:
            return ""
        if lower_raw.startswith(root + "/"):
            raw = raw[len(root) + 1:]
    return raw.lower().strip("/")


def is_isolated_path(abs_or_rel_path):
    """判断指定路径是否命中"项目信息隔离"清单（含父目录前缀匹配）

    规则:
      1. 隔离清单为空时恒定返回 False（零开销兜底，未使用该功能时无任何影响）；
      2. 入参可为绝对路径或相对路径（相对路径按"相对仓库根"处理）；
      3. 前缀匹配:隔离"项目A/output"时，其下所有子孙文件/目录全部命中。
    返回 True 表示该路径应被隔离（不进 AI 上下文 / 项目手册 / RAG 索引）。
    """
    if not abs_or_rel_path:
        return False
    isolated = _ISOLATION_CTX.get("paths") or set()
    if not isolated:
        return False
    rel = _normalize_isolation_path(abs_or_rel_path)
    if not rel:
        return False
    for p in isolated:
        if rel == p or rel.startswith(p + "/"):
            return True
    return False