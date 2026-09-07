# -*- coding: utf-8 -*-
"""
文件编辑工具配置项
所有可调参数统一在此配置，无需修改核心逻辑
"""
import sys
import os
import json
from typing import Dict, Any

# 自动将项目根目录加入Python路径，解决跨模块导入问题
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

# 自动加载仓库路径配置（和api_server逻辑保持一致，避免循环导入）
def _get_default_repository_path() -> str:
    """获取跨平台默认仓库路径:统一使用当前用户文档目录下的AI仓库文件夹（任何Windows/Mac/Linux均存在）"""
    default_path = os.path.join(os.path.expanduser("~"), "Documents", "AI仓库文件夹")
    return os.path.normpath(default_path).replace("\\", "/")

CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")
REPOSITORY_PATH: str = _get_default_repository_path()
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user_config = json.load(f)
        if "repository_path" in user_config:
            REPOSITORY_PATH = os.path.normpath(user_config["repository_path"]).replace("\\", "/")
    except Exception:
        # 配置加载失败使用默认路径，不影响核心功能
        pass

# 全局开关
DEBUG: bool = False  # 是否输出匹配调试日志
ENABLE_AUTO_RETRY: bool = True  # 匹配失败是否自动重试
ENABLE_BACKUP: bool = True  # 修改前是否自动备份原文件

# 匹配引擎参数
MATCH_THRESHOLD: float = 0.85  # 全内容相似度阈值，建议0.85~0.95
BASE_LINE_THRESHOLD: float = 0.4  # 基准行相似度阈值
# 优化调整：从20下调至10，适配含<>的短锚点（如HTML短标签、泛型定义）
SHORT_BASE_SCORE_THRESHOLD: int = 15  # 短基准行触发归一化的得分阈值（中文2分/英文1分，10对应5中文/10英文）
MAX_RETRY_TIMES: int = 3  # 匹配失败最大重试次数
RETRY_ADD_CONTEXT_LINES: int = 1  # 重试时自动给锚点前后增加的行数

# 路径配置（自动基于项目根目录生成）
BACKUP_DIR: str = os.path.join(PROJECT_ROOT, "backup", "file_editor/")  # 备份文件存储目录
SUPPORTED_FILE_TYPES: tuple = (
    ".py", ".md", ".txt", ".json", ".yaml", ".yml", ".html", ".css", ".js", ".ts",  # 基础编程语言与文档
    ".java", ".cpp", ".c", ".h", ".hpp", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala",  # 后端编程语言
    ".ini", ".cfg", ".conf", ".toml", ".env", ".properties", ".xml",  # 配置文件
    ".sh", ".bat", ".ps1", ".spec", ".iss",  # 脚本与打包配置
    ".csv", ".sql",  # 数据文件
    ".rst", ".log",  # 文档与日志
    ".vue", ".jsx", ".tsx", ".scss", ".sass", ".less",  # 前端框架
    ".dockerfile", ".gitignore", ".gitattributes", ".editorconfig",  # 项目配置
)  # 支持编辑的文件类型

# 备份保留策略
BACKUP_RETENTION_DAYS: int = 30  # 备份文件默认保留天数，超过自动清理
BACKUP_MAX_COUNT: int = 1000  # 最大备份文件数量，超过自动清理最早的备份
