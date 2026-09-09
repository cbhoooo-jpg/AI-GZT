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
    'temp', 'tmp', 'models', '.cache',
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
      2. 后缀命中 EXCLUDE_FILE_EXTS 黑名单排除。
    返回 True 表示应排除。
    """
    if not file_name:
        return False
    lower_name = file_name.lower()
    # 文件名精确匹配黑名单
    if lower_name in EXCLUDE_FILE_NAMES:
        return True
    # 后缀黑名单（含点，小写）
    ext = os.path.splitext(lower_name)[1]
    if ext in EXCLUDE_FILE_EXTS:
        return True
    return False


def prune_walk_dirs(dirs):
    """对 os.walk 的 dirs 列表原地剪枝（排除噪音目录，阻止递归进入）

    用法:
        for root, dirs, files in os.walk(path):
            prune_walk_dirs(dirs)   # 必须在处理 files 前调用
            ...
    返回被排除的目录名列表，便于调用方统计或打印日志。
    """
    removed = []
    kept = []
    for d in dirs:
        if is_noise_dir(d):
            removed.append(d)
        else:
            kept.append(d)
    # os.walk 通过原地修改 dirs 实现剪枝
    dirs[:] = kept
    return removed