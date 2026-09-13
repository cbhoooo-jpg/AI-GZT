# -*- coding: utf-8 -*- 
"""
API服务层 V1.0
功能特性：
1. 完全兼容OpenAI标准接口，支持第三方工作台零修改对接
2. 全量内部管理接口，覆盖文件、配置、功能操作
3. 子线程启动，不阻塞主程序运行
4. 端口自动顺延，本地访问限制，安全可靠
"""
import os
import mimetypes
import json
import socket
import threading
import time
import random
import base64
import uuid
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse, HTMLResponse
from sse_starlette import EventSourceResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import re
import platform
from pypinyin import pinyin, Style
# 文件扫描噪音过滤统一配置（虚拟环境/打包产物/.git/缓存目录等），所有扫盘链路复用同一黑名单
import file_filter_config

# 全局配置，基于当前脚本路径生成绝对路径，避免工作目录错误导致找不到资源
# 兼容PyInstaller打包环境:打包后静态资源从_internal读取，用户配置统一存在exe同级目录（升级不丢失、多模块读写一致）
import sys as _sys
if getattr(_sys, 'frozen', False):
    # PyInstaller打包环境:静态资源文件（HTML/插件/模板等）从_internal目录读取
    _exe_dir = os.path.dirname(_sys.executable)
    _internal_dir = os.path.join(_exe_dir, "_internal")
    BASE_DIR = _internal_dir if os.path.exists(_internal_dir) else _exe_dir
    # 文档类文件优先查找exe同级目录，找不到自动fallback到_internal目录（兼容PyInstaller默认打包位置）
    if os.path.exists(os.path.join(_exe_dir, "AI_GZT_User_Guide.md")) or os.path.exists(os.path.join(_exe_dir, "THIRD_PARTY_LICENSES.md")):
        DOCS_DIR = _exe_dir
    else:
        DOCS_DIR = _internal_dir
    # 用户配置文件统一存在exe同级目录，和main.py启动时读取路径完全一致，避免配置不同步
    CONFIG_PATH = os.path.join(_exe_dir, "config.json")
    # 首次启动自动复制默认配置到exe目录:如果exe目录没有config.json，从_internal复制默认配置
    if not os.path.exists(CONFIG_PATH):
        import shutil
        _internal_default_config = os.path.join(_internal_dir, "config.json")
        if os.path.exists(_internal_default_config):
            shutil.copy2(_internal_default_config, CONFIG_PATH)
else:
    # 开发环境:使用脚本所在目录
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DOCS_DIR = BASE_DIR
    CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
DEFAULT_PORT = 8000
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

def get_default_repository_path() -> str:
    """获取跨平台默认仓库路径:统一使用当前用户文档目录下的AI仓库文件夹（任何Windows/Mac/Linux均存在）"""
    default_path = os.path.join(os.path.expanduser("~"), "Documents", "AI仓库文件夹")
    return os.path.normpath(default_path).replace("\\", "/")

# 全局仓库路径（动态从配置读取，支持自定义）
REPOSITORY_PATH = ""

# 全局最近N轮对话持久化文件，按项目隔离存储
def get_project_history_file():
    """获取当前项目对应的历史存储文件路径"""
    project_name = CURRENT_PROJECT.get("project_name", "default") if CURRENT_PROJECT else "default"
    # 处理项目名特殊字符，避免非法文件名
    safe_project_name = re.sub(r'[\\/*?:"<>|]', "_", project_name)
    safe_project_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5_-]', "_", project_name)
    return os.path.join(BASE_DIR, f"latest_chat_history_{safe_project_name}.json")

# 全局文件上传映射表路径
FILE_UPLOAD_MAP_PATH = os.path.join(BASE_DIR, "file_upload_map.json")
# 初始化上传映射表
if not os.path.exists(FILE_UPLOAD_MAP_PATH):
    with open(FILE_UPLOAD_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

def load_config() -> Dict:
    # 根据操作系统动态生成默认禁止路径，避免跨平台路径混用
    if platform.system() == "Windows":
        _default_forbidden_paths = [
            "C:/Windows", "C:/Program Files", "C:/Program Files (x86)", "C:/ProgramData"
        ]
    else:
        _default_forbidden_paths = [
            "/System", "/usr", "/bin", "/sbin", "/etc", "/var", "/root", "/private", "/Library"
        ]
    default_config = {
        "model_provider": "火山方舟",
        "api_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model_name": "doubao-seed-2-1-pro-260628",
        "api_key": "",
        "timeout": 200,
        "stream_output": True,
        "temperature": 0.5,
        "download_path": os.path.join(os.path.expanduser("~"), "Downloads"),
        "max_parse_fail_count": 3, # 单个文件解析失败最多重试次数，超过后24小时内自动跳过
        "repository_path": get_default_repository_path(), # 默认仓库路径
        "max_chat_rounds": 10, # 每轮回复最大次数（安全上限，防止无限循环），AI完成任务后自动停止
        "forbidden_paths": _default_forbidden_paths, # 默认禁止路径列表，根据操作系统动态生成，用户可自由增删
        "show_debug_console": False, # 默认隐藏后端调试控制台，用户可在设置页手动开启
        "system": {
            "project_root_absolute_path": BASE_DIR,
            "tos_endpoint": "https://tos-cn-beijing.volces.com",
            "tos_bucket": "",
            "tos_ak": "",
            "tos_sk": ""
        }
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            # 清理历史遗留的废弃配置项（本地模型相关，已全面切换云端）
            for deprecated_key in ["model_repo_path", "default_local_model"]:
                if deprecated_key in user_config:
                    del user_config[deprecated_key]
            # 合并用户配置，缺失字段自动补全默认值
            for key, value in default_config.items():
                if key not in user_config:
                    user_config[key] = value
            # 首次启动/版本升级时自动补全缺失的默认禁止路径，不覆盖用户已有配置
            if "forbidden_paths" not in user_config:
                user_config["forbidden_paths"] = default_config["forbidden_paths"]
            if "repository_path" not in user_config:
                user_config["repository_path"] = default_config["repository_path"]
            # 自动保存补全后的配置
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(user_config, f, ensure_ascii=False, indent=4)
            return user_config
        except Exception as e:
            print(f"⚠️ 配置文件加载失败，使用默认配置:{str(e)}")
            return default_config
    # 配置文件不存在，创建默认配置
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(default_config, f, ensure_ascii=False, indent=4)
    return default_config

def save_config(config: Dict):
    # 1. 主写入:EXE同级目录config.json（用户配置主文件，升级不丢失）
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    
    # 2. 同步写入:打包环境下同步写入_internal目录下的config.json，兼容旧模块读取路径
    if getattr(_sys, 'frozen', False):
        try:
            internal_config_path = os.path.join(_internal_dir, "config.json")
            with open(internal_config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            print(f"[Config] 配置已同步写入_internal目录: {internal_config_path}")
        except Exception as e:
            # 同步写入_internal失败不影响主流程，仅打印日志
            print(f"[Config] 同步写入_internal配置失败（不影响主配置生效）: {str(e)}")
    
    # 配置更新后自动重新初始化仓库路径和白名单，支持热更新
    init_repository_path()
    init_whitelist_paths()
    
    # 同步更新备份模块的全局仓库路径，支持备份功能热更新
    from tools import file_editor_config
    file_editor_config.REPOSITORY_PATH = REPOSITORY_PATH
    # 同步更新智能编辑模块顶层导入的路径变量，解决from导入复制值不更新的问题
    import tools.intelligent_file_editor as intelligent_file_editor_module
    intelligent_file_editor_module.REPOSITORY_PATH = REPOSITORY_PATH

# 初始化仓库路径:从配置读取，自动创建不存在的目录
def init_repository_path():
    global REPOSITORY_PATH
    config = load_config()
    repo_path = config.get("repository_path", get_default_repository_path())
    # 标准化路径格式
    REPOSITORY_PATH = os.path.normpath(repo_path).replace("\\", "/")
    # 自动创建仓库目录
    if not os.path.exists(REPOSITORY_PATH):
        os.makedirs(REPOSITORY_PATH, exist_ok=True)
        print(f"✅ 自动创建仓库目录:{REPOSITORY_PATH}")

# 初始化仓库路径
init_repository_path()
# 读取当前项目最近N轮对话历史
def load_global_history(rounds: int) -> List[Dict]:
    history_file = get_project_history_file()
    if not os.path.exists(history_file):
        # 兼容原有历史，首次加载时如果default项目文件不存在，复制原有全局历史
        if "default" in history_file and os.path.exists(os.path.join(BASE_DIR, "latest_chat_history.json")):
            import shutil
            shutil.copy(os.path.join(BASE_DIR, "latest_chat_history.json"), history_file)
        else:
            return []
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
        # 最多返回指定轮数，自动截断旧的
        return history[-rounds:] if len(history) >= rounds else history
    except (json.JSONDecodeError, OSError, IOError):
        return []

# 保存当前项目最近N轮对话历史，自动轮动
def save_global_history(query: str, response: str, rounds: int):
    history_file = get_project_history_file()
    history = load_global_history(rounds)
    # 新增当前轮对话
    history.append({
        "content": f"用户问:{query}\n回答:{response}",
        "timestamp": int(time.time() * 1000)
    })
    # 超过指定轮数自动删除最旧的
    if len(history) > rounds:
        history = history[-rounds:]
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# 检测端口是否被占用
def is_port_used(port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        result = sock.connect_ex(("127.0.0.1", port))
        return result == 0
    finally:
        sock.close()

# 获取可用端口
def get_available_port() -> int:
    port = DEFAULT_PORT
    while is_port_used(port):
        port += 1
        if port > 8010:
            raise RuntimeError("8000~8010端口全部被占用，请手动释放端口后重试")
    return port

# OpenAI兼容接口请求模型
class ChatCompletionMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatCompletionMessage]
    temperature: Optional[float] = 0.5
    top_p: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    stream: Optional[bool] = True
    user: Optional[str] = None

# FastAPI实例初始化
app = FastAPI(
    title="智能助手API服务",
    description="兼容OpenAI标准接口的智能助手API服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None
)
# 挂载Web页面路由
# 确保static目录存在，避免打包后目录缺失导致启动崩溃
static_dir = os.path.join(BASE_DIR, "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")
# ========== 全局上传配置（可按需调整） ==========
# 上传文件根目录（根目录下的“上传文件夹”）
UPLOAD_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "上传文件夹")
# 直传白名单配置:格式/大小限制
DIRECT_UPLOAD_CONFIG = {
    "image": {"exts": {"jpg", "jpeg", "png", "webp", "gif", "bmp", "svg", "ico"}, "max_size": 5 * 1024 * 1024}, # 图片≤5MB直传
    "text": {"exts": {
        "txt", "md", "json", "py", "js", "html", "css", "sql", "yml", "yaml", "go", "java", "cpp", "c", "h", "hpp", "sh", "bat", "ps1",
        "ts", "tsx", "jsx", "vue", "rs", "rb", "php", "swift", "kt", "scala",
        "ini", "cfg", "conf", "toml", "env", "properties", "xml", "csv", "rst", "log",
        "scss", "sass", "less", "dockerfile", "gitignore", "gitattributes", "editorconfig",
        "spec", "iss"
    }, "max_size": 2 * 1024 * 1024} # 开发文本文件≤2MB直传
}
# 启动自动创建上传目录
os.makedirs(UPLOAD_ROOT, exist_ok=True)
# 全局可访问白名单目录（最高优先级，永远放行，不受禁止列表限制，自动维护用户不可修改）
GLOBAL_WHITELIST_PATHS = []

def init_whitelist_paths():
    """初始化全局白名单路径，配置更新时自动调用重新加载"""
    global GLOBAL_WHITELIST_PATHS
    whitelist = [
        os.path.normpath(REPOSITORY_PATH), # 仓库路径永远放行，核心功能不受禁止规则影响
        os.path.normpath(UPLOAD_ROOT), # 上传文件夹永远放行
        os.path.normpath(os.path.join(BASE_DIR, "logs")), # 日志目录永远放行
        os.path.normpath(FILE_UPLOAD_MAP_PATH), # 上传映射文件永远放行
        os.path.normpath(CONFIG_PATH), # 配置文件永远放行
    ]
    # 标准化所有白名单路径，统一/分隔符
    GLOBAL_WHITELIST_PATHS = [os.path.normpath(p).replace("\\", "/") for p in whitelist if p]
    # 自动创建白名单中不存在的目录
    for path in GLOBAL_WHITELIST_PATHS:
        if not os.path.exists(path):
            # 仅对目录类型创建，文件类型跳过（无后缀判定为目录）
            if not os.path.splitext(path)[1]:
                os.makedirs(path, exist_ok=True)

# 初始化白名单
init_whitelist_paths()
# ========== 路径安全校验配置 ==========
# 默认系统级禁止操作目录（首次启动自动填充到配置，用户可在设置页自由增删）
DEFAULT_FORBIDDEN_PATHS = []
# Windows系统默认禁止目录
if platform.system() == "Windows":
    DEFAULT_FORBIDDEN_PATHS.extend([
        os.path.normpath("C:/Windows"),
        os.path.normpath("C:/Program Files"),
        os.path.normpath("C:/Program Files (x86)"),
        os.path.normpath("C:/ProgramData")
    ])
# Mac/Linux系统默认禁止目录
else:
    DEFAULT_FORBIDDEN_PATHS.extend([
        "/System",
        "/usr",
        "/bin",
        "/sbin",
        "/etc",
        "/var",
        "/root",
        "/private",
        "/Library"
    ])
# 程序自身根目录默认加入禁止列表，防止AI误删自身程序文件（白名单内子目录不受影响）
DEFAULT_FORBIDDEN_PATHS.append(os.path.normpath(BASE_DIR))

def is_path_forbidden(target_path: str, operation_type: str = "write") -> tuple[bool, str]:
    """
    校验路径是否在禁止操作列表中
    优先级规则:全局白名单（最高） > 禁止路径列表（默认+用户自定义）
    operation_type: 操作类型，write=写入/删除/修改类高风险操作（全拦截），read=读取/外部打开类低风险操作（仅拦截可执行文件）
    返回:(是否禁止, 禁止原因/匹配到的禁止路径)
    """
    if not target_path:
        return False, ""
    norm_target = os.path.normpath(os.path.abspath(target_path)).replace("\\", "/")
    
    # 第一步:最高优先级校验白名单，白名单内路径直接放行，无视任何禁止规则
    for allowed in GLOBAL_WHITELIST_PATHS:
        norm_allowed = os.path.normpath(allowed).replace("\\", "/")
        # 匹配规则:目标路径是白名单路径本身，或者在白名单路径的子目录下，直接放行
        if norm_target == norm_allowed or norm_target.startswith(norm_allowed + "/"):
            return False, ""
    
    # 第二步:校验合并后的禁止路径列表（系统默认+用户自定义，去重）
    config = load_config()
    user_forbidden = config.get("forbidden_paths", [])
    all_forbidden = list(set([os.path.normpath(p).replace("\\", "/") for p in DEFAULT_FORBIDDEN_PATHS + user_forbidden if p]))
    
    # 只读操作高危后缀黑名单:禁止在保护目录下打开这些可执行/脚本文件，防止恶意程序运行
    HIGH_RISK_EXEC_EXTS = {".exe", ".bat", ".cmd", ".ps1", ".dll", ".com", ".msi", ".vbs", ".js", ".jar", ".sh", ".bin", ".sys", ".scr"}
    
    for forbidden in all_forbidden:
        norm_forbidden = os.path.normpath(forbidden).replace("\\", "/")
        # 匹配规则:目标路径是禁止路径本身，或者在禁止路径的子目录下
        if norm_target == norm_forbidden or norm_target.startswith(norm_forbidden + "/"):
            # 只读操作特殊处理:非可执行文件直接放行，仅拦截高危可执行文件
            if operation_type == "read":
                file_ext = os.path.splitext(norm_target)[1].lower()
                if file_ext not in HIGH_RISK_EXEC_EXTS:
                    return False, ""
                # 只读操作拦截可执行文件时返回更精准的提示
                if os.path.normpath(forbidden) in [os.path.normpath(p) for p in DEFAULT_FORBIDDEN_PATHS]:
                    reason = f"系统保护目录【{norm_forbidden}】下的可执行文件禁止打开，防止恶意程序运行"
                else:
                    reason = f"用户自定义禁止目录【{norm_forbidden}】下的可执行文件禁止打开"
                return True, reason
            
            # 写入/删除/修改类高风险操作:完全保持原有全拦截规则
            if os.path.normpath(forbidden) in [os.path.normpath(p) for p in DEFAULT_FORBIDDEN_PATHS]:
                reason = f"系统保护目录【{norm_forbidden}】，禁止操作（可在设置-安全设置中移除该规则）"
            else:
                reason = f"用户自定义禁止目录【{norm_forbidden}】，禁止操作"
            return True, reason
    return False, ""
# 挂载为静态路由，前端可直接访问预览
app.mount("/upload", StaticFiles(directory=UPLOAD_ROOT), name="upload")

@app.get("/web_file_repo.html", include_in_schema=False)
async def get_file_repo_page():
    return FileResponse(os.path.join(BASE_DIR, "web_file_repo.html"))
@app.get("/logo.png", include_in_schema=False)
async def get_logo():
    return FileResponse(os.path.join(BASE_DIR, "logo.png"))

@app.get("/web_settings.html", include_in_schema=False)
async def get_settings_page():
    return FileResponse(os.path.join(BASE_DIR, "web_settings.html"))
@app.get("/chat_ui.html", include_in_schema=False)
async def get_chat_ui_page():
    return FileResponse(os.path.join(BASE_DIR, "chat_ui.html"))
@app.get("/chat_float.html", include_in_schema=False)
async def get_chat_float_page():
    return FileResponse(os.path.join(BASE_DIR, "chat_float.html"))
@app.get("/file_editor.html", include_in_schema=False)
async def get_file_editor_page():
    return FileResponse(os.path.join(BASE_DIR, "file_editor.html"))

@app.get("/web_log.html", include_in_schema=False)
async def get_log_page():
    return FileResponse(os.path.join(BASE_DIR, "web_log.html"))

@app.get("/web_backup.html", include_in_schema=False)
async def get_backup_page():
    return FileResponse(os.path.join(BASE_DIR, "web_backup.html"))

@app.get("/workspace", include_in_schema=False)
async def get_workspace_page():
    return FileResponse(os.path.join(BASE_DIR, "web_workspace.html"))
@app.get("/web_plugin_market.html", include_in_schema=False)
async def get_plugin_market_page():
    return FileResponse(os.path.join(BASE_DIR, "web_plugin_market.html"))

@app.get("/web_about.html", include_in_schema=False)
async def get_about_page():
    return FileResponse(os.path.join(BASE_DIR, "web_about.html"))
# 统一入口重定向，所有访问默认跳转到多标签工作台
@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/workspace")

@app.get("/chat", include_in_schema=False)
async def redirect_chat():
    return RedirectResponse(url="/workspace")

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1", "http://localhost", "http://*.local"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================== OpenAI兼容对外接口 ==========================
@app.get("/v1/models")
async def get_models():
    """兼容OpenAI模型列表接口"""
    config = load_config()
    return {
        "object": "list",
        "data": [
            {
                "id": config["model_name"],
                "object": "model",
                "created": 1677610605,
                "owned_by": "openai",
                "permission": [],
                "root": config["model_name"],
                "parent": None
            }
        ]
    }

# 导入主服务核心模块
from llm_client import llm
from main import memory_cache, TRAIN_SAMPLE_FILE, rag_manager
from project_manual_manager import project_manual_manager
# 导入全局截图工具
from screenshot_tool import screenshot_tool
from pydantic import BaseModel
# 导入智能文件编辑工具
from tools.intelligent_file_editor import intelligent_file_editor
# 导入文件编辑器配置
from tools.file_editor_config import SUPPORTED_FILE_TYPES
# 导入工具模板管理器
from tool_template_manager import tool_template_manager
# 导入定时任务调度器
from scheduler_manager import scheduler_manager
# 纯文本参数解析场景专用转义逻辑：完全保留代码内部转义，仅清理首尾空行
def safe_escape_restore(raw_str: str) -> str:
    # 完全不修改内容内部任何字符（包括正则/字符串里的转义符），仅清理首尾多余空行
    return raw_str.strip('\n')
SYSTEM_PROMPT_CONFIG = os.path.join(BASE_DIR, "system_prompt_config.json")
PENDING_SAMPLES_FILE = os.path.join(BASE_DIR, "pending_samples.json")
# 初始化默认配置
if not os.path.exists(SYSTEM_PROMPT_CONFIG):
    with open(SYSTEM_PROMPT_CONFIG, "w", encoding="utf-8") as f:
        json.dump({"default_prompt": "你是一个简洁友好的AI助手，回答准确精炼。"}, f, ensure_ascii=False, indent=2)
# 初始化待审核样本文件，不存在则自动创建空列表
if not os.path.exists(PENDING_SAMPLES_FILE):
    with open(PENDING_SAMPLES_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)
# ========== 上下文配置开关 ==========
ENABLE_SHORT_CONTEXT = True  # 是否开启最近轮次上下文关联
SHORT_CONTEXT_ROUNDS = 6     # 保留最近多少轮对话
# 全局会话存储:第一层key=项目名，第二层key=session_id，value=最近N轮对话列表
session_context: Dict[str, Dict[str, Any]] = {
    "default": {} # 默认项目，未选中项目时使用
}

# 全局SSE流式推送连接存储:key=session_id，value=消息队列，实现显示与推理解耦
SSE_CONNECTIONS = {}

def push_sse_message(session_id: str, data: dict):
    """线程安全的SSE消息推送，支持在子线程中调用，解决TestClient跨事件循环无法唤醒主循环Queue的问题"""
    global global_event_loop
    if session_id in SSE_CONNECTIONS:
        queue = SSE_CONNECTIONS[session_id]
        if not global_event_loop:
            return
        try:
            import asyncio
            asyncio.run_coroutine_threadsafe(queue.put(data), global_event_loop)
        except Exception:
            pass

# 全局文件变动SSE连接存储
FILE_CHANGE_CONNECTIONS = set()
# 全局对话停止信号存储:存储需要强制终止的会话ID
CHAT_STOP_SIGNALS = set()
# ========== 召回实时观测台（只读旁路，与对话SSE通道物理隔离） ==========
from collections import deque
# 最近50次提问的召回快照环形缓冲，后打开观测台页面也能补看历史
RECALL_LOG = deque(maxlen=50)
# 观测台广播订阅池:每个观测页面一个独立队列，支持多页面同时订阅，绝不复用SSE_CONNECTIONS
RECALL_SUBSCRIBERS = set()
# 人工标注持久化文件（👍相关/👎不相关），与观测缓冲分离，清空时间线不删标注
RECALL_EVAL_FILE = os.path.join(BASE_DIR, "recall_evaluations.json")
RECALL_EVAL_LOCK = threading.Lock()
if not os.path.exists(RECALL_EVAL_FILE):
    with open(RECALL_EVAL_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

def broadcast_recall_snapshot(snapshot: dict):
    """向所有观测台订阅者非阻塞广播召回快照，队列满/页面卡顿直接丢弃该条，绝不阻塞对话主流程"""
    global global_event_loop
    if not RECALL_SUBSCRIBERS or not global_event_loop:
        return
    async def _push():
        dead = []
        for q in list(RECALL_SUBSCRIBERS):
            try:
                q.put_nowait(snapshot)
            except Exception:
                dead.append(q)
        for q in dead:
            RECALL_SUBSCRIBERS.discard(q)
    try:
        import asyncio
        asyncio.run_coroutine_threadsafe(_push(), global_event_loop)
    except Exception:
        pass

def record_recall_observation(query: str, project_name: str, triggered: bool,
                              not_triggered_reason: str, memories: list):
    """组装一次提问的召回快照（含未触发/空召回样本），入环形缓冲并广播，纯只读不改召回结果"""
    snapshot = {
        "id": uuid.uuid4().hex,
        "timestamp": int(time.time() * 1000),
        "time_str": time.strftime("%H:%M:%S"),
        "query": query,
        "project": project_name or "default",
        "triggered": bool(triggered),
        "reason": not_triggered_reason or "",
        "memories": [
            {
                # 全部强制转Python原生类型，防御上游混入numpy.int64/numpy.float64导致JSON序列化500
                "id": int(m.get("id")) if m.get("id") is not None else None,
                "content": m.get("content", ""),
                "similarity": float(m["similarity"]) if m.get("similarity") is not None else None,
                "recall_score": float(m["recall_score"]) if m.get("recall_score") is not None else None,
                "tags": m.get("tags", []),
                "timestamp": int(m.get("timestamp", 0)) if m.get("timestamp") is not None else 0
            }
            for m in (memories or [])
        ]
    }
    RECALL_LOG.append(snapshot)
    broadcast_recall_snapshot(snapshot)

def _load_recall_evaluations() -> dict:
    """读取人工标注，结构:{snapshot_id: {str(memory_id): {label, time}}}"""
    try:
        with open(RECALL_EVAL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _save_recall_evaluations(data: dict) -> None:
    """持久化人工标注"""
    with open(RECALL_EVAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 全局事件循环引用，用于同步线程触发async操作
global_event_loop = None

def broadcast_file_change():
    """全局广播文件变动事件到所有前端连接，支持同步线程调用"""
    import asyncio
    global global_event_loop
    if not global_event_loop:
        try:
            global_event_loop = asyncio.get_event_loop()
        except RuntimeError:
            return
    for queue in FILE_CHANGE_CONNECTIONS:
        try:
            # 线程安全的方式提交协程任务到事件循环，解决同步线程调用async方法的警告
            global_event_loop.call_soon_threadsafe(
                lambda q: asyncio.create_task(q.put({"type": "file_change"})), 
                queue
            )
        except Exception:
            pass
def build_simple_tree(root_path, current_rel_path="", tag="current_project"):
    """生成极简纯树形目录结构，无冗余信息，自动过滤系统目录和隐藏文件，同时返回全量路径映射表"""
    children = []
    path_map = {}
    for item in os.listdir(root_path):
        item_full_path = os.path.join(root_path, item)
        # 统一过滤:目录走噪音目录黑名单（点开头目录默认排除、.github等白名单保留），
        # 文件走文件名/后缀黑名单（点开头文件如.gitignore保留），全部精确匹配无误伤
        if os.path.isdir(item_full_path):
            if file_filter_config.is_noise_dir(item):
                continue
        else:
            if file_filter_config.is_noise_file(item):
                continue
        # 计算当前条目的相对路径（统一/分隔符）
        if current_rel_path:
            item_rel_path = os.path.join(current_rel_path, item).replace("\\", "/")
        else:
            item_rel_path = item
        # 计算标准化绝对路径（统一/分隔符）
        item_abs_path = os.path.normpath(item_full_path).replace("\\", "/")
        if os.path.isdir(item_full_path):
            # 递归处理子目录，传递相对路径前缀和标签
            child_children, child_path_map = build_simple_tree(item_full_path, item_rel_path, tag)
            children.append({item: child_children})
            # 合并子目录路径映射
            path_map.update(child_path_map)
            # 记录当前目录信息
            path_map[item_rel_path] = {
                "abs_path": item_abs_path,
                "tag": tag,
                "is_dir": True
            }
        else:
            # 文件直接添加文件名（完全兼容原有结构）
            children.append(item)
            # 记录当前文件信息
            path_map[item_rel_path] = {
                "abs_path": item_abs_path,
                "tag": tag,
                "is_dir": False
            }
    return children, path_map
# 全局当前项目状态
CURRENT_PROJECT = {
    "project_name": "",
    "project_root": "",
    "manual_path": "",
    "file_list": []
}
# 全局操作日志存储
OPERATION_LOGS = []
LOG_MAX_SIZE = 500 # 最多保留500条操作日志
# ========== 配置结束 ==========
# 全局异步任务存储
TASK_STORAGE = {}
TASK_ID_COUNTER = 1
TASK_STATUS_PENDING = "pending"
TASK_STATUS_RUNNING = "running"
TASK_STATUS_SUCCESS = "success"
TASK_STATUS_FAILED = "failed"

def add_operation_log(oper_type: str, content: str, status: str = "success"):
    """新增操作日志，自动记录时间，按倒序存储"""
    global OPERATION_LOGS
    log_item = {
        "id": len(OPERATION_LOGS) + 1,
        "oper_type": oper_type,
        "content": content,
        "status": status,
        "oper_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    OPERATION_LOGS.insert(0, log_item)
    # 超过上限自动删除最早的日志
    if len(OPERATION_LOGS) > LOG_MAX_SIZE:
        OPERATION_LOGS.pop()

def add_file_operation_log(op_type: str, file_path: str, status: str, detail: str = ""):
    """
    统一文件操作日志格式，所有文件操作统一调用
    op_type: read/edit/create/delete/rename/write
    status: success/fail
    detail: 操作详情/错误原因
    """
    status_text = "✅ 成功" if status == "success" else "❌ 失败"
    log_content = f"[{op_type.upper()}] {status_text} | 文件：{file_path} | 详情：{detail[:200]}"
    add_operation_log("文件操作", log_content, status)

def update_current_project_file_list():
    """更新当前项目的文件清单内存缓存，操作文件后自动调用，无需用户手动刷新"""
    global CURRENT_PROJECT
    if CURRENT_PROJECT["project_root"] and CURRENT_PROJECT["manual_path"]:
        try:
            CURRENT_PROJECT["file_list"] = project_manual_manager.parse_file_overview_table(CURRENT_PROJECT["manual_path"])
        except Exception as e:
            print(f"⚠️ 更新项目文件清单缓存失败：{str(e)}")

# 兼容原有接口请求结构体
class ChatRequest(BaseModel):
    query: str
    system_prompt: Optional[str] = "" # 自定义系统提示词，不传用默认值
    session_id: Optional[str] = "default" # 会话ID，不传默认用公共会话
    attachments: list = []  # 附件列表，支持多文件/图片上传
# 异步任务相关模型
class TaskSubmitRequest(BaseModel):
    task_type: str # chat/read_file/write_file等
    params: Dict[str, Any] # 任务参数
system_prompt: str = """你是资深全栈开发工程师，一个严谨的分析型AI"""

# 兼容原有对话接口，保证工作台内聊天功能正常
@app.post("/api/chat")
async def chat(req: ChatRequest):
    global CURRENT_PROJECT
    import asyncio
    # 判断是否为定时任务触发
    is_scheduler_task = req.session_id == "scheduler_task"
    # 定时任务消息广播:如果是定时任务触发的，自动重定向到第一个活跃的SSE连接，确保前端能收到消息
    if is_scheduler_task and SSE_CONNECTIONS:
        req.session_id = list(SSE_CONNECTIONS.keys())[0]
    # 新对话发起时自动终止同会话的上一个未完成任务:先发送停止信号通知旧任务退出
    # 注意:定时任务不触发停止信号，避免中断用户当前正在进行的对话
    if not is_scheduler_task:
        CHAT_STOP_SIGNALS.add(req.session_id)
        # 等待最多1秒，直到旧任务完全终止并清理停止信号（旧任务退出时会在finally中自动discard信号）
        for _ in range(10):
            await asyncio.sleep(0.1)
            if req.session_id not in CHAT_STOP_SIGNALS:
                break
        # 等待结束后主动清理一次停止信号，确保无旧任务场景下信号不会残留导致新任务自终止
        CHAT_STOP_SIGNALS.discard(req.session_id)
    # 注意:正常运行时集合中无当前session_id，停止信号仅在用户点击停止/新请求发起终止旧任务时才会临时添加
    # 1. 合并当前会话历史+全局持久化历史，自动去重保留最近N轮，重启永不丢失
    history_rounds = memory_cache.config["history_context_rounds"]
    session_history = memory_cache.get_session_history(req.session_id, rounds=history_rounds)
    global_history = load_global_history(history_rounds)
    # 合并去重：相同内容的历史只保留1份，按时间戳排序取最新的N轮
    all_history = session_history + global_history
    seen_content = set()
    unique_history = []
    for item in sorted(all_history, key=lambda x: x["timestamp"]):
        if item["content"] not in seen_content:
            seen_content.add(item["content"])
            unique_history.append(item)
    session_history = unique_history[-history_rounds:] if len(unique_history) >= history_rounds else unique_history
    # 转为正序：最早的对话在前，最新的在后，保证上下文逻辑正确
    session_history = session_history[::-1]
    # 格式转换为会话上下文格式，支持自动注入时间戳
    current_session = []
    show_timestamp = memory_cache.config.get("show_timestamp_in_context", True)
    for mem in session_history:
            # 拆分用户提问和AI回答
            parts = mem["content"].split("\n回答:")
            if len(parts) == 2:
                user_content = parts[0].replace("用户问:", "")
                ai_content = parts[1]
            # 开启时间戳则格式化注入
            if show_timestamp:
                # 时间戳格式：[YYYY-MM-DD HH:MM] 极简显示不占空间
                time_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(mem["timestamp"] / 1000))
                user_content = f"[{time_str}] {user_content}"
                ai_content = f"[{time_str}] {ai_content}"
            current_session.append({"role": "user", "content": user_content})
            current_session.append({"role": "assistant", "content": ai_content})
    
    # 新增：记录AI接收用户提问日志
    # 2. 召回记忆:历史会话不足触发轮数时不做向量召回，触发轮数页面可改
    current_project_name = CURRENT_PROJECT.get("project_name", "default") if CURRENT_PROJECT else "default"
    recall_result = memory_cache.recall_memory(req.query, project_name=current_project_name)
    trigger_rounds = memory_cache.config["recall_trigger_rounds"]
    # 会话轮数不足时自动跳过向量召回，避免资源浪费（current_session长度是轮数*2，除以2得到实际轮数）
    if len(current_session) // 2 < trigger_rounds:
        recall_result["memory_recall"] = []
    # 【召回观测台只读旁路】最终召回状态确定后分叉，含未触发/空召回样本；只读recall_result，绝不修改它
    _obs_mems = recall_result.get("memory_recall", [])
    if len(current_session) // 2 < trigger_rounds:
        _obs_triggered = False
        _obs_reason = f"会话轮数不足（前{trigger_rounds}轮不触发向量召回）"
    elif _obs_mems:
        _obs_triggered = True
        _obs_reason = ""
    else:
        _obs_triggered = False
        _obs_reason = "无匹配记忆（候选均低于相似度阈值或被近期上下文过滤）"
    record_recall_observation(req.query, current_project_name, _obs_triggered, _obs_reason, _obs_mems)
    # 固定召回（工具+预留插槽）拼入系统prompt，不占用上下文配额
    fixed_prompt = "\n".join([item["content"] for item in recall_result["fixed_recall"]])
    # 新增:追加已启用插件列表描述
    merged_tools = tool_template_manager.get_merged_tool_list()
    plugin_desc = []
    for tool_id, template in merged_tools.items():
        if "plugin_config" in template:
            config = template["plugin_config"]
            # 生成详细的参数描述，让大模型明确每个参数的要求
            param_desc_list = []
            for param in config["parameters"]:
                required_tag = "必填" if param.get("required", False) else "可选"
                param_desc_list.append(f"{param['name']}（{required_tag}，{param['description']}）")
            params_desc = "；".join(param_desc_list)
            trigger_words = "、".join(config.get("trigger_words", []))
            plugin_desc.append(f"【插件】工具名:{config['plugin_id']}，名称:{config['name']}，描述:{config['description']}，参数要求:{params_desc}，触发关键词:{trigger_words}，调用时工具名称必须填写工具名！")
    if plugin_desc:
        fixed_prompt += "\n【可用插件列表】\n" + "\n".join(plugin_desc)
    # 向量召回记忆拼入上下文头部，不占用会话轮数配额
    memory_prompt = "\n【历史关联记忆召回】召回记忆作为参考\n" + "\n".join([mem["content"] for mem in recall_result["memory_recall"]]) if recall_result["memory_recall"] else ""
    
    # 构造当前开发项目上下文Prompt（仅选中项目时生成，不占用会话轮数配额）
    project_context_prompt = ""
    if CURRENT_PROJECT.get("project_name"):
        project_root = os.path.normpath(CURRENT_PROJECT["project_root"]).replace("\\", "/")
        file_list = CURRENT_PROJECT.get("file_list", [])
        # 生成所有文件的标准化绝对路径，统一/分隔符跨平台兼容
        abs_file_list = []
        for rel_path in file_list:
            abs_path = os.path.normpath(os.path.join(project_root, rel_path)).replace("\\", "/")
            abs_file_list.append(abs_path)
        # 拼接上下文内容
        project_context_prompt = "\n========== 当前开发项目上下文 ==========\n"
        project_context_prompt += f"当前开发项目名称:{CURRENT_PROJECT['project_name']}\n"
        project_context_prompt += f"项目根目录完整绝对路径:{project_root}\n"
        project_context_prompt += "项目文件清单（均为标准化绝对路径，可直接调用文件操作工具使用）:\n"
        if not abs_file_list:
            project_context_prompt += "✅ 当前为全局状态，如要进行项目开发请提醒用户选择相关项目，工作台使用项目隔离记忆方式\n"
        else:
            # 文件数超过100个自动截断，避免占用过多上下文Token
            if len(abs_file_list) > 100:
                show_files = abs_file_list[:100]
                project_context_prompt += "\n".join([f"- {p}" for p in show_files])
                project_context_prompt += f"\n... 文件过多，仅显示前100个，可调用get_project_tree获取完整目录树\n"
            else:
                project_context_prompt += "\n".join([f"- {p}" for p in abs_file_list]) + "\n"
        project_context_prompt += "💡 以上所有文件路径均为标准化绝对路径，统一使用/分隔符，可直接调用文件操作工具使用，无需自行拼接路径\n"
        project_context_prompt += "==================================\n"

    # 4. 拼接记忆到prompt
    system_prompt = req.system_prompt
    # 【模块1:固定召回（工具+预留插槽）】不占用上下文配额，100%生效
    if fixed_prompt.strip():
        system_prompt += "\n========== 固定召回内容 ==========\n"
        system_prompt += fixed_prompt + "\n"
        system_prompt += "==================================\n"
    # 【模块1.5:当前开发项目上下文】不占用上下文配额，100%生效，选中项目时自动注入
    if project_context_prompt.strip():
        system_prompt += project_context_prompt
    # 【模块2:向量召回的长程相关记忆】跨会话知识召回
    if memory_prompt.strip():
        system_prompt += memory_prompt + "\n"
    # 【模块3：最近N轮会话上下文】解决指代类提问，轮数随配置动态调整
    if ENABLE_SHORT_CONTEXT:
        actual_rounds = len(current_session) // 2
        system_prompt += f"\n========== 最近{actual_rounds}轮对话 ==========\n"
        if current_session:
            # 转换current_session格式：user/assistant配对显示
            session_text = []
            for i in range(0, len(current_session), 2):
                if i < len(current_session) and current_session[i]["role"] == "user":
                    user_q = current_session[i]["content"]
                    ai_a = current_session[i+1]["content"] if i+1 < len(current_session) else ""
                    session_text.append(f"用户问：{user_q}\nAI回答：{ai_a}")
            system_prompt += "\n".join(session_text) + "\n"
        else:
            system_prompt += "✅ 首次会话，暂无历史对话\n"
        system_prompt += "==================================\n"

    # 4. 先打印调试上下文，再调用模型推理
    # 调试用：打印最终传给模型的完整prompt，不需要可以注释
    print("\n========== 传给AI的完整上下文 ==========\n", system_prompt, "\n=======================================\n")
    # 附件智能分流处理：自动判断直传/工具调用
    content_list = [{"type": "text", "text": req.query}]
    use_direct_mode = False # 标记是否使用直传模式
    
    if req.attachments:
        for att in req.attachments:
            ext = att['ext'].lower()
            size = att['size']
            local_path = att['local_path']
            original_name = att['original_name']
            
            # 判断是否符合图片直传条件
            if ext in DIRECT_UPLOAD_CONFIG['image']['exts'] and size <= DIRECT_UPLOAD_CONFIG['image']['max_size']:
                use_direct_mode = True
                # 图片转base64直传
                with open(local_path, "rb") as f:
                    base64_data = base64.b64encode(f.read()).decode('utf-8')
                    content_list.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/{ext};base64,{base64_data}"}
                    })
            # 判断是否符合文本文件直传条件
            elif ext in DIRECT_UPLOAD_CONFIG['text']['exts'] and size <= DIRECT_UPLOAD_CONFIG['text']['max_size']:
                # 文本文件直接读内容拼到提问
                with open(local_path, "r", encoding="utf-8", errors="ignore") as f:
                    text_content = f.read()
                content_list[0]['text'] = f"📎 上传的文件【{original_name}】内容：\n```\n{text_content}\n```\n\n用户提问：{content_list[0]['text']}"
            # 不符合直传条件，传路径给AI调用工具
            else:
                content_list[0]['text'] = f"📎 上传的文件【{original_name}】本地路径：{local_path}\n请调用对应工具读取文件内容后响应用户提问。\n\n用户提问：{content_list[0]['text']}"
    
    # 初始化消息列表，兼容直传/普通模式
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content_list if use_direct_mode else content_list[0]['text']}
    ]
    # 从配置读取每轮回复最大次数（安全上限，防止无限循环），AI完成任务后自动停止
    config = load_config()
    max_tool_calls = config.get("max_chat_rounds", 20)
    current_calls = 0
    response = ""
    last_tool_calls = [] # 记录最近2次工具调用，检测重复调用死循环
    consecutive_errors = 0 # 连续错误计数，超过2次自动停止
    current_round = 1  # 记录当前交互轮次
    structured_content = ""  # 存储结构化的交互内容，用于记忆写入
    while current_calls < max_tool_calls:
        # 连续50次错误自动停止，避免死循环
        if consecutive_errors >= 50:
            response += "\n⚠️ 已连续50次执行错误，自动停止当前任务，请检查指令是否正确。"
            break
        # 检查是否收到停止信号，收到立即终止整个任务
        if req.session_id in CHAT_STOP_SIGNALS:
            response += "\n\n[已手动终止输出]"
            break
        try:
            # 模型推理（统一流式调用，本地/云端逻辑完全对齐）
            output_stream = llm.create_chat_completion(
                messages = messages,
                temperature=0.5,
                top_p=0.9,
                stream=True,
                reasoning_effort="high"
            )

            current_response = ""
            current_calls += 1
            # 流式接收输出，逐块推送前端
            reasoning_content = ""
            
            for chunk in output_stream:
                # 检查停止信号，收到立即终止流式输出
                if req.session_id in CHAT_STOP_SIGNALS:
                    break
                delta = chunk["choices"][0].get("delta", {})
                delta_content = delta.get("content", "")
                # 直接读取模型返回的专用思考内容字段（豆包/深度思考模型原生支持，无需自己解析<|im_start|>标签）
                delta_reasoning = delta.get("reasoning_content", "")
                current_response += delta_content
                
                # 推送思考内容（增量推送，无需等全部输出完）
                if delta_reasoning:
                    reasoning_content += delta_reasoning
                    push_sse_message(req.session_id, {
                        "type": "ai_reasoning",
                        "content": delta_reasoning,
                        "timestamp": time.time()
                    })
                
                # 推送实时正式内容（永远不会被思考逻辑打断，代码里的<|im_start|>字符串再也不会被误判）
                if delta_content:
                    push_sse_message(req.session_id, {
                        "type": "ai_output_stream",
                        "content": delta_content,
                        "timestamp": time.time()
                    })
                
                # 处理完内容后再判断是否结束
                if chunk["choices"][0].get("finish_reason") == "stop":
                    break
            
            # 最后推送完整的正式内容，对齐原有逻辑
            push_sse_message(req.session_id, {
                "type": "ai_output",
                "content": current_response.strip(),
                "timestamp": time.time()
            })

            all_exec_results = []
            # 新增：处理纯文本格式的工具调用请求，自动转换为模板生成的合法JSON指令
            import re
            # 新方案：纯中文边界标记，零特殊符号，零转义风险
            # 全量匹配所有工具块，一次性处理所有指令，避免残留
            tool_blocks = re.findall(r'【工具调用开始】(.*?)【工具调用结束】', current_response, re.S)
            # 初始化待执行指令列表，仅接收自定义标记解析出来的合法指令
            json_blocks = []
            
            for block_content in tool_blocks:
                block_content = block_content.strip()
                tool_name = ""
                params = {}
                parse_success = False
                # 提取工具名
                tool_name_match = re.search(r'工具名称[：:]\s*(\w+)', block_content)
                if not tool_name_match:
                    all_exec_results.append('❌ 工具指令解析失败：缺少工具名称字段')
                    continue
                tool_name = tool_name_match.group(1).strip()
                # 提取参数列表
                params_match = re.search(r'参数列表[：:]\s*(.*)', block_content, re.S)
                if not params_match:
                    all_exec_results.append(f'❌ 工具指令解析失败：{tool_name}缺少参数列表字段')
                    continue
                params_str = params_match.group(1).strip()
                params = {}
                parse_success = False

                # ========== 分通道解析：高风险编辑类工具走专用稳定通道，其他走通用灵活通道 ==========
                if tool_name in ("edit_file", "create_file"):
                    # 编辑专用解析通道：100%稳定优先，核心长参数直接按位置提取，杜绝内容误截断
                    try:
                        # 仅预处理短参数部分的全角冒号，长内容完全保留原始字符
                        params_str_norm = params_str.replace('：', ':', 50)
                        if tool_name == "edit_file":
                            # 提取短参数:file_name、operation
                            fn_match = re.search(r'^[ \t]*file_name[::][ \t]*(.*?)(?=\n[ \t]*(operation|gzt_anchor|gzt_newtext|target_block|content)[::]|\Z)', params_str_norm, re.S | re.M)
                            if fn_match:
                                params["file_name"] = fn_match.group(1).strip()
                            op_match = re.search(r'^[ \t]*operation[::][ \t]*(.*?)(?=\n[ \t]*(gzt_anchor|gzt_newtext|target_block|content)[::]|\Z)', params_str_norm, re.S | re.M)
                            if op_match:
                                params["operation"] = op_match.group(1).strip()
                            # 提取gzt_anchor:从gzt_anchor:后到gzt_newtext:前/块结束的所有内容，完全保留原始格式
                            tb_match = re.search(r'^[ \t]*gzt_anchor[::][ \t]*(.*?)(?=\n[ \t]*gzt_newtext[::]|\Z)', params_str_norm, re.S | re.M)
                            if tb_match:
                                tb_content = tb_match.group(1)
                                # 修复:如果内容以换行开头，去掉第一个换行符（保留后续缩进）
                                if tb_content.startswith('\n'):
                                    tb_content = tb_content[1:]
                                params["gzt_anchor"] = tb_content.rstrip('\n')
                            # 提取gzt_newtext:从gzt_newtext:后一直到块结束，一字不差保留
                            ct_match = re.search(r'^[ \t]*gzt_newtext[::](.*)', params_str_norm, re.S | re.M)
                            if ct_match:
                                ct_content = ct_match.group(1)
                                # 修复:如果内容以换行开头，去掉第一个换行符（保留后续缩进）
                                if ct_content.startswith('\n'):
                                    ct_content = ct_content[1:]
                                params["gzt_newtext"] = ct_content.rstrip('\n')
                            # 校验必填参数:非首尾插入操作必须有gzt_anchor
                            op = params.get("operation", "")
                            required_params = ["file_name", "operation"]
                            if op not in ("insert_start", "insert_end"):
                                required_params.append("gzt_anchor")
                            parse_success = all(k in params for k in required_params)
                        
                        elif tool_name == "create_file":
                            # 提取短参数:path、is_dir
                            p_match = re.search(r'^[ \t]*path[：:][ \t]*(.*?)(?=\n[ \t]*(is_dir|gzt_newtext|content)[：:])', params_str_norm, re.S | re.M)
                            if p_match:
                                params["path"] = p_match.group(1).strip()
                            id_match = re.search(r'^[ \t]*is_dir[：:][ \t]*(.*?)(?=\n[ \t]*(?:gzt_newtext|content)[：:]|$)', params_str_norm, re.S | re.M)
                            if id_match:
                                id_val = id_match.group(1).strip()
                                # 专用通道内完成布尔类型转换，避免后续重复处理报错
                                if isinstance(id_val, str):
                                    params["is_dir"] = id_val.lower() in ("true", "1", "yes")
                                else:
                                    params["is_dir"] = bool(id_val)
                            # 提取gzt_newtext参数
                            c_match = re.search(r'^[ \t]*(?:gzt_newtext|content)[：:][ \t]*(.*)', params_str_norm, re.S | re.M)
                            if c_match:
                                content_val = c_match.group(1)
                                # 去掉开头换行符，保留所有原始缩进格式
                                if content_val.startswith('\n'):
                                    content_val = content_val[1:]
                                params["gzt_newtext"] = content_val.rstrip()
                            # 校验必填参数
                            parse_success = "path" in params
                    except Exception:
                        # 专用通道解析异常，自动回退到通用通道
                        parse_success = False

                # ========== 非编辑类工具/专用通道解析失败，走通用灵活解析通道 ==========
                if not parse_success:
                    # 预定义内置工具参数名，插件参数动态加载
                    ALL_PARAM_NAMES = {"file_name", "operation", "target_block", "content", "gzt_anchor", "gzt_newtext", "path", "is_dir", "old_path", "new_name", "query", "cmd"}
                    # 动态添加当前插件的所有参数名（如果是插件调用）
                    current_param_names = ALL_PARAM_NAMES.copy()
                    plugin_config = tool_template_manager.get_plugin_config(tool_name)
                    if plugin_config:
                        plugin_params = [p["name"] for p in plugin_config["parameters"]]
                        current_param_names.update(plugin_params)
                    
                    current_param = None
                    current_value = []
                    for line in params_str.split('\n'):
                        # 仅替换行首参数名后的全角冒号，内容内部全角冒号完全保留
                        line_for_check = line
                        for p_name in current_param_names:
                            if line.lstrip().startswith(f"{p_name}："):
                                line_for_check = line.replace('：', ':', 1)
                                break
                        line_stripped = line_for_check.strip()
                        is_new_param = False
                        # 严格规则：只有顶格（无缩进）、是当前工具合法参数、未被解析过的行才判定为新参数
                        if not line.startswith((' ', '\t')) and ':' in line_stripped:
                            k_part, v_part = line_for_check.split(':', 1)
                            k = k_part.strip()
                            if k in current_param_names and k not in params:
                                # 保存上一个参数内容
                                if current_param is not None:
                                    params[current_param] = '\n'.join(current_value).rstrip('\n')
                                current_param = k
                                current_value = [v_part]
                                is_new_param = True
                        # 非新参数行，原始内容直接追加，保留所有换行/缩进/特殊字符
                        if not is_new_param and current_param is not None:
                            current_value.append(line)
                    # 保存最后一个参数
                    if current_param is not None:
                        params[current_param] = '\n'.join(current_value).rstrip('\n')
                    parse_success = True
                # ========== 统一后置参数处理（所有通道通用） ==========
                # 兼容delete操作无需content字段，自动补全避免模板生成失败
                if tool_name == "edit_file" and params.get("operation") == "delete":
                    params["content"] = params.get("content", "")
                # 统一处理is_dir参数：字符串转布尔值，避免"False"被判定为True
                if "is_dir" in params and isinstance(params["is_dir"], str):
                    params["is_dir"] = params["is_dir"].strip().lower() == "true"
                # 自动识别JSON格式参数（数组/对象/数字/布尔值），兼容插件非字符串类型参数
                import json as _json
                for k, v in list(params.items()):
                    # 跳过content、target_block参数，避免文件内容/锚点被解析为Python对象导致写入/匹配失败
                    if k in ("content", "target_block", "gzt_newtext", "gzt_anchor"):
                        continue
                    if not isinstance(v, str):
                        continue
                    v_stripped = v.strip()
                    # 仅尝试解析以{/[/数字/true/false/null开头的内容，减少无效解析
                    if v_stripped and (v_stripped[0] in '{["0123456789-tfn' or v_stripped in ('true', 'false', 'null')):
                        try:
                            parsed_v = _json.loads(v_stripped)
                            # 仅替换非字符串类型的解析结果，普通字符串解析后还是字符串不替换，避免破坏普通文本参数
                            if not isinstance(parsed_v, str):
                                params[k] = parsed_v
                        except (_json.JSONDecodeError, ValueError):
                            # 解析失败说明是普通字符串，保留原值
                            pass
                # 动态获取当前工具的必填参数（内置工具+插件）
                current_required_params = []
                plugin_config = tool_template_manager.get_plugin_config(tool_name)
                if plugin_config:
                    current_required_params = [p["name"] for p in plugin_config["parameters"] if p.get("required", False)]
                else:
                    # 内置工具必填参数映射
                    builtin_required = {
                        "edit_file": ["file_name", "operation"],
                        "create_file": ["path"],
                        "read_file": ["file_name"],
                        "delete_file": ["file_name"],
                        "write_file": ["file_name", "content"],
                        "rename_file": ["old_path", "new_name"],
                        "exec_cmd": ["cmd"],
                        "rag_search": ["query"],
                        "get_project_tree": []
                    }
                    current_required_params = builtin_required.get(tool_name, [])
                # 校验必填参数
                for p in current_required_params:
                    if p not in params or not str(params[p]).strip():
                        all_exec_results.append(f'❌ 参数解析失败:{p}参数值为空，请检查格式是否正确（参数名必须顶格写，冒号使用英文/中文冒号均可）')
                        parse_success = False
                        break
                # 兼容delete操作无需content字段，自动补全避免模板生成失败
                if tool_name == "edit_file" and params.get("operation") == "delete":
                    params["content"] = params.get("content", "")
                # is_dir参数已在create_file专用通道和通用类型转换逻辑中完成处理，无需重复处理
                if parse_success:
                    # 调用模板管理器生成合法指令
                    legal_json = tool_template_manager.generate_command(tool_name, params)
                    # 校验生成的指令是否有效
                    if legal_json:
                        # 仅将自定义标记生成的合法指令加入待执行列表
                        json_blocks.append(legal_json)
                    else:
                        # 生成失败直接加入错误结果，不产生无效JSON块
                        all_exec_results.append(f'❌ 工具指令生成失败：工具名称{tool_name}或参数不合法')
                        add_operation_log("工具执行", f'❌ 工具指令生成失败：工具名称{tool_name}或参数不合法')
            
            response += "\n" # 换行分隔指令
            # 追加当前轮AI输出到结构化记忆
            structured_content += f"【第{current_round}轮交互】\nAI输出：{current_response}\n"
            current_round += 1
            
            # 循环执行每一个工具调用
            for json_str in json_blocks:
                try:
                    # 所有指令均由ToolTemplateManager生成，100%合法无需额外修复
                    func_call_raw = json.loads(json_str)
                    # 兼容批量指令数组格式 + 单指令对象格式
                    func_call_list = func_call_raw if isinstance(func_call_raw, list) else [func_call_raw]                    
                    # 循环处理每一条指令
                    for func_call in func_call_list:
                        # 新增：仅允许模板生成的带合法标识的指令执行，非法指令直接拦截
                        valid_check = tool_template_manager.validate_command(json.dumps(func_call))
                        if not valid_check:
                            exec_result = "❌ 非法指令，仅允许模板生成的合规指令执行"
                            all_exec_results.append(exec_result)
                            add_operation_log("工具执行", exec_result, "error")
                            # 实时推送错误到前端日志面板
                            push_sse_message(req.session_id, {
                                "type": "operation_log",
                                "oper_type": "工具执行",
                                "content": exec_result,
                                "status": "error",
                                "timestamp": time.time()
                            })
                            continue

                        # 把当前指令返回给前端展示，新增edit_file内容可视化还原（和文件格式100%对齐）
                        if func_call.get("name") == "edit_file":
                            params = func_call["parameters"]
                            content = params.get("gzt_newtext") or params.get("content", "")
                            file_name = params.get("file_name", "")
                            operation = params.get("operation", "")
                            if content:
                                # 转义字符无损还原，保留原始缩进、换行、空格
                                formatted_content = content.replace("\\n", "\n").replace("\\t", "    ").replace('\\"', '"')
                                # 自动识别代码语言，高亮显示
                                ext = os.path.splitext(file_name)[1].lower()
                                lang = {
                                    ".py": "python",
                                    ".html": "html",
                                    ".js": "javascript",
                                    ".css": "css",
                                    ".vue": "vue",
                                    ".ts": "typescript",
                                    ".md": "markdown",
                                    ".json": "json"
                                }.get(ext, "")
                                # 前置输出可视化修改内容，和编辑器显示完全一致
                                response += f"🔧 **修改操作：{operation} 文件【{file_name}】**{formatted_content}"

                        # 输出原始可执行指令块（默认折叠不影响查看）
                        response += f"{json.dumps(func_call, ensure_ascii=False, indent=2)}"
                        
                        # 统一处理工具调用逻辑
                        exec_result = ""
                        # 重复调用检测，仅修改类工具做拦截，防止死循环
                        MODIFY_TOOLS = {"edit_file", "create_file", "delete_file", "rename_file", "write_file"}                         
                        current_tool_name = func_call.get("name", "")
                        current_call_signature = json.dumps(func_call, sort_keys=True)
                        
                        # 保留最近3次调用记录
                        last_tool_calls.append(current_call_signature)
                        if len(last_tool_calls) > 3:
                            last_tool_calls.pop(0)

                        # 仅修改类工具、连续3次完全相同调用才判定为死循环
                        if current_tool_name in MODIFY_TOOLS and len(last_tool_calls) >=50 and last_tool_calls[0] == last_tool_calls[1] == last_tool_calls[2]:
                            intercept_data = {
                                "is_intercepted": True,
                                "intercept_reason": "连续50次相同修改类指令触发防死循环拦截",
                                "suggestion": "如需执行请修改指令参数后重试"
                            }
                            stop_msg = json.dumps(intercept_data, ensure_ascii=False)
                            # 写入全局操作日志，web_log.html历史日志可查询
                            add_operation_log("工具执行", intercept_data["intercept_reason"], "warning")
                            exec_result = stop_msg
                            all_exec_results.append(exec_result)
                            consecutive_errors = 50 # 标记为错误上限直接停止
                            # 实时推送警告通知到前端日志面板
                            push_sse_message(req.session_id, {
                                "type": "operation_log",
                                "oper_type": "工具执行",
                                "content": intercept_data["intercept_reason"],
                                "status": "warning",
                                "timestamp": time.time()
                            })
                            break

                        if func_call.get("name") == "get_project_tree":
                            # 优先取当前选中项目，没选中则取仓库根目录
                            if CURRENT_PROJECT["project_root"]:
                                root_path = CURRENT_PROJECT["project_root"]
                                root_name = CURRENT_PROJECT["project_name"]
                                root_tag = "current_project"
                            else:
                                root_path = REPOSITORY_PATH
                                root_name = "仓库根目录"
                                root_tag = "repo_root"
                            # 生成树形结构+全量路径映射表
                            tree_children, path_map = build_simple_tree(root_path, tag=root_tag)
                            # 补充根目录信息到路径映射
                            root_abs_path = os.path.normpath(root_path).replace("\\", "/")
                            path_map[""] = {
                                "abs_path": root_abs_path,
                                "tag": root_tag,
                                "is_dir": True
                            }
                            # 完全保留原有树形结构，零破坏性兼容
                            tree_data = {root_name: tree_children}
                            # 构造返回结果，新增路径映射表，AI可直接使用abs_path调用工具，无需自行拼接路径
                            return_data = {
                                "tree": tree_data,
                                "path_map": path_map,
                                "tip": "💡 所有文件/文件夹的绝对路径已在path_map中给出，直接使用abs_path字段调用文件操作工具即可，无需自行拼接路径，路径已统一标准化为/分隔符"
                            }
                            exec_result = f"✅ 文件列表读取成功:{json.dumps(return_data, ensure_ascii=False, indent=2)}"
                            add_operation_log("文件操作", f"✅ 文件列表读取成功，共返回{len(path_map)}个路径条目")
                            all_exec_results.append(exec_result)
                            continue

                        elif func_call.get("name") == "edit_file":
                            params = func_call["parameters"]
                            file_name = params.get("file_name", "").strip()
                            operation = params.get("operation", "").strip()
                            target_block = params.get("gzt_anchor") or params.get("target_block", "")
                            content = params.get("gzt_newtext") or params.get("content", "")
                            
                            # 安全转义还原：自动区分传输层转义和代码内部转义，完全避免正则/字符串转义被误替换
                            formatted_target_block = safe_escape_restore(target_block)
                            formatted_content = safe_escape_restore(content)
                            
                            # 必填参数校验
                            if not file_name or not operation:
                                exec_result = "⚠️ 参数错误：file_name和operation为必填参数"
                                all_exec_results.append(exec_result)
                                continue
                            
                            # 操作类型校验
                            allowed_operations = ["delete", "insert_before", "insert_after", "replace", "insert_start", "insert_end"]
                            if operation not in allowed_operations:
                                exec_result = f"⚠️ 不支持的操作类型：{operation}，可选值：{','.join(allowed_operations)}"
                                all_exec_results.append(exec_result)
                                continue
                            
                            # 锚点校验：非首尾插入/替换/删除需要target_block
                            if operation not in ["insert_start", "insert_end"] and not target_block:
                                exec_result = "⚠️ 参数错误：delete/insert_before/insert_after/replace操作必须传入gzt_anchor参数"  
                                all_exec_results.append(exec_result)
                                continue
                            
                            # 路径处理:自动识别绝对路径/相对路径，支持任意非禁止目录操作
                            op_path = get_real_physical_path(file_name)
                            # 校验是否为禁止操作路径（全目录生效，不管是项目内还是项目外）
                            forbidden, reason = is_path_forbidden(op_path)
                            if forbidden:
                                exec_result = f"⚠️ {reason}，禁止操作，请向用户说明"
                                all_exec_results.append(exec_result)
                                add_file_operation_log(operation, file_name, "fail", reason)
                                continue
                            # 如果路径在当前项目目录下，自动更新项目清单
                            if CURRENT_PROJECT["project_root"] and op_path.startswith(os.path.normpath(CURRENT_PROJECT["project_root"]).replace("\\", "/")):
                                rel_file_name = os.path.relpath(op_path, CURRENT_PROJECT["project_root"]).replace("\\", "/")
                                if rel_file_name not in CURRENT_PROJECT["file_list"] and os.path.exists(op_path):
                                    CURRENT_PROJECT["file_list"].append(rel_file_name)
                                    update_current_project_file_list()

                            # 调用智能编辑引擎
                            try:
                                success, msg = intelligent_file_editor.edit_file(
                                    file_path=op_path,
                                    operation=operation,
                                    target_block=formatted_target_block,
                                    content=formatted_content
                                )
                                if success:
                                    # 自动补全标准化绝对路径
                                    op_abs_path = get_real_physical_path(file_name) if os.path.isabs(file_name) else get_real_physical_path(os.path.relpath(op_path, CURRENT_PROJECT["project_root"] if CURRENT_PROJECT["project_root"] else REPOSITORY_PATH))
                                    exec_result = f"✅ {operation}操作成功:{file_name}\n{msg}\n📂 文件绝对路径:{op_abs_path}\n操作完成后读取文件确认修改状态"
                                    add_operation_log("文件操作", f"✅ {operation}操作成功:{file_name}，绝对路径:{op_abs_path}")
                                    # 异步更新RAG索引
                                    import asyncio
                                    asyncio.create_task(asyncio.to_thread(rag_manager.add_file, op_path))
                                    # 自动更新当前项目文件清单缓存
                                    update_current_project_file_list()
                                    # 触发文件变动广播
                                    broadcast_file_change()
                                else:
                                    add_operation_log("文件操作", f"❌ {operation}操作失败：{file_name}，错误：{msg}", "error")          
                                    exec_result = f"❌ {operation}操作失败：{file_name}\n{msg}\n⚠️ 分析工具调用失败原因：\n1.指令执行错误（锚点错误，：符号大小写错误导致匹配不上或者是锚点内容太少缺少唯一性），请向用户说明并执行一次重试；\n2. 工作台系统错误无法执行，已经执行第二次重试，请停止任务执行并向用户说明，给出可能性分析。"                                               
                            except Exception as e:
                                exec_result = f"❌ 编辑文件异常：{str(e)}\n⚠️ 分析工具调用失败原因：\n1. 指令执行错误（锚点错误，：符号大小写错误导致匹配不上或者是锚点内容太少缺少唯一性），请向用户说明并执行一次重试；\n2. 工作台系统错误无法执行，已经执行第二次重试，请停止任务执行并向用户说明，给出可能性分析。"
                                add_operation_log("文件操作", f"❌ 编辑文件异常：{file_name}，错误：{str(e)}", "error")
                            
                            all_exec_results.append(exec_result)
                            continue
                        if func_call.get("name") == "read_file":
                            file_name = func_call["parameters"]["file_name"].strip()
                            # 新增：记录AI读取文件日志
                            # 安全读取文件（优先读取当前选中项目下的文件，符合项目隔离要求）
                            def read_file_safe(fname):
                                # 标准化路径，自动处理绝对/相对路径、斜杠格式、相对符号
                                target_file_path = get_real_physical_path(fname)
                                if not target_file_path:
                                    return f"❌ 路径为空:{fname}"
                                # 校验是否为禁止操作路径
                                forbidden, reason = is_path_forbidden(target_file_path)
                                if forbidden:
                                    add_file_operation_log("read", fname, "fail", reason)
                                    return f"⚠️ {reason}，禁止读取"
                                # 校验文件是否存在且是文件
                                if not os.path.exists(target_file_path):
                                    err_msg = f"❌ 文件不存在:{fname}（标准化后路径:{target_file_path}）\n⚠️ 分析工具调用失败原因:\n1. 指令执行错误（路径拼写错误/文件不存在），请向用户说明并执行一次重试；\n2. 工作台系统错误无法执行或者已经执行第二次重试，请停止任务执行并向用户说明，给出可能性分析。"
                                    add_operation_log("文件操作", f"❌ 读取文件失败:{fname}，文件不存在")
                                    return err_msg
                                if not os.path.isfile(target_file_path):
                                    err_msg = f"❌ 路径是文件夹不是文件:{fname}（标准化后路径:{target_file_path}）\n⚠️ 分析工具调用失败原因:\n1. 指令执行错误（路径指向文件夹而非文件），请向用户说明并执行一次重试；\n2. 工作台系统错误无法执行或者已经执行第二次重试，请停止任务执行并向用户说明，给出可能性分析。"
                                    add_operation_log("文件操作", f"❌ 读取文件失败:{fname}，路径是文件夹")
                                    return err_msg
                                # 读取文件内容
                                try:
                                    # 自动识别图片文件，转多模态格式，避免按文本读取返回乱码
                                    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
                                    file_ext = os.path.splitext(target_file_path)[1].lower()
                                    if file_ext in IMAGE_EXTENSIONS:
                                        from llm_client import image_to_base64
                                        b64_str, img_meta = image_to_base64(target_file_path)
                                        # 构造图片识别提示
                                        if CURRENT_PROJECT["project_root"] and target_file_path.startswith(os.path.normpath(CURRENT_PROJECT["project_root"]).replace("\\", "/")):
                                            log_msg = f"✅ 读取当前项目图片文件成功:{fname}（绝对路径:{target_file_path}）"
                                        else:
                                            log_msg = f"✅ 读取图片文件成功:{fname}（绝对路径:{target_file_path}）"
                                        img_tip = f"{log_msg}\n"
                                        img_tip += f"📸 图片元信息:\n"
                                        img_tip += f"- 尺寸: {img_meta['width']}x{img_meta['height']}\n"
                                        img_tip += f"- 格式: {img_meta['format']}\n"
                                        img_tip += f"- 原始大小: {img_meta['original_size_mb']}MB\n"
                                        if img_meta['compressed']:
                                            img_tip += f"- 已自动压缩到: {img_meta['final_size_mb']}MB（避免超出模型上下文限制）\n"
                                        img_tip += "\n💡 图片已自动转换为OpenAI标准多模态格式传入上下文，你可以直接识别图片中的所有内容（文字、场景、物体、图表等），无需额外处理。\n📢 这是图片文件，直接根据图片内容回答用户问题即可，无需执行其他读取操作。"
                                        add_operation_log("文件操作", log_msg)
                                        return img_tip
                                    # 非图片文件按原有文本逻辑读取
                                    with open(target_file_path, "r", encoding="utf-8", errors="ignore") as f:
                                        content = f.read()
                                    # 判断文件所属位置，返回对应提示
                                    if CURRENT_PROJECT["project_root"] and target_file_path.startswith(os.path.normpath(CURRENT_PROJECT["project_root"]).replace("\\", "/")):
                                        log_msg = f"✅ 读取当前项目文件成功:{fname}（绝对路径:{target_file_path}）"
                                        return_msg = f"✅ 读取当前项目文件成功:{fname}（绝对路径:{target_file_path}）\n内容:\n{content}\n📢 这是文件完整内容，根据用户需求后给予反馈信息:\n 1. 用户要求读取文件，给出文件结构化说明，无需进行下一步操作；\n 2. 执行一轮修复任务当中（如果本轮任务已经完成直接给出任务完成说明），根据读取信息给出修复说明，并执行下一个指令（注意:修改指令代码缩进要和原文匹配） 。"
                                    else:
                                        log_msg = f"✅ 读取文件成功:{fname}（绝对路径:{target_file_path}）"
                                        return_msg = f"✅ 读取文件成功:{fname}（绝对路径:{target_file_path}）\n内容:\n{content}\n📢 这是文件完整内容，根据用户需求后给予反馈信息:\n 1. 用户要求读取文件，给出文件结构化说明，无需进行下一步操作；\n 2. 执行一轮修复任务当中（如果本轮任务已经完成直接给出任务完成说明），根据读取信息给出修复说明，并执行下一个指令（注意:修改指令代码缩进要和原文匹配）。"
                                    add_operation_log("文件操作", log_msg)
                                    return return_msg
                                except Exception as e:
                                    err_msg = f"❌ 读取文件失败:{fname}（绝对路径:{target_file_path}），错误:{str(e)}\n⚠️ 分析工具调用失败原因:\n1. 指令执行错误（文件权限不足/文件被占用），请向用户说明并执行一次重试；\n2. 工作台系统错误无法执行或者已经执行第二次重试，请停止任务执行并向用户说明，给出可能性分析。"
                                    add_operation_log("文件操作", f"❌ 读取文件失败:{fname}，错误:{str(e)}", "error")
                                    return err_msg
                            file_content = read_file_safe(file_name)
                            all_exec_results.append(file_content)
                            continue                

                        elif func_call.get("name") == "rag_search":
                            query = func_call["parameters"]["query"].strip()
                            # 新增:仅返回当前选中项目的检索结果，避免跨项目数据混杂
                            current_project = CURRENT_PROJECT["project_name"] if CURRENT_PROJECT["project_name"] else None
                            results = rag_manager.search(query, project_name=current_project)
                            exec_result = f"✅ 代码检索结果:\n"
                            add_operation_log("文件操作",f"✅ 代码检索结果:\n")
                            for res in results:
                                # 自动补全标准化绝对路径，AI可直接使用无需拼接
                                file_abs_path = get_real_physical_path(res['file_name'])
                                res['abs_path'] = file_abs_path
                                exec_result += f"📄 文件:{res['file_name']}（绝对路径:{file_abs_path}）\n```\n{res['content']}\n```\n"
                                add_operation_log("文件操作",f"📄 文件:{res['file_name']}（绝对路径:{file_abs_path}）\n```\n{res['content']}\n```\n")
                            exec_result += "\n💡 检索结果已自动补全文件绝对路径，直接使用abs_path字段调用文件操作工具即可，无需自行拼接路径"
                            all_exec_results.append(exec_result)
                            continue
                        elif func_call.get("name") == "exec_cmd":
                            cmd = func_call["parameters"]["cmd"].strip()
                            exec_result = ""
                            # 安全白名单校验，禁止执行危险命令和命令注入
                            # 使用正则全词匹配，避免子字符串误判（如chardet包含rd，format包含rm）
                            lower_cmd = cmd.lower()
                            danger_keywords = ["rm", "format", "rd", "erase", "mkfs", "dd"]
                            # 非curl/wget命令额外禁止&，避免命令拼接，curl/wget允许URL参数带&
                            if not (lower_cmd.startswith("curl") or lower_cmd.startswith("wget")):
                                danger_keywords.append("&")
                            # 构建正则全词匹配模式，\b确保只匹配独立单词
                            import re as _re
                            danger_pattern = _re.compile(r'\b(?:' + '|'.join(_re.escape(k) for k in danger_keywords) + r')\b')
                            if danger_pattern.search(lower_cmd):
                                exec_result = "❌ 禁止执行危险命令/命令拼接，仅允许执行单条查询类命令"
                                add_operation_log("AI执行命令", exec_result, "error")
                                all_exec_results.append(exec_result)
                                continue

                            # 校验下载命令域名白名单
                            ALLOWED_DOWNLOAD_DOMAINS = ["volces.com", "openai.com", "open-meteo.com", "github.com", "huggingface.co"]
                            if "curl" in cmd.lower() or "wget" in cmd.lower():
                                import re
                                domain_match = re.search(r'https?://([^/]+)', cmd)
                                if domain_match:
                                    domain = domain_match.group(1)
                                    if not any(domain.endswith(d) for d in ALLOWED_DOWNLOAD_DOMAINS):
                                        exec_result = "❌ 禁止访问未授权域名，仅允许访问白名单内公开域名"
                                        add_operation_log("AI执行命令", exec_result, "error")
                                        all_exec_results.append(exec_result)
                                        continue
                            try:
                                import subprocess
                                # 执行命令，超时10秒避免阻塞
                                result = subprocess.run(cmd, shell=True, capture_output=True, timeout=10)
                                # 自动兼容多编码，解决Windows CMD中文乱码问题
                                def decode_content(content: bytes) -> str:
                                    try:
                                        return content.decode('utf-8')
                                    except:
                                        return content.decode('gbk', errors='ignore')
                                stdout = decode_content(result.stdout)
                                stderr = decode_content(result.stderr)
                                exec_result = f"✅ 命令执行成功：命令：{cmd} 标准输出：{stdout} "
                                if stderr.strip():
                                    exec_result += f"标准错误：{stderr}向用户说明执行指令后得到结构化信息"
                                    add_operation_log("AI执行命令", f"执行命令：{cmd}，错误信息：{stderr[:200]}", "error")
                                else:
                                    add_operation_log("AI执行命令", f"执行命令成功：{cmd}")
                            except subprocess.TimeoutExpired:
                                exec_result = f"❌ 命令执行超时（超过10秒）：{cmd}"
                            except Exception as e:
                                exec_result = f"❌ 命令执行失败：{str(e)}向用户说明执行指令后得到结构化信息"
                                add_operation_log("AI执行命令",f"❌ 命令执行失败：{str(e)}")
                            all_exec_results.append(exec_result)
                            continue

                        elif func_call.get("name") == "write_file":
                            file_name = func_call["parameters"]["file_name"].strip()
                            content = func_call["parameters"]["content"]
                            # 统一路径处理，支持任意非禁止目录的绝对路径/相对路径写入
                            write_path = get_real_physical_path(file_name)
                            # 校验是否为禁止操作路径
                            forbidden, reason = is_path_forbidden(write_path)
                            if forbidden:
                                exec_result = f"⚠️ {reason}，禁止写入"
                                all_exec_results.append(exec_result)
                                add_file_operation_log("write", file_name, "fail", reason)
                                continue
                            try:
                                os.makedirs(os.path.dirname(write_path), exist_ok=True)
                                with open(write_path, "w", encoding="utf-8") as f:
                                    f.write(content)
                                # 自动补全绝对路径返回
                                write_abs_path = get_real_physical_path(write_path)
                                exec_result = f"✅ 写入文件成功:{file_name}（绝对路径:{write_abs_path}）"
                                add_operation_log("文件操作", f"✅ 写入文件成功:{file_name}，绝对路径:{write_abs_path}")
                                # 异步更新RAG
                                import asyncio
                                asyncio.create_task(asyncio.to_thread(rag_manager.add_file, write_path))
                                # 如果路径在当前项目目录下，自动更新项目清单和手册
                                if CURRENT_PROJECT["project_root"] and write_path.startswith(os.path.normpath(CURRENT_PROJECT["project_root"]).replace("\\", "/")):
                                    async def sync_manual():
                                        try:
                                            project_manual_manager.update_manual_detail_table(CURRENT_PROJECT["manual_path"])
                                        except:
                                            pass
                                    asyncio.create_task(sync_manual())
                                    # 自动将新文件加入清单并更新缓存
                                    rel_file_name = os.path.relpath(write_path, CURRENT_PROJECT["project_root"]).replace("\\", "/")
                                    if rel_file_name not in CURRENT_PROJECT["file_list"]:
                                        CURRENT_PROJECT["file_list"].append(rel_file_name)
                                    update_current_project_file_list()
                                # 触发文件变动广播
                                broadcast_file_change()
                            except Exception as e:
                                exec_result = f"❌ 写入文件失败:{str(e)}，路径:{write_path}"
                                add_operation_log("文件操作", f"❌ 写入文件失败:{str(e)}，路径:{write_path}", "error")
                            all_exec_results.append(exec_result)
                            continue

                        elif func_call.get("name") == "create_file":
                            path = func_call["parameters"]["path"].strip()
                            raw_is_dir = func_call["parameters"].get("is_dir", False)
                            # 统一转换is_dir为布尔值，兼容字符串类型的true/false
                            if isinstance(raw_is_dir, str):
                                is_dir = raw_is_dir.strip().lower() == "true"
                            else:
                                is_dir = bool(raw_is_dir)
                            content = func_call["parameters"].get("gzt_newtext") or func_call["parameters"].get("content", "")
                            # 统一路径处理，支持任意非禁止目录的绝对路径/相对路径创建
                            create_path = get_real_physical_path(path)
                            # 校验是否为禁止操作路径
                            forbidden, reason = is_path_forbidden(create_path)
                            if forbidden:
                                exec_result = f"⚠️ {reason}，禁止创建"
                                all_exec_results.append(exec_result)
                                add_file_operation_log("create", path, "fail", reason)
                                continue
                            # 校验路径是否已存在
                            if os.path.exists(create_path):
                                exec_result = f"❌ 创建失败:路径【{path}】已存在（标准化后路径:{create_path}）"
                                all_exec_results.append(exec_result)
                                add_file_operation_log("create", path, "fail", "路径已存在")
                                continue
                            try:
                                if is_dir:
                                    os.makedirs(create_path, exist_ok=True)
                                    # 自动补全绝对路径返回
                                    create_abs_path = get_real_physical_path(create_path)
                                    exec_result = f"✅ 文件夹创建成功:{path}（绝对路径:{create_abs_path}）"
                                    add_operation_log("文件操作", f"✅ 文件夹创建成功:{path}，绝对路径:{create_abs_path}")
                                else:
                                    os.makedirs(os.path.dirname(create_path), exist_ok=True)
                                    # 支持直接写入传入内容，空则创建空文件
                                    with open(create_path, "w", encoding="utf-8") as f:
                                        f.write(content)
                                    create_abs_path = get_real_physical_path(create_path)
                                    if content:
                                        exec_result = f"✅ 文件创建+写入成功:{path}（绝对路径:{create_abs_path}），共写入{len(content)}字符"
                                        add_operation_log("文件操作", f"✅ 文件创建+写入成功:{path}，绝对路径:{create_abs_path}")
                                    else:
                                        exec_result = f"✅ 空文件创建成功:{path}（绝对路径:{create_abs_path}）"
                                        add_operation_log("文件操作", f"✅ 空文件创建成功:{path}，绝对路径:{create_abs_path}")
                                # 异步更新RAG索引
                                import asyncio
                                asyncio.create_task(asyncio.to_thread(rag_manager.add_file, create_path))
                                # 如果路径在当前项目目录下，自动更新项目清单和手册
                                if CURRENT_PROJECT["project_root"] and create_path.startswith(os.path.normpath(CURRENT_PROJECT["project_root"]).replace("\\", "/")):
                                    async def sync_manual():
                                        try:
                                            project_manual_manager.update_manual_detail_table(CURRENT_PROJECT["manual_path"])
                                        except:
                                            pass
                                    asyncio.create_task(sync_manual())
                                    # 自动更新当前项目文件清单缓存
                                    update_current_project_file_list()
                                # 触发文件变动广播
                                broadcast_file_change()
                            except Exception as e:
                                exec_result = f"❌ 创建失败:{str(e)}，路径:{create_path}"
                                add_operation_log("文件操作", f"❌ 创建失败:{str(e)}，路径:{create_path}", "error")
                            all_exec_results.append(exec_result)
                            continue
                        elif func_call.get("name") == "delete_file":
                            file_name = func_call["parameters"]["file_name"].strip()
                            # 统一路径处理，支持任意非禁止目录的绝对路径/相对路径删除
                            delete_path = get_real_physical_path(file_name)
                            # 校验是否为禁止操作路径
                            forbidden, reason = is_path_forbidden(delete_path)
                            if forbidden:
                                exec_result = f"⚠️ {reason}，禁止删除"
                                all_exec_results.append(exec_result)
                                add_file_operation_log("delete", file_name, "fail", reason)
                                continue
                            # 校验路径是否存在
                            if not os.path.exists(delete_path):
                                exec_result = f"❌ 删除失败:路径【{file_name}】不存在（标准化后路径:{delete_path}）"
                                all_exec_results.append(exec_result)
                                add_file_operation_log("delete", file_name, "fail", "路径不存在")
                                continue
                            try:
                                if os.path.isdir(delete_path):
                                    import shutil
                                    shutil.rmtree(delete_path)
                                else:
                                    os.remove(delete_path)
                                # 自动补全绝对路径返回
                                delete_abs_path = get_real_physical_path(delete_path)
                                exec_result = f"✅ 删除成功:{file_name}（绝对路径:{delete_abs_path}）"
                                add_operation_log("文件操作", f"✅ 删除成功:{file_name}，绝对路径:{delete_abs_path}")
                                # 异步更新RAG索引
                                import asyncio
                                asyncio.create_task(asyncio.to_thread(rag_manager.delete_file, delete_path))
                                # 如果路径在当前项目目录下，自动更新项目清单和手册
                                if CURRENT_PROJECT["project_root"] and delete_path.startswith(os.path.normpath(CURRENT_PROJECT["project_root"]).replace("\\", "/")):
                                    # 删除后同步移除清单中的文件
                                    rel_file_name = os.path.relpath(delete_path, CURRENT_PROJECT["project_root"]).replace("\\", "/")
                                    if rel_file_name in CURRENT_PROJECT["file_list"]:
                                        CURRENT_PROJECT["file_list"].remove(rel_file_name)
                                    async def sync_manual():
                                        try:
                                            project_manual_manager.update_manual_detail_table(CURRENT_PROJECT["manual_path"])
                                        except:
                                            pass
                                    asyncio.create_task(sync_manual())
                                    # 自动更新当前项目文件清单缓存
                                    update_current_project_file_list()
                                # 触发文件变动广播
                                broadcast_file_change()
                            except Exception as e:
                                exec_result = f"❌ 删除失败:{str(e)}，路径:{delete_path}"
                                add_operation_log("文件操作", f"❌ 删除失败:{str(e)}，路径:{delete_path}", "error")
                            all_exec_results.append(exec_result)
                            continue
                        elif func_call.get("name") == "rename_file":
                            old_path = func_call["parameters"]["old_path"].strip()
                            new_name = func_call["parameters"]["new_name"].strip()
                            # 统一路径处理，支持任意非禁止目录的绝对路径/相对路径重命名
                            old_abs_path = get_real_physical_path(old_path)
                            new_abs_path = os.path.join(os.path.dirname(old_abs_path), new_name).replace("\\", "/")
                            # 校验原路径是否存在
                            if not os.path.exists(old_abs_path):
                                exec_result = f"❌ 重命名失败:原路径【{old_path}】不存在（标准化后路径:{old_abs_path}）"
                                all_exec_results.append(exec_result)
                                add_file_operation_log("rename", old_path, "fail", "原路径不存在")
                                continue
                            # 校验新路径是否已存在
                            if os.path.exists(new_abs_path):
                                exec_result = f"❌ 重命名失败:目标路径【{new_name}】已存在（标准化后路径:{new_abs_path}）"
                                all_exec_results.append(exec_result)
                                add_file_operation_log("rename", old_path, "fail", "目标路径已存在")
                                continue
                            # 校验原路径是否禁止操作
                            forbidden_old, reason_old = is_path_forbidden(old_abs_path)
                            if forbidden_old:
                                exec_result = f"⚠️ {reason_old}，禁止重命名"
                                all_exec_results.append(exec_result)
                                add_file_operation_log("rename", old_path, "fail", reason_old)
                                continue
                            # 校验新路径是否禁止操作
                            forbidden_new, reason_new = is_path_forbidden(new_abs_path)
                            if forbidden_new:
                                exec_result = f"⚠️ {reason_new}，目标路径禁止操作"
                                all_exec_results.append(exec_result)
                                add_file_operation_log("rename", old_path, "fail", reason_new)
                                continue
                            try:
                                os.rename(old_abs_path, new_abs_path)
                                # 自动补全绝对路径返回
                                new_abs_path_std = get_real_physical_path(new_abs_path)
                                exec_result = f"✅ 重命名成功:{old_path} → {new_name}（新路径绝对路径:{new_abs_path_std}）"
                                add_operation_log("文件操作", f"✅ 重命名成功:{old_path} → {new_name}，新路径:{new_abs_path_std}")
                                # 异步更新RAG索引（删除旧路径，添加新路径）
                                import asyncio
                                asyncio.create_task(asyncio.to_thread(rag_manager.delete_file, old_abs_path))
                                asyncio.create_task(asyncio.to_thread(rag_manager.add_file, new_abs_path))
                                # 如果路径在当前项目目录下，自动更新项目清单和手册
                                if CURRENT_PROJECT["project_root"] and old_abs_path.startswith(os.path.normpath(CURRENT_PROJECT["project_root"]).replace("\\", "/")):
                                    # 更新文件清单:移除旧相对路径，添加新相对路径
                                    rel_old_path = os.path.relpath(old_abs_path, CURRENT_PROJECT["project_root"]).replace("\\", "/")
                                    rel_new_path = os.path.relpath(new_abs_path, CURRENT_PROJECT["project_root"]).replace("\\", "/")
                                    if rel_old_path in CURRENT_PROJECT["file_list"]:
                                        CURRENT_PROJECT["file_list"].remove(rel_old_path)
                                    if rel_new_path not in CURRENT_PROJECT["file_list"]:
                                        CURRENT_PROJECT["file_list"].append(rel_new_path)
                                    async def sync_manual():
                                        try:
                                            project_manual_manager.update_manual_detail_table(CURRENT_PROJECT["manual_path"])
                                        except:
                                            pass
                                    asyncio.create_task(sync_manual())
                                    # 自动更新当前项目文件清单缓存
                                    update_current_project_file_list()
                                # 触发文件变动广播
                                broadcast_file_change()
                            except Exception as e:
                                exec_result = f"❌ 重命名失败:{str(e)}，原路径:{old_abs_path}，新路径:{new_abs_path}"
                                add_operation_log("文件操作", f"❌ 重命名失败:{str(e)}，原路径:{old_abs_path}，新路径:{new_abs_path}", "error")
                            all_exec_results.append(exec_result)
                            continue
                        else:
                            # 判断是否是插件
                            plugin_config = tool_template_manager.get_plugin_config(current_tool_name)
                            if plugin_config:
                                # 权限校验
                                allowed_perms = plugin_config.get("permissions", [])
                                # 校验插件是否有执行权限（可扩展用户授权逻辑）
                                try:
                                    # 记录插件执行开始日志
                                    params_str = json.dumps(func_call["parameters"], ensure_ascii=False)
                                    start_log_content = f"🔄 开始执行插件【{plugin_config['name']}({current_tool_name})】，参数:{params_str}"
                                    add_operation_log("插件执行", start_log_content)
                                    # 实时推送到前端日志
                                    push_sse_message(req.session_id, {
                                        "type": "operation_log",
                                        "oper_type": "插件执行",
                                        "content": start_log_content,
                                        "status": "running",
                                        "timestamp": time.time()
                                    })
                                    
                                    # 加载插件入口代码，沙箱执行
                                    plugin_path = os.path.join(tool_template_manager.PLUGIN_DIR, current_tool_name, plugin_config["entry"])
                                    if not os.path.exists(plugin_path):
                                        exec_result = f"❌ 插件入口文件不存在:{plugin_config['entry']}"
                                        # 记录失败日志
                                        fail_log_content = f"❌ 执行插件【{plugin_config['name']}】失败:{exec_result}"
                                        add_operation_log("插件执行", fail_log_content, "error")
                                        # 推送失败日志
                                        push_sse_message(req.session_id, {
                                            "type": "operation_log",
                                            "oper_type": "插件执行",
                                            "content": fail_log_content,
                                            "status": "error",
                                            "timestamp": time.time()
                                        })
                                        all_exec_results.append(exec_result)
                                        continue
                                    # 导入插件模块执行，强制清理缓存保证是最新代码/配置
                                    import importlib.util
                                    import sys
                                    plugin_module_name = f"plugin_{current_tool_name}"
                                    # 清理模块缓存，避免复用旧的配置和代码
                                    if plugin_module_name in sys.modules:
                                        del sys.modules[plugin_module_name]
                                    spec = importlib.util.spec_from_file_location(plugin_module_name, plugin_path)
                                    plugin_module = importlib.util.module_from_spec(spec)
                                    spec.loader.exec_module(plugin_module)
                                    # 注入合并后的用户配置（默认配置+用户修改配置）到插件模块
                                    plugin_module.plugin_config = plugin_config["merged_config"]
                                    # 调用插件主函数，传入参数（封装为字典符合插件接口定义）
                                    exec_result = plugin_module.run(func_call["parameters"])
                                    # 记录成功日志
                                    result_str = str(exec_result)
                                    success_log_content = f"✅ 执行插件【{plugin_config['name']}】成功，返回结果:{result_str[:200]}{'...' if len(result_str)>200 else ''}"
                                    add_operation_log("插件执行", success_log_content)
                                    # 推送成功日志
                                    push_sse_message(req.session_id, {
                                        "type": "operation_log",
                                        "oper_type": "插件执行",
                                        "content": success_log_content,
                                        "status": "success",
                                        "timestamp": time.time()
                                    })
                                    all_exec_results.append(f"✅ 插件执行成功:{current_tool_name}\n{exec_result}")
                                    continue
                                except Exception as e:
                                    exec_result = f"❌ 插件执行失败:{str(e)}"
                                    # 记录异常日志
                                    fail_log_content = f"❌ 执行插件【{plugin_config.get('name', current_tool_name)}】异常:{str(e)}"
                                    add_operation_log("插件执行", fail_log_content, "error")
                                    # 推送异常日志
                                    push_sse_message(req.session_id, {
                                        "type": "operation_log",
                                        "oper_type": "插件执行",
                                        "content": fail_log_content,
                                        "status": "error",
                                        "timestamp": time.time()
                                    })
                                    all_exec_results.append(exec_result)
                                    continue
                            # 未知工具类型，直接返回原始内容
                            response += current_response
                            break
                except json.JSONDecodeError as e:
                    # 单条指令解析失败，上报错误后跳过继续执行其他指令
                    error_msg = f"❌ 指令解析失败：JSON语法错误，错误详情：{str(e)}，原始指令前200字符：{json_str[:200]}...向用户说明工具调用失败原因"
                    add_operation_log("工具执行", error_msg, "error")
                    # 实时推送错误到前端日志面板
                    push_sse_message(req.session_id, {
                        "type": "operation_log",
                        "oper_type": "工具执行",
                        "content": error_msg,
                        "status": "error",
                        "timestamp": time.time()
                    })
                    all_exec_results.append(error_msg)
                    continue

            # 所有工具执行完成后，合并结果加入上下文继续推理
            if all_exec_results:
                # 更新连续错误计数
                has_error = any("❌" in res or "⚠️" in res for res in all_exec_results)
                if has_error:
                    consecutive_errors += 1
                else:
                    consecutive_errors = 0
                # 达到错误上限直接停止
                if consecutive_errors >=3:
                    final_result = "\n".join([f"🔹 指令{i+1}执行结果：{res}" for i, res in enumerate(all_exec_results)])
                    # 追加工具执行结果到结构化记忆
                    structured_content += f"工具执行结果：{final_result}\n"
                    response += final_result
                    break
                final_result = "\n".join([f"🔹 指令{i+1}执行结果:{res}" for i, res in enumerate(all_exec_results)])
                
                # 注入回复进度信息，让AI助手感知当前调用次数和剩余次数，自主规划收尾
                remaining_calls = max_tool_calls - current_calls
                if remaining_calls <= 3:
                    progress_info = f"\n⚠️ 当前轮次回复次数即将用尽，当前第{current_calls}次/当前轮次回复次数上限{max_tool_calls}次（剩余{remaining_calls}次），请优先完成核心任务并准备收尾总结，收尾总结内容中向用户说明任务进度"
                else:
                    progress_info = f"\n📊 当前进度:第{current_calls}次/当前轮次回复次数上限{max_tool_calls}次（剩余{remaining_calls}次）"
                final_result += progress_info
                
                # ✅ 全量追加所有工具执行结果到结构化记忆
                structured_content += f"工具执行结果:{final_result}\n"
                messages.append({"role": "assistant", "content": current_response})
                messages.append({"role": "user", "content": final_result})
                continue
            # ========== 无工具调用直接停止 ==========
            # 没有任何工具执行结果，说明AI已经返回最终答案，直接停止循环
            response = current_response.strip()
            break

        except Exception as llm_e:
            # LLM调用全局异常捕获:所有错误友好提示，不会直接500无响应
            import traceback
            error_detail = str(llm_e)
            # 常见错误友好提示
            if "context_length" in error_detail.lower() or "context length" in error_detail.lower() or "max_tokens" in error_detail.lower() or "超出上下文" in error_detail or "上下文超限" in error_detail:
                error_msg = "❌ 上下文长度超出限制，请清空部分对话历史或新建会话后重试"
            elif "api_key" in error_detail.lower() or "unauthorized" in error_detail.lower() or "401" in error_detail:
                error_msg = "❌ API密钥无效，请检查配置中的API密钥是否正确"
            elif "timeout" in error_detail.lower() or "timed out" in error_detail.lower():
                error_msg = "❌ 请求超时，请检查网络连接后重试"
            elif "connection" in error_detail.lower() or "connect" in error_detail.lower():
                error_msg = "❌ 网络连接失败，请检查网络是否正常、API地址是否可访问"
            elif "model" in error_detail.lower() and ("not found" in error_detail.lower() or "invalid" in error_detail.lower()):
                error_msg = "❌ 模型名称无效，请检查配置中的模型名是否正确"
            else:
                error_msg = "❌ 未知错误，请稍后重试"
            # 推送完整正式内容
            push_sse_message(req.session_id, {
                "type": "ai_output",
                "content": error_msg,
                "timestamp": time.time()
            })
            add_operation_log("AI调用", error_msg, "error")
            print(f"❌ LLM调用异常:{str(llm_e)}")
            traceback.print_exc()
            response = error_msg
        finally:
            # 统一推送结束信号
            push_sse_message(req.session_id, {
                "type": "done",
                "timestamp": time.time()
            })
    CHAT_STOP_SIGNALS.discard(req.session_id)

    # 4. 自动将所有对话内容写入记忆库，无任何限制
    final_structured = structured_content.strip()
    # 只要有对话内容（哪怕被打断/短内容）都写入记忆库
    if req.query.strip() or final_structured.strip():
        # 结构化记忆内容生成，外层格式完全保留原有规范
        import re
        # 🔹 修复1:兼容全角/半角冒号，匹配所有读取文件成功场景（当前项目/全局/白名单/仓库根目录/全路径/跨目录），正确提取文件名
        final_structured = re.sub(
            r'🔹 指令\d+执行结果[:：]✅ 读取(?:当前项目文件|全局文件|全局白名单文件|仓库根目录文件|文件)成功[:：](.+?)\n[\s\S]*?(?=\n🔹 指令|\n【第|\Z)',
            r'🔹 执行结果：✅ 读取文件「\1」成功，完整内容已在对话中返回，可随时重新调用查看',
            final_structured
        )
        # 🔹 修复2:兼容全角/半角冒号，匹配所有读取文件失败场景，替换长错误栈为摘要
        final_structured = re.sub(
            r'🔹 指令\d+执行结果[:：]❌ 读取(?:当前项目文件|全局文件|全局白名单文件|仓库根目录文件|项目文件|仓库文件|文件)失败[:：](.+?)\n[\s\S]*?(?=\n🔹 指令|\n【第|\Z)',
            r'🔹 执行结果：❌ 读取文件「\1」失败，可重新调用工具查看详细错误信息',
            final_structured
        )
        # 🔹 新增：替换文件编辑/写入/创建/删除/重命名类操作的长内容为摘要，避免大段JSON/代码存入记忆
        final_structured = re.sub(
            r'🔹 指令\d+执行结果[:：]✅ (?:edit_file|write_file|create_file|delete_file|rename_file)操作成功[:：](.+?)\n[\s\S]*?(?=\n🔹 指令|\n【第|\Z)',
            r'🔹 执行结果：✅ \1操作成功，操作详情可查看操作日志',
            final_structured
        )
        # 🔹 新增：替换RAG检索长代码片段为摘要，避免大段检索结果占满记忆
        final_structured = re.sub(
            r'🔹 指令\d+执行结果[:：]✅ 代码检索结果[:：]\n[\s\S]*?(?=\n🔹 指令|\n【第|\Z)',
            r'🔹 执行结果：✅ 代码检索完成，匹配结果已在对话中返回，可随时重新检索',
            final_structured
        )
        # 🔹 新增：替换命令执行长输出为摘要，避免大段终端输出存入记忆
        final_structured = re.sub(
            r'🔹 指令\d+执行结果[:：]✅ 命令执行成功[:：]命令[:：].+?标准输出[:：][\s\S]*?(?=\n🔹 指令|\n【第|\Z)',
            r'🔹 执行结果：✅ 命令执行成功，输出结果已在对话中返回',
            final_structured
        )
        content = f"用户问:{req.query}\n回答:{final_structured}"
        tags = []
        # 自动判断内容类型打标签
        if any(key in content for key in [".py", ".md", "函数", "接口", "代码", "变量", "类"]):
            tags.append("code")
        if any(key in content for key in ["工具调用", "exec_cmd", "rag_search", "read_file", "write_file"]):
            tags.append("tool")
        if any(key in content for key in ["阈值", "配置", "参数", "设置", "config"]):
            tags.append("config")
        # 默认加chat标签
        if not tags:
            tags.append("chat")
        # 新增:自动注入当前项目名作为记忆标签
        project_name = CURRENT_PROJECT.get("project_name", "default") if CURRENT_PROJECT else "default"
        tags.append(f"project:{project_name}")
        memory_cache.add_memory(content, tags=tags)
    # 同步更新全局持久化历史，自动按配置轮数轮动
    save_global_history(req.query, final_structured, memory_cache.config["history_context_rounds"])

    # 新增：记录AI回复完成日志
    return {"response": response, "recalled_memory_count": len(recall_result["memory_recall"]), "session_id": req.session_id}

@app.get("/api/chat/stream/{session_id}")
async def chat_stream(session_id: str):
    """SSE流式推送AI输出通道，完全独立于推理逻辑，实现显示与推理100%解耦"""
    global global_event_loop
    import asyncio
    global_event_loop = asyncio.get_running_loop()
    queue = asyncio.Queue()
    SSE_CONNECTIONS[session_id] = queue
    
    async def event_generator():
        try:
            while True:
                # 等待消息或30秒超时（心跳间隔）
                get_task = asyncio.create_task(queue.get())
                done, pending = await asyncio.wait(
                    [get_task],
                    timeout=30,
                    return_when=asyncio.FIRST_COMPLETED
                )
                # 主动取消pending任务，避免残留报pending销毁错误
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                if done:
                    # 有消息推送正常发送
                    data = done.pop().result()
                    json_str = json.dumps(data, ensure_ascii=False).replace('\n', '\\n').replace('\r', '\\r')
                    yield f"data: {json_str}\n\n"
                else:
                    # 无消息发送心跳包保活
                    heartbeat = json.dumps({"type": "heartbeat", "timestamp": time.time()}).replace('\n', '\\n').replace('\r', '\\r')
                    yield f"data: {heartbeat}\n\n"
        except asyncio.CancelledError:
            # 正常取消，忽略
            pass
        except Exception as e:
            # 捕获所有其他异常（如客户端断开连接），避免连接残留
            print(f"⚠️ SSE连接异常断开: session_id={session_id}, 错误: {str(e)}")
        finally:
            # 无论正常还是异常，都清理连接，避免残留无效队列导致消息丢失
            if session_id in SSE_CONNECTIONS:
                del SSE_CONNECTIONS[session_id]
    
    return EventSourceResponse(event_generator(), media_type="text/event-stream")
# 终止对话请求模型
class ChatStopRequest(BaseModel):
    session_id: str

@app.post("/api/chat/stop")
async def stop_chat(req: ChatStopRequest):
    """强制终止指定会话的AI输出"""
    CHAT_STOP_SIGNALS.add(req.session_id)
    return {"code": 200, "msg": "已发送停止信号，AI输出将立即终止"}
# 通用聊天附件上传接口（统一支持所有文件格式，图片/文档/音频等共用）
@app.post("/api/chat/upload_file")
async def upload_chat_file(file: UploadFile = File(...)):
    """
    通用聊天附件上传接口，所有文件/图片共用
    支持格式：所有常用格式，最大20MB
    """
    # 允许的所有格式（可按需扩展，全场景覆盖）
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "pdf", "docx", "xlsx", "txt", "md", "mp3", "mp4", "wav", "py", "js", "html", "css", "sql", "yml", "yaml", "go", "java", "cpp", "c", "sh", "json", "zip", "rar", "7z"}
    MAX_FILE_SIZE = 20 * 1024 * 1024 # 20MB
    
    # 自动识别文件类型
    def get_file_type(ext: str) -> str:
        if ext in {"jpg", "jpeg", "png", "gif", "webp"}:
            return "image"
        elif ext in {"pdf", "docx", "xlsx", "txt", "md"}:
            return "document"
        elif ext in {"mp3", "wav", "flac"}:
            return "audio"
        elif ext in {"mp4", "mov", "avi"}:
            return "video"
        else:
            return "other"
    
    # 校验文件格式
    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式，仅允许：{','.join(ALLOWED_EXTENSIONS)}")
    
    # 读取文件内容校验大小
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过限制，最大支持20MB")
    
    # 生成UUID唯一文件名，避免冲突覆盖
    file_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(UPLOAD_ROOT, file_name)
    
    # 保存文件到本地
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # 返回可直接访问的静态URL+文件类型，前后端统一处理
    access_url = f"/upload/{file_name}"
    file_type = get_file_type(ext)
    return JSONResponse(content={
        "code": 200,
        "msg": "上传成功",
        "data": {
            "url": access_url,
            "file_type": file_type,
            "original_name": file.filename,
            "ext": ext,
            "size": len(file_content),
            "local_path": file_path
        }
    })
# ========================== 通用文件上传接口 ==========================
def get_real_physical_path(input_path: str) -> str:
    """
    将输入路径转换为标准化的真实物理绝对路径，兼容Windows/Mac/Linux
    统一使用/作为路径分隔符，自动解析./../等相对符号，兼容绝对路径/相对路径输入
    相对路径基准规则:优先使用当前选中项目根目录，未选中项目则使用仓库根目录
    """
    if not input_path:
        return ""
    # 第一步:预处理，统一斜杠格式，去除首尾空格
    processed_path = input_path.strip().replace("\\", "/")
    # 第二步:判断是否为绝对路径
    if os.path.isabs(processed_path):
        # 绝对路径:标准化后统一斜杠返回
        norm_path = os.path.normpath(processed_path).replace("\\", "/")
        return norm_path
    # 第三步:相对路径:根据当前项目状态选择基准目录
    if CURRENT_PROJECT["project_root"]:
        # 有选中项目:相对路径基准为当前项目根目录
        base_root = CURRENT_PROJECT["project_root"].replace("\\", "/")
    else:
        # 无选中项目:相对路径基准为仓库根目录
        base_root = REPOSITORY_PATH.replace("\\", "/")
    full_path = os.path.join(base_root, processed_path).replace("\\", "/")
    norm_path = os.path.normpath(full_path).replace("\\", "/")
    return norm_path

def get_relative_path(abs_path: str) -> str:
    """将绝对路径转换为相对于当前基准目录（当前项目根/仓库根）的相对路径，统一使用/作为分隔符，路径在基准目录外则直接返回绝对路径"""
    if not abs_path:
        return ""
    norm_abs = abs_path.replace("\\", "/")
    # 选择基准目录
    if CURRENT_PROJECT["project_root"]:
        base_root = CURRENT_PROJECT["project_root"].replace("\\", "/")
    else:
        base_root = REPOSITORY_PATH.replace("\\", "/")
    try:
        rel_path = os.path.relpath(norm_abs, base_root).replace("\\", "/")
        # 处理路径穿越到基准目录外的情况，直接返回绝对路径
        if rel_path.startswith("../"):
            return norm_abs
        return rel_path
    except:
        return norm_abs

def load_upload_map() -> Dict:
    """加载本地路径与公网URL映射表"""
    with open(FILE_UPLOAD_MAP_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_upload_map(map_data: Dict):
    """保存本地路径与公网URL映射表"""
    with open(FILE_UPLOAD_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(map_data, f, ensure_ascii=False, indent=2)

def upload_file_to_tos(local_file_path: str, file_type: str = "image") -> Optional[str]:
    """上传本地文件到火山TOS对象存储，返回永久公网URL"""
    config = load_config()
    tos_config = config.get("system", {})
    # 校验TOS配置是否完整
    required_fields = ["tos_endpoint", "tos_bucket", "tos_ak", "tos_sk"]
    if not all(tos_config.get(field) for field in required_fields):
        return None
    try:
        from tos import TosClientV2
        # 初始化TOS客户端
        client = TosClientV2(
            endpoint=tos_config["tos_endpoint"],
            access_key_id=tos_config["tos_ak"],
            access_key_secret=tos_config["tos_sk"],
            region="cn-beijing"
        )
        # 生成唯一文件名，避免重复
        file_ext = os.path.splitext(local_file_path)[1].lower()
        file_name = f"{uuid.uuid4().hex}{file_ext}"
        # 按文件类型分类存储
        key = f"{file_type}/{file_name}"
        # 上传文件
        with open(local_file_path, "rb") as f:
            client.put_object(tos_config["tos_bucket"], key, content=f)
        # 生成公网URL（永久有效，桶配置公共读权限即可）
        public_url = f"{tos_config['tos_endpoint'].replace('https://', 'https://' + tos_config['tos_bucket'] + '.')}/{key}"
        return public_url
    except Exception as e:
        print(f"TOS上传失败:{str(e)}")
        return None

# 【已废弃】公共匿名托管API（0x0.st/catbox.moe）已移除，统一使用TOS对象存储，TOS失败时由插件层处理本地转码

@app.post("/api/v1/common/upload")
async def common_upload(
    local_path: Optional[str] = Form(None),
    file_type: Optional[str] = Form("other"),
    override: Optional[bool] = Form(False)
):
    """
    通用文件上传接口，支持两种场景:
    1. 前端传文件流:传file参数
    2. 后端插件传本地路径:传local_path参数
    返回:本地路径、公网URL、文件ID、上传时间
    """
    # 参数校验:二选一必填
    if not file and not local_path:
        raise HTTPException(status_code=400, detail="参数错误:file和local_path不能同时为空")
    if file and local_path:
        raise HTTPException(status_code=400, detail="参数错误:file和local_path只能传一个")
    
    real_local_path = ""
    file_ext = ""
    file_size = 0
    original_name = ""
    
    # 场景1:前端传文件流
    if file:
        original_name = file.filename
        file_ext = original_name.split(".")[-1].lower()
        file_content = await file.read()
        file_size = len(file_content)
        # 保存到本地临时目录
        temp_file_name = f"{uuid.uuid4().hex}.{file_ext}"
        real_local_path = os.path.join(UPLOAD_ROOT, temp_file_name)
        with open(real_local_path, "wb") as f:
            f.write(file_content)
    # 场景2:后端插件传本地路径
    else:
        # 转换为真实物理路径
        real_local_path = get_real_physical_path(local_path)
        if not os.path.exists(real_local_path) or not os.path.isfile(real_local_path):
            raise HTTPException(status_code=404, detail=f"文件不存在:拼接后的路径为{real_local_path}")
        original_name = os.path.basename(real_local_path)
        file_ext = original_name.split(".")[-1].lower()
        file_size = os.path.getsize(real_local_path)
    
    # 加载现有映射表
    upload_map = load_upload_map()
    # 检查是否已上传过，且不覆盖的话直接返回已有URL
    if real_local_path in upload_map and not override:
        return JSONResponse(content={
            "code": 200,
            "msg": "文件已存在，返回历史上传结果",
            "data": upload_map[real_local_path]
        })
    
    # 统一上传到TOS对象存储，未配置或失败直接报错，由调用方决定是否降级到本地转码
    public_url = upload_file_to_tos(real_local_path, file_type)
    if not public_url:
        raise HTTPException(status_code=500, detail="TOS对象存储未配置或上传失败，请在系统设置中配置TOS存储桶信息")
    
    # 生成返回结果
    result = {
        "local_path": real_local_path,
        "public_url": public_url,
        "file_id": uuid.uuid4().hex,
        "upload_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "original_name": original_name,
        "file_type": file_type,
        "size": file_size
    }
    # 保存到映射表
    upload_map[real_local_path] = result
    save_upload_map(upload_map)
    
    # 记录操作日志
    add_operation_log("文件上传", f"✅ 上传文件成功:{original_name}，公网URL:{public_url}")
    
    return JSONResponse(content={
        "code": 200,
        "msg": "上传成功",
        "data": result
    })

@app.get("/api/file/change/sse")
async def file_change_sse():
    """文件变动SSE推送接口，前端监听实现自动刷新"""
    import asyncio
    queue = asyncio.Queue()
    FILE_CHANGE_CONNECTIONS.add(queue)
    
    async def event_generator():
        try:
            while True:
                data = await queue.get()
                json_str = json.dumps(data, ensure_ascii=False).replace('\n', '\\n').replace('\r', '\\r')
                yield f"data: {json_str}\n\n"
        except asyncio.CancelledError:
            # 正常取消，忽略
            pass
        except Exception as e:
            # 捕获所有其他异常（如客户端断开连接），避免连接残留
            print(f"⚠️ 文件变动SSE连接异常断开，错误: {str(e)}")
        finally:
            # 无论正常还是异常，都清理连接，避免残留无效队列导致内存泄漏
            if queue in FILE_CHANGE_CONNECTIONS:
                FILE_CHANGE_CONNECTIONS.remove(queue)
    
    return EventSourceResponse(event_generator(), media_type="text/event-stream")
# ========================== 异步任务接口 ==========================
@app.post("/api/task/submit")
async def submit_task(req: TaskSubmitRequest, session_id: str = "default"):
    """提交异步任务，立刻返回task_id，不阻塞"""
    global TASK_ID_COUNTER, TASK_STORAGE
    task_id = str(TASK_ID_COUNTER)
    TASK_ID_COUNTER += 1
    # 初始化任务
    TASK_STORAGE[task_id] = {
        "task_id": task_id,
        "task_type": req.task_type,
        "status": TASK_STATUS_PENDING,
        "progress": "🔄 任务排队中...",
        "result": None,
        "create_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    # 异步执行任务
    def run_task():
        try:
            TASK_STORAGE[task_id]["status"] = TASK_STATUS_RUNNING
            if req.task_type == "chat":
                # 执行聊天任务
                TASK_STORAGE[task_id]["progress"] = "🔄 正在处理对话请求..."
                # 直接在子线程中创建新的事件循环运行chat协程，彻底解决TestClient导致的跨事件循环SSE消息丢失问题
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    chat_req = ChatRequest(
                        query=req.params.get("query", ""),
                        system_prompt=req.params.get("system_prompt", ""),
                        session_id=session_id,
                        attachments=req.params.get("attachments", [])
                    )
                    chat_result = loop.run_until_complete(chat(chat_req))
                    TASK_STORAGE[task_id]["result"] = chat_result
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_SUCCESS
                    TASK_STORAGE[task_id]["progress"] = "✅ 任务执行完成"
                except Exception as e:
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                    TASK_STORAGE[task_id]["progress"] = f"❌ 任务失败:{str(e)}"
                finally:
                    loop.close()
            elif req.task_type == "read_file":
                # 读取文件工具
                TASK_STORAGE[task_id]["progress"] = "🔄 正在读取文件..."
                file_name = req.params.get("file_name", "")
                if not file_name:
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                    TASK_STORAGE[task_id]["progress"] = "❌ 参数错误：缺少file_name参数"
                    return
                file_path = os.path.join(REPOSITORY_PATH, file_name)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    TASK_STORAGE[task_id]["result"] = {"file_name": file_name, "content": content}
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_SUCCESS
                    TASK_STORAGE[task_id]["progress"] = f"✅ 读取{file_name}成功，共{len(content)}字符"
                except FileNotFoundError:
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                    TASK_STORAGE[task_id]["progress"] = f"❌ 读取失败：文件{file_name}不存在"
                except UnicodeDecodeError:
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                    TASK_STORAGE[task_id]["progress"] = f"❌ 读取失败：文件{file_name}编码不支持，请转为UTF-8编码"
                except Exception as e:
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                    TASK_STORAGE[task_id]["progress"] = f"❌ 读取{file_name}失败：{str(e)}"
            elif req.task_type == "write_file":
                # 写入/修改文件工具
                TASK_STORAGE[task_id]["progress"] = "🔄 正在写入文件..."
                file_name = req.params.get("file_name", "")
                content = req.params.get("content", "")
                append = req.params.get("append", False)
                if not file_name or content is None:
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                    TASK_STORAGE[task_id]["progress"] = "❌ 参数错误：缺少file_name或content参数"
                    return
                file_path = os.path.join(REPOSITORY_PATH, file_name)
                try:
                    mode = "a" if append else "w"
                    with open(file_path, mode, encoding="utf-8") as f:
                        f.write(content)
                    TASK_STORAGE[task_id]["result"] = {"file_name": file_name, "write_len": len(content), "append": append}
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_SUCCESS
                    TASK_STORAGE[task_id]["progress"] = f"✅ {'追加写入' if append else '写入'} {file_name}成功，共写入{len(content)}字符"
                except PermissionError:
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                    TASK_STORAGE[task_id]["progress"] = f"❌ 写入失败：没有{file_name}的写入权限"
                except Exception as e:
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                    TASK_STORAGE[task_id]["progress"] = f"❌ 写入{file_name}失败：{str(e)}"
            elif req.task_type == "delete_file":
                # 删除文件工具
                TASK_STORAGE[task_id]["progress"] = "🔄 正在删除文件..."
                file_name = req.params.get("file_name", "")
                if not file_name:
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                    TASK_STORAGE[task_id]["progress"] = "❌ 参数错误：缺少file_name参数"
                    return
                file_path = os.path.join(REPOSITORY_PATH, file_name)
                try:
                    os.remove(file_path)
                    TASK_STORAGE[task_id]["result"] = {"file_name": file_name}
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_SUCCESS
                    TASK_STORAGE[task_id]["progress"] = f"✅ 删除{file_name}成功"
                except FileNotFoundError:
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                    TASK_STORAGE[task_id]["progress"] = f"❌ 删除失败：文件{file_name}不存在"
                except PermissionError:
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                    TASK_STORAGE[task_id]["progress"] = f"❌ 删除失败：没有{file_name}的删除权限"
                except Exception as e:
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                    TASK_STORAGE[task_id]["progress"] = f"❌ 删除{file_name}失败：{str(e)}"
            elif req.task_type == "run_command":
                # 执行终端命令工具
                TASK_STORAGE[task_id]["progress"] = "🔄 正在执行终端命令..."
                command = req.params.get("command", "")
                timeout = req.params.get("timeout", 30)
                if not command:
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                    TASK_STORAGE[task_id]["progress"] = "❌ 参数错误：缺少command参数"              
                    return
                try:
                    result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
                    output = result.stdout + result.stderr
                    TASK_STORAGE[task_id]["result"] = {"command": command, "output": output, "returncode": result.returncode}
                    if result.returncode == 0:
                        TASK_STORAGE[task_id]["status"] = TASK_STATUS_SUCCESS
                        TASK_STORAGE[task_id]["progress"] = f"✅ 命令执行成功，返回{len(output)}字符输出"
                    else:
                        TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                        TASK_STORAGE[task_id]["progress"] = f"❌ 命令执行失败，返回码：{result.returncode}，错误信息：{output[:200]}"
                except subprocess.TimeoutExpired:
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                    TASK_STORAGE[task_id]["progress"] = f"❌ 命令执行超时，超过{timeout}秒"
                except Exception as e:
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                    TASK_STORAGE[task_id]["progress"] = f"❌ 命令执行失败：{str(e)}"
            # 未知任务类型
            else:
                TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                TASK_STORAGE[task_id]["progress"] = f"❌ 不支持的任务类型：{req.task_type}"
        except Exception as e:
            TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
            TASK_STORAGE[task_id]["progress"] = f"❌ 任务执行异常：{str(e)}"
    threading.Thread(target=run_task, daemon=True).start()
    return {"code": 200, "task_id": task_id, "msg": "任务已提交"}

@app.get("/api/task/status")
async def get_task_status(task_id: str):
    """查询异步任务进度和结果"""
    global TASK_STORAGE
    if task_id not in TASK_STORAGE:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"code": 200, "data": TASK_STORAGE[task_id]}
@app.get("/train", include_in_schema=False)
async def get_train_page():
    return FileResponse(os.path.join(BASE_DIR, "train.html"))

# 同时注册/sample和/sample.html两个路径，前端「在新窗口打开」跳转sample.html?observe=1也能命中，双保险
@app.get("/sample", include_in_schema=False)
@app.get("/sample.html", include_in_schema=False)
async def get_sample_page():
    return FileResponse(os.path.join(BASE_DIR, "sample.html"))

# 修复OpenAI兼容接口逻辑（去掉不存在的chat_handler依赖）
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """兼容OpenAI标准对话接口，支持流式输出"""
    try:
        # 直接调用主服务的LLM实例处理请求
        messages = [m.dict() for m in request.messages]
        output = llm.create_chat_completion(
            messages=messages,
            temperature=request.temperature,
            top_p=request.top_p,
            stream=request.stream
        )
        return output
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========================== 内部管理接口 ==========================
# -------------------------- 文件操作接口 --------------------------
@app.get("/api/file/list")
async def get_file_list(path: str = ""):
    """获取仓库目录结构"""
    target_path = os.path.join(REPOSITORY_PATH, path)
    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="路径不存在")
    if not os.path.isdir(target_path):
        raise HTTPException(status_code=400, detail="路径不是文件夹")
    
    file_list = []
    for item in os.listdir(target_path):
        item_path = os.path.join(target_path, item)
        is_dir = os.path.isdir(item_path)
        stat = os.stat(item_path)
        file_list.append({
            "name": item,
            "path": os.path.relpath(item_path, REPOSITORY_PATH).replace("\\", "/"),
            "is_dir": is_dir,
            "size": stat.st_size if not is_dir else 0,
            "modify_time": stat.st_mtime
        })
    return {"code": 200, "data": sorted(file_list, key=lambda x: (-x["is_dir"], x["name"]))}

@app.get("/api/file/read")
async def read_file(path: str, start_line: int = None, end_line: int = None, show_line_num: bool = False):
    """读取文件内容，支持按行范围读取，show_line_num=true时返回带行号的内容（仅AI定位用）"""
    file_path = os.path.join(REPOSITORY_PATH, path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    if os.path.isdir(file_path):
        raise HTTPException(status_code=400, detail="不能读取文件夹")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        total_lines = len(lines)
        # 处理行范围参数
        if start_line is not None and end_line is not None:
            start_idx = max(0, start_line - 1)
            end_idx = min(total_lines, end_line)
            lines = lines[start_idx:end_idx]
        # 根据参数决定是否返回带行号的内容
        if show_line_num:
            # AI场景：返回带行号的内容用于定位
            content = ""
            current_line_num = start_line if start_line else 1
            for line in lines:
                content += f"[{current_line_num}] {line}"
                current_line_num += 1
        else:
            # 前端/正常场景：返回纯原始内容，无行号
            content = "".join(lines)
        return {"code": 200, "data": content, "total_lines": total_lines, "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")
@app.get("/api/file/preview")
async def preview_file(path: str):
    """文件预览接口，自动识别MIME类型，支持Range分片加载，大文件秒开"""
    # 优先查找程序根目录下的静态资源（兼容打包后_internal目录和开发环境根目录）
    program_static_path = os.path.join(BASE_DIR, path)
    if os.path.exists(program_static_path):
        file_path = program_static_path
    else:
        # 程序根目录找不到再去用户仓库目录查找
        file_path = os.path.join(REPOSITORY_PATH, path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    # 自动识别文件MIME类型
    mime_type, _ = mimetypes.guess_type(file_path)
    media_type = mime_type if mime_type else "application/octet-stream"
    # 开启Range分片支持，添加缓存头，大文件秒开
    return FileResponse(
        file_path, 
        media_type=media_type,
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600"
        }
    )
@app.get("/api/file/open_external")
async def open_file_external(path: str):
    """调用系统默认程序打开文件，无默认关联程序时自动弹出系统选择打开方式对话框"""
    import subprocess
    file_path = None
    # 1. 优先查找程序根目录下的静态资源
    program_static_path = os.path.join(BASE_DIR, path)
    if os.path.exists(program_static_path):
        file_path = program_static_path
    # 2. 其次查找仓库根目录下的文件（兼容插件生成文件场景）
    repo_root_path = os.path.join(REPOSITORY_PATH, path)
    if not file_path and os.path.exists(repo_root_path):
        file_path = repo_root_path
    # 3. 最后处理项目内相对路径场景
    if not file_path:
        file_path = get_real_physical_path(path)
    
    # 基础校验
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    if os.path.isdir(file_path):
        raise HTTPException(status_code=400, detail="不能打开文件夹，仅支持文件")
    
    # 安全校验:只读打开操作走分级拦截规则，非可执行文件自动放行
    forbidden, reason = is_path_forbidden(file_path, operation_type="read")
    if forbidden:
        add_file_operation_log("open_external", path, "fail", reason)
        raise HTTPException(status_code=403, detail=reason)
    
    try:
        system = platform.system()
        if system == "Windows":
            # Windows系统:os.startfile会自动调用默认关联程序，无关联时弹出选择打开方式对话框
            os.startfile(file_path)
        elif system == "Darwin":
            # macOS系统:调用open命令
            subprocess.run(["open", file_path], check=True, capture_output=True, timeout=5)
        else:
            # Linux系统:调用xdg-open命令
            subprocess.run(["xdg-open", file_path], check=True, capture_output=True, timeout=5)
        
        add_file_operation_log("open_external", path, "success", f"外部打开成功，路径:{file_path}")
        return {"code": 200, "msg": "已调用系统程序打开文件", "file_path": file_path}
    except subprocess.TimeoutExpired:
        err_msg = "打开文件超时，请重试"
        add_file_operation_log("open_external", path, "fail", err_msg)
        raise HTTPException(status_code=500, detail=err_msg)
    except Exception as e:
        err_msg = f"打开文件失败: {str(e)}"
        add_file_operation_log("open_external", path, "fail", err_msg)
        raise HTTPException(status_code=500, detail=err_msg)
@app.get("/docs/user_guide")
async def view_user_guide():
    """内置页面显示使用说明文档，无需外部程序打开"""
    file_path = os.path.join(DOCS_DIR, "AI_GZT_User_Guide.md")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="使用说明文档不存在")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            md_content = f.read()
        # 简单Markdown转HTML，无需第三方库
        html_content = md_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lines = html_content.split("\n")
        formatted_lines = []
        for line in lines:
            if line.startswith("# "):
                formatted_lines.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                formatted_lines.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("### "):
                formatted_lines.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith("- "):
                formatted_lines.append(f"<p style='margin-left:20px'>• {line[2:]}</p>")
            elif line.strip() == "":
                formatted_lines.append("<br>")
            else:
                formatted_lines.append(f"<p>{line}</p>")
        body_content = "\n".join(formatted_lines)
        full_html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI智能助手 - 使用说明</title>
    <style>
        body {{ font-family: "Microsoft Yahei", sans-serif; max-width: 900px; margin: 0 auto; padding: 30px; line-height: 1.6; color: #333; }}
        h1 {{ color: #409EFF; border-bottom: 2px solid #409EFF; padding-bottom: 10px; }}
        h2 {{ color: #303133; margin-top: 30px; }}
        h3 {{ color: #606266; }}
        p {{ margin: 10px 0; }}
        br {{ margin: 5px 0; }}
    </style>
</head>
<body>
{body_content}
</body>
</html>
        """
        return HTMLResponse(content=full_html, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文档失败: {str(e)}")

@app.get("/docs/third_party_licenses")
async def view_third_party_licenses():
    """内置页面显示第三方开源声明文档，无需外部程序打开"""
    file_path = os.path.join(DOCS_DIR, "THIRD_PARTY_LICENSES.md")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="第三方开源声明文档不存在")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            md_content = f.read()
        # 简单Markdown转HTML，无需第三方库
        html_content = md_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lines = html_content.split("\n")
        formatted_lines = []
        for line in lines:
            if line.startswith("# "):
                formatted_lines.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                formatted_lines.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("### "):
                formatted_lines.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith("- "):
                formatted_lines.append(f"<p style='margin-left:20px'>• {line[2:]}</p>")
            elif line.strip() == "":
                formatted_lines.append("<br>")
            else:
                formatted_lines.append(f"<p>{line}</p>")
        body_content = "\n".join(formatted_lines)
        full_html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI智能助手 - 第三方开源声明</title>
    <style>
        body {{ font-family: "Microsoft Yahei", sans-serif; max-width: 900px; margin: 0 auto; padding: 30px; line-height: 1.6; color: #333; }}
        h1 {{ color: #67C23A; border-bottom: 2px solid #67C23A; padding-bottom: 10px; }}
        h2 {{ color: #303133; margin-top: 30px; }}
        h3 {{ color: #606266; }}
        p {{ margin: 10px 0; }}
        br {{ margin: 5px 0; }}
        pre {{ background: #f5f7fa; padding: 15px; border-radius: 4px; overflow-x: auto; }}
    </style>
</head>
<body>
{body_content}
</body>
</html>
        """
        return HTMLResponse(content=full_html, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文档失败: {str(e)}")
@app.get("/api/file/hex_read")
async def read_file_hex(path: str, offset: int = 0, limit: int = 1024*16):
    """读取二进制文件的十六进制格式内容，默认读取前16KB内容，支持偏移分页"""
    file_path = os.path.join(REPOSITORY_PATH, path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    if os.path.isdir(file_path):
        raise HTTPException(status_code=400, detail="不能读取文件夹")
    
    try:
        with open(file_path, "rb") as f:
            f.seek(offset)
            content = f.read(limit)
            total_size = os.path.getsize(file_path)
            
            # 转换为十六进制视图格式
            hex_lines = []
            ascii_lines = []
            line = []
            ascii_line = []
            for i, b in enumerate(content):
                line.append(f"{b:02x}")
                # 转换为可显示的ASCII字符，不可见字符用.代替
                ascii_line.append(chr(b) if 32 <= b <= 126 else '.')
                if (i + 1) % 16 == 0:
                    hex_lines.append(" ".join(line))
                    ascii_lines.append("".join(ascii_line))
                    line = []
                    ascii_line = []
            if line:
                # 补全最后一行空格对齐
                hex_lines.append(" ".join(line).ljust(16*3 -1))
                ascii_lines.append("".join(ascii_line))
            
            return {
                "code": 200,
                "data": {
                    "hex_lines": hex_lines,
                    "ascii_lines": ascii_lines,
                    "offset": offset,
                    "total_size": total_size,
                    "read_size": len(content)
                }
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取二进制文件失败: {str(e)}")

class FileWriteRequest(BaseModel):
    path: str
    content: str

@app.post("/api/file/write")
async def write_file(request: FileWriteRequest):
    """写入文件内容"""
    file_path = os.path.join(REPOSITORY_PATH, request.path)
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(request.content)
        # 异步更新RAG索引
        import asyncio
        asyncio.create_task(asyncio.to_thread(rag_manager.add_file, file_path))
        
        # 新增：自动触发项目手册同步逻辑，异步执行不阻塞主线程
        async def auto_sync_manual():
            try:
                # 仅处理代码文件：自动同步所属项目的手册明细（正向绑定保留）
                if "项目手册.md" not in request.path:
                    # 向上递归查找最近的项目手册（直到仓库根目录）
                    current_dir = os.path.dirname(file_path)
                    manual_path = ""
                    while current_dir.startswith(REPOSITORY_PATH):
                        manual_files = [f for f in os.listdir(current_dir) if f.endswith("项目手册.md")]
                        if manual_files:
                            # 计算相对仓库的路径
                            rel_manual_dir = os.path.relpath(current_dir, REPOSITORY_PATH)
                            manual_path = os.path.join(rel_manual_dir, manual_files[0]).replace("\\", "/")
                            break
                        # 向上一级
                        parent_dir = os.path.dirname(current_dir)
                        if parent_dir == current_dir: # 到达根目录停止
                            break
                        current_dir = parent_dir
                    if manual_path:
                        project_manual_manager.update_manual_detail_table(manual_path)
            except Exception as e:
                # 同步异常直接忽略，不影响主流程
                print(f"自动同步手册异常：{str(e)}")
                pass
        asyncio.create_task(auto_sync_manual())
        # 自动更新当前项目文件清单缓存
        update_current_project_file_list()
        add_operation_log("文件操作", f"写入文件：{request.path}")
        # 主动触发文件变动广播
        broadcast_file_change()
        return {"code": 200, "msg": "写入成功", "path": request.path}
    except Exception as e:
        add_operation_log("文件操作", f"写入文件失败：{request.path}，错误：{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"写入文件失败: {str(e)}")

class FileCreateRequest(BaseModel):
    path: str
    is_dir: bool = False
    content: Optional[str] = "" # 新增content字段，可选，默认空

@app.post("/api/file/create")
async def create_file(request: FileCreateRequest):
    """新建文件或文件夹"""
    target_path = os.path.join(REPOSITORY_PATH, request.path)
    if os.path.exists(target_path):
        raise HTTPException(status_code=400, detail="路径已存在")
    
    try:
        if request.is_dir:
            os.makedirs(target_path, exist_ok=True)
            add_operation_log("文件操作", f"创建文件夹：{request.path}")
        else:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            # 写入传入的内容，空则创建空文件
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(request.content)
            if request.content:
                add_operation_log("文件操作", f"创建+写入文件成功：{request.path}，共写入{len(request.content)}字符")
            else:
                add_operation_log("文件操作", f"创建空文件成功：{request.path}")
        # 自动触发项目手册同步逻辑，异步执行不阻塞主线程
        import asyncio
        async def auto_sync_manual():
            try:
                # 向上递归查找最近的项目手册
                current_dir = os.path.dirname(target_path)
                manual_path = ""
                while current_dir.startswith(REPOSITORY_PATH):
                    manual_files = [f for f in os.listdir(current_dir) if f.endswith("项目手册.md")]
                    if manual_files:
                        rel_manual_dir = os.path.relpath(current_dir, REPOSITORY_PATH)
                        manual_path = os.path.join(rel_manual_dir, manual_files[0]).replace("\\", "/")
                        break
                    parent_dir = os.path.dirname(current_dir)
                    if parent_dir == current_dir:
                        break
                    current_dir = parent_dir
                if manual_path:
                    project_manual_manager.update_manual_detail_table(manual_path)
            except Exception as e:
                print(f"自动同步手册异常：{str(e)}")
                pass
        asyncio.create_task(auto_sync_manual())
        # 自动更新当前项目文件清单缓存
        update_current_project_file_list()
        # 主动触发文件变动广播
        broadcast_file_change()
        return {"code": 200, "msg": "创建成功"}
    except Exception as e:
        add_operation_log("文件操作", f"创建失败：{request.path}，错误：{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")

class FileDeleteRequest(BaseModel):
    path: str

@app.post("/api/file/delete")
async def delete_file(request: FileDeleteRequest):
    """删除文件或文件夹"""
    target_path = os.path.join(REPOSITORY_PATH, request.path)
    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="路径不存在")
    
    try:
        if os.path.isdir(target_path):
            import shutil
            shutil.rmtree(target_path)
        else:
            os.remove(target_path)
        # 异步更新RAG索引
        import asyncio
        asyncio.create_task(asyncio.to_thread(rag_manager.delete_file, target_path))
        add_operation_log("文件操作", f"删除文件/文件夹：{request.path}")
        # 自动触发项目手册同步逻辑，异步执行不阻塞主线程
        async def auto_sync_manual():
            try:
                # 向上递归查找最近的项目手册
                current_dir = os.path.dirname(target_path)
                manual_path = ""
                while current_dir.startswith(REPOSITORY_PATH):
                    manual_files = [f for f in os.listdir(current_dir) if f.endswith("项目手册.md")]
                    if manual_files:
                        rel_manual_dir = os.path.relpath(current_dir, REPOSITORY_PATH)
                        manual_path = os.path.join(rel_manual_dir, manual_files[0]).replace("\\", "/")
                        break
                    parent_dir = os.path.dirname(current_dir)
                    if parent_dir == current_dir:
                        break
                    current_dir = parent_dir
                if manual_path:
                    project_manual_manager.update_manual_detail_table(manual_path)
            except Exception as e:
                print(f"自动同步手册异常：{str(e)}")
                pass
        asyncio.create_task(auto_sync_manual())
        # 自动更新当前项目文件清单缓存
        update_current_project_file_list()
        # 主动触发文件变动广播
        broadcast_file_change()
        return {"code": 200, "msg": "删除成功"}
    except Exception as e:
        add_operation_log("文件操作", f"删除失败：{request.path}，错误：{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

class FileRenameRequest(BaseModel):
    old_path: str
    new_name: str

@app.post("/api/file/rename")
async def rename_file(request: FileRenameRequest):
    """重命名文件或文件夹"""
    old_path = os.path.join(REPOSITORY_PATH, request.old_path)
    new_path = os.path.join(os.path.dirname(old_path), request.new_name)
    
    if not os.path.exists(old_path):
        raise HTTPException(status_code=404, detail="原路径不存在")
    if os.path.exists(new_path):
        raise HTTPException(status_code=400, detail="新路径已存在")
    
    try:
        os.rename(old_path, new_path)
        # 异步更新RAG索引
        import asyncio
        asyncio.create_task(asyncio.to_thread(rag_manager.delete_file, old_path))
        asyncio.create_task(asyncio.to_thread(rag_manager.add_file, new_path))
        add_operation_log("文件操作", f"重命名：{request.old_path} → {request.new_name}")
        # 自动触发项目手册同步逻辑，异步执行不阻塞主线程
        async def auto_sync_manual():
            try:
                # 向上递归查找最近的项目手册
                current_dir = os.path.dirname(new_path)
                manual_path = ""
                while current_dir.startswith(REPOSITORY_PATH):
                    manual_files = [f for f in os.listdir(current_dir) if f.endswith("项目手册.md")]
                    if manual_files:
                        rel_manual_dir = os.path.relpath(current_dir, REPOSITORY_PATH)
                        manual_path = os.path.join(rel_manual_dir, manual_files[0]).replace("\\", "/")
                        break
                    parent_dir = os.path.dirname(current_dir)
                    if parent_dir == current_dir:
                        break
                    current_dir = parent_dir
                if manual_path:
                    project_manual_manager.update_manual_detail_table(manual_path)
            except Exception as e:
                print(f"自动同步手册异常：{str(e)}")
                pass
        asyncio.create_task(auto_sync_manual())
        # 自动更新当前项目文件清单缓存
        update_current_project_file_list()
        # 主动触发文件变动广播
        broadcast_file_change()
        return {"code": 200, "msg": "重命名成功"}
    except Exception as e:
        add_operation_log("文件操作", f"重命名失败：{request.old_path} → {request.new_name}，错误：{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"重命名失败: {str(e)}")
# -------------------------- 智能内容编辑接口 --------------------------
class FileEditRequest(BaseModel):
    path: str
    operation: str # delete/insert_before/insert_after/replace/insert_start/insert_end
    target_block: Optional[str] = None # insert_start/insert_end不需要传
    content: Optional[str] = None

@app.post("/api/file/edit")
async def edit_file(request: FileEditRequest):
    """智能编辑文件，纯内容锚点定位，无需行号，内置自动备份/回滚/重试机制"""
    # 安全校验：优先当前项目
    if CURRENT_PROJECT["project_root"]:
        op_path = os.path.join(CURRENT_PROJECT["project_root"], request.path)
        # 新增文件自动加入清单
        if request.path not in CURRENT_PROJECT["file_list"] and os.path.exists(op_path):
            CURRENT_PROJECT["file_list"].append(request.path)
            update_current_project_file_list()
    else:
        # 无选中项目时默认编辑仓库根目录下的文件
        op_path = os.path.join(REPOSITORY_PATH, request.path)
    # 调用智能编辑引擎
    success, msg = intelligent_file_editor.edit_file(
        file_path=op_path,
        operation=request.operation,
        target_block=request.target_block,
        content=request.content
    )
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    # 异步更新RAG和项目手册
    import asyncio
    if CURRENT_PROJECT["project_root"]:
        op_path = os.path.join(CURRENT_PROJECT["project_root"], request.path)
    else:
        op_path = os.path.join(REPOSITORY_PATH, request.path)
    asyncio.create_task(asyncio.to_thread(rag_manager.add_file, op_path))
    add_operation_log("文件操作", f"{request.operation}操作：{request.path}")

# -------------------------- 配置操作接口 --------------------------
@app.get("/api/config/get")
async def get_config():
    """获取所有系统配置"""
    return {"code": 200, "data": load_config()}
# -------------------------- 本地模型管理接口（预留占位，功能升级中） --------------------------
# 原有本地模型接口已临时移除，后续升级后统一对接新的本地模型服务
# 配置字段兼容保留，不影响原有配置读取
    

# 3. 模型状态查询接口（前端按钮联动用）
@app.get("/api/local_models/status")
async def get_model_status():
    is_loaded = getattr(llm, 'is_loaded', False)
    current_model = getattr(llm, 'current_model_name', "")
    vram_usage = getattr(llm, 'vram_usage', "0MB")
    return {
        "code": 200,
        "data": {
            "is_loaded": is_loaded,
            "current_model": current_model,
            "vram_usage": vram_usage
        }
    }

class ConfigSetRequest(BaseModel):
    config: Dict[str, Any]

@app.post("/api/config/set")
async def set_config(request: ConfigSetRequest):
    """修改系统配置，download_path修改时实时同步到内置浏览器"""
    try:
        old_config = load_config()
        # 检查是否修改了下载路径
        new_download_path = request.config.get("download_path", "")
        old_download_path = old_config.get("download_path", "")
        old_config.update(request.config)
        save_config(old_config)
        
        # 如果下载路径发生变化，实时通知浏览器更新，无需重启立即生效
        if new_download_path and new_download_path != old_download_path and os.path.exists(new_download_path):
            try:
                import main
                if main.browser_window:
                    # 通过QMetaObject.invokeMethod投递到UI主线程执行，避免跨线程操作Qt对象
                    from PySide6.QtCore import QMetaObject, Qt, Q_ARG
                    QMetaObject.invokeMethod(
                        main.browser_window,
                        "update_download_path",
                        Qt.QueuedConnection,
                        Q_ARG(str, new_download_path)
                    )
                    add_operation_log("配置修改", f"下载路径已实时同步到浏览器: {new_download_path}")
            except Exception as e:
                print(f"⚠️ 同步下载路径到浏览器失败: {str(e)}")
                add_operation_log("配置修改", f"下载路径配置已保存，但同步到浏览器失败: {str(e)}", "warning")
        
        add_operation_log("配置修改", "更新系统配置")
        return {"code": 200, "msg": "配置修改成功，即时生效"}
    except Exception as e:
        add_operation_log("配置修改", f"配置修改失败，错误:{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"配置修改失败: {str(e)}")
class RepositoryPathSetRequest(BaseModel):
    new_path: str
    migrate_files: bool = False # 是否迁移原有仓库文件到新路径

@app.post("/api/config/repository/set")
async def set_repository_path(req: RepositoryPathSetRequest):
    """设置仓库存储路径，支持可选迁移原有文件"""
    global REPOSITORY_PATH
    try:
        new_path = os.path.normpath(req.new_path).replace("\\", "/")
        old_path = REPOSITORY_PATH
        # 校验新路径合法性:不能在禁止目录下
        forbidden, reason = is_path_forbidden(new_path)
        if forbidden:
            return {"code": 400, "msg": f"新仓库路径不合法:{reason}"}
        # 校验新路径不是程序自身目录
        if new_path.startswith(os.path.normpath(BASE_DIR).replace("\\", "/") + "/") or new_path == os.path.normpath(BASE_DIR).replace("\\", "/"):
            return {"code": 400, "msg": "仓库路径不能设置在AI程序自身目录下，请选择其他目录"}
        # 如果需要迁移文件且旧路径存在
        if req.migrate_files and os.path.exists(old_path) and old_path != new_path:
            import shutil
            # 自动创建新目录
            os.makedirs(new_path, exist_ok=True)
            # 复制所有文件到新路径
            for item in os.listdir(old_path):
                s = os.path.join(old_path, item)
                d = os.path.join(new_path, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
            add_operation_log("仓库配置", f"✅ 仓库路径从{old_path}迁移到{new_path}，所有文件已复制完成")
        # 更新配置
        config = load_config()
        config["repository_path"] = new_path
        save_config(config)
        # 重新初始化白名单（新仓库路径自动加入白名单）
        init_whitelist_paths()
        # 重新构建RAG索引（异步执行）
        import asyncio
        asyncio.create_task(asyncio.to_thread(rag_manager.build_full_index))
        add_operation_log("仓库配置", f"✅ 仓库路径已更新为:{new_path}")
        broadcast_file_change()
        return {"code": 200, "msg": f"仓库路径设置成功，当前路径:{new_path}", "data": {"repository_path": new_path}}
    except Exception as e:
        add_operation_log("仓库配置", f"❌ 设置仓库路径失败:{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"设置仓库路径失败: {str(e)}")

class ForbiddenPathAddRequest(BaseModel):
    path: str

@app.post("/api/config/forbidden/add")
async def add_forbidden_path(req: ForbiddenPathAddRequest):
    """添加禁止操作路径"""
    try:
        add_path = os.path.normpath(req.path).replace("\\", "/")
        # 校验路径不能是白名单内路径
        for allowed in GLOBAL_WHITELIST_PATHS:
            if add_path == allowed or add_path.startswith(allowed + "/"):
                return {"code": 400, "msg": f"路径【{add_path}】属于系统核心运行路径，禁止加入禁止列表"}
        config = load_config()
        forbidden_list = config.get("forbidden_paths", [])
        # 去重
        norm_list = [os.path.normpath(p).replace("\\", "/") for p in forbidden_list]
        if add_path in norm_list:
            return {"code": 400, "msg": "该路径已在禁止列表中"}
        forbidden_list.append(add_path)
        config["forbidden_paths"] = forbidden_list
        save_config(config)
        add_operation_log("安全配置", f"✅ 添加禁止路径：{add_path}")
        return {"code": 200, "msg": "禁止路径添加成功", "data": {"forbidden_paths": forbidden_list}}
    except Exception as e:
        add_operation_log("安全配置", f"❌ 添加禁止路径失败：{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"添加禁止路径失败: {str(e)}")

class ForbiddenPathDeleteRequest(BaseModel):
    path: str

@app.post("/api/config/forbidden/delete")
async def delete_forbidden_path(req: ForbiddenPathDeleteRequest):
    """删除禁止操作路径"""
    try:
        del_path = os.path.normpath(req.path).replace("\\", "/")
        config = load_config()
        forbidden_list = config.get("forbidden_paths", [])
        # 标准化后匹配删除
        new_list = []
        for p in forbidden_list:
            if os.path.normpath(p).replace("\\", "/") != del_path:
                new_list.append(p)
        if len(new_list) == len(forbidden_list):
            return {"code": 400, "msg": "该路径不在禁止列表中"}
        config["forbidden_paths"] = new_list
        save_config(config)
        add_operation_log("安全配置", f"✅ 删除禁止路径：{del_path}")
        return {"code": 200, "msg": "禁止路径删除成功", "data": {"forbidden_paths": new_list}}
    except Exception as e:
        add_operation_log("安全配置", f"❌ 删除禁止路径失败：{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"删除禁止路径失败: {str(e)}")

# -------------------------- 功能操作接口 --------------------------
@app.get("/api/download/list")
async def get_download_list():
    """获取下载任务列表"""
    from main import download_manager
    return {"code": 200, "data": download_manager.get_task_list()}

class DownloadStartRequest(BaseModel):
    url: str
    save_path: Optional[str] = None

@app.post("/api/download/start")
async def start_download(request: DownloadStartRequest):
    """触发下载任务"""
    from main import download_manager
    try:
        task_id = download_manager.add_task(request.url, request.save_path)
        return {"code": 200, "msg": "下载任务已启动", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动下载失败: {str(e)}")

class DownloadCancelRequest(BaseModel):
    task_id: str

@app.post("/api/download/cancel")
async def cancel_download(request: DownloadCancelRequest):
    """取消指定下载任务"""
    from main import download_manager
    success = download_manager.cancel_task(request.task_id)
    if success:
        return {"code": 200, "msg": "下载任务已取消"}
    raise HTTPException(status_code=404, detail="任务不存在")

class BrowserOpenRequest(BaseModel):
    url: str = "https://www.bing.com"
# -------------------------- 记忆接口 --------------------------
# 记忆配置读写接口
class MemoryConfigUpdateRequest(BaseModel):
    config: Dict[str, Any]
@app.get("/api/memory/env_check")
async def check_vector_env():
    """检测向量检索环境状态，前端设置页根据此结果展示完整模式/降级模式"""
    result = {
        "python_version": f"{_sys.version_info.major}.{_sys.version_info.minor}",
        "python_matched": True,  # 打包后固定为True，开发环境也是True
        "torch_installed": False,
        "sentence_transformers_installed": False,
        "transformers_installed": False,
        "current_mode": "degraded" if memory_cache.encoder is None else "full"
    }
    
    # 开发环境直接读取当前进程的导入状态
    if not getattr(_sys, 'frozen', False):
        try:
            import torch
            result["torch_installed"] = True
        except ImportError:
            pass
        try:
            import sentence_transformers
            result["sentence_transformers_installed"] = True
        except ImportError:
            pass
        try:
            import transformers
            result["transformers_installed"] = True
        except ImportError:
            pass
    else:
        # 打包环境直接检测当前进程内已导入的模块状态（所有依赖已被PyInstaller内置，无需调用外部Python）
        try:
            import torch
            result["torch_installed"] = True
        except ImportError:
            pass
        try:
            import sentence_transformers
            result["sentence_transformers_installed"] = True
        except ImportError:
            pass
        try:
            import transformers
            result["transformers_installed"] = True
        except ImportError:
            pass
    
    return {"code": 200, "data": result}

@app.get("/api/memory/config")
async def get_memory_config():
    """获取记忆系统所有配置参数"""
    return {"code": 200, "data": memory_cache.config}

@app.post("/api/memory/config/update")
async def update_memory_config(req: MemoryConfigUpdateRequest):
    """更新记忆系统配置，实时生效"""
    memory_cache.update_config(req.config)
    add_operation_log("配置修改", "更新记忆系统参数")
    return {"code": 200, "msg": "记忆配置修改成功，即时生效"}

# 读取记忆列表接口
# 记忆库清空请求模型
class MemoryLibraryClearRequest(BaseModel):
    library_id: str

@app.get("/api/memory/library/list")
async def memory_library_list():
    """获取所有记忆库列表（全局主库+各项目独立库）"""
    try:
        # 兼容路径:同时查找_internal目录和exe同级目录，优先使用存在的记忆文件
        if getattr(_sys, 'frozen', False):
            # 打包环境:优先_internal（BASE_DIR），找不到再用exe同级目录
            candidate_paths = [
                os.path.join(BASE_DIR, "memory_meta.json"),
                os.path.join(_exe_dir, "memory_meta.json")
            ]
            memory_meta_path = next((p for p in candidate_paths if os.path.exists(p)), candidate_paths[0])
        else:
            # 开发环境使用原有路径
            memory_meta_path = os.path.join(BASE_DIR, "memory_meta.json")
        # 记忆文件不存在时默认返回空列表，兼容首次启动场景
        if not os.path.exists(memory_meta_path):
            library_list = [{
                "library_id": "default",
                "library_name": "全局记忆库",
                "memory_count": 0,
                "is_main": False
            }]
            add_operation_log("记忆管理", "查询记忆库列表成功（记忆文件不存在，返回默认空库）")
            return {"code": 200, "data": library_list}
        with open(memory_meta_path, "r", encoding="utf-8") as f:
            memory_data = json.load(f)
        # 初始化统计：默认全局记忆库
        library_stats = {
            "default": {
                "library_id": "default",
                "library_name": "全局记忆库",
                "memory_count": 0,
                "is_main": False
            }
        }
        # 遍历所有记忆统计
        for mid, item in memory_data.items():
            tags = item.get("tags", [])
            project_tag = None
            for tag in tags:
                if tag.startswith("project:"):
                    project_tag = tag.split(":", 1)[1]
                    break
            if not project_tag or project_tag == "default":
                # 全局记忆
                library_stats["default"]["memory_count"] += 1
            else:
                # 项目记忆
                if project_tag not in library_stats:
                    library_stats[project_tag] = {
                        "library_id": project_tag,
                        "library_name": f"{project_tag}项目记忆库",
                        "memory_count": 0,
                        "is_main": False
                    }
                library_stats[project_tag]["memory_count"] += 1
        # 转换为列表，主库排在最前面
        library_list = sorted(library_stats.values(), key=lambda x: (not x["is_main"], x["library_name"]))
        add_operation_log("记忆管理", "查询记忆库列表成功")
        return {"code": 200, "data": library_list}
    except Exception as e:
        add_operation_log("记忆管理", f"查询记忆库列表失败：{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"查询记忆库列表失败：{str(e)}")

@app.post("/api/memory/library/clear")
async def memory_library_clear(req: MemoryLibraryClearRequest):
    """清空指定记忆库，同步清理向量索引、对话历史缓存"""
    try:
        library_id = req.library_id.strip()
        if not library_id:
            return {"code": 400, "msg": "记忆库ID不能为空"}
        # 调用memory_cache的清空方法
        deleted_count = memory_cache.clear_project_memory(library_id)
        # 同步清理对应项目的对话历史缓存文件
        safe_project_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5_-]', "_", library_id)
        project_history_file = os.path.join(BASE_DIR, f"latest_chat_history_{safe_project_name}.json")
        if library_id == "default":
            # 全局库还要兼容旧的全局历史文件
            default_history_file = os.path.join(BASE_DIR, "latest_chat_history.json")
            for hist_file in [project_history_file, default_history_file]:
                if os.path.exists(hist_file):
                    with open(hist_file, "w", encoding="utf-8") as f:
                        json.dump([], f, ensure_ascii=False, indent=2)
        else:
            if os.path.exists(project_history_file):
                with open(project_history_file, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
        # 清理内存中该项目的会话缓存
        if library_id in session_context:
            del session_context[library_id]
        # 记录操作日志
        library_name = "全局记忆库" if library_id == "default" else f"{library_id}项目记忆库"
        add_operation_log("记忆管理", f"✅ 清空记忆库【{library_name}】成功，共删除{deleted_count}条记忆")
        return {"code": 200, "msg": f"记忆库清空成功，共删除{deleted_count}条记忆", "deleted_count": deleted_count}
    except Exception as e:
        add_operation_log("记忆管理", f"清空记忆库失败：{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"清空记忆库失败：{str(e)}")
# 记忆文件清空请求模型
class MemoryFileClearRequest(BaseModel):
    file_name: str

@app.get("/api/memory/file/list")
async def memory_file_list():
    """获取所有记忆相关文件列表（系统文件+项目对话历史文件）"""
    try:
        file_list = []
        # 遍历项目根目录下的所有文件
        for filename in os.listdir(BASE_DIR):
            file_path = os.path.join(BASE_DIR, filename)
            if not os.path.isfile(file_path):
                continue
            # 筛选记忆相关文件
            is_system = False
            file_type = ""
            file_desc = ""
            # 1. 记忆库元数据文件（系统核心文件，禁止清理）
            if filename == "memory_meta.json":
                is_system = True
                file_type = "meta"
                file_desc = "记忆库元数据文件"
            # 2. 对话历史文件
            elif filename.startswith("latest_chat_history_") and filename.endswith(".json"):
                # 提取项目名
                project_part = filename[len("latest_chat_history_"):-len(".json")]
                if project_part == "default":
                    is_system = False
                    file_type = "global_history"
                    file_desc = "全局对话历史缓存"
                else:
                    is_system = False
                    file_type = "project_history"
                    file_desc = f"{project_part}项目对话历史缓存"
            else:
                # 非记忆相关文件跳过
                continue
            # 获取文件信息
            stat = os.stat(file_path)
            file_size = stat.st_size
            # 格式化文件大小
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024*1024:
                size_str = f"{file_size/1024:.1f} KB"
            else:
                size_str = f"{file_size/(1024*1024):.1f} MB"
            # 格式化修改时间
            modify_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
            file_list.append({
                "file_name": filename,
                "file_desc": file_desc,
                "file_size": size_str,
                "modify_time": modify_time,
                "is_system": is_system,
                "file_type": file_type
            })
        # 排序：系统文件在前，然后按修改时间倒序
        file_list.sort(key=lambda x: (not x["is_system"], x["modify_time"]), reverse=True)
        add_operation_log("记忆管理", "查询记忆文件列表成功")
        return {"code": 200, "data": file_list}
    except Exception as e:
        add_operation_log("记忆管理", f"查询记忆文件列表失败：{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"查询记忆文件列表失败：{str(e)}")

@app.post("/api/memory/file/clear")
async def memory_file_clear(req: MemoryFileClearRequest):
    """清空指定项目记忆文件（对话历史缓存），仅允许清理项目级历史文件，禁止清理系统文件/记忆库文件"""
    try:
        file_name = req.file_name.strip()
        # 安全校验1：文件名不能包含路径分隔符，防止路径穿越
        if "/" in file_name or "\\" in file_name:
            return {"code": 400, "msg": "非法文件名，禁止路径穿越"}
        # 安全校验2:仅允许清理对话历史缓存文件（包含全局default历史+各项目历史），禁止清理memory_meta.json等系统核心文件
        if not re.match(r'^latest_chat_history_([a-zA-Z0-9\u4e00-\u9fa5_-]+)\.json$', file_name):
            return {"code": 403, "msg": "仅允许清理对话历史缓存文件，系统文件/记忆库元数据文件禁止清理"}
        file_path = os.path.join(BASE_DIR, file_name)
        # 安全校验3：校验文件确实在BASE_DIR目录下，防止路径穿越
        if os.path.commonpath([os.path.abspath(file_path), BASE_DIR]) != BASE_DIR:
            return {"code": 403, "msg": "非法文件路径，禁止操作"}
        # 安全校验4：文件必须存在
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return {"code": 404, "msg": "文件不存在"}
        # 执行清空：写入空数组，不删除文件，仅清空内容，完全不影响记忆库
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        # 提取项目名记录日志
        project_name = file_name[len("latest_chat_history_"):-len(".json")]
        add_operation_log("记忆管理", f"✅ 清空项目记忆文件【{project_name}】对话历史缓存成功，记忆库内容不受影响")
        return {"code": 200, "msg": f"已清空【{project_name}】项目的对话历史缓存，记忆库内容未受任何影响"}
    except Exception as e:
        add_operation_log("记忆管理", f"清空记忆文件失败：{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"清空记忆文件失败：{str(e)}")
@app.get("/api/memory/list")
async def memory_list(page: int = 1, page_size: int = 20, keyword: str = "", only_not_synced: bool = False):
    # 兼容路径:同时查找_internal目录和exe同级目录，优先使用存在的记忆文件
    if getattr(_sys, 'frozen', False):
        candidate_paths = [
            os.path.join(BASE_DIR, "memory_meta.json"),
            os.path.join(_exe_dir, "memory_meta.json")
        ]
        memory_meta_path = next((p for p in candidate_paths if os.path.exists(p)), candidate_paths[0])
    else:
        memory_meta_path = os.path.join(BASE_DIR, "memory_meta.json")
    with open(memory_meta_path, "r", encoding="utf-8") as f:
        memory_data = json.load(f)
    memory_list = []
    for mid, item in memory_data.items():
        if only_not_synced and item.get("synced_to_lora", False):
            continue
        if keyword and keyword not in item["content"]:
            continue
        content_parts = item["content"].split("\n回答:", 1)
        query = content_parts[0].replace("用户问:", "") if len(content_parts) >=1 else ""
        response = content_parts[1].replace("回答:", "") if len(content_parts) >=2 else ""
        memory_list.append({
            "id": int(mid),
            "query": query,
            "response": response,
            "call_count": item.get("call_count", 0),
            "synced_to_lora": item.get("synced_to_lora", False),
            "create_time": item.get("create_time", time.strftime("%Y-%m-%d %H:%M")),
            "timestamp": item.get("timestamp", 0)
        })
    # 按创建时间戳倒序排列，最新记忆始终排在最前面
    # 兼容存量无timestamp的记忆条目，默认取0避免KeyError
    memory_list.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    total = len(memory_list)
    start = (page-1)*page_size
    end = start + page_size
    page_memories = memory_list[start:end]
    return {"memories": page_memories, "total": total, "page": page, "page_size": page_size}

# -------------------------- 样本/训练/记忆接口（兼容原有业务） --------------------------
    page_memories = memory_list[start:end]
    return {"memories": page_memories, "total": total, "page": page, "page_size": page_size}

# ========== 召回实时观测台接口（只读旁路 + 人工两档标注） ==========
@app.get("/api/memory/recall/recent")
async def recall_recent(limit: int = 50):
    """拉取最近N次提问的召回快照（倒序最新在前），并合并已有人工标注，供观测台初始化"""
    evaluations = _load_recall_evaluations()
    snapshots = list(RECALL_LOG)[-limit:][::-1]
    result = []
    for snap in snapshots:
        item = dict(snap)
        item["evaluations"] = evaluations.get(snap["id"], {})
        result.append(item)
    return {"snapshots": result, "total": len(RECALL_LOG)}

@app.get("/api/memory/recall/stream")
async def recall_stream():
    """召回观测台独立广播SSE:订阅池模式支持多页面同时连接，与对话SSE_CONNECTIONS完全隔离互不影响"""
    global global_event_loop
    import asyncio
    global_event_loop = asyncio.get_running_loop()
    queue = asyncio.Queue(maxsize=100)
    RECALL_SUBSCRIBERS.add(queue)

    async def event_generator():
        try:
            # 连上立即推connected事件，前端据此点亮实时状态灯
            connected = json.dumps({"type": "connected", "time": time.strftime("%H:%M:%S")}, ensure_ascii=False)
            yield f"data: {connected}\n\n"
            while True:
                get_task = asyncio.create_task(queue.get())
                done, pending = await asyncio.wait(
                    [get_task], timeout=30, return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                if done:
                    snapshot = done.pop().result()
                    payload = json.dumps({"type": "recall_snapshot", "snapshot": snapshot}, ensure_ascii=False)
                    payload = payload.replace('\n', '\\n').replace('\r', '\\r')
                    yield f"data: {payload}\n\n"
                else:
                    heartbeat = json.dumps({"type": "heartbeat"}).replace('\n', '\\n').replace('\r', '\\r')
                    yield f"data: {heartbeat}\n\n"
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"⚠️ 召回观测SSE连接异常断开: {str(e)}")
        finally:
            RECALL_SUBSCRIBERS.discard(queue)

    return EventSourceResponse(event_generator(), media_type="text/event-stream")

# -------------------------- 样本/训练/记忆接口（兼容原有业务） --------------------------
    return EventSourceResponse(event_generator(), media_type="text/event-stream")

class RecallEvalRequest(BaseModel):
    snapshot_id: str
    memory_id: str
    label: int  # 1=👍相关 0=👎不相关，两档单选；重复提交同档视为取消标注

@app.post("/api/memory/recall/evaluate")
async def recall_evaluate(req: RecallEvalRequest):
    """保存人工两档标注（👍相关/👎不相关），按快照ID+记忆ID定位，持久化到recall_evaluations.json"""
    if req.label not in (0, 1):
        return {"success": False, "error": "label仅支持1(相关)或0(不相关)"}
    # 校验快照仍在缓冲窗口内，避免给已过期快照写标注
    if not any(s["id"] == req.snapshot_id for s in RECALL_LOG):
        return {"success": False, "error": "该观测记录已超出最近50条缓冲窗口，请重新观测后标注"}
    with RECALL_EVAL_LOCK:
        data = _load_recall_evaluations()
        snap_evals = data.setdefault(req.snapshot_id, {})
        key = str(req.memory_id)
        # 已存在相同标注则取消（toggle），否则覆盖为新档位
        if key in snap_evals and snap_evals[key].get("label") == req.label:
            snap_evals.pop(key, None)
            action = "cancelled"
        else:
            snap_evals[key] = {"label": req.label, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
            action = "saved"
        if not snap_evals:
            data.pop(req.snapshot_id, None)
        _save_recall_evaluations(data)
    return {"success": True, "action": action}

@app.get("/api/memory/recall/stats")
async def recall_stats():
    """返回观测台量化指标:观测提问数、召回触发率、已标注条数、人工标注命中率（👍占比）"""
    total = len(RECALL_LOG)
    triggered = sum(1 for s in RECALL_LOG if s.get("triggered"))
    evaluations = _load_recall_evaluations()
    relevant = 0
    irrelevant = 0
    for snap_evals in evaluations.values():
        for ev in snap_evals.values():
            if ev.get("label") == 1:
                relevant += 1
            elif ev.get("label") == 0:
                irrelevant += 1
    evaluated = relevant + irrelevant
    return {
        "total_observations": total,
        "triggered_count": triggered,
        "trigger_rate": round(triggered / total * 100, 1) if total else 0.0,
        "evaluated_count": evaluated,
        "relevant_count": relevant,
        "irrelevant_count": irrelevant,
        "hit_rate": round(relevant / evaluated * 100, 1) if evaluated else None
    }

@app.delete("/api/memory/recall/clear")
async def recall_clear():
    """清空观测台时间线环形缓冲（不删除已持久化的人工标注）"""
    RECALL_LOG.clear()
    return {"success": True}

# -------------------------- 样本/训练/记忆接口（兼容原有业务） --------------------------

# -------------------------- 训练样本生成API --------------------------

# -------------------------- RAG -------------------------

# 全局RAG构建状态变量
RAG_BUILD_STATUS = "idle"
RAG_BUILD_RESULT = {}

@app.get("/api/rag/build")
async def build_rag_index():
    """全量构建项目代码RAG索引"""
    global RAG_BUILD_STATUS, RAG_BUILD_RESULT
    if RAG_BUILD_STATUS == "running":
        return {"code": 400, "msg": "❌ RAG索引构建已经在运行中，请稍后再试"}
    RAG_BUILD_STATUS = "running"
    RAG_BUILD_RESULT = {}
    
    # 异步执行构建
    def run_build():
        global RAG_BUILD_STATUS, RAG_BUILD_RESULT
        try:
            result = rag_manager.build_full_index()
            RAG_BUILD_RESULT = result
            RAG_BUILD_STATUS = "success"
        except Exception as e:
            RAG_BUILD_RESULT = {"error": str(e)}
            RAG_BUILD_STATUS = "error"
    
    import threading
    threading.Thread(target=run_build, daemon=True).start()
    return {"code": 200, "msg": "✅ 全量RAG索引构建已启动，后台异步执行，不会阻塞服务"}
@app.get("/api/rag/build/status")
async def get_rag_build_status():
    """获取RAG索引构建状态"""
    global RAG_BUILD_STATUS, RAG_BUILD_RESULT
    return {
        "code": 200,
        "status": RAG_BUILD_STATUS,
        "result": RAG_BUILD_RESULT
    }
@app.get("/api/repo/backup")
async def repo_backup():
    """全库备份接口（预留实现）"""
    # TODO：后续实现全库压缩打包、下载功能
    return {"code": 200, "msg": "✅ 全库备份功能开发中，敬请期待"}
# 获取全局默认系统提示词
@app.get("/api/config/system_prompt")
async def get_system_prompt():
    with open(SYSTEM_PROMPT_CONFIG, "r", encoding="utf-8") as f:
        config = json.load(f)
    return {"code": 200, "data": config["default_prompt"]}

# 修改全局默认系统提示词
@app.post("/api/config/system_prompt")
async def update_system_prompt(request: Request):
    data = await request.json()
    new_prompt = data.get("prompt", "").strip()
    if not new_prompt:
        return {"code": 400, "msg": "提示词不能为空"}
    with open(SYSTEM_PROMPT_CONFIG, "w", encoding="utf-8") as f:
        json.dump({"default_prompt": new_prompt}, f, ensure_ascii=False, indent=2)
    add_operation_log("配置修改", "更新全局系统提示词")
    return {"code": 200, "msg": "✅ 全局系统提示词修改成功，下次对话自动生效"}

# ========================== Prompt模板管理接口 ==========================
# Prompt模板配置路径
PROMPT_TPL_PATH = os.path.join(BASE_DIR, "prompt_templates.json")

# 初始化默认配置
if not os.path.exists(PROMPT_TPL_PATH):
    with open(PROMPT_TPL_PATH, "w", encoding="utf-8") as f:
        json.dump({"system_templates": [
                {
                "id": "customA",
                "name": "日常对话助手",
                "content": "你是一个简洁友好的AI助手，回答准确精炼。",
                "editable": True
                },
                {
                "id": "req_analysis",
                "name": "需求分析师",
                "content": "你是懂沟通、会共情的资深产品需求分析师，是用户做项目的贴心顾问，核心目标是和用户一起把模糊需求梳理成可落地的完整方案，全程沟通自然友好，不要生硬像机器人。\n====================\n【核心工作流程（按顺序执行，不能跳步）】\n1. 第一步：先读取当前项目手册、现有文件清单，快速了解项目已有基础\n2. 第二步：友好引导挖需求（必须执行）：\n   👉 语气自然，可加适当语气助词（哦、哈、呀之类的），不要生硬提问\n   👉 结合用户的具体需求问2~3个最核心的问题，不要问通用套话，比如用户说要做双色球项目，就问「你是想要纯后台跑脚本出数据，还是需要做可视化网页呀？」，不要问生硬的「你的使用场景是什么」\n   👉 禁止脑补用户需求，等用户把核心信息说清楚再输出方案\n3. 第三步：输出草稿方案和用户对齐：\n   把你理解的核心需求、大致模块、排期优先级用简洁的话和用户确认，比如「我理解下来你需要的是3个核心功能：xxx、xxx、xxx，对吗？有没有要补充或者砍掉的呀？」\n4. 第四步：同步更新+生成文档：\n   • 先更新【项目手册.md】里的「核心目标、功能范围、风险点」三个章节，确保项目全局信息同步\n   • 生成独立的【项目开发规划方案.md】，作为开发阶段的执行指导，必须包含：\n     1. 项目概述（做什么、给谁用、目标是什么）\n     2. 详细需求清单（每个功能点的具体要求）\n     3. 模块拆分+优先级+依赖关系表\n     4. 开发排期/里程碑节点\n     5. 每个模块的验收标准\n     6. 风险点+应对方案\n     7. 后续开发建议\n5. 第五步：方案确认+衔接下一阶段：\n   把生成的规划方案发给用户，问下「你看看还有没有要补充调整的？如果没问题的话，我建议你切换到【资深全栈开发工程师】身份模板，就可以按规划开始开发啦😉」\n====================\n【禁止规则】\n• 禁止输出任何代码，只做需求梳理、方案输出、文档生成工作\n• 禁止用生硬的指令式话术，比如不要说「你必须回答以下问题」，要说「我先和你确认几个小细节哦」\n• 禁止跳步直接出方案，必须先和用户对齐需求\n• 禁止越界做开发的活，方案确认完主动引导切换开发身份",
                "editable": True
                },
                {
                "id": "code_gen",
                "name": "开发工程师",
                "content": "你是资深全栈开发工程师，严格遵循项目代码规范，根据已知信息，分析后输出可直接运行的高质量代码，开发项目文件使用模块化方式，每个文件的功能给出注释，优先使用项目现有框架能力实现需求，代码附带清晰注释，同步给出实现逻辑说明。\n工具调用指令必须输出在正式content字段，禁止写在reasoning_content思考过程中。\n（已知信息包括:1，用户对话信息；2，所有AI可以自行使用工具读取检索文件的信息；3，系统给出的项目的信息和文件清单）。\n【开发工作流规则】\n1. 收到新项目开发需求后，第一步必须先读取当前项目的「项目手册」：\n   • 如果是新项目文件还不完善，先输出「开发架构方案+项目规划文件」，包含技术栈选型、模块拆分、文件清单、每个模块的功能定义，待确认后再往下走；\n   • 如果是项目修复需求，先读取项目手册，确定项目架构，模块功能后再读取相关文件排查问题根因，给出修复方案和说明等待用户确认后才能执行下一步操作。\n2. 第二步必须先调用`get_project_tree`工具查询当前项目完整文件清单，明确哪些文件需要新建、哪些需要修改：\n   • 严禁凭记忆/臆断文件是否存在\n   • 严禁未获取文件清单前执行任何文件创建/写入/修改操作\n3. 第三步必须先列出需要读取的关联文件清单，主动调用读取工具读取对应文件内容，**严禁凭记忆/通用知识编写任何代码**\n4. 第四步输出修改方案，明确要修改/创建的文件列表、每个文件的修改点、关联影响，待确认后再执行修改\n5. 第五步文件操作强制规范：\n   ✅ 修改单个文件前必须先读取该文件的最新内容，确保修改完全匹配现有代码结构、缩进、命名规范\n   ✅ 每次仅允许执行1个文件操作，批量操作必须逐个执行，上一个文件校验完成才能执行下一个\n6. 第六步操作成功强制校验：\n   每完成1个文件的创建/修改/写入操作后，必须立刻执行校验，未完成校验不得进入下一个操作：调用`read_file`工具读取刚操作的文件完整内容，逐段确认内容和预期完全一致，无缺失、无格式错误\n7. 第七步修改完成后主动检查关联文件是否需要同步修改，需要的话先读取关联文件确认后再改\n\n【刚性禁止项（违反直接拦截返回错误）】\n❌ 禁止跳过校验步骤，未校验的操作视为未执行\n❌ 禁止批量执行多个文件操作后统一校验，必须单文件操作完成立刻校验",
                "editable": True
                },
                {
                "id": "bug_fix",
                "name": "分析修复专家",
                "content": "你资深问题修复专家，认真分析用户的对话需求，回复用户的问题，并负责处理【已确认的代码问题】和【已复现的运行报错】，严格遵循精准聚焦修改原则，零次生问题、全链路留痕，修复方案必须可落地可验证。\n工具调用指令必须输出在正式content字段，禁止写在reasoning_content思考过程中。\n---\n## 🔴 核心规则\n1. 当收到用户的项目修复需求，先读取项目手册，确定项目架构、模块功能后才能执行下一步操作；\n2. 定位问题时优先使用`exec_cmd`精准检索或`rag_search`语义检索提取相关代码片段，仅在需要理解完整文件结构时使用`read_file`全量读取；\n3. 第三步输出修改方案，明确要修改/创建的文件列表、每个文件的修改点、关联影响，待用户确认修复方案后再执行修改；\n4. 用户确认修复方案后执行相应的任务，读取要修改的文件确认修改位置；\n5. 文件操作强制规范：\n   ✅ 修改单个文件前必须先读取该文件的最新内容，确保修改完全匹配现有代码结构、缩进、命名规范\n   ✅ 每次仅允许执行1个文件操作，批量操作必须逐个执行，上一个文件校验完成才能执行下一个\n6. 操作成功强制校验：\n   每完成1个文件的创建/修改/写入操作后，必须立刻执行校验，未完成校验不得进入下一个操作：调用`read_file`或`exec_cmd`读取刚操作的文件相关内容，确认修改内容和预期完全一致，无缺失、无格式错误\n---\n## 📋 核心职责（负责做以下两类事）\n1. 修复【测试/运行/线上场景的明确报错】，包含报错日志、复现路径的问题\n2. 精准检索相关代码后给出修改方案（修改方案必须包含有替代方案，并向用户说明权衡利弊后的最优方案）\n---\n## 🔧 刚性执行流程（必须严格按顺序走）\n\n### 场景：单个运行错误/BUG修复\n\n#### 步骤1：根因定位\n✅ 先获取完整报错信息、复现路径、操作上下文\n✅ 优先使用`exec_cmd`精准检索或`rag_search`语义检索定位相关代码，仅在需要理解完整文件结构时使用`read_file`全量读取\n✅ 定位100%明确的根因，禁止猜问题\n✅ 输出根因分析报告给用户确认，明确：错误原因、影响范围、修改方案（修改内容中有影响程序功能的，必须征求用户意见给出替代方案，和用户讨论实施细节）\n✅ 用户确认方案后才开始修改\n---\n#### 步骤2：修改&验证\n1. 【改】执行精准聚焦修改，仅修改和错误直接相关的代码\n2. 每次输出只能修改一个文件，不能执行多文件一次修改\n3. 修改完成后校验：\n   ✅ 使用`exec_cmd`精准检索或`read_file`读取修改后的文件相关内容确认修改正确\n---\n## 📌 【新增】精准聚焦修改原则说明\n- **只改与当前问题有直接因果关系的代码**，需要改几处就改几处，不限制修改数量\n- **绝对不碰当前功能正常的代码**，即使代码风格/结构/命名看起来不合理也不动\n- **不做预防性优化、不顺手重构、不主动统一代码风格**\n- **判断标准**：如果不改这处代码，问题能不能解决？能解决就不改，不能解决就必须改",
                "editable": True
                },
                {
                "id": "doc_gen",
                "name": "文档生成专家",
                "content": "你是专业技术文档工程师，输出结构清晰、逻辑严谨、易于理解的技术文档，包含功能说明、使用方法、参数说明、注意事项。",
                "editable": True
                },
                {
                "id": "customB",
                "name": "图片视频专家",
                "content": "你是专业级AI影视全链路制作专家，专属职责是承接用户的影视/短视频/动画制作需求，从需求解析到素材生成再到最终成片全流程标准化交付，所有环节严格遵循用户确认机制，不私自跳过任何步骤。\n\n【核心能力清单】\n1. 需求智能解析：自动提取用户给出的所有核心信息，缺失的关键信息主动询问用户补全，所有自动补全的细节必须明确标注告知用户可调整\n2. 专业剧本生成：根据需求生成符合影视工业标准的分镜头剧本，包含时长分配、镜头类型、画面细节、音效说明\n3. 素材智能生产：调用生图插件生成符合剧本要求的标准化素材：\n   - 人物类：生成正面/侧面/45度斜侧/局部特写4个角度的统一风格人物卡片\n   - 场景类：生成全景/中景/近景/特写4个角度的统一风格场景卡片\n   - 所有素材默认1920x1920高清分辨率，无水印，风格统一适配后续视频生成要求\n4. 成片落地交付：收集用户确认后的所有素材、剧本，调用视频生成插件完成成片制作，主动同步成片地址和本地保存路径\n\n【标准化工作流程（必须严格按顺序执行，禁止跳步）】\n步骤1：需求接收与校验\n- 收到用户需求后2分钟内完成信息提取，列出已确认的核心要素、待确认的缺失要素，主动询问用户补全\n- 自动识别需求是否涉及风控敏感内容，如有风险第一时间告知用户并提供合规替代方案\n\n步骤2：剧本生成与确认\n- 根据完整需求生成专业分镜头剧本，明确标注自动补全的细节内容\n- 剧本生成后主动发给用户确认，收到用户修改意见立即调整，直到用户确认剧本定稿才进入下一步\n\n步骤3：素材生成与确认\n- 根据定稿剧本生成所有需要的人物/场景卡片，每个素材明确标注对应剧本的镜头位置\n- 素材生成后主动发给用户确认，收到用户修改意见立即调整，直到用户确认所有素材定稿才进入下一步\n\n步骤4：成片生成与交付\n- 把定稿的剧本、所有素材作为参数传入视频生成插件，严格匹配用户要求的时长、尺寸、音频规则\n- 生成完成后主动同步成片在线地址、本地保存路径，询问用户是否需要调整优化\n\n【输出规范要求】\n1. 剧本输出规范：\n   - 明确标注总时长、画面比例、整体风格\n   - 每个镜头按「时间区间+镜头类型+画面描述+音效说明」的格式输出\n   - 自动补全的内容标注「🔹 AI自动补全，可调整」\n2. 素材输出规范：\n   - 每张素材标注「类型+对应镜头+角度」\n   - 所有素材统一风格、统一配色，无明显违和感\n3. 成片输出规范：\n   - 主动说明生成的成片对应的剧本、素材版本\n   - 同步在线地址和本地路径，有效期标注清楚\n\n【交互约束规则】\n1. 每个环节必须得到用户明确确认才能进入下一个环节，禁止私自推进\n2. 所有修改意见100%响应，不遗漏任何用户提出的调整要求\n3. 生成过程中出现任何报错/风控拦截第一时间告知用户，同时给出替代方案\n4. 所有生成内容保证无版权风险，可直接用于商用场景\n\n【参数适配标准（内置无需用户告知）】\n1. 生图默认参数：size=1920x1920，风格匹配用户需求，提示词自动加入「高清无水印、边缘清晰、适合图生视频使用」\n2. 视频生成默认参数：尺寸匹配用户需求，时长匹配剧本总时长，generate_audio默认开启，素材自动按优先级传入参考图参数",
                "editable": True
                }
            ],
            "custom_templates": []        
            }, f, ensure_ascii=False, indent=2)

# 初始化默认模板
def init_default_prompt_tpl():
    default_tpl = {
        "system_templates": [
                {
                "id": "customA",
                "name": "日常对话助手",
                "content": "你是一个简洁友好的AI助手，回答准确精炼。",
                "editable": True
                },
                {
                "id": "req_analysis",
                "name": "需求分析师",
                "content": "你是懂沟通、会共情的资深产品需求分析师，是用户做项目的贴心顾问，核心目标是和用户一起把模糊需求梳理成可落地的完整方案，全程沟通自然友好，不要生硬像机器人。\n====================\n【核心工作流程（按顺序执行，不能跳步）】\n1. 第一步：先读取当前项目手册、现有文件清单，快速了解项目已有基础\n2. 第二步：友好引导挖需求（必须执行）：\n   👉 语气自然，可加适当语气助词（哦、哈、呀之类的），不要生硬提问\n   👉 结合用户的具体需求问2~3个最核心的问题，不要问通用套话，比如用户说要做双色球项目，就问「你是想要纯后台跑脚本出数据，还是需要做可视化网页呀？」，不要问生硬的「你的使用场景是什么」\n   👉 禁止脑补用户需求，等用户把核心信息说清楚再输出方案\n3. 第三步：输出草稿方案和用户对齐：\n   把你理解的核心需求、大致模块、排期优先级用简洁的话和用户确认，比如「我理解下来你需要的是3个核心功能：xxx、xxx、xxx，对吗？有没有要补充或者砍掉的呀？」\n4. 第四步：同步更新+生成文档：\n   • 先更新【项目手册.md】里的「核心目标、功能范围、风险点」三个章节，确保项目全局信息同步\n   • 生成独立的【项目开发规划方案.md】，作为开发阶段的执行指导，必须包含：\n     1. 项目概述（做什么、给谁用、目标是什么）\n     2. 详细需求清单（每个功能点的具体要求）\n     3. 模块拆分+优先级+依赖关系表\n     4. 开发排期/里程碑节点\n     5. 每个模块的验收标准\n     6. 风险点+应对方案\n     7. 后续开发建议\n5. 第五步：方案确认+衔接下一阶段：\n   把生成的规划方案发给用户，问下「你看看还有没有要补充调整的？如果没问题的话，我建议你切换到【资深全栈开发工程师】身份模板，就可以按规划开始开发啦😉」\n====================\n【禁止规则】\n• 禁止输出任何代码，只做需求梳理、方案输出、文档生成工作\n• 禁止用生硬的指令式话术，比如不要说「你必须回答以下问题」，要说「我先和你确认几个小细节哦」\n• 禁止跳步直接出方案，必须先和用户对齐需求\n• 禁止越界做开发的活，方案确认完主动引导切换开发身份",
                "editable": True
                },
                {
                "id": "code_gen",
                "name": "开发工程师",
                "content": "你是资深全栈开发工程师，严格遵循项目代码规范，根据已知信息，分析后输出可直接运行的高质量代码，开发项目文件使用模块化方式，每个文件的功能给出注释，优先使用项目现有框架能力实现需求，代码附带清晰注释，同步给出实现逻辑说明。\n工具调用指令必须输出在正式content字段，禁止写在reasoning_content思考过程中。\n（已知信息包括:1，用户对话信息；2，所有AI可以自行使用工具读取检索文件的信息；3，系统给出的项目的信息和文件清单）。\n【开发工作流规则】\n1. 收到新项目开发需求后，第一步必须先读取当前项目的「项目手册」：\n   • 如果是新项目文件还不完善，先输出「开发架构方案+项目规划文件」，包含技术栈选型、模块拆分、文件清单、每个模块的功能定义，待确认后再往下走；\n   • 如果是项目修复需求，先读取项目手册，确定项目架构，模块功能后再读取相关文件排查问题根因，给出修复方案和说明等待用户确认后才能执行下一步操作。\n2. 第二步必须先调用`get_project_tree`工具查询当前项目完整文件清单，明确哪些文件需要新建、哪些需要修改：\n   • 严禁凭记忆/臆断文件是否存在\n   • 严禁未获取文件清单前执行任何文件创建/写入/修改操作\n3. 第三步必须先列出需要读取的关联文件清单，主动调用读取工具读取对应文件内容，**严禁凭记忆/通用知识编写任何代码**\n4. 第四步输出修改方案，明确要修改/创建的文件列表、每个文件的修改点、关联影响，待确认后再执行修改\n5. 第五步文件操作强制规范：\n   ✅ 修改单个文件前必须先读取该文件的最新内容，确保修改完全匹配现有代码结构、缩进、命名规范\n   ✅ 每次仅允许执行1个文件操作，批量操作必须逐个执行，上一个文件校验完成才能执行下一个\n6. 第六步操作成功强制校验：\n   每完成1个文件的创建/修改/写入操作后，必须立刻执行校验，未完成校验不得进入下一个操作：调用`read_file`工具读取刚操作的文件完整内容，逐段确认内容和预期完全一致，无缺失、无格式错误\n7. 第七步修改完成后主动检查关联文件是否需要同步修改，需要的话先读取关联文件确认后再改\n\n【刚性禁止项（违反直接拦截返回错误）】\n❌ 禁止跳过校验步骤，未校验的操作视为未执行\n❌ 禁止批量执行多个文件操作后统一校验，必须单文件操作完成立刻校验",
                "editable": True
                },
                {
                "id": "bug_fix",
                "name": "分析修复专家",
                "content": "你资深问题修复专家，认真分析用户的对话需求，回复用户的问题，并负责处理【已确认的代码问题】和【已复现的运行报错】，严格遵循精准聚焦修改原则，零次生问题、全链路留痕，修复方案必须可落地可验证。\n工具调用指令必须输出在正式content字段，禁止写在reasoning_content思考过程中。\n---\n## 🔴 核心规则\n1. 当收到用户的项目修复需求，先读取项目手册，确定项目架构、模块功能后才能执行下一步操作；\n2. 定位问题时优先使用`exec_cmd`精准检索或`rag_search`语义检索提取相关代码片段，仅在需要理解完整文件结构时使用`read_file`全量读取；\n3. 第三步输出修改方案，明确要修改/创建的文件列表、每个文件的修改点、关联影响，待用户确认修复方案后再执行修改；\n4. 用户确认修复方案后执行相应的任务，读取要修改的文件确认修改位置；\n5. 文件操作强制规范：\n   ✅ 修改单个文件前必须先读取该文件的最新内容，确保修改完全匹配现有代码结构、缩进、命名规范\n   ✅ 每次仅允许执行1个文件操作，批量操作必须逐个执行，上一个文件校验完成才能执行下一个\n6. 操作成功强制校验：\n   每完成1个文件的创建/修改/写入操作后，必须立刻执行校验，未完成校验不得进入下一个操作：调用`read_file`或`exec_cmd`读取刚操作的文件相关内容，确认修改内容和预期完全一致，无缺失、无格式错误\n---\n## 📋 核心职责（负责做以下两类事）\n1. 修复【测试/运行/线上场景的明确报错】，包含报错日志、复现路径的问题\n2. 精准检索相关代码后给出修改方案（修改方案必须包含有替代方案，并向用户说明权衡利弊后的最优方案）\n---\n## 🔧 刚性执行流程（必须严格按顺序走）\n\n### 场景：单个运行错误/BUG修复\n\n#### 步骤1：根因定位\n✅ 先获取完整报错信息、复现路径、操作上下文\n✅ 优先使用`exec_cmd`精准检索或`rag_search`语义检索定位相关代码，仅在需要理解完整文件结构时使用`read_file`全量读取\n✅ 定位100%明确的根因，禁止猜问题\n✅ 输出根因分析报告给用户确认，明确：错误原因、影响范围、修改方案（修改内容中有影响程序功能的，必须征求用户意见给出替代方案，和用户讨论实施细节）\n✅ 用户确认方案后才开始修改\n---\n#### 步骤2：修改&验证\n1. 【改】执行精准聚焦修改，仅修改和错误直接相关的代码\n2. 每次输出只能修改一个文件，不能执行多文件一次修改\n3. 修改完成后校验：\n   ✅ 使用`exec_cmd`精准检索或`read_file`读取修改后的文件相关内容确认修改正确\n---\n## 📌 【新增】精准聚焦修改原则说明\n- **只改与当前问题有直接因果关系的代码**，需要改几处就改几处，不限制修改数量\n- **绝对不碰当前功能正常的代码**，即使代码风格/结构/命名看起来不合理也不动\n- **不做预防性优化、不顺手重构、不主动统一代码风格**\n- **判断标准**：如果不改这处代码，问题能不能解决？能解决就不改，不能解决就必须改",
                "editable": True
                },
                {
                "id": "doc_gen",
                "name": "文档生成专家",
                "content": "你是专业技术文档工程师，输出结构清晰、逻辑严谨、易于理解的技术文档，包含功能说明、使用方法、参数说明、注意事项。",
                "editable": True
                },
                {
                "id": "customB",
                "name": "图片视频专家",
                "content": "你是专业级AI影视全链路制作专家，专属职责是承接用户的影视/短视频/动画制作需求，从需求解析到素材生成再到最终成片全流程标准化交付，所有环节严格遵循用户确认机制，不私自跳过任何步骤。\n\n【核心能力清单】\n1. 需求智能解析：自动提取用户给出的所有核心信息，缺失的关键信息主动询问用户补全，所有自动补全的细节必须明确标注告知用户可调整\n2. 专业剧本生成：根据需求生成符合影视工业标准的分镜头剧本，包含时长分配、镜头类型、画面细节、音效说明\n3. 素材智能生产：调用生图插件生成符合剧本要求的标准化素材：\n   - 人物类：生成正面/侧面/45度斜侧/局部特写4个角度的统一风格人物卡片\n   - 场景类：生成全景/中景/近景/特写4个角度的统一风格场景卡片\n   - 所有素材默认1920x1920高清分辨率，无水印，风格统一适配后续视频生成要求\n4. 成片落地交付：收集用户确认后的所有素材、剧本，调用视频生成插件完成成片制作，主动同步成片地址和本地保存路径\n\n【标准化工作流程（必须严格按顺序执行，禁止跳步）】\n步骤1：需求接收与校验\n- 收到用户需求后2分钟内完成信息提取，列出已确认的核心要素、待确认的缺失要素，主动询问用户补全\n- 自动识别需求是否涉及风控敏感内容，如有风险第一时间告知用户并提供合规替代方案\n\n步骤2：剧本生成与确认\n- 根据完整需求生成专业分镜头剧本，明确标注自动补全的细节内容\n- 剧本生成后主动发给用户确认，收到用户修改意见立即调整，直到用户确认剧本定稿才进入下一步\n\n步骤3：素材生成与确认\n- 根据定稿剧本生成所有需要的人物/场景卡片，每个素材明确标注对应剧本的镜头位置\n- 素材生成后主动发给用户确认，收到用户修改意见立即调整，直到用户确认所有素材定稿才进入下一步\n\n步骤4：成片生成与交付\n- 把定稿的剧本、所有素材作为参数传入视频生成插件，严格匹配用户要求的时长、尺寸、音频规则\n- 生成完成后主动同步成片在线地址、本地保存路径，询问用户是否需要调整优化\n\n【输出规范要求】\n1. 剧本输出规范：\n   - 明确标注总时长、画面比例、整体风格\n   - 每个镜头按「时间区间+镜头类型+画面描述+音效说明」的格式输出\n   - 自动补全的内容标注「🔹 AI自动补全，可调整」\n2. 素材输出规范：\n   - 每张素材标注「类型+对应镜头+角度」\n   - 所有素材统一风格、统一配色，无明显违和感\n3. 成片输出规范：\n   - 主动说明生成的成片对应的剧本、素材版本\n   - 同步在线地址和本地路径，有效期标注清楚\n\n【交互约束规则】\n1. 每个环节必须得到用户明确确认才能进入下一个环节，禁止私自推进\n2. 所有修改意见100%响应，不遗漏任何用户提出的调整要求\n3. 生成过程中出现任何报错/风控拦截第一时间告知用户，同时给出替代方案\n4. 所有生成内容保证无版权风险，可直接用于商用场景\n\n【参数适配标准（内置无需用户告知）】\n1. 生图默认参数：size=1920x1920，风格匹配用户需求，提示词自动加入「高清无水印、边缘清晰、适合图生视频使用」\n2. 视频生成默认参数：尺寸匹配用户需求，时长匹配剧本总时长，generate_audio默认开启，素材自动按优先级传入参考图参数",
                "editable": True
                }
            ],
        "custom_templates": []
    }
    with open(PROMPT_TPL_PATH, "w", encoding="utf-8") as f:
        json.dump(default_tpl, f, ensure_ascii=False, indent=2)
    return default_tpl

# 读取模板列表
def load_prompt_tpl():
    if not os.path.exists(PROMPT_TPL_PATH):
        return init_default_prompt_tpl()
    try:
        with open(PROMPT_TPL_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError, IOError):
        # 文件损坏返回默认
        return init_default_prompt_tpl()

# 模板保存请求模型
class PromptSaveRequest(BaseModel):
    tpl_id: str
    content: str

# 模板重置请求模型
class PromptResetRequest(BaseModel):
    tpl_id: str

# 获取所有Prompt模板
@app.get("/api/prompt/templates")
async def get_prompt_templates():
    tpls = load_prompt_tpl()
    return {"code": 200, "data": tpls}

# 保存Prompt模板
@app.post("/api/prompt/save")
async def save_prompt_template(req: PromptSaveRequest):
    tpls = load_prompt_tpl()
    # 查找系统模板
    found = False
    for tpl in tpls["system_templates"]:
        if tpl["id"] == req.tpl_id:
            tpl["content"] = req.content.strip()
            found = True
            break
    # 没找到查自定义模板
    if not found:
        for tpl in tpls["custom_templates"]:
            if tpl["id"] == req.tpl_id:
                tpl["content"] = req.content.strip()
                found = True
                break
    if not found:
        raise HTTPException(status_code=404, detail="模板不存在")
    # 写入文件
    with open(PROMPT_TPL_PATH, "w", encoding="utf-8") as f:
        json.dump(tpls, f, ensure_ascii=False, indent=2)
    add_operation_log("配置修改", f"修改Prompt模板：{req.tpl_id}")
    return {"code": 200, "msg": "模板保存成功"}

# -------------------------- 插件管理接口 --------------------------
class PluginInstallRequest(BaseModel):
    plugin_path: str # 本地插件路径/云端插件ID
    is_local: bool = True

class PluginOperateRequest(BaseModel):
    plugin_id: str
class PluginConfigSaveRequest(BaseModel):
    plugin_id: str
    config: Dict[str, Any]

@app.get("/api/plugin/list")
async def get_plugin_list():
    """获取所有已安装+可安装插件列表"""
    # 已安装插件
    installed = []
    for plugin_id, template in tool_template_manager._plugin_templates.items():
        config = template["plugin_config"]
        installed.append({
            "plugin_id": plugin_id,
            "name": config["name"],
            "description": config["description"],
            "version": config.get("version", "1.0.0"),
            "author": config.get("author", "未知"),
            "icon": config.get("icon", ""),
            "enabled": plugin_id in tool_template_manager._enabled_plugins,
            "permissions": config.get("permissions", []),
            "config": config.get("config", []),
            "actions": config.get("actions", [])
        })
    # 可安装插件（后续扩展云端插件市场）
    available = []
    return {"code": 200, "data": {"installed": installed, "available": available}}

@app.post("/api/plugin/install")
async def install_plugin(req: PluginInstallRequest):
    """安装插件"""
    try:
        if req.is_local:
            # 本地插件:复制到plugins目录
            import shutil
            plugin_name = os.path.basename(req.plugin_path.rstrip(os.sep))
            target_path = os.path.join(tool_template_manager.PLUGIN_DIR, plugin_name)
            shutil.copytree(req.plugin_path, target_path)
            # 重新加载插件
            tool_template_manager.load_plugins()
            add_operation_log("插件管理", f"✅ 安装插件成功:{plugin_name}")
            return {"code": 200, "msg": "插件安装成功"}
        else:
            # 云端插件后续扩展
            return {"code": 400, "msg": "云端插件市场开发中"}
    except Exception as e:
        return {"code": 500, "msg": f"安装失败:{str(e)}"}
@app.post("/api/plugin/install/local")
async def install_local_plugin(plugin_file: UploadFile = File(...)):
    """上传本地zip插件包安装"""
    try:
        import zipfile
        import shutil
        # 临时保存zip文件
        temp_path = f"./temp_{plugin_file.filename}"
        with open(temp_path, "wb") as f:
            f.write(await plugin_file.read())
        # 解压到plugins目录
        plugin_name = os.path.splitext(plugin_file.filename)[0]
        target_path = os.path.join(tool_template_manager.PLUGIN_DIR, plugin_name)
        if os.path.exists(target_path):
            shutil.rmtree(target_path)
        os.makedirs(target_path, exist_ok=True)
        with zipfile.ZipFile(temp_path, 'r') as zip_ref:
            zip_ref.extractall(target_path)
        # 删除临时文件
        os.remove(temp_path)
        # 重新加载插件
        tool_template_manager.load_plugins()
        add_operation_log("插件管理", f"✅ 上传安装插件成功:{plugin_name}")
        return {"code": 200, "msg": "插件安装成功"}
    except Exception as e:
        return {"code": 500, "msg": f"安装失败:{str(e)}"}
@app.post("/api/plugin/install/folder")
async def install_plugin_folder(request: Request, plugin_name: str = Form(...), file_count: int = Form(...)):
    """上传本地插件文件夹安装"""
    try:
        import shutil
        target_path = os.path.join(tool_template_manager.PLUGIN_DIR, plugin_name)
        # 清理旧版本
        if os.path.exists(target_path):
            shutil.rmtree(target_path)
        os.makedirs(target_path, exist_ok=True)
        # 保存所有文件
        for i in range(file_count):
            file = await request.form()
            uploaded_file = file.get(f"file_{i}")
            relative_path = file.get(f"path_{i}")
            # 构建完整路径
            full_path = os.path.join(target_path, relative_path)
            # 创建父目录
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            # 写入文件
            with open(full_path, "wb") as f:
                f.write(await uploaded_file.read())
        # 重新加载插件
        tool_template_manager.load_plugins()
        add_operation_log("插件管理", f"✅ 上传文件夹安装插件成功:{plugin_name}")
        return {"code": 200, "msg": "插件安装成功"}
    except Exception as e:
        return {"code": 500, "msg": f"安装失败:{str(e)}"}

@app.post("/api/plugin/uninstall")
async def uninstall_plugin(req: PluginOperateRequest):
    """卸载插件"""
    try:
        config = tool_template_manager.get_plugin_config(req.plugin_id)
        if not config:
            return {"code": 404, "msg": "插件不存在"}
        plugin_dir = os.path.join(tool_template_manager.PLUGIN_DIR, req.plugin_id)
        import shutil
        shutil.rmtree(plugin_dir)
        tool_template_manager.load_plugins()
        add_operation_log("插件管理", f"✅ 卸载插件成功:{req.plugin_id}")
        return {"code": 200, "msg": "插件卸载成功"}
    except Exception as e:
        return {"code": 500, "msg": f"卸载失败:{str(e)}"}

@app.post("/api/plugin/enable")
async def enable_plugin(req: PluginOperateRequest):
    """启用插件"""
    if req.plugin_id in tool_template_manager._plugin_templates:
        tool_template_manager._enabled_plugins.add(req.plugin_id)
        return {"code": 200, "msg": "插件已启用"}
    return {"code": 404, "msg": "插件不存在"}

@app.post("/api/plugin/disable")
async def disable_plugin(req: PluginOperateRequest):
    """禁用插件"""
    if req.plugin_id in tool_template_manager._enabled_plugins:
        tool_template_manager._enabled_plugins.remove(req.plugin_id)
        return {"code": 200, "msg": "插件已禁用"}
    return {"code": 404, "msg": "插件不存在"}
@app.get("/api/plugin/config")
async def get_plugin_config(plugin_id: str):
    """获取插件的配置定义+当前用户配置值（每次请求强制读取磁盘最新配置，禁用内存缓存）"""
    plugin_config = tool_template_manager.get_plugin_config(plugin_id)
    if not plugin_config:
        return {"code":404, "msg":"插件不存在"}
    # 每次请求强制读取磁盘上的用户配置文件，不使用内存缓存
    user_config_path = os.path.join(tool_template_manager.PLUGIN_DIR, plugin_id, "user_config.json")
    user_config = {}
    if os.path.exists(user_config_path):
        try:
            with open(user_config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
        except:
            pass
    # 实时合并默认配置+用户最新配置，确保返回的是磁盘最新内容
    default_config = {}
    for config_item in plugin_config.get("config", []):
        if "key" in config_item and "default" in config_item:
            default_config[config_item["key"]] = config_item["default"]
    # 用户配置覆盖默认值
    current_config = {**default_config, **user_config}
    # 设置响应头禁用浏览器缓存，确保前端每次都拿到最新数据
    response = JSONResponse(content={"code":200, "data": {
        "config_definition": plugin_config.get("config", []),
        "current_config": current_config,
        "support_test": plugin_config.get("support_test", False)
    }})
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.post("/api/plugin/config/save")
async def save_plugin_config(req: PluginConfigSaveRequest):
    """保存用户修改的插件配置"""
    plugin_config = tool_template_manager.get_plugin_config(req.plugin_id)
    if not plugin_config:
        return {"code":404, "msg":"插件不存在"}
    # 校验配置项合法性，只允许修改plugin.json中预定义的配置字段
    allowed_keys = [item["key"] for item in plugin_config.get("config", [])]
    # 清理所有字符串配置的前后空白字符（空格/制表符/换行），避免用户复制时带多余字符
    filtered_config = {}
    for k, v in req.config.items():
        if k in allowed_keys:
            if isinstance(v, str):
                filtered_config[k] = v.strip()
            else:
                filtered_config[k] = v
    # 保存到用户配置文件
    user_config_path = os.path.join(tool_template_manager.PLUGIN_DIR, req.plugin_id, "user_config.json")
    try:
        with open(user_config_path, "w", encoding="utf-8") as f:
            json.dump(filtered_config, f, ensure_ascii=False, indent=2)
        # 重新加载插件配置，即时生效不用重启
        tool_template_manager.load_plugins()
        # 清理插件模块缓存，下次执行自动读取最新配置
        import sys
        plugin_module_name = f"plugin_{req.plugin_id}"
        if plugin_module_name in sys.modules:
            del sys.modules[plugin_module_name]
        add_operation_log("插件管理", f"✅ 保存插件{req.plugin_id}配置成功")
        return {"code":200, "msg":"配置保存成功，即时生效"}
    except Exception as e:
        return {"code":500, "msg":f"保存失败:{str(e)}"}
@app.post("/api/plugin/test")
async def test_plugin_connection(req: PluginOperateRequest):
    """测试插件连接（仅支持标记了support_test: true的插件）"""
    plugin_config = tool_template_manager.get_plugin_config(req.plugin_id)
    if not plugin_config:
        return {"code":404, "msg":"插件不存在"}
    if not plugin_config.get("support_test", False):
        return {"code":400, "msg":"该插件不支持连接测试功能"}
    try:
        # 动态加载插件模块，调用test_connection方法
        import importlib.util
        import sys
        plugin_path = os.path.join(tool_template_manager.PLUGIN_DIR, req.plugin_id, plugin_config["entry"])
        if not os.path.exists(plugin_path):
            return {"code":500, "msg":"插件入口文件不存在"}
        plugin_module_name = f"plugin_{req.plugin_id}"
        if plugin_module_name in sys.modules:
            del sys.modules[plugin_module_name]
        spec = importlib.util.spec_from_file_location(plugin_module_name, plugin_path)
        plugin_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin_module)
        # 注入最新配置
        plugin_module.plugin_config = plugin_config["merged_config"]
        # 调用测试连接方法
        if hasattr(plugin_module, "test_connection"):
            success, msg = plugin_module.test_connection()
            if success:
                add_operation_log("插件管理", f"✅ 插件{req.plugin_id}连接测试成功:{msg}")
                return {"code":200, "msg":msg}
            else:
                add_operation_log("插件管理", f"❌ 插件{req.plugin_id}连接测试失败:{msg}", "error")
                return {"code":500, "msg":msg}
        else:
            return {"code":400, "msg":"插件未实现test_connection方法"}
    except Exception as e:
        add_operation_log("插件管理", f"❌ 插件{req.plugin_id}连接测试异常:{str(e)}", "error")
        return {"code":500, "msg":f"测试异常:{str(e)}"}

class PluginActionRequest(BaseModel):
    plugin_id: str
    action_key: str

@app.post("/api/plugin/action")
async def execute_plugin_action(req: PluginActionRequest):
    """执行插件自定义操作（启动/停止/查询状态等卡片按钮触发）"""
    plugin_config = tool_template_manager.get_plugin_config(req.plugin_id)
    if not plugin_config:
        return {"code":404, "msg":"插件不存在"}
    # 校验action_key合法性
    valid_actions = [action.get("key") for action in plugin_config.get("actions", [])]
    if req.action_key not in valid_actions:
        return {"code":400, "msg":f"非法操作，插件未定义该操作:{req.action_key}"}
    try:
        # 动态加载最新插件代码
        import importlib.util
        import sys
        plugin_path = os.path.join(tool_template_manager.PLUGIN_DIR, req.plugin_id, plugin_config["entry"])
        if not os.path.exists(plugin_path):
            return {"code":500, "msg":"插件入口文件不存在"}
        plugin_module_name = f"plugin_{req.plugin_id}"
        if plugin_module_name in sys.modules:
            del sys.modules[plugin_module_name]
        spec = importlib.util.spec_from_file_location(plugin_module_name, plugin_path)
        plugin_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin_module)
        # 注入最新用户配置
        plugin_module.plugin_config = plugin_config["merged_config"]
        # 调用插件统一操作处理方法
        if hasattr(plugin_module, "handle_action"):
            success, result = plugin_module.handle_action(req.action_key)
            if success:
                add_operation_log("插件操作", f"✅ 执行插件【{plugin_config['name']}】操作【{req.action_key}】成功:{result}")
                return {"code":200, "msg":result}
            else:
                add_operation_log("插件操作", f"❌ 执行插件【{plugin_config['name']}】操作【{req.action_key}】失败:{result}", "error")
                return {"code":500, "msg":result}
        else:
            return {"code":400, "msg":"插件未实现handle_action方法，不支持自定义操作"}
    except Exception as e:
        add_operation_log("插件操作", f"❌ 执行插件【{plugin_config['name']}】操作【{req.action_key}】异常:{str(e)}", "error")
        return {"code":500, "msg":f"操作执行异常:{str(e)}"}

# 插件生成接口
class PluginGenerateRequest(BaseModel):
    plugin_info: Dict[str, Any]
    config_list: Optional[List[Dict[str, Any]]] = None
    param_list: Optional[List[Dict[str, Any]]] = None
    permission: str = "none"
    save_dir: str = os.path.join(os.path.expanduser("~"), "Documents", "AI仓库文件夹", "插件开发").replace("\\", "/")
    preset_template_id: Optional[str] = None

# 插件预制模板接口
@app.get("/api/plugin/templates")
async def get_plugin_templates():
    """获取所有预制插件模板列表，前端插件开发页面直接调用，错误模板自动跳过，永远返回成功避免前端加载失败"""
    try:
        templates = tool_template_manager.get_preset_template_list()
        return {"code": 200, "data": templates if templates else []}
    except Exception as e:
        print(f"❌ 获取模板列表异常:{str(e)}")
        return {"code": 200, "data": []}

# 插件预览接口
class PluginPreviewRequest(BaseModel):
    plugin_info: Dict[str, Any]
    config_list: Optional[List[Dict[str, Any]]] = None
    param_list: Optional[List[Dict[str, Any]]] = None
    permission: str = "none"
    preset_template_id: Optional[str] = None

@app.post("/api/plugin/preview")
async def preview_plugin(req: PluginPreviewRequest):
    """预览插件生成的代码内容，不写入文件"""
    try:
        # 临时目录生成插件后读取内容返回，自动清理
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            result = tool_template_manager.generate_plugin_template(
                plugin_info=req.plugin_info,
                config_list=req.config_list,
                param_list=req.param_list,
                permission=req.permission,
                save_dir=temp_dir,
                preset_template_id=req.preset_template_id
            )
            if not result["success"]:
                return {"code": 400, "msg": result["msg"]}
            # 读取所有生成的文件内容
            content = {}
            for file_path in result["files"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_name = os.path.basename(file_path)
                    content[file_name] = f.read()
            return {"code": 200, "data": content}
    except Exception as e:
        return {"code": 500, "msg": f"预览生成失败:{str(e)}"}
@app.post("/api/plugin/generate")
async def generate_plugin(req: PluginGenerateRequest):
    """一键生成符合规范的插件模板"""
    try:
        result = tool_template_manager.generate_plugin_template(
            plugin_info=req.plugin_info,
            config_list=req.config_list,
            param_list=req.param_list,
            permission=req.permission,
            save_dir=req.save_dir,
            preset_template_id=req.preset_template_id
        )
        if result["success"]:
            # 重新加载插件列表，生成的插件直接出现在已安装列表
            tool_template_manager.load_plugins()
            add_operation_log("插件管理", result["msg"])
            return {"code": 200, "msg": result["msg"], "data": result["files"]}
        else:
            return {"code": 400, "msg": result["msg"]}
    except Exception as e:
        add_operation_log("插件管理", f"❌ 生成插件失败:{str(e)}", "error")
        return {"code": 500, "msg": f"生成插件失败:{str(e)}"}
# ===================================================
@app.post("/api/browser/open")
async def open_browser(request: BrowserOpenRequest):
    """启动内置浏览器并打开指定URL"""
    from main import browser_window
    browser_window.load_url(request.url)
    browser_window.show()
    return {"code": 200, "msg": "浏览器已启动"}
# ========================== 定时任务管理接口 ==========================
@app.get("/web_scheduler.html", include_in_schema=False)
async def get_scheduler_page():
    return FileResponse(os.path.join(BASE_DIR, "web_scheduler.html"))

@app.get("/api/scheduler/tasks")
async def get_scheduler_tasks():
    """获取所有定时任务列表"""
    return scheduler_manager.get_all_tasks()

@app.post("/api/scheduler/tasks")
async def create_scheduler_task(req: Request):
    """创建定时任务"""
    data = await req.json()
    task = scheduler_manager.create_task(data)
    add_operation_log("定时任务", f"✅ 创建定时任务成功:{task['name']}")
    return task

@app.put("/api/scheduler/tasks/{task_id}")
async def update_scheduler_task(task_id: str, req: Request):
    """更新定时任务"""
    data = await req.json()
    task = scheduler_manager.update_task(task_id, data)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    add_operation_log("定时任务", f"✅ 更新定时任务成功:{task['name']}")
    return task

@app.post("/api/scheduler/tasks/{task_id}/cancel")
async def cancel_scheduler_task(task_id: str):
    """取消定时任务"""
    success = scheduler_manager.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在")
    add_operation_log("定时任务", f"✅ 取消定时任务成功:{task_id}")
    return {"code": 200, "msg": "任务已取消"}

@app.delete("/api/scheduler/tasks/{task_id}")
async def delete_scheduler_task(task_id: str):
    """删除定时任务"""
    success = scheduler_manager.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在")
    add_operation_log("定时任务", f"✅ 删除定时任务成功:{task_id}")
    return {"code": 200, "msg": "任务已删除"}

# ========================== 项目管理接口 ==========================
@app.get("/api/project/list")
async def get_project_list():
    """获取所有可开发项目列表（自动识别包含项目手册的文件夹）"""
    try:
        project_list = []
        for root, dirs, files in os.walk(REPOSITORY_PATH):
            # 剪枝:排除虚拟环境/.git/打包产物等噪音目录，避免遍历数万依赖文件
            file_filter_config.prune_walk_dirs(dirs)
            for file in files:
                if file.endswith("项目手册.md"):
                    project_name = os.path.basename(root)
                    project_root = os.path.relpath(root, REPOSITORY_PATH).replace("\\", "/")
                    manual_path = os.path.join(project_root, file).replace("\\", "/")
                    project_list.append({
                        "project_name": project_name,
                        "project_root": project_root,
                        "manual_path": manual_path
                    })
        return {"code": 200, "data": project_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取项目列表失败: {str(e)}")

class SwitchProjectRequest(BaseModel):
    project_name: str
    project_root: str
    manual_path: str

@app.post("/api/project/switch")
async def switch_project(req: SwitchProjectRequest):
    """切换当前开发项目"""
    global CURRENT_PROJECT
    try:
        # 解析对应项目手册的文件清单（修复:manual_path拼接仓库根路径转绝对路径，避免工作目录不匹配导致读取失败）
        abs_manual_path = os.path.join(REPOSITORY_PATH, req.manual_path).replace("\\", "/")
        file_list = project_manual_manager.parse_file_overview_table(abs_manual_path)
        # 更新全局状态
        CURRENT_PROJECT = {
            "project_name": req.project_name,
            "project_root": os.path.join(REPOSITORY_PATH, req.project_root).replace("\\", "/"),
            "manual_path": abs_manual_path,
            "file_list": file_list
        }
        # 新增:如果新项目不存在于session_context中，自动初始化空的会话池
        if req.project_name not in session_context:
            session_context[req.project_name] = {}
        add_operation_log("项目管理", f"切换到项目：{req.project_name}")
        print(f"✅ 已切换到项目【{req.project_name}】，根目录：{CURRENT_PROJECT['project_root']}")
        return {"code": 200, "msg": f"已切换到项目【{req.project_name}】", "file_list": file_list}
    except Exception as e:
        add_operation_log("项目管理", f"切换项目失败，错误：{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"切换项目失败: {str(e)}")

# ========================== 项目手册管理接口 ==========================
class DeleteProjectRequest(BaseModel):
    project_name: str
    project_root: str

@app.post("/api/project/delete")
async def delete_project(req: DeleteProjectRequest):
    """删除项目并同步清理所有关联数据"""
    global CURRENT_PROJECT
    try:
        # 1. 路径安全校验，防止穿越
        project_abs_path = os.path.normpath(os.path.join(REPOSITORY_PATH, req.project_root))
        if not project_abs_path.startswith(os.path.normpath(REPOSITORY_PATH)) or not os.path.exists(project_abs_path):
            raise HTTPException(status_code=400, detail="项目路径不合法或不存在")
        
        # 2. 如果删除的是当前选中项目，自动切回default默认项目
        if CURRENT_PROJECT.get("project_name") == req.project_name:
            CURRENT_PROJECT = {
                "project_name": "default",
                "project_root": "",
                "manual_path": "",
                "file_list": []
            }
            add_operation_log("项目管理", f"删除项目【{req.project_name}】为当前项目，自动切回默认项目")
        
        # 3. 删除仓库中的项目文件夹
        import shutil
        shutil.rmtree(project_abs_path)
        
        # 4. 同步删除对应项目的记忆历史文件
        safe_project_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5_-]', "_", req.project_name)
        project_history_file = os.path.join(BASE_DIR, f"latest_chat_history_{safe_project_name}.json")
        if os.path.exists(project_history_file):
            os.remove(project_history_file)
        
        # 5. 清理内存中该项目的所有会话缓存
        if req.project_name in session_context:
            del session_context[req.project_name]
        
        # 6. 清理该项目的所有RAG索引
        import asyncio
        asyncio.create_task(asyncio.to_thread(rag_manager.delete_project, req.project_name))
        
        # 7. 清理总记忆库中所有属于该项目的记忆（匹配标签project:项目名）
        meta_path = "./memory_meta.json"
        memories = {}
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                memories = json.load(f)
        to_delete_ids = []
        project_tag = f"project:{req.project_name}"
        for mid, mem in memories.items():
            if project_tag in mem.get("tags", []):
                to_delete_ids.append(mid)
        for mid in to_delete_ids:
            del memories[mid]
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(memories, f, ensure_ascii=False, indent=2)
        
        add_operation_log("项目管理", f"✅ 删除项目成功:{req.project_name}，关联记忆文件/会话缓存/总库记忆已同步清理")
        broadcast_file_change()
        return {"code": 200, "msg": f"项目【{req.project_name}】已成功删除，所有关联数据已清理"}
    except Exception as e:
        add_operation_log("项目管理", f"❌ 删除项目失败:{req.project_name}，错误:{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"删除项目失败:{str(e)}")
from project_manual_manager import project_manual_manager
class ProjectManualCreateRequest(BaseModel):
    project_name: str
    save_path: str = "" # 保存路径，空则默认保存到项目根目录

@app.post("/api/project-manual/create")
async def create_project_manual(req: ProjectManualCreateRequest):
    """创建标准化项目手册"""
    success, result = project_manual_manager.generate_template(req.project_name, req.save_path)
    if success:
        # 自动加入RAG索引
        import asyncio
        asyncio.create_task(asyncio.to_thread(rag_manager.add_file, result))
        # 触发文件变动广播，前端自动刷新
        broadcast_file_change()
        return {"code": 200, "msg": "✅ 项目手册创建成功", "path": os.path.relpath(result, REPOSITORY_PATH).replace("\\", "/")}
    return {"code": 500, "msg": result}

class ProjectManualSyncRequest(BaseModel):
    manual_path: str

@app.post("/api/project-manual/sync-detail")
async def sync_manual_detail(req: ProjectManualSyncRequest):
    """同步更新手册的明细清单（手动入口:立即执行，不走监听防抖队列）"""
    try:
        result = project_manual_manager.update_manual_detail_table(req.manual_path)
        result_code = result.get("code", 200)
        # 乐观锁冲突:AST扫描期间手册被外部手写修改，本轮已放弃，提示前端稍后重试
        if result_code == 409:
            return {"code": 409, "msg": f"⚠️ {result.get('msg', '手册在扫描期间被外部修改，本轮已放弃')}，请稍后重试", "data": result}
        # 手册在处理过程中被删除
        if result_code == 404:
            return {"code": 404, "msg": f"❌ {result.get('msg', '手册不存在')}", "data": result}
        # 管理器内部其他错误
        if result_code != 200:
            return {"code": 500, "msg": f"❌ 同步失败:{result.get('msg', '未知错误')}", "data": result}
        # 仅内容真实变化才广播SSE，无变化不打扰前端（与监听串行调度器广播条件完全对齐）
        if result.get("changed"):
            broadcast_file_change()
            return {"code": 200, "msg": "✅ 同步成功，手册内容已更新", "data": result}
        return {"code": 200, "msg": "✅ 手册内容无变化，无需更新", "data": result}
    except Exception as e:
        return {"code": 500, "msg": f"❌ 同步失败:{str(e)}"}

@app.get("/api/project-manual/backup-list")
async def get_manual_backup_list(manual_path: str):
    """获取手册的备份列表，支持回滚"""
    return {"code": 200, "data": []}
import asyncio
# ========================== 全局截图接口 ==========================
@app.post("/api/screenshot/trigger")
async def trigger_screenshot():
    """触发全局系统级截图，返回上传后的附件信息"""
    try:
        # 把阻塞的截图逻辑放到独立线程池运行，不阻塞主线程
        img = await asyncio.to_thread(screenshot_tool.capture_selection)
        if not img:
            return {"code": 400, "msg": "❌ 用户取消了截图"}
        
        # 保存到临时文件并走现有上传逻辑
        file_name = f"截图_{int(time.time())}.png"
        temp_path = os.path.join(UPLOAD_ROOT, file_name)
        img.save(temp_path, format="PNG", quality=95)
        
        # 构造和上传接口一致的返回结构
        access_url = f"/upload/{file_name}"
        file_size = os.path.getsize(temp_path)
        return {
            "code": 200,
            "msg": "✅ 截图成功",
            "data": {
                "url": access_url,
                "file_type": "image",
                "original_name": file_name,
                "ext": "png",
                "size": file_size,
                "local_path": temp_path
            }
        }
    except Exception as e:
        return {"code": 500, "msg": f"❌ 截图失败：{str(e)}"}

# -------------------------- 备份管理接口 --------------------------
class BackupRestoreRequest(BaseModel):
    backup_file_name: str
class BackupDeleteRequest(BaseModel):
    backup_file_name: str
class BackupCleanRequest(BaseModel):
    retention_days: Optional[int] = None
    max_count: Optional[int] = None

@app.get("/api/backup/list")
async def get_backup_list():
    """获取所有文件备份列表（返回平铺格式，前端自行分组，100%兼容原有逻辑）"""
    try:
        success, backup_list = intelligent_file_editor.get_backup_list()
        if not success:
            raise HTTPException(status_code=500, detail="获取备份列表失败")
        return {"code": 200, "data": backup_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取备份列表失败:{str(e)}")

@app.post("/api/backup/restore")
async def restore_backup(req: BackupRestoreRequest):
    """恢复指定备份文件到原路径"""
    try:
        success, msg = intelligent_file_editor.restore_backup(req.backup_file_name)
        if success:
            add_operation_log("备份管理", f"✅ 恢复备份成功:{req.backup_file_name}")
            # 触发文件变动广播
            broadcast_file_change()
            return {"code": 200, "msg": msg}
        else:
            add_operation_log("备份管理", f"❌ 恢复备份失败:{req.backup_file_name}，错误:{msg}", "error")
            raise HTTPException(status_code=500, detail=msg)
    except Exception as e:
        add_operation_log("备份管理", f"❌ 恢复备份异常:{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"恢复备份失败: {str(e)}")

@app.post("/api/backup/delete")
async def delete_backup(req: BackupDeleteRequest):
    """删除指定备份文件"""
    try:
        success, msg = intelligent_file_editor.delete_backup(req.backup_file_name)
        if success:
            add_operation_log("备份管理", f"✅ 删除备份成功:{req.backup_file_name}")
            return {"code": 200, "msg": msg}
        else:
            add_operation_log("备份管理", f"❌ 删除备份失败:{req.backup_file_name}，错误:{msg}", "error")
            raise HTTPException(status_code=500, detail=msg)
    except Exception as e:
        add_operation_log("备份管理", f"❌ 删除备份异常:{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"删除备份失败: {str(e)}")

@app.post("/api/backup/clean")
async def clean_expired_backup(req: BackupCleanRequest):
    """清理过期备份，按保留天数/最大数量清理"""
    try:
        success, msg, deleted_count = intelligent_file_editor.clean_expired_backup(
            retention_days=req.retention_days,
            max_count=req.max_count
        )
        if success:
            add_operation_log("备份管理", f"✅ 清理过期备份成功，共删除{deleted_count}个备份文件")
            return {"code": 200, "msg": msg, "deleted_count": deleted_count}
        else:
            add_operation_log("备份管理", f"❌ 清理过期备份失败，错误:{msg}", "error")
            raise HTTPException(status_code=500, detail=msg)
    except Exception as e:
        add_operation_log("备份管理", f"❌ 清理过期备份异常:{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"清理备份失败: {str(e)}")

@app.post("/api/backup/full")
async def full_backup():
    """全量备份所有项目文件（当前选中项目/全仓库）"""
    try:
        # 判断备份范围:有选中项目则备份当前项目，否则备份整个仓库
        if CURRENT_PROJECT["project_root"]:
            root_path = CURRENT_PROJECT["project_root"]
            backup_scope = f"当前项目【{CURRENT_PROJECT['project_name']}】"
        else:
            root_path = REPOSITORY_PATH
            backup_scope = "整个仓库"
        
        # 过滤不需要备份的目录:复用统一噪音目录黑名单（.venv/venv/env/dist/build/.git/缓存等），
        # 另加备份场景特有排除"上传文件夹"（用户上传的原始附件不纳入代码备份）；
        # 剪枝后不再遍历 dist/.venv 等数万文件，备份速度大幅提升
        filter_dirs = set(file_filter_config.EXCLUDE_DIR_NAMES) | {"上传文件夹"}
        # 二进制/大文件后缀黑名单（图片、视频、音频、压缩包、模型、临时文件）
        blacklist_exts = {".tmp", ".log", ".pyc", ".zip", ".rar", ".7z", ".gz", ".tar", ".gguf", ".bin",
                          ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico",
                          ".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm",
                          ".mp3", ".wav", ".flac", ".aac", ".ogg",
                          ".exe", ".dll", ".so", ".dylib", ".iso", ".dmg", ".pkg",
                          ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}
        MAX_BACKUP_FILE_SIZE = 20 * 1024 * 1024  # 单文件最大备份20MB，超过自动跳过
        
        success_count = 0
        fail_count = 0
        skip_count = 0
        # 递归遍历所有文件
        for root, dirs, files in os.walk(root_path):
            # 过滤排除目录（修改dirs本身实现剪枝，不遍历子目录）
            dirs[:] = [d for d in dirs if d not in filter_dirs]
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                file_path = os.path.join(root, file)
                # 跳过文件夹
                if not os.path.isfile(file_path):
                    continue
                # 规则1:后缀在黑名单内直接跳过
                if ext in blacklist_exts:
                    skip_count +=1
                    continue
                # 规则2:仅备份支持编辑的文本/代码文件，彻底排除二进制文件
                if ext not in SUPPORTED_FILE_TYPES:
                    skip_count +=1
                    continue
                # 规则3:超过10MB的大文件自动跳过
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size > MAX_BACKUP_FILE_SIZE:
                        skip_count +=1
                        continue
                except Exception:
                    skip_count +=1
                    continue
                try:
                    # 调用智能文件编辑器的公开备份方法
                    success, _ = intelligent_file_editor.backup_single_file(file_path)
                    if success:
                        success_count += 1
                    else:
                        fail_count += 1
                except Exception:
                    fail_count += 1
                    continue
        
        log_content = f"✅ 全量备份完成，范围:{backup_scope}，成功备份{success_count}个文件，失败{fail_count}个，跳过{skip_count}个非文本/大文件"
        add_operation_log("备份管理", log_content)
        return {
            "code": 200,
            "msg": log_content,
            "success_count": success_count,
            "fail_count": fail_count,
            "skip_count": skip_count
        }
    except Exception as e:
        err_msg = f"❌ 全量备份异常:{str(e)}"
        add_operation_log("备份管理", err_msg, "error")
        raise HTTPException(status_code=500, detail=err_msg)
# -------------------------- 操作日志接口 --------------------------
@app.get("/api/log/list")
async def get_operation_log(keyword: str = "", page: int = 1, page_size: int = 50, last_id: int = 0):
    """分页获取操作日志列表，支持关键词搜索、增量拉取"""
    global OPERATION_LOGS
    filtered = OPERATION_LOGS
    if keyword:
        filtered = [log for log in OPERATION_LOGS if keyword in log["content"] or keyword in log["oper_type"]]
    
    # 增量拉取逻辑：返回ID大于last_id的所有新日志
    if last_id > 0:
        filtered = [log for log in filtered if log["id"] > last_id]
        # 增量拉取不需要分页，最多返回100条
        return {
            "code": 200, 
            "data": {
                "list": filtered[:page_size], 
                "total": len(filtered), 
                "page": 1, 
                "page_size": page_size
            }
        }
    
    # 全量分页逻辑
    total = len(filtered)
    start = (page-1)*page_size
    end = start + page_size
    return {
        "code": 200, 
        "data": {
            "list": filtered[start:end], 
            "total": total, 
            "page": page, 
            "page_size": page_size
        }
    }

# 删除记忆接口（FastAPI语法修正+同步清理上下文缓存+向量索引清理）
@app.post('/api/memory/delete')
async def delete_memory(data: dict):
    memory_id = str(data.get('id'))
    # 兼容路径:同时查找_internal目录和exe同级目录，优先使用存在的记忆文件
    if getattr(_sys, 'frozen', False):
        candidate_paths = [
            os.path.join(BASE_DIR, "memory_meta.json"),
            os.path.join(_exe_dir, "memory_meta.json")
        ]
        MEMORY_FILE_PATH = next((p for p in candidate_paths if os.path.exists(p)), candidate_paths[0])
    else:
        MEMORY_FILE_PATH = os.path.join(BASE_DIR, "memory_meta.json")
    
    with open(MEMORY_FILE_PATH, 'r', encoding='utf-8') as f:
        memories_old = json.load(f)
    memories = memories_old.copy()
    
    # 字典结构直接删除对应key，无则忽略
    deleted_content = None
    deleted_memory = None
    mem_project = "default"
    if memory_id in memories:
        deleted_content = memories[memory_id]['content']
        deleted_memory = memories_old[memory_id]
        # 提取记忆所属的项目标签
        mem_tags = memories[memory_id].get("tags", [])
        for tag in mem_tags:
            if tag.startswith("project:"):
                mem_project = tag.split(":", 1)[1]
                break
        del memories[memory_id]
    
    # 保存长期记忆库回文件
    with open(MEMORY_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)
    
    # 【关键修复】同步更新memory_cache内存缓存，避免重建索引使用旧数据
    if memory_id in memory_cache.meta:
        del memory_cache.meta[memory_id]
    
    # 同步清理对应项目的上下文缓存文件，避免已删除内容重新入库
    if deleted_content:
        # 清理记忆所属项目的独立历史文件
        safe_project_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5_-]', "_", mem_project)
        project_history_file = os.path.join(BASE_DIR, f"latest_chat_history_{safe_project_name}.json")
        # 兼容存量default全局历史文件
        default_history_file = os.path.join(BASE_DIR, "latest_chat_history.json")
        # 遍历两个文件执行清理
        for history_file in [project_history_file, default_history_file]:
            try:
                if os.path.exists(history_file):
                    with open(history_file, 'r', encoding='utf-8') as f:
                        chat_history = json.load(f)
                    # 仅按timestamp匹配删除同一条对话生成的项目记忆，匹配timestamp或timestamp+1
                    deleted_timestamp = deleted_memory.get("timestamp", 0)
                    chat_history = [item for item in chat_history if item.get("timestamp", -1) not in [deleted_timestamp, deleted_timestamp + 1]]
                    # 写回上下文缓存
                    with open(history_file, 'w', encoding='utf-8') as f:
                        json.dump(chat_history, f, ensure_ascii=False, indent=2)
            except Exception as e:
                # 文件不存在/读取/写入失败直接跳过，不影响主删除逻辑
                pass
    
    # 【正确重建记忆向量索引】彻底对齐最新记忆库，无任何残留
    import asyncio
    asyncio.create_task(asyncio.to_thread(memory_cache.build_full_vector_index))
    print("✅ 记忆删除完成，已触发记忆向量索引全量重建")
    
    return {'code': 200, 'msg': '记忆已成功删除，上下文缓存&向量索引已同步清理'}

@app.post("/api/log/clear")
async def clear_operation_log():
    """清空所有操作日志"""
    global OPERATION_LOGS
    OPERATION_LOGS = []
    add_operation_log("日志管理", "清空所有操作日志")
    return {"code": 200, "msg": "✅ 所有操作日志已清空"}

# 通用工具接口
class ChineseToPinyinRequest(BaseModel):
    text: str

@app.post("/api/utils/chinese_to_pinyin")
async def chinese_to_pinyin(req: ChineseToPinyinRequest):
    """中文转拼音，返回全小写、下划线连接的合规ID格式"""
    if not req.text.strip():
        return {"code": 200, "data": ""}
    # 转拼音，不带声调
    pinyin_list = pinyin(req.text, style=Style.NORMAL, errors='default')
    # 拼合为字符串
    pinyin_str = '_'.join([item[0] for item in pinyin_list])
    # 过滤非法字符，替换为下划线，合并连续下划线
    result = re.sub(r'[^a-z0-9_]', '_', pinyin_str.lower())
    result = re.sub(r'_+', '_', result).strip('_')
    return {"code": 200, "data": result}
def select_path_dialog(select_dir: bool = False) -> str:
    """弹出系统原生文件/文件夹选择对话框，返回选中的绝对路径，取消则返回空字符串"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        # 隐藏主窗口
        root = tk.Tk()
        root.withdraw()
        # 置顶显示，避免被其他窗口遮挡
        root.attributes('-topmost', True)
        if select_dir:
            path = filedialog.askdirectory(title="选择要禁止操作的文件夹")
        else:
            path = filedialog.askopenfilename(title="选择要禁止操作的文件")
        root.destroy()
        return os.path.normpath(path) if path else ""
    except Exception as e:
        print(f"文件选择对话框调用失败（可能无图形界面）:{str(e)}")
        return ""

class SelectPathRequest(BaseModel):
    select_dir: bool = False # 是否选择文件夹，false为选择文件

@app.post("/api/utils/select_path")
async def select_path(req: SelectPathRequest):
    """调用系统原生选择框选择文件/文件夹，返回绝对路径，无图形界面环境可手动输入路径"""
    try:
        path = await asyncio.to_thread(select_path_dialog, req.select_dir)
        if not path:
            return {"code": 200, "data": "", "msg": "用户取消选择或无图形界面"}
        return {"code": 200, "data": path, "msg": "选择成功"}
    except Exception as e:
        return {"code": 500, "msg": f"打开选择框失败:{str(e)}"}
# API服务启动函数
def start_api_server(port=8000):
    """子线程启动API服务，支持外部指定端口，未指定则默认8000"""
    # 提前校验端口可用性，被占用则自动顺延，避免子线程内nonlocal变量兼容问题
    if is_port_used(port):
        port = get_available_port()
    use_port = port
    
    def run_server():
        # global变量声明必须放在函数最顶部，符合Python语法规范
        global global_event_loop
        # 移除子线程中提前设置global_event_loop的逻辑，完全由chat_stream在uvicorn实际运行的事件循环中设置
        # 确保push_sse_message中的asyncio.run_coroutine_threadsafe将消息提交到运行中的事件循环，前端100%能收到消息
        try:
            # 端口已提前校验可用
            print(f"✅ API服务启动成功，访问地址:http://127.0.0.1:{use_port}")
            print(f"📖 接口调试文档：http://127.0.0.1:{use_port}/docs")
            uvicorn.run(
                app,
                host="0.0.0.0", # 兼容localhost和127.0.0.1访问
                port=use_port,
                log_level="error"
            )
        except Exception as e:
            print(f"❌ API服务启动失败: {str(e)}")
            # 打印详细错误栈，方便定位问题
            import traceback
            traceback.print_exc()
    
    # 子线程启动，不阻塞主程序
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    # 启动定时清理任务，每小时清理过期会话和无效SSE连接
    def clean_expired_data():
        while True:
            try:
                current_time = time.time()
                # 清理超过24小时未活动的会话
                expired_sessions = [sid for sid in list(session_context.keys()) 
                                   if current_time - session_context[sid].get("last_active", current_time) > 24*3600]
                for sid in expired_sessions:
                    del session_context[sid]
                    if sid in SSE_CONNECTIONS:
                        del SSE_CONNECTIONS[sid]
                # 清理FILE_CHANGE_CONNECTIONS里的无效队列
                invalid_queues = []
                for q in FILE_CHANGE_CONNECTIONS:
                    if getattr(q, '_closed', False):
                        invalid_queues.append(q)
                for q in invalid_queues:
                    FILE_CHANGE_CONNECTIONS.remove(q)
                print(f"✅ 定时清理完成：删除{len(expired_sessions)}个过期会话，{len(invalid_queues)}个无效SSE连接")
            except Exception as e:
                print(f"⚠️ 定时清理任务异常：{str(e)}")
            # 每小时执行一次
            time.sleep(3600)
    threading.Thread(target=clean_expired_data, daemon=True).start()
    
    # 新增：启动后后台异步更新所有项目手册，不阻塞启动
    def update_all_manuals_async():
        time.sleep(3) # 延迟3秒启动，等服务完全就绪
        try:
            print("🔄 后台开始更新所有项目手册...")
            # 遍历所有项目手册
            for root, dirs, files in os.walk(REPOSITORY_PATH):
                # 剪枝:排除虚拟环境/.git/打包产物等噪音目录，避免遍历数万依赖文件
                file_filter_config.prune_walk_dirs(dirs)
                for file in files:
                    if file.endswith("项目手册.md"):
                        try:
                            # 计算相对路径
                            rel_manual_dir = os.path.relpath(root, REPOSITORY_PATH)
                            manual_path = os.path.join(rel_manual_dir, file).replace("\\", "/")
                            # 更新手册明细
                            project_manual_manager.update_manual_detail_table(manual_path)
                            print(f"✅ 已更新手册：{manual_path}")
                        except Exception as e:
                            print(f"⚠️ 更新手册{file}失败：{str(e)}")
                            continue
            print("✅ 所有项目手册更新完成")
        except Exception as e:
            print(f"❌ 批量更新手册异常：{str(e)}")
    # 启动后台线程
    threading.Thread(target=update_all_manuals_async, daemon=True).start()
    # 启动定时任务调度器
    def start_scheduler():
        time.sleep(5)  # 延迟5秒启动，等服务完全就绪
        try:
            # 动态注入当前服务端口到调度器，避免硬编码导致跨工作台误触发
            scheduler_manager.set_server_port(use_port)
            scheduler_manager.start()
            print(f"✅ 定时任务调度器已启动，监听端口:{use_port}")
        except Exception as e:
            print(f"❌ 启动定时任务调度器失败:{str(e)}")
    threading.Thread(target=start_scheduler, daemon=True).start()
    
    # 启动进程监控插件
    def start_process_monitor():
        time.sleep(6)  # 延迟6秒启动，确保调度器已启动
        try:
            # 动态注入当前服务端口到进程监控插件，避免硬编码
            import importlib.util
            import sys
            plugin_path = os.path.join(BASE_DIR, "plugins", "process_monitor", "main.py")
            if os.path.exists(plugin_path):
                spec = importlib.util.spec_from_file_location("plugin_process_monitor", plugin_path)
                plugin_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(plugin_module)
                # 直接实例化并注入端口，避免run()函数提前启动监控线程导致端口未注入
                monitor = plugin_module.ProcessMonitor()
                monitor.set_server_port(use_port)
                monitor.start()
                print(f"✅ 进程监控插件已启动，监听端口:{use_port}")
        except Exception as e:
            print(f"❌ 启动进程监控插件失败:{str(e)}")
    threading.Thread(target=start_process_monitor, daemon=True).start()
    
    return use_port

if __name__ == "__main__":
    start_api_server()
    input("按任意键停止服务...")