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
# 项目信息隔离管理模块:用户在文件仓库右键"加入项目信息隔离"后，
# 被隔离路径及其全部子孙不再进入 AI 上下文/项目手册第二三章/RAG索引，根治运行期临时文件导致的信息膨胀
import isolation_manager
# 启动即把磁盘上的隔离清单注入统一过滤模块（内存态），
# 保证所有扫盘链路（AI上下文注入/项目手册同步/RAG索引）在首次调用前即已生效
try:
    isolation_manager.refresh_injection()
except Exception as _iso_err:
    print(f"⚠️ 项目信息隔离清单启动注入失败:{_iso_err}")
# 长命令后台任务机制 P0:进程树命令执行器（根治Windows下subprocess.run超时只杀cmd.exe、
# 孙进程持管道导致communicate永久阻塞，以及pause/set /p无控制台输入挂死）
import command_runner

# 全局配置，基于当前脚本路径生成绝对路径，避免工作目录错误导致找不到资源
# 长命令后台任务机制 P1:后台任务管理器（超时不杀转后台、完成跨轮回灌、query/cancel）
import background_task_manager
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

# 9 槽位模型配置统一落位:与 config.json 同目录（开发环境=项目根，打包后=exe 同级），
# 复用 CONFIG_PATH 已解析好的目录，避免打包环境下两处路径口径分叉
MODELS_CONFIG_PATH = os.path.join(os.path.dirname(CONFIG_PATH), "models_config.json")


def _atomic_write_json(path: str, data, indent: int = 4):
    """原子写入JSON文件:先写同目录临时文件再os.replace替换，避免写入过程中崩溃/断电导致原文件被截断为空"""
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


DEFAULT_PORT = 8000
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

def get_default_repository_path() -> str:
    """获取默认仓库路径
    Windows版统一使用D盘根目录下的AI仓库文件夹（避免首次安装默认建到C盘用户文档目录、占用系统盘空间）；
    Mac/Linux无盘符概念，沿用当前用户文档目录下的AI仓库文件夹（该目录在任何系统下均存在）
    """
    if platform.system() == "Windows":
        # Windows安装版默认仓库固定到D盘根目录，路径统一使用/分隔符
        default_path = "D:/AI仓库文件夹"
    else:
        default_path = os.path.join(os.path.expanduser("~"), "Documents", "AI仓库文件夹")
    return os.path.normpath(default_path).replace("\\", "/")

# 全局仓库路径（动态从配置读取，支持自定义）
REPOSITORY_PATH = ""

# 全局最近N轮对话持久化文件，按项目隔离存储
# 该文件同时承担「次级 @主控 的内容落点」:由 append_main_context 追加，主控下轮 load_global_history 读取
def get_project_history_file():
    """获取当前项目对应的历史存储文件路径（主控上下文 + 次级 @主控 通知共用）"""
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
        # 单模型时代的 model_provider/api_url/model_name/api_key/timeout/stream_output/temperature
        # 已全部迁入 models_config.json 的 9 槽位，此处不再保留（并由下方 deprecated 列表主动清理老配置回写）
        "download_path": os.path.join(os.path.expanduser("~"), "Downloads"),
        "max_parse_fail_count": 3, # 单个文件解析失败最多重试次数，超过后24小时内自动跳过
        "repository_path": get_default_repository_path(), # 默认仓库路径
        "rag_max_file_size_kb": 512,
        "rag_cpu_threads": 0,
        "max_chat_rounds": 15, # 每轮回复最大次数（安全上限，防止无限循环），AI完成任务后自动停止
        "forbidden_paths": _default_forbidden_paths, # 默认禁止路径列表，根据操作系统动态生成，用户可自由增删
        "show_debug_console": False, # 默认隐藏后端调试控制台，用户可在设置页手动开启
        "theme_primary_color": "#165DFF", # 界面主题主色（前端各页+Qt外壳统一生效，配置页可视化编辑）
        "theme_bg_page": "#F5F7FA", # 界面底色（页面框架底色，与主色独立设置，配置页可视化编辑）
        "theme_bg_card": "#FFFFFF", # 卡片底色（卡片/容器底色，与主色独立设置，配置页可视化编辑）
        # ===== AI思考模式开关（三个页面各自独立持久化，互不同步、互不覆盖）=====
        # show_think_mode       :主对话页（PageO0x2f.vue 的普通实例）
        # show_think_mode_float :悬浮窗（PageO0x2f.vue 的 ?mode=float 实例，与主对话页同文件、靠 isFloat 分流）
        # show_think_mode_dev   :次级开发页（1.vue）
        # 兜底策略:老用户 config.json 缺上述字段时，load_config 会自动补 True（等价改造前的"默认开启"行为，无感升级）
        "show_think_mode": True,
        "show_think_mode_float": True,
        "show_think_mode_dev": True,
        "system": {
            "project_root_absolute_path": BASE_DIR,
            "tos_endpoint": "https://tos-cn-beijing.volces.com",
            "tos_bucket": "",
            "tos_ak": "",
            "tos_sk": ""
        },
        # 工具输出截断/落盘/跨轮老化配置（P0-1/P0-5），用户config.json缺失时自动补全
        "tool_output": {
            "truncate_enabled": True,        # 总开关
            "head_chars": 24000,             # 头部保留字符数
            "tail_chars": 8000,              # 尾部保留字符数
            "trigger_chars": 60000,          # 超过此字符数才触发截断
            "save_to_disk": True,            # 完整结果是否落盘
            "output_dir_name": "tool_outputs", # 落盘目录名（打包时exe同级）
            "max_saved_files": 50,          # 落盘文件最多保留个数
            "exec_cmd_timeout": 60,          # exec_cmd超时秒数
            "aging_enabled": True,           # 跨轮老化总开关
            "aging_keep_rounds": 4,          # 保护代数:最近N代工具结果完整保留
            "aging_trigger_chars": 120000,    # messages总字符超此值才触发老化
            "aging_max_per_round": 3         # 单轮最多归档条数
        }
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            # 清理历史遗留的废弃配置项（本地模型相关，已全面切换云端）
            # 补充:单模型时代的模型字段已迁入 models_config.json 9 槽位，此处主动清理防止老 config.json 回写复活
            for deprecated_key in [
                "model_repo_path", "default_local_model",
                "model_provider", "api_url", "model_name", "api_key",
                "timeout", "stream_output", "temperature", "lastCloudProvider",
            ]:
                if deprecated_key in user_config:
                    del user_config[deprecated_key]
            # 合并用户配置，缺失字段自动补全默认值
            for key, value in default_config.items():
                if key not in user_config:
                    user_config[key] = value
            # 首次启动/版本升级时自动补全缺失的默认禁止路径，不覆盖用户已有配置
            if "forbidden_paths" not in user_config:
                user_config["forbidden_paths"] = default_config["forbidden_paths"]
            # 配置项缺失或为空串时均自动补全默认仓库路径（Windows为D:/AI仓库文件夹），空串不处理会被解析为当前工作目录
            if not user_config.get("repository_path"):
                user_config["repository_path"] = default_config["repository_path"]
            # 自动保存补全后的配置（原子写入，避免崩溃/断电把配置文件截断为空）
            _atomic_write_json(CONFIG_PATH, user_config)
            return user_config
        except Exception as e:
            print(f"⚠️ 配置文件加载失败，使用默认配置:{str(e)}")
            return default_config
    # 配置文件不存在，创建默认配置（原子写入）
    _atomic_write_json(CONFIG_PATH, default_config)
    return default_config

def save_config(config: Dict):
    # 1. 主写入:EXE同级目录config.json（用户配置主文件，升级不丢失，原子写入防截断）
    _atomic_write_json(CONFIG_PATH, config)
    
    # 2. 同步写入:打包环境下同步写入_internal目录下的config.json，兼容旧模块读取路径
    if getattr(_sys, 'frozen', False):
        try:
            internal_config_path = os.path.join(_internal_dir, "config.json")
            _atomic_write_json(internal_config_path, config)
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


# ==================== 9 槽位模型配置模块（阶段 2 新增） ====================
# 用途:9 个模型槽位（模型1~模型9）的读写与密钥脱敏，字段与前端 9 个模型配置页一一对应。
# 设计要点:
#   1. 单一数据源:所有读写均走 MODELS_CONFIG_PATH（与 CONFIG_PATH 同级同规则）；
#   2. 自动补全:文件缺失自动生成 9 槽默认结构；已有文件缺槽自动补齐（用户零操作）；
#   3. 密钥脱敏:对外 list 接口返回脱敏值（保留前 4 位 + ****），内部 get 接口返回明文；
#   4. 空值不回写:save 时若密钥为空或脱敏形态，保留原值不覆盖（防止"只改温度丢密钥"）。

# 单个槽位字段定义（键名与前端 9 个配置页控件一一对应）
_MODEL_SLOT_FIELDS = {
    "display_name": "",       # 槽位别名（前端展示用）
    "api_url": "",            # API地址
    "model_name": "",         # 模型ID
    "api_key": "",            # API-keys（落盘明文，接口返回时脱敏）
    "timeout": 200,           # 请求超时（秒）
    "temperature": 0.5,       # 温度参数
    "max_tokens": 0,          # 单次输出上限（0=自动，调用时不发送该参数，自动使用模型上限）
    "max_reply_rounds": 20,   # 每轮回复次数上限（承接旧界面「回复上限」的循环次数语义）
    "max_chat_rounds": 10,    # 上下文轮数
    "enabled_plugins": [],    # 已启用插件ID列表（空数组=全量注入，向后兼容）
    "stream_output": True,    # 输出模式（流式开关）
    "persona_name": "",       # 人设名称
    "persona_prompt": "",     # 人设提示词
    "fixed_prompt_1": "",     # 固定提示1
    "fixed_prompt_2": "",     # 固定提示2
    "fixed_prompt_3": "",     # 固定提示3
}


def _default_model_slot(slot: int) -> Dict:
    """生成单个槽位的默认配置（每次新建对象，避免多槽位共享同一引用）"""
    item = {"slot": int(slot)}
    item.update(_MODEL_SLOT_FIELDS)
    return item


def _load_models_config() -> Dict:
    """读取 9 槽位模型配置:文件缺失/损坏自动重建，缺槽自动补齐后回写，保证始终 9 槽齐全"""
    raw: Dict[str, Any] = {}
    # 首次启动:exe 同级无 models_config.json 时，从 _internal 的脱敏模板复制生成（预置 9 槽位人设/固定提示，用户只需填 API Key）
    if not os.path.exists(MODELS_CONFIG_PATH) and getattr(_sys, 'frozen', False):
        try:
            import shutil
            _tpl = os.path.join(os.path.dirname(MODELS_CONFIG_PATH), "_internal", "models_config.example.json")
            if os.path.exists(_tpl):
                shutil.copy2(_tpl, MODELS_CONFIG_PATH)
                print(f"[api_server] 首次启动自动从模板生成 models_config.json: {MODELS_CONFIG_PATH}")
        except Exception as e:
            print(f"[api_server] 复制 models_config 模板失败（不影响空壳兜底）: {e}")
    if os.path.exists(MODELS_CONFIG_PATH):
        try:
            with open(MODELS_CONFIG_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f) or {}
        except Exception as e:
            print(f"⚠️ models_config.json 解析失败，将重建默认结构: {e}")
            raw = {}
    models = raw.get("models", [])
    if not isinstance(models, list):
        models = []
    # 按 slot 号建索引，保留用户已填内容
    by_slot: Dict[int, Dict] = {}
    for item in models:
        if isinstance(item, dict):
            try:
                by_slot[int(item.get("slot"))] = item
            except (TypeError, ValueError):
                continue
    # 1~9 逐一补齐（缺槽用默认值；已有槽位缺字段也补齐）
    merged: List[Dict] = []
    for s in range(1, 10):
        base = by_slot.get(s) or _default_model_slot(s)
        for k, v in _MODEL_SLOT_FIELDS.items():
            base.setdefault(k, v)
        base["slot"] = s
        if not base.get("display_name"):
            base["display_name"] = f"模型{s}"
        merged.append(base)
    # 透传 runtime 节（读写全量往返不得丢失；缺失/损坏用出厂默认兜底，与 model_registry.get_runtime 一致）
    runtime = raw.get("runtime")
    if not isinstance(runtime, dict):
        runtime = {}
    runtime.setdefault("max_concurrency", 3)
    runtime.setdefault("retry", 1)
    result = {"version": raw.get("version", 1), "runtime": runtime, "models": merged}
    # 首次生成 / 槽位数不齐时回写，保持磁盘状态与内存一致
    if (not os.path.exists(MODELS_CONFIG_PATH)) or (len(models) != len(merged)):
        try:
            _atomic_write_json(MODELS_CONFIG_PATH, result)
        except Exception as e:
            print(f"⚠️ models_config.json 回写失败（不影响本次读取）: {e}")
    return result


def _save_models_config(data: Dict) -> None:
    """写盘 9 槽位模型配置（复用 _atomic_write_json，避免写入中断导致文件被截断）"""
    _atomic_write_json(MODELS_CONFIG_PATH, data)


def _mask_api_key(key: Any) -> str:
    """密钥脱敏:长度 <8 返回 ****；否则保留前 4 位 + ****（列表页展示用）"""
    if not key or not isinstance(key, str):
        return ""
    if len(key) < 8:
        return "****"
    return key[:4] + "****"


def _is_masked_or_empty(key: Any) -> bool:
    """判断密钥是否为「空值 / 脱敏形态」—— 是则保存时保留原值不覆盖（防误清空）"""
    if key is None or not isinstance(key, str):
        return True
    if key.strip() == "":
        return True
    if key.endswith("****"):
        return True
    return False


# ==================== 9 槽位模型配置模块结束 ====================

# 初始化仓库路径:从配置读取，自动创建不存在的目录
def init_repository_path():
    global REPOSITORY_PATH
    config = load_config()
    # 配置缺失/为空串时兜底默认仓库路径（Windows为D:/AI仓库文件夹），避免空串被解析为当前工作目录
    repo_path = config.get("repository_path") or get_default_repository_path()
    # 标准化路径格式
    REPOSITORY_PATH = os.path.normpath(repo_path).replace("\\", "/")
    # 盘符存在性校验:路径盘符不存在（如虚拟机无D盘）时回退到用户文档目录，避免模块顶层初始化崩溃
    if os.name == "nt" and len(REPOSITORY_PATH) >= 2 and REPOSITORY_PATH[1] == ":":
        if not os.path.exists(REPOSITORY_PATH[:2] + "/"):
            _fallback_repo = os.path.join(os.path.expanduser("~"), "Documents", "AI仓库文件夹")
            print(f"⚠️ 仓库路径盘符 {REPOSITORY_PATH[:2]} 不存在，自动回退到:{_fallback_repo}")
            REPOSITORY_PATH = os.path.normpath(_fallback_repo).replace("\\", "/")
    # 自动创建仓库目录（创建失败时兜底回退，避免异常中断模块顶层初始化导致启动中止）
    if not os.path.exists(REPOSITORY_PATH):
        try:
            os.makedirs(REPOSITORY_PATH, exist_ok=True)
            print(f"✅ 自动创建仓库目录:{REPOSITORY_PATH}")
        except OSError as e:
            _fallback_repo = os.path.join(os.path.expanduser("~"), "Documents", "AI仓库文件夹")
            print(f"⚠️ 创建仓库目录失败({e})，已回退到:{_fallback_repo}")
            REPOSITORY_PATH = os.path.normpath(_fallback_repo).replace("\\", "/")
            os.makedirs(REPOSITORY_PATH, exist_ok=True)
            print(f"✅ 已创建回退仓库目录:{REPOSITORY_PATH}")

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

# 次级模型 @主控 → 投递主控上下文（真送达主模型，而非只到前端）
# 由 orchestrator 通过 set_main_injector 注入后回调调用（不反向 import，杜绝循环依赖）
def append_main_context(text: str, sender: str = "") -> None:
    """把次级消息追加到「当前项目」历史文件，主控下轮 load_global_history 即可读到"""
    body = str(text or "").strip()
    if not body:
        return
    history_file = get_project_history_file()
    try:
        history = []
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        if not isinstance(history, list):
            history = []
    except (json.JSONDecodeError, OSError, IOError):
        history = []
    sender_tag = f"来自{sender}|" if sender else ""
    history.append({
        "content": f"【{sender_tag}次级消息】{body}",
        "timestamp": int(time.time() * 1000),
    })
    try:
        rounds = memory_cache.config["history_context_rounds"]
    except Exception:
        rounds = 20
    if len(history) > rounds:
        history = history[-rounds:]
    try:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"[AI] 追加主控上下文失败: {e}")

# ========== 次级 @主控 唤醒主控模型（2026-10-13 新增；S1 走 /api/chat 主链路自调用）==========
# 模块级端口变量:由 start_api_server 在运行时确定 use_port 后写入，供 wake_main 读取（不硬编码端口）
_SERVER_PORT: int = 0


def wake_main(text: str, sender: str = "", task_id: str = "") -> None:
    """次级 @主控 → 唤醒主控模型跑一轮（把回报作为"一条用户提交"打进 /api/chat 主链路）

    - 复用 scheduler_manager 现成 HTTP 自调用范式（同 /api/chat 自调用写法，端口动态读取）;
    - 上下文与人手对话天然同源: /api/chat 内部走 load_global_history + 全链路装配，
      且 append_main_context 已把本回报写入同一历史文件 → 主控看到的视图与人手一致;
    - session_id 用主会话 "default"（与前端主控页一致，前端能在主控页看到唤醒交互）;
    - 无兜底: 调用失败仅打印，不重试、不降级（按用户口径:测试期能立刻发现链路断开）;
    - 来源标识: 保持现状 header 口径 "[来自{sender}|任务 #{task_id}]"，拼在 query 前，
      不新增字段、不改存历史逻辑（零侵入）。
    """
    body = str(text or "").strip()
    if not body:
        return
    port = int(_SERVER_PORT or 0)
    if port <= 0:
        print("[Wake] 唤醒主控失败:端口未注入（服务尚未启动?）")
        return
    header = f"[来自{sender}|任务 #{task_id}]" if (sender or task_id) else ""
    query = f"{header}\n\n{body}" if header else body
    try:
        import httpx
        httpx.post(
            f"http://127.0.0.1:{port}/api/chat",
            json={
                "query": query,
                "session_id": "default",
                "attachments": [],
            },
            timeout=300,
        )
    except Exception as e:
        print(f"[Wake] 唤醒主控失败: {e}")

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
    version="1.1.0",
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
    # 工具完整输出落盘目录永远放行（frozen时在exe同级、开发时在BASE_DIR，与save_full_tool_output路径一致）
    try:
        _to_dir_name = (load_config().get("tool_output") or {}).get("output_dir_name") or "tool_outputs"
    except Exception:
        _to_dir_name = "tool_outputs"
    _to_base = os.path.dirname(_sys.executable) if getattr(_sys, "frozen", False) else BASE_DIR
    whitelist.append(os.path.normpath(os.path.join(_to_base, _to_dir_name)))
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

# 阶段1（前端重构 · 决策C① · 步骤1.6）:新前端 AI-GZT-v2 静态产物挂载为 /webapp
#  —— 与上方 /upload 及下方全部旧页面路由【并存】，旧功能一行不动、零影响；
#  —— html=True:访问 /webapp 或子目录时自动返回 index.html（SPA 入口）；
#  —— 前端路由已改 Hash 模式（createWebHashHistory），# 之后不发给服务端，无需额外 catch-all 回退；
#  —— os.path.isdir 保护:前端尚未执行 npm run build（dist 不存在）时不挂载，
#     避免 StaticFiles 指向不存在的目录导致启动报错，旧页面照常可用。
_WEBAPP_DIST_DIR = os.path.join(BASE_DIR, "AI-GZT-v2", "dist")
if os.path.isdir(_WEBAPP_DIST_DIR):
    app.mount("/webapp", StaticFiles(directory=_WEBAPP_DIST_DIR, html=True), name="webapp")
    print(f"✅ 新前端已挂载:http://127.0.0.1:<端口>/webapp  ->  {_WEBAPP_DIST_DIR}")
else:
    print(f"ℹ️ 新前端产物不存在（{_WEBAPP_DIST_DIR}），/webapp 暂未挂载；"
          f"请先在 AI-GZT-v2 目录执行 npm install && npm run build")

# 修复方案A（头像接入 · 2026-10-13）:补挂 /assets 静态路由，解决「头像/图标 404 → 显示 alt 文字」
#  —— 根因:前端 8 个次级对话页（1.vue ~ 7-2.vue）与主对话页 PageO0x2f.vue 的
#     头像/图标均使用【绝对路径】/assets/xxx（如 /assets/avatars/model_2.png、
#     /assets/icons/logo.png），而 vite base:'./' 只重写相对路径引用、【不重写绝对路径】
#     → 构建产物里仍是 /assets/...；但整个新前端挂在 /webapp 子路径下
#     → 浏览器请求漏掉 /webapp 前缀 → 404 → <img> 加载失败 → 渲染 alt="AI" 文字
#     （即"看起来还是原来的 AI 文字徽标"现象的成因）。
#  —— 方案:将 /assets 直接映射到 dist/assets，1 处改动同时覆盖
#     8 个次级页头像 + 主对话页 + 悬浮窗 + 主控图标兜底。
#  —— 保护:os.path.isdir 判断，dist 不存在时不挂载，避免 StaticFiles 指向不存在目录导致启动报错。
#  —— 兼容:与 /webapp、/static、/upload 挂载并存，互不冲突（/webapp/assets/... 仍可访问）。
_WEBAPP_ASSETS_DIR = os.path.join(_WEBAPP_DIST_DIR, "assets")
if os.path.isdir(_WEBAPP_ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=_WEBAPP_ASSETS_DIR), name="webapp_assets")
    print(f"✅ 前端 absolute 资源已挂载:/assets  ->  {_WEBAPP_ASSETS_DIR}")

@app.get("/logo.png", include_in_schema=False)
async def get_logo():
    return FileResponse(os.path.join(BASE_DIR, "logo.png"))

# 统一入口重定向，所有访问默认跳转到新前端（AI-GZT-v2 构建产物）
@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/webapp/")

@app.get("/chat", include_in_schema=False)
async def redirect_chat():
    return RedirectResponse(url="/webapp/")

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
    """兼容OpenAI模型列表接口
    模型名统一取自 models_config.json 槽位1（与 /api/models/* 唯一数据源一致）；
    单模型时代的 config["model_name"] 已废弃，避免删字段后 KeyError
    """
    _models = _load_models_config().get("models", []) or []
    _slot1 = next((m for m in _models if int(m.get("slot", 0) or 0) == 1), None)
    if _slot1 is None and _models:
        _slot1 = _models[0]
    _model_name = str((_slot1 or {}).get("model_name", "") or "unknown")
    return {
        "object": "list",
        "data": [
            {
                "id": _model_name,
                "object": "model",
                "created": 1677610605,
                "owned_by": "openai",
                "permission": [],
                "root": _model_name,
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
# 导入符号定位器（AST 静态解析:符号名 -> 文件+行号+签名+源码）
import ast_symbol_index
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

# 全局SSE流式推送连接存储:key=session_id，value=该会话所有窗口的队列集合（订阅池），实现显示与推理解耦 + 多窗实时同达
SSE_CONNECTIONS = {}

def _strip_naked_tool_json(text: str) -> str:
    """【M1·根因修复】剥离"无标记包裹的裸工具调用对象"文本块。

    背景:工具/插件模板会以「双下划线模板版本字段 + name + parameters」这种
    无中文标记的裸对象形态出现在模型输出里；现有净化只认「工具调用开始…结束」
    中文标记块 → 裸对象两头都抓不到，会被原样落盘、原样派发给次级对话。
    实现（2026-10-12 加固:只删"确定是裸对象"的整块，绝不误伤后续轮次）:
      ① 定位模板版本字段 → 向前取最近左花括号作为候选对象起点；
      ② 候选起点必须与字段同行且距离 ≤200 字符，跨行/过远一律视为正文引用 → 跳过不删；
      ③ 向后逐字符做括号配对（感知引号与反斜杠转义）；
      ④ 配对失败 → 跳过不删（旧实现此处从起点截到末尾，是"首轮之后内容全丢"的根因）；
      ⑤ 待删区间若跨轮次/工具结果边界（含「第N轮交互」或「工具执行结果」）→ 跳过不删；
      ⑥ 用 search_from 游标单调推进，跳过时不回头，避免死循环。
    最后收敛多余空行，避免历史里出现大片空白。
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


# 方案A:会话级"本轮输出"实时快照，key=session_id，value={"query","reasoning","output","done"}
# 用途:切页/断线时SSE增量被丢弃，前端切回后按query据此补齐缺口（记忆库与生成完整，仅前端展示链路丢包）
SESSION_LAST_OUTPUT = {}

def push_sse_message(session_id: str, data: dict):
    """线程安全的SSE消息推送，支持在子线程中调用，解决TestClient跨事件循环无法唤醒主循环Queue的问题"""
    global global_event_loop
    # 方案A:实时累积本轮输出快照（不依赖SSE队列存活，断线期间仍持续累积，供前端切回补齐）
    # 【修复·根因级】原实现是 `if _snap is not None` —— 快照不存在就完全不累积。
    # 而 SESSION_LAST_OUTPUT 全项目只有一处创建（主控 POST /api/chat 时建 "default"），
    # 次级通道 sec_{slot} 从未被创建过快照 → 次级事件在"无人订阅"时永久丢失，
    # 这就是"打开次级页看不到内容、必须切页回读"的根因。
    # 现改为:任何通道（含 sec_{slot}）首次出现事件即自动建快照，与主控 default 同一套机制。
    _stype = str(data.get("type") or "")
    _snap = SESSION_LAST_OUTPUT.get(session_id)
    if _snap is None:
        # events:无订阅期间发生的业务事件序列（供前端建连时按序回放"过程"，见 chat_stream 的 sec_ 分支）
        _snap = {"query": "", "reasoning": "", "output": "", "done": False, "events": []}
        SESSION_LAST_OUTPUT[session_id] = _snap
    # 兼容老结构快照（进程热更/历史对象缺字段时不炸）
    if not isinstance(_snap.get("events"), list):
        _snap["events"] = []
    if _stype == "dispatch":
        # 新一轮派发 → 清空快照（重放时只回放"本轮"内容，不与上一轮混淆）
        _snap["query"] = str(data.get("content") or "")
        _snap["reasoning"] = ""
        _snap["output"] = ""
        _snap["done"] = False
        # 【事件回放·新增】新一轮起手 → 事件序列同步清空（回放只保留"本轮"过程，不与上一轮混淆）
        _snap["events"] = []
        # 【M4a·根因修复】新一轮派发 → 同时复位"上一轮已闭轮"标记
        _snap["_stream_closed"] = False
    elif _stype == "ai_reasoning":
        _snap["reasoning"] += str(data.get("content") or "")
    elif _stype == "ai_output_stream":
        # 【M4b·根因修复】上一轮已闭轮（ai_output 已把快照固化为"单轮完整正文"）→ 本轮流式从空重累，
        #   避免快照把"第1轮 + 第2轮 + …"整轮拼接成一条，被前端 syncLastOutput 整段顶替当前气泡
        if _snap.get("_stream_closed"):
            _snap["output"] = ""
            _snap["_stream_closed"] = False
        _snap["output"] += str(data.get("content") or "")
    elif _stype == "ai_output":
        # 【M4b·根因修复】终态直接用"单轮完整正文"覆盖快照（原实现仅在为空时兜底，流式已累加过就永不纠偏），
        #   并打上闭轮标记，供下一轮流式分支识别"该从空重累"
        _snap["output"] = str(data.get("content") or "") or _snap["output"]
        _snap["done"] = True
        _snap["_stream_closed"] = True
    elif _stype in ("report", "secondary_summary"):
        _snap["done"] = True
    # 【事件回放·新增】无论当前是否有订阅者，先把本次事件按序记入回放队列；
    # 位置必须在下方 `if not queues: return` 之前 —— 这是"无订阅期间的过程留痕"的唯一落点。
    # 上限 2000 条（超出裁头），防长任务把内存堆爆；只记前端可渲染的业务事件，跳过 heartbeat。
    if _stype in ("dispatch", "ai_reasoning", "ai_output_stream", "ai_output", "report", "secondary_summary"):
        _rev = _snap.get("events")
        if isinstance(_rev, list):
            try:
                _rev.append(dict(data))
            except Exception:
                _rev.append({"type": _stype, "content": str(data.get("content") or "")})
            if len(_rev) > 2000:
                del _rev[:len(_rev) - 2000]
    # 订阅池取该会话队列:无队列=该通道当前无窗口订阅，静默丢弃（级别=debug，不打印以免刷屏）
    queues = SSE_CONNECTIONS.get(session_id)
    if not queues:
        return
    if not global_event_loop:
        return
    try:
        import asyncio
        # 订阅池模式:向该会话所有已连接窗口广播（主窗 + 悬浮窗实时同达）
        for queue in list(queues):
            asyncio.run_coroutine_threadsafe(queue.put(data), global_event_loop)
    except Exception:
        pass

def broadcast_scheduler_notice(text: str):
    """向所有活跃工作台会话广播一条定时任务系统通知（复用push_sse_message，非阻塞；不写历史、不污染推理流）"""
    for sid in list(SSE_CONNECTIONS.keys()):
        if sid == "scheduler_task":
            continue
        push_sse_message(sid, {"type": "scheduler_notice", "content": text})

# P1:把线程安全的SSE推送函数注入后台任务管理器（监控线程在提升/完成/取消/超时时推送事件，P2卡片消费）
background_task_manager.background_task_manager.set_sse_pusher(push_sse_message)

# P1(阶段4):任务编排器挂接 —— SSE 推送复用同一线程安全函数；启动超时守护线程（硬终止②兜底）
try:
    import orchestrator as _orch
    _orch.set_sse_pusher(push_sse_message)
    # 注入「主控上下文追加器」:次级 @主控 的内容会被真正写入当前项目历史，主控下轮可读到（回调注入，杜绝循环依赖）
    _orch.set_main_injector(append_main_context)
    # 【2026-10-13 新增】注入「主控唤醒器」:次级 @主控 后触发一次主控模型调用（走 /api/chat 主链路，与人手对话上下文同源）
    _orch.set_main_waker(wake_main)
    _orch.start_timeout_guard()
except Exception as _orch_err:
    print(f"⚠️ 任务编排器挂接失败（不影响旧链路）: {_orch_err}")

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
        # 动态隔离:被用户右键"加入项目信息隔离"的路径（目录则整棵子树）直接跳过，
        # 不进入注入 AI 上下文的文件树，根治运行期临时文件导致的项目信息无上限膨胀
        if file_filter_config.is_isolated_path(item_full_path):
            continue
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
LOG_ID_COUNTER = 0 # 全局单调日志ID计数器，永不复用，杜绝满上限后ID恒为501导致增量刷新死锁
# 日志落盘文件:打包环境存exe同级目录（用户可见、升级不丢失），开发环境存项目根目录，与config.json路径策略一致
if getattr(_sys, 'frozen', False):
    OPERATION_LOGS_FILE = os.path.join(_exe_dir, "operation_logs.json")
else:
    OPERATION_LOGS_FILE = os.path.join(BASE_DIR, "operation_logs.json")
_LOG_PERSIST_TIMER = None
_LOG_PERSIST_LOCK = threading.Lock()

def _persist_operation_logs():
    """立即将当前内存日志全量写入文件（倒序最新在前），任何异常都不影响主流程"""
    try:
        with _LOG_PERSIST_LOCK:
            # 先做C层原子快照，避免Timer线程序列化期间主线程insert/pop导致"list changed size during iteration"
            snapshot = list(OPERATION_LOGS)
            with open(OPERATION_LOGS_FILE, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _schedule_log_persist(delay: float = 5.0):
    """防抖落盘:日志高频变更时合并为delay秒后一次写盘；delay<=0时立即写盘（清空场景）"""
    global _LOG_PERSIST_TIMER
    if _LOG_PERSIST_TIMER is not None:
        _LOG_PERSIST_TIMER.cancel()
    if delay <= 0:
        _LOG_PERSIST_TIMER = None
        _persist_operation_logs()
        return
    _LOG_PERSIST_TIMER = threading.Timer(delay, _persist_operation_logs)
    _LOG_PERSIST_TIMER.daemon = True
    _LOG_PERSIST_TIMER.start()

def _load_operation_logs():
    """启动时恢复最近500条日志，ID计数器初始化为历史最大ID（清空日志也不回退，杜绝ID重复）"""
    global OPERATION_LOGS, LOG_ID_COUNTER
    try:
        if os.path.exists(OPERATION_LOGS_FILE):
            with open(OPERATION_LOGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, list):
                OPERATION_LOGS = saved[:LOG_MAX_SIZE]
                max_id = max([int(item.get("id", 0)) for item in OPERATION_LOGS if isinstance(item, dict)] or [0])
                LOG_ID_COUNTER = max_id
    except Exception:
        OPERATION_LOGS = []
        LOG_ID_COUNTER = 0

# 启动即从落盘文件恢复历史日志
_load_operation_logs()
# ========== 配置结束 ==========
# 全局异步任务存储
TASK_STORAGE = {}
TASK_ID_COUNTER = 1
TASK_STATUS_PENDING = "pending"
TASK_STATUS_RUNNING = "running"
TASK_STATUS_SUCCESS = "success"
TASK_STATUS_FAILED = "failed"

def add_operation_log(oper_type: str, content: str, status: str = "success"):
    """新增操作日志，自动记录时间，按倒序存储；ID全局单调递增，满500条滚动删除最早一条"""
    global OPERATION_LOGS, LOG_ID_COUNTER
    LOG_ID_COUNTER += 1
    log_item = {
        "id": LOG_ID_COUNTER,
        "oper_type": oper_type,
        "content": content,
        "status": status,
        "oper_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    OPERATION_LOGS.insert(0, log_item)
    # 超过上限自动删除最早的日志
    if len(OPERATION_LOGS) > LOG_MAX_SIZE:
        OPERATION_LOGS.pop()
    # 防抖5秒批量落盘，高频写日志不拖慢对话主流程
    _schedule_log_persist(5.0)

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

# ==================== 工具输出截断/落盘/跨轮老化（P0-1/P0-5）====================
def _get_tool_output_config() -> Dict:
    """读取tool_output配置节点，缺失值用默认值兜底，任何异常都不影响主流程"""
    defaults = {
        "truncate_enabled": True,          # 总开关
        "head_chars": 24000,               # 头部保留字符数
        "tail_chars": 8000,                # 尾部保留字符数
        "trigger_chars": 60000,            # 超过此字符数才触发截断
        "save_to_disk": True,              # 完整结果是否落盘
        "output_dir_name": "tool_outputs", # 落盘目录名（打包时exe同级）
        "max_saved_files": 50,            # 落盘文件最多保留个数
        "exec_cmd_timeout": 60,            # exec_cmd超时秒数
        "aging_enabled": True,             # 跨轮老化总开关
        "aging_keep_rounds": 4,            # 保护代数:最近N代工具结果完整保留
        "aging_trigger_chars": 120000,      # messages总字符超此值才触发老化
        "aging_max_per_round": 3,          # 单轮最多归档条数
    }
    try:
        cfg = load_config().get("tool_output") or {}
        defaults.update(cfg)
    except Exception:
        pass
    return defaults

def _cleanup_tool_output_dir(dir_path: str, max_files: int):
    """落盘文件超量时按修改时间从最早开始删除，只清理.txt，任何异常不外抛"""
    try:
        if not os.path.isdir(dir_path):
            return
        files = [os.path.join(dir_path, f) for f in os.listdir(dir_path) if f.endswith(".txt")]
        if len(files) <= max_files:
            return
        files.sort(key=lambda p: os.path.getmtime(p))
        for p in files[:len(files) - max_files]:
            try:
                os.remove(p)
            except Exception:
                pass
    except Exception as e:
        print(f"⚠️ 清理tool_outputs目录失败:{e}")

# 上传文件夹/截图保留上限（时效性高，硬编码 100）
UPLOAD_MAX_FILES = 100

def _cleanup_upload_dir():
    """上传文件夹（含截图）超量时按 mtime 删最早，保留最新 UPLOAD_MAX_FILES 个，任何异常不外抛"""
    try:
        if not os.path.isdir(UPLOAD_ROOT):
            return
        files = [os.path.join(UPLOAD_ROOT, f) for f in os.listdir(UPLOAD_ROOT)
                 if os.path.isfile(os.path.join(UPLOAD_ROOT, f))]
        if len(files) <= UPLOAD_MAX_FILES:
            return
        files.sort(key=lambda p: os.path.getmtime(p))
        for p in files[:len(files) - UPLOAD_MAX_FILES]:
            try:
                os.remove(p)
            except Exception:
                pass
    except Exception as e:
        print(f"⚠️ 清理上传文件夹失败:{e}")

def save_full_tool_output(tool_name: str, index, full_text) -> Optional[str]:
    """完整工具结果落盘，返回绝对路径；任何失败只返回None，绝不抛异常影响主流程。
    打包环境存exe同级目录，开发环境存BASE_DIR，与config.json路径策略一致。"""
    try:
        cfg = _get_tool_output_config()
        if getattr(_sys, "frozen", False):
            base = os.path.dirname(_sys.executable)
        else:
            base = BASE_DIR
        dir_path = os.path.join(base, str(cfg.get("output_dir_name") or "tool_outputs"))
        os.makedirs(dir_path, exist_ok=True)
        _cleanup_tool_output_dir(dir_path, int(cfg.get("max_saved_files", 200)))
        safe_name = re.sub(r'[\\/:*?"<>|\s]+', "_", str(tool_name))[:30] or "tool"
        # 加毫秒防止同秒同名覆盖
        ms = int(time.time() * 1000) % 1000
        fname = f"{time.strftime('%Y%m%d_%H%M%S')}_{ms:03d}_{safe_name}_{index}.txt"
        fpath = os.path.join(dir_path, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(full_text if isinstance(full_text, str) else str(full_text))
        return fpath
    except Exception as e:
        print(f"⚠️ 工具输出落盘失败:{e}")
        return None

def truncate_tool_output(tool_name: str, index, full_text) -> str:
    """工具输出统一截断:超阈值保留头尾、中间替换为带地图的省略提示，完整结果落盘。
    只作用于进messages的副本；严格按行边界切分，绝不截断半行代码。"""
    text = full_text if isinstance(full_text, str) else str(full_text)
    try:
        cfg = _get_tool_output_config()
        if not cfg.get("truncate_enabled", True):
            return text
        trigger = int(cfg.get("trigger_chars", 40000))
        if len(text) <= trigger:
            return text
        head_chars = int(cfg.get("head_chars", 24000))
        tail_chars = int(cfg.get("tail_chars", 8000))
        lines = text.split("\n")
        total_lines = len(lines)
        # 头部按整行累计到head_chars
        hc, head_end = 0, 0
        for i, ln in enumerate(lines):
            add = len(ln) + 1
            if hc + add > head_chars and head_end > 0:
                break
            hc += add
            head_end = i + 1
        # 尾部按整行累计到tail_chars
        tc, tail_start = 0, total_lines
        for i in range(total_lines - 1, -1, -1):
            add = len(lines[i]) + 1
            if tc + add > tail_chars and tail_start < total_lines:
                break
            tc += add
            tail_start = i
        # 头尾重叠说明全文不长到需要截断，原样返回
        if head_end >= tail_start:
            return text
        head_part = "\n".join(lines[:head_end])
        tail_part = "\n".join(lines[tail_start:])
        omitted = tail_start - head_end
        saved_path = ""
        if cfg.get("save_to_disk", True):
            saved_path = save_full_tool_output(tool_name, index, text) or ""
        if saved_path:
            retrieve = (f"完整结果已保存:{saved_path}\n"
                        f"取回方式:①read_file 加 start_line/end_line 参数按行翻页读取；"
                        f"②exec_cmd 用 findstr / Select-String 按关键词定位"
                        f"（例:Select-String -Path \"{saved_path}\" -Pattern \"关键词\" -Context 3,3）。")
        else:
            retrieve = "完整结果未落盘，请缩小命令输出范围（如加过滤条件/分页参数）后重新执行。"
        omit_tip = (
            f"\n⚠️ 输出过长已省略中间部分:原始共 {total_lines} 行 / {len(text)} 字符，\n"
            f"当前保留第 1-{head_end} 行与第 {tail_start + 1}-{total_lines} 行，省略 {omitted} 行。\n"
            f"{retrieve}\n"
        )
        return head_part + "\n" + omit_tip + "\n" + tail_part
    except Exception as e:
        print(f"⚠️ 截断工具输出失败:{e}")
        return text

def _contains_dangerous_command(cmd: str) -> bool:
    """危险命令判定:拆分管道/分号后逐段检查段首程序名，避免\\bformat\\b误杀Format-Table等
    PowerShell cmdlet（段首token含连字符不命中纯单词黑名单）。段首为rm/rd/del/erase/format/
    mkfs/dd等危险程序才拦截。判定异常时保守放行。
    【2026-10-12 调整】按用户要求取消「命令拼接（&）」单独拦截，含&的拼接命令照常放行；
    危险程序保护仍按段首程序名生效（如 "dir & del x" 依旧命中 del 段被拦）。
    """
    try:
        dangerous_progs = {"rm", "rmdir", "rd", "del", "erase", "format", "mkfs", "dd"}
        segments = re.split(r'\|\|?|&&?|;', cmd)
        for seg in segments:
            seg = seg.strip().strip('"').strip("'")
            if not seg:
                continue
            parts = seg.split()
            first = parts[0].strip('"').strip("'") if parts else ""
            prog = first.replace("\\", "/").split("/")[-1].lower()
            if "." in prog:
                prog = prog.split(".")[0]
            if prog in dangerous_progs:
                return True
        return False
    except Exception:
        return False


# P0 兜底（2026-10-12 用户方案）:工具调用块未闭合自动补足
# 背景:AI 输出被模型/网络原生截断、或 AI 漏写结束标记时，下方解析处的全量正则匹配会把
#       这些块静默丢弃 → 工具未执行 → 文件没写成、任务中断。本函数只补结束标记，绝不猜内容。
# 规则（保守，避免误判）:
#   1. 只认「独占一行」的起止标记（strip 后与该行完全相同才算），正文句中提及、示例引用一律不计数；
#   2. 按行序栈式扫描:先见到开始标记才计深度，孤立结束标记不倒扣；
#   3. 开始数 > 结束数时，仅在文本末尾补齐缺失的结束标记，不做任何猜内容操作；
#   4. 数量匹配 / 无开始标记 → 原样返回，零开销；
#   5. 标记字面量用常量拼接构造，源码中不出现完整标记，避免本文件被上层标记扫描误判。
# 返回:(补全后的文本, 补足的结束标记数量)
def _autoclose_tool_blocks(text: str):
    try:
        _begin_mark = "【" + "工具调用开始" + "】"
        _end_mark = "【" + "工具调用结束" + "】"
        if not text or _begin_mark not in text:
            return text, 0
        # 【2026-10-12 升级·遇新开先闭合旧块】逐行重建:
        #   ① 遇到新的开始标记时，若上一块尚未闭合，先就地补一个结束标记再开新块；
        #   ② 文本结束时若仍处于开块状态，逐层补齐剩余结束标记；
        #   ③ 本次无任何补足时，原样返回入参，保证"块本就配平"场景与改动前 100% 一致。
        # 背景:原实现只在文本末尾一次性补 N 个结束标记，导致"连续多个未闭合开始标记"
        #   会被下游非贪婪正则跨块合并成一个大块（首行变叙述文字）→ 结构校验整批静默丢弃。
        _out_lines = []
        _depth = 0
        _padded = 0
        for _raw_line in text.splitlines():
            _line = _raw_line.strip()
            if _line == _begin_mark:
                if _depth > 0:
                    _out_lines.append(_end_mark)
                    _padded += 1
                _depth += 1
                _out_lines.append(_raw_line)
            elif _line == _end_mark:
                if _depth > 0:
                    _depth -= 1
                _out_lines.append(_raw_line)
            else:
                _out_lines.append(_raw_line)
        while _depth > 0:
            _out_lines.append(_end_mark)
            _padded += 1
            _depth -= 1
        if _padded <= 0:
            return text, 0
        return "\n".join(_out_lines), _padded
    except Exception:
        return text, 0

# P1-9.3: 不计入连续错误计数的结果标记——参数/指令格式纠正信号、系统保护路径提示属于给AI的
# 纠正信号而非系统故障，累计到3次会误杀长任务；其余真正含❌的执行失败才计数（阈值3不变）
_NON_FATAL_RESULT_MARKERS = (
    "参数错误",        # read_file翻页参数非法、edit_file必填参数/操作类型校验等
    "参数解析失败",    # 必填参数值为空等通用解析通道提示
    "指令解析失败",    # 工具块缺字段、JSON语法错误等格式纠正信号
    "工具指令生成失败", # 工具名/参数不合法
    "禁止操作",        # 系统保护目录/用户自定义禁止路径提示（reason中固定含此语）
    "请向用户说明",    # 编辑/读取失败引导语（锚点错误等已内含"重试一次后停止"指令）
)

def age_tool_messages(messages: list, current_round: int = 0) -> int:
    """跨轮老化（P0-5）:最近aging_keep_rounds代工具结果完整保留；更早的消息仅在messages
    总字符超阈值时，把最老的最多aging_max_per_round条原地替换为'一行结论+落盘指针'。
    只处理role=user且以🔹执行结果标记开头的消息，不删消息、不破坏角色配对；
    归档后消息不以🔹开头，天然退出代际序列且幂等；落盘失败的消息本轮不老化。返回归档条数。"""
    try:
        cfg = _get_tool_output_config()
        if not cfg.get("aging_enabled", True):
            return 0
        keep = int(cfg.get("aging_keep_rounds", 2))
        trigger = int(cfg.get("aging_trigger_chars", 60000))
        max_per_round = int(cfg.get("aging_max_per_round", 3))
        total_chars = sum(len(m.get("content") or "") for m in messages)
        if total_chars <= trigger:
            return 0
        # 仅识别真实工具结果消息（归档后的指针消息不以🔹开头，天然退出代际序列、幂等）
        tool_positions = [i for i, m in enumerate(messages)
                          if m.get("role") == "user" and str(m.get("content") or "").lstrip().startswith("🔹")]
        # 最近keep代完整保留，其余按时间从老到新作为候选
        candidates = tool_positions[:-keep] if len(tool_positions) > keep else []
        if not candidates:
            return 0
        archived = 0
        for idx in candidates:
            if archived >= max_per_round:
                break
            content = messages[idx].get("content") or ""
            if "工具结果已归档" in content:
                continue
            saved = save_full_tool_output("age_archive", f"r{current_round}_{idx}", content)
            if not saved:
                continue  # 失败安全:落盘失败本轮不老化，保持原文，下轮再试
            lines = content.split("\n")
            first_line = lines[0].strip()[:100]
            last_line = ""
            for ln in reversed(lines):
                if ln.strip():
                    last_line = ln.strip()[:100]
                    break
            k = tool_positions.index(idx) + 1  # 该消息为第几条工具结果（代次序号）
            messages[idx]["content"] = (
                f"[第{k}轮工具结果已归档] {first_line}；"
                f"结论/要点:{last_line or '见存盘文件'}；"
                f"原始共{len(lines)}行已存盘:{saved}，"
                f"需要时用 read_file 的 start_line/end_line 翻页或 Select-String 关键词检索取回。"
            )
            archived += 1
        return archived
    except Exception as e:
        print(f"⚠️ 跨轮老化失败:{e}")
        return 0

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
    # 消 Pydantic v2 的 model_ 命名空间冲突警告（model_slot 等字段会触发 UserWarning，此处显式放行，零副作用）
    model_config = {"protected_namespaces": ()}
    query: str
    system_prompt: Optional[str] = "" # 自定义系统提示词，不传用默认值
    session_id: Optional[str] = "default" # 会话ID，不传默认用公共会话
    attachments: list = []  # 附件列表，支持多文件/图片上传
    task_name: Optional[str] = "" # 定时任务名称，仅定时任务触发时携带（用于系统提示文案，默认空对普通对话无影响）
    thinking: bool = False # AI思考模式开关:开启后透传 reasoning_effort="high" 驱动模型深度思考，默认关闭保证向后兼容
    model_slot: int = 1 # 模型槽位（主对话固定 1，系统自动按该槽位读 models_config.json 的人设/3固定提示/温度/回复上限/api_url/model_name/api_key，用户无感）
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
    # 方案A:初始化/重置本轮会话输出快照（供前端切回后按query补齐断线期间丢弃的流式增量）
    SESSION_LAST_OUTPUT[req.session_id] = {"query": req.query, "reasoning": "", "output": "", "done": False}
    # 判断是否为定时任务触发
    is_scheduler_task = req.session_id == "scheduler_task"
    # 定时任务使用独立会话ID，禁止劫持用户工作台会话，避免污染用户对话流、抢占用户SSE推送通道
    if is_scheduler_task:
        req.session_id = "scheduler_task"
        # 广播一条系统通知到所有活跃工作台会话（仅临时UI气泡，不写历史、不注入推理流）
        broadcast_scheduler_notice(f"⏰ AI 开始执行定时任务:{req.task_name or '定时任务'}")
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
    # 上下文轮数:优先读当前模型槽位 max_chat_rounds（页面「上下文轮数」），缺失回退全局 history_context_rounds
    from model_registry import get_slot_config as _get_slot_cfg_hist
    _hist_slot_cfg = _get_slot_cfg_hist(int(getattr(req, "model_slot", 1) or 1)) or {}
    history_rounds = int(_hist_slot_cfg.get("max_chat_rounds", 0) or 0) or memory_cache.config["history_context_rounds"]
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
    # 升序:最早的对话在前，最新的在后，保证上下文逻辑正确
    # （unique_history 已按 timestamp 升序排序并取最近 N 条，此处不再反转）
    # 格式转换为会话上下文格式，支持自动注入时间戳
    current_session = []
    show_timestamp = memory_cache.config.get("show_timestamp_in_context", True)
    for mem in session_history:
            # 拆分用户提问和AI回答
            # 【修复·根因级】兜底赋值:历史里可能存在非"用户问:...\n回答:..."标准格式的记录
            # （例如只有用户侧提问、或内容里含多个"回答:"导致 split 出 3 段以上）。
            # 旧代码在 len(parts) != 2 时不赋值，随后 if show_timestamp 分支直接引用
            # user_content / ai_content → UnboundLocalError → FastAPI 500，
            # 表现为"主控派发过一次任务后，第二次对话直接断开、必须切项目才能再发"。
            # 现改为:先兜底置空，split 成功才覆盖；非标准格式整段作为用户内容，
            #          不生成空字符串的 AI 回复，避免污染上下文。
            user_content = ""
            ai_content = ""
            parts = mem["content"].split("\n回答:")
            if len(parts) == 2:
                user_content = parts[0].replace("用户问:", "")
                ai_content = parts[1]
            else:
                user_content = str(mem.get("content") or "").replace("用户问:", "")
            # 开启时间戳则格式化注入
            if show_timestamp:
                # 时间戳格式:[YYYY-MM-DD HH:MM] 极简显示不占空间
                time_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(mem["timestamp"] / 1000))
                if user_content:
                    user_content = f"[{time_str}] {user_content}"
                if ai_content:
                    ai_content = f"[{time_str}] {ai_content}"
            # 仅在内容非空时入上下文，防止出现 {"role":"assistant","content":""} 这类空消息
            if user_content:
                current_session.append({"role": "user", "content": user_content})
            if ai_content:
                current_session.append({"role": "assistant", "content": ai_content})
    
    # P1:跨轮"完成回灌"——取出本会话所有已结束后台任务的真实结果，成对注入历史之后、当前提问之前；
    # 只进本轮上下文、不写向量记忆库，drain一次性清空，AI下一轮即可看到真实退出码/耗时/日志尾部
    for _done_task in background_task_manager.background_task_manager.drain_pending(req.session_id):
        _done_notice = background_task_manager.background_task_manager.build_pending_notice(_done_task)
        current_session.append({"role": "user", "content": _done_notice})
        current_session.append({"role": "assistant", "content": "已收到该后台任务的真实结果，我将结合退出码与日志向用户汇报或继续后续步骤。"})
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
    # 【模块0前置:按模型槽位读配置（人设/3个固定提示）——主对话自动分配 model_slot=1，用户无感】
    from model_registry import get_slot_config as _get_slot_config
    _slot_no = int(getattr(req, "model_slot", 1) or 1)
    _slot_cfg = _get_slot_config(_slot_no) or {}
    _persona_name = str(_slot_cfg.get("persona_name", "") or "")
    _persona_prompt = str(_slot_cfg.get("persona_prompt", "") or "").strip()
    # 固定召回（工具+预留插槽）拼入系统prompt，不占用上下文配额
    # 【唯一数据源】按模型槽位读 models_config.json 的 fixed_prompt_1/2/3（memory_config.fixed_recall 仅作兜底）
    _slot_fixed_parts = []
    for _fk in ("fixed_prompt_1", "fixed_prompt_2", "fixed_prompt_3"):
        _fv = str(_slot_cfg.get(_fk, "") or "").strip()
        if _fv:
            _slot_fixed_parts.append(_fv)
    if _slot_fixed_parts:
        fixed_prompt = "\n".join(_slot_fixed_parts)
    else:
        fixed_prompt = "\n".join([item["content"] for item in recall_result["fixed_recall"]])
    # 新增:追加已启用插件列表描述
    # 【插件按槽位过滤】enabled_plugins 缺失/非list/空数组 → 全量注入（向后兼容，防误清空致模型裸奔）
    merged_tools = tool_template_manager.get_merged_tool_list()
    _enabled_plugins = _slot_cfg.get("enabled_plugins")
    if isinstance(_enabled_plugins, list) and len(_enabled_plugins) > 0:
        _allowed_plugins = set(str(x) for x in _enabled_plugins)
        _filtered_tools = {}
        for _tid, _tpl in merged_tools.items():
            _pid = str((_tpl.get("plugin_config") or {}).get("plugin_id", _tid))
            if _pid in _allowed_plugins or str(_tid) in _allowed_plugins:
                _filtered_tools[_tid] = _tpl
        merged_tools = _filtered_tools
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
    # 【模块0:模型人设 —— 按模型ID读 models_config.json（主对话自动分配 model_slot=1）】
    # 说明:3 个固定提示已统一由下方「固定召回内容」段按槽位注入（唯一数据源），此处不再重复拼接，杜绝双份注入
    system_prompt = ""
    if _persona_prompt:
        system_prompt += f"========== 模型人设（{_persona_name or _slot_cfg.get('display_name', '')}）==========\n{_persona_prompt}\n==================================\n"
    if req.system_prompt:
        system_prompt += req.system_prompt
    # 【模块1:固定召回（工具+预留插槽）】不占用上下文配额，100%生效
    if fixed_prompt.strip():
        system_prompt += "\n========== 固定召回内容 ==========\n"
        system_prompt += fixed_prompt + "\n"
        system_prompt += "==================================\n"
    # 【模块1.2:可派发角色清单 + 派发协议】纯复用 orchestrator.build_role_pool，排除主控自身槽位
    # 作用:让主控模型"看得见"次级角色，能自主 @人设名 派发；异常静默兜底，池空不注入，绝不改原 system_prompt 行为
    try:
        _dispatchable = [r for r in _orch.build_role_pool() if int(r.get("slot", 0) or 0) != _slot_no]
        if _dispatchable:
            system_prompt += "\n========== 可派发角色清单 ==========\n"
            system_prompt += _orch.pool_brief(_dispatchable) + "\n"
            system_prompt += "【派发协议】如需把任务派给某角色，请在回复正文中以 @人设名 标记（如 @开发），系统会自动派发。\n"
            system_prompt += "==================================\n"
    except Exception as _rp_err:
        print(f"⚠️ 可派发角色清单注入失败（不影响主对话）: {_rp_err}")

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
    _image_hints = []  # 【多图修正】收集所有图片附件的提示文案，循环结束后统一前置，避免后图覆盖前图提示导致顺序颠倒
    
    if req.attachments:
        for att in req.attachments:
            ext = att['ext'].lower()
            size = att['size']
            local_path = att['local_path']
            original_name = att['original_name']
            
            # 判断是否符合图片直传条件
            if ext in DIRECT_UPLOAD_CONFIG['image']['exts'] and size <= DIRECT_UPLOAD_CONFIG['image']['max_size']:
                use_direct_mode = True
                # 【多图修正】每张图片各收集一条提示（顺序即发送顺序），循环结束后统一前置到提问原文上方
                _image_hints.append(original_name)
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
                content_list[0]['text'] = f"📎 上传的文件【{original_name}】本地路径:{local_path}\n请调用对应工具读取文件内容后响应用户提问。\n\n用户提问:{content_list[0]['text']}"
        # 【多图修正】所有附件处理完毕后统一前置图片提示:每张图独立一行，顺序与发送顺序一致（图A→图B→→原文）
        if _image_hints:
            _hint_block = "\n".join([f"（用户上传了图片【{_n}】）" for _n in _image_hints])
            content_list[0]['text'] = f"{_hint_block}\n\n{content_list[0]['text']}"
    
    # 初始化消息列表，兼容直传/普通模式
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content_list if use_direct_mode else content_list[0]['text']}
    ]
    # 从槽位配置读取每轮回复最大次数（承接页面「回复上限」语义 max_reply_rounds），缺失时回退 20
    config = load_config()
    max_tool_calls = int(_slot_cfg.get("max_reply_rounds", 20) or 20) if _slot_cfg else int(config.get("max_reply_rounds", 20) or 20)
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
            # 模型推理（按模型槽位调用独立客户端:api_url/model_name/api_key/timeout/temperature/max_tokens 全部来自 models_config.json）
            # AI思考模式开关:开启（thinking=True）时通过 extra_body 透传 reasoning_effort="high" 驱动深度思考；
            # 关闭时完全不带该参数（而非传 None），避免部分推理客户端拒绝空值导致调用失败
            # 【甲+乙】标准 OpenAI SDK 的 chat.completions.create() 不认顶层 reasoning_effort（会抛 unexpected keyword argument）；
            #   甲:统一放进 extra_body 官方透传口子，网关不认也仅是无害参数，不报错；
            #   乙:万一某客户端连 extra_body 都不支持 → try/except TypeError 去掉该参数原样重试一次，兜底绝不崩。
            _reasoning_on = bool(getattr(req, "thinking", False))
            from model_registry import get_client as _get_slot_client
            _slot_client = _get_slot_client(_slot_no)
            _slot_max_tokens = int(_slot_cfg.get("max_tokens", 0) or 0)
            _slot_call_kwargs = {
                "model": _slot_cfg.get("model_name", ""),
                "messages": messages,
                "temperature": float(_slot_cfg.get("temperature", 0.5) or 0.5),
                "top_p": 0.9,
                "stream": True,
                "timeout": int(_slot_cfg.get("timeout", 200) or 200),
            }
            if _slot_max_tokens > 0:
                _slot_call_kwargs["max_tokens"] = _slot_max_tokens
            if _reasoning_on:
                # 双保险口径:方舟（doubao-seed 系）认 thinking；OpenAI 系认 reasoning_effort；互不认均为无害透传
                _slot_call_kwargs["extra_body"] = {"thinking": {"type": "enabled"}, "reasoning_effort": "high"}
            try:
                output_stream = _slot_client.chat.completions.create(**_slot_call_kwargs)
            except TypeError as _reason_err:
                # 兜底:客户端不认 thinking/reasoning_effort/extra_body → 去掉后原样重试一次（保证任何客户端都不再报错中断）
                if _reasoning_on and ("reasoning_effort" in str(_reason_err) or "extra_body" in str(_reason_err) or "thinking" in str(_reason_err)):
                    print(f"⚠️ 客户端不支持思考模式透传，已自动去掉该参数重试:{str(_reason_err)[:120]}")
                    _slot_call_kwargs.pop("extra_body", None)
                    output_stream = _slot_client.chat.completions.create(**_slot_call_kwargs)
                else:
                    raise

            current_response = ""
            current_calls += 1
            # 流式接收输出，逐块推送前端
            reasoning_content = ""
            
            # 用独立线程执行同步流式生成器，主事件循环只 await 队列，避免同步 next() 独占事件循环导致全站卡死
            _chunk_queue = asyncio.Queue()
            _consumer_loop = asyncio.get_running_loop()
            _chunk_sentinel = object()
            _stream_stop = threading.Event()

            def _produce_chunks():
                try:
                    for _chunk in output_stream:
                        if _stream_stop.is_set():
                            break
                        _consumer_loop.call_soon_threadsafe(_chunk_queue.put_nowait, _chunk)
                except Exception as _err:
                    _consumer_loop.call_soon_threadsafe(_chunk_queue.put_nowait, ("__stream_error__", _err))
                finally:
                    _consumer_loop.call_soon_threadsafe(_chunk_queue.put_nowait, _chunk_sentinel)

            _producer_thread = threading.Thread(target=_produce_chunks, daemon=True)
            _producer_thread.start()

            while True:
                chunk = await _chunk_queue.get()
                if chunk is _chunk_sentinel:
                    break
                if isinstance(chunk, tuple) and len(chunk) == 2 and chunk[0] == "__stream_error__":
                    raise chunk[1]
                # 检查停止信号，收到立即终止流式输出
                if req.session_id in CHAT_STOP_SIGNALS:
                    _stream_stop.set()
                    break
                # 兼容 OpenAI SDK 对象（ChatCompletionChunk）与 dict 两种返回形态:SDK 对象属性访问优先，dict 下标兜底
                # （切换 get_client(slot) 后返回的是 SDK 对象，chunk["choices"] 会抛 not subscriptable）
                _choices = getattr(chunk, "choices", None)
                if _choices is None and isinstance(chunk, dict):
                    _choices = chunk.get("choices") or []
                if not _choices:
                    continue
                _choice = _choices[0]
                _delta = getattr(_choice, "delta", None)
                if _delta is None and isinstance(_choice, dict):
                    _delta = _choice.get("delta")
                if _delta is None:
                    continue
                delta_content = (getattr(_delta, "content", None) if not isinstance(_delta, dict) else _delta.get("content")) or ""
                # 直接读取模型返回的专用思考内容字段（豆包/深度思考模型原生支持，无需自己解析<|im_start|>标签）
                delta_reasoning = (getattr(_delta, "reasoning_content", None) if not isinstance(_delta, dict) else _delta.get("reasoning_content")) or ""
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
                
                # 处理完内容后再判断是否结束（同一兼容口径:SDK 对象属性访问优先，dict 兜底）
                _finish_reason = getattr(_choice, "finish_reason", None)
                if _finish_reason is None and isinstance(_choice, dict):
                    _finish_reason = _choice.get("finish_reason")
                if _finish_reason == "stop":
                    break
            # 通知生产者线程停止，释放底层流式连接
            _stream_stop.set()
            
            # 最后推送完整的正式内容，对齐原有逻辑
            push_sse_message(req.session_id, {
                "type": "ai_output",
                "content": current_response.strip(),
                "timestamp": time.time()
            })

            all_exec_results = []
            # 新增:处理纯文本格式的工具调用请求，自动转换为模板生成的合法JSON指令
            import re
            # 【P0 兜底 2026-10-12】解析前先做一次"未闭合补足":AI 输出可能被模型/网络原生截断，
            #   或 AI 漏写结束标记 → 下方全量匹配会把这部分块静默丢弃 → 文件没写成 / 任务中断。
            #   这里只补结束标记、不补内容；残缺内容由 AI 在回读校验环节自行发现并续写剩余部分。
            _autoclosed_response, _autoclose_padded = _autoclose_tool_blocks(current_response)
            if _autoclose_padded > 0:
                # 未补足时函数返回原文，此分支不进入，行为与改动前 100% 一致
                current_response = _autoclosed_response
                # 提示不带❌前缀，不参与连续错误计数，避免长任务被连续误杀
                all_exec_results.append(
                    f"⚠️ 系统检测到本轮回复中有 {_autoclose_padded} 个工具块缺少结束标记，"
                    "已在解析前自动补全（仅补标记，不补内容）。"
                    "如本轮写入结果不完整，请对本轮工具执行结果进行回读校验，并继续补写剩余内容。"
                )
            # [A2B-B] 成对代码围栏保护:反引号内不参与识别，识别后逐块还原
            _a2b_fence_store = []
            def _a2b_fence_hide(_m):
                _a2b_fence_store.append(_m.group(0))
                return "__A2B_FENCE_" + str(len(_a2b_fence_store) - 1) + "__"
            _a2b_scan_text = re.sub(r"```[\s\S]*?```", _a2b_fence_hide, current_response)
            # [A2B-A] 结构校验:块内首个非空行必须是 工具名称<冒号>xxx，否则静默丢弃
            _a2b_tk_o = chr(0x3010) + "工具调用" + "开始" + chr(0x3011)
            _a2b_tk_c = chr(0x3010) + "工具调用" + "结束" + chr(0x3011)
            _a2b_colon = chr(0xFF1A)
            # 【2026-10-12 切块口径统一】由"非贪婪正则"改为"行首独占逐行扫描":
            #   正则 .*? 会把相邻两个块跨块合并成一个大块（首行变成叙述文字）→ 结构校验整批丢弃。
            #   改为与补全器同一套口径（行 strip 后与标记整行全等才算起止），保证每块首行即工具名。
            _a2b_raw = []
            _a2b_in_block = False
            _a2b_buf = []
            for _a2b_scan_line in _a2b_scan_text.splitlines():
                _a2b_s = _a2b_scan_line.strip()
                if _a2b_s == _a2b_tk_o:
                    _a2b_in_block = True
                    _a2b_buf = []
                elif _a2b_s == _a2b_tk_c:
                    if _a2b_in_block:
                        _a2b_raw.append("\n".join(_a2b_buf))
                        _a2b_in_block = False
                        _a2b_buf = []
                elif _a2b_in_block:
                    _a2b_buf.append(_a2b_scan_line)
            tool_blocks = []
            for _a2b_b in _a2b_raw:
                _a2b_b_restored = re.sub(r"__A2B_FENCE_(\d+)__", lambda _m: _a2b_fence_store[int(_m.group(1))], _a2b_b)
                _a2b_first = ""
                for _a2b_ln in _a2b_b_restored.splitlines():
                    if _a2b_ln.strip():
                        _a2b_first = _a2b_ln.strip()
                        break
                if re.match("^工具名称[" + _a2b_colon + r":]\s*\w+", _a2b_first):
                    tool_blocks.append(_a2b_b_restored)
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
                            fn_match = re.search(r'^[ \t]*file_name[：:][ \t]*(.*?)(?=\n[ \t]*(operation|gzt_anchor|gzt_newtext|target_block|content)[：:]|\Z)', params_str_norm, re.S | re.M)
                            if fn_match:
                                params["file_name"] = fn_match.group(1).strip()
                            op_match = re.search(r'^[ \t]*operation[：:][ \t]*(.*?)(?=\n[ \t]*(gzt_anchor|gzt_newtext|target_block|content)[：:]|\Z)', params_str_norm, re.S | re.M)
                            if op_match:
                                params["operation"] = op_match.group(1).strip()
                            # 提取gzt_anchor:从gzt_anchor:后到gzt_newtext:前/块结束的所有内容，完全保留原始格式
                            tb_match = re.search(r'^[ \t]*gzt_anchor[：:][ \t]*(.*?)(?=\n[ \t]*gzt_newtext[：:]|\Z)', params_str_norm, re.S | re.M)
                            if tb_match:
                                tb_content = tb_match.group(1)
                                # 修复:如果内容以换行开头，去掉第一个换行符（保留后续缩进）
                                if tb_content.startswith('\n'):
                                    tb_content = tb_content[1:]
                                params["gzt_anchor"] = tb_content.rstrip('\n')
                            # 提取gzt_newtext:从gzt_newtext:后一直到块结束，一字不差保留
                            ct_match = re.search(r'^[ \t]*gzt_newtext[：:](.*)', params_str_norm, re.S | re.M)
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
                    # 翻页参数仅read_file需要，按工具名放行，避免进入全局白名单污染其它工具的参数解析
                    if tool_name == "read_file":
                        current_param_names.update({"start_line", "end_line"})
                    # 符号定位参数仅locate_symbol需要，按工具名放行（file为通用词，避免进入全局白名单污染其它工具）
                    if tool_name == "locate_symbol":
                        current_param_names.update({"symbol", "file", "with_content"})
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
                        "locate_symbol": ["symbol"],
                        "get_project_tree": [],
                        "query_background_task": ["task_id"],
                        "cancel_background_task": ["task_id"]
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
            
            response += current_response + "\n" # 换行分隔指令:同步保留本轮AI原文（含工具调用原文）
            # 追加当前轮AI输出到结构化记忆
            structured_content += f"【第{current_round}轮交互】\nAI输出:{current_response}\n"
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
                            # P0-1: 进messages前统一截断+完整结果落盘（大仓库目录树兜底）
                            all_exec_results.append(truncate_tool_output("get_project_tree", len(all_exec_results) + 1, exec_result))
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
                                    exec_result = f"❌ {operation}操作失败：{file_name}\n{msg}\n⚠️ 分析工具调用失败原因：\n1.指令执行错误（锚点错误，：符号大小写错误导致匹配不上或者是锚点内容太少缺少唯一性，锚点内容必须整行），请向用户说明并执行一次重试；\n2. 工作台系统错误无法执行，已经执行第二次重试，请停止任务执行并向用户说明，给出可能性分析。"                                               
                            except Exception as e:
                                exec_result = f"❌ 编辑文件异常：{str(e)}\n⚠️ 分析工具调用失败原因：\n1. 指令执行错误（锚点错误，：符号大小写错误导致匹配不上或者是锚点内容太少缺少唯一性锚点内容必须整行），请向用户说明并执行一次重试；\n2. 工作台系统错误无法执行，已经执行第二次重试，请停止任务执行并向用户说明，给出可能性分析。"
                                add_operation_log("文件操作", f"❌ 编辑文件异常：{file_name}，错误：{str(e)}", "error")
                            
                            all_exec_results.append(exec_result)
                            continue
                        # ==================== 媒体读取（read_media）:图片直通 / 视频抽帧 ====================
                        # 设计要点:工具层只做「转码 + 登记像素 + 返回文字」，像素由消息构造层补插一条 user 多模态消息送达模型
                        if func_call.get("name") == "read_media":
                            media_params = func_call.get("parameters") or {}
                            media_path = (media_params.get("path") or "").strip()
                            media_start = media_params.get("start") or ""
                            media_duration = media_params.get("duration") or ""
                            # 宿主层可能为未传的可选参数注入空串，统一转字符串再 strip，避免被误判为"已传参"
                            media_start = (media_start if isinstance(media_start, str) else str(media_start)).strip()
                            media_duration = (media_duration if isinstance(media_duration, str) else str(media_duration)).strip()
                            if not media_path:
                                all_exec_results.append("❌ 参数错误:read_media 缺少必填参数 path（媒体文件路径，如 D:/xxx/a.png 或 D:/xxx/a.mp4）")
                                continue
                            # 路径标准化（与 read_file 同源入口，自动处理绝对/相对路径与斜杠格式）
                            media_abs_path = get_real_physical_path(media_path)
                            if not media_abs_path:
                                all_exec_results.append(f"❌ 路径为空:{media_path}")
                                continue
                            # 复用统一禁止路径校验:读取类操作，仅拦截保护目录下的高危可执行文件
                            media_forbidden, media_reason = is_path_forbidden(media_abs_path, operation_type="read")
                            if media_forbidden:
                                add_file_operation_log("read", media_path, "fail", media_reason)
                                all_exec_results.append(f"⚠️ {media_reason}，禁止读取")
                                continue
                            if not os.path.exists(media_abs_path):
                                all_exec_results.append(f"❌ 媒体文件不存在:{media_path}（标准化后路径:{media_abs_path}）\n⚠️ 请检查路径拼写是否正确，或文件是否已被移动，确认后重新调用。")
                                continue
                            if not os.path.isfile(media_abs_path):
                                all_exec_results.append(f"❌ 路径是文件夹不是文件:{media_path}（标准化后路径:{media_abs_path}）")
                                continue
                            # 扩展名一级粗分流:图片 / 视频 / 其他（真实类型以转码或探测结果为准）
                            media_ext = os.path.splitext(media_abs_path)[1].lower()
                            # 图片与视频扩展名集合（视频集合统一取 media_reader 内定义，避免重复维护）
                            import media_reader as _mr
                            _IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif", ".ico", ".psd", ".tga", ".pcx", ".dds", ".qoi", ".icns"}
                            if media_ext in _IMG_EXTS:
                                # 图片分支:三级降级转码（像素级 → 质量级 → 兜底只返元信息）
                                try:
                                    media_b64, media_meta = _mr.media_image_to_base64(media_abs_path)
                                except Exception as e:
                                    all_exec_results.append(f"❌ 图片读取失败:{media_path}（绝对路径:{media_abs_path}）\n原因:{e}\n💡 heic/avif/svg/相机RAW 等格式 PIL 无法解码，请先转换为 PNG/JPG 后再读取。")
                                    continue
                                _mtip = f"尺寸 {media_meta.get('width')}x{media_meta.get('height')}｜格式 {media_meta.get('format')}｜原始 {media_meta.get('original_size_mb')}MB｜输出 {media_meta.get('final_size_mb')}MB"
                                if not media_b64:
                                    # 第三级兜底:仅返回元信息文字，不登记像素（永不 OOM、永不爆 token）
                                    media_log_msg = f"✅ 读取图片成功（已降级为元信息）:{media_path}\n📸 {_mtip}\n⚠️ {media_meta.get('degrade_reason')}"
                                else:
                                    # 登记像素，由消息构造层补插一条 user 多模态消息送达模型
                                    _mr.register_media("image", media_abs_path, media_b64, media_meta)
                                    media_log_msg = f"✅ 读取图片文件成功:{media_path}（绝对路径:{media_abs_path}）\n📸 {_mtip}\n💡 图片像素已随本消息传入，可直接识别其中的文字、场景、物体与图表，无需再次读取。"
                                add_operation_log("文件操作", media_log_msg)
                                all_exec_results.append(media_log_msg)
                                continue
                            elif media_ext in _mr.VIDEO_EXTENSIONS:
                                # 视频分支（阶段B）:ffprobe 探测 → 停滞段扫描 → 五道闸门智能抽帧 → 逐帧三级降级 → 登记像素
                                # 起止时间支持纯秒数 / 分:秒 / 时:分:秒 三种写法，非法写法由 media_reader 返回明确纠正
                                _vres = _mr.extract_video_frames(media_abs_path, media_start or None, media_duration or None)
                                if _vres.get("ok"):
                                    _vframes = _vres.get("frames") or []
                                    _vstamps = [f.get("timestamp") for f in _vframes if isinstance(f, dict)]
                                    media_log_msg = (
                                        f"✅ 读取视频文件成功:{media_path}（绝对路径:{media_abs_path}）\n"
                                        f"{_vres.get('report') or _vres.get('message')}\n"
                                        f"💡 已抽取 {len(_vframes)} 帧（时间戳(s): {_vstamps}），帧像素已随本消息传入，可直接识别画面内容，无需再次读取。"
                                    )
                                else:
                                    media_log_msg = f"⚠️ 视频读取暂不可用:{media_path}\n{_vres.get('message')}"
                                add_operation_log("文件操作", media_log_msg)
                                all_exec_results.append(media_log_msg)
                                continue
                            else:
                                all_exec_results.append(f"⚠️ read_media 不支持该类型:{media_ext or '无扩展名'}（{media_path}）\n💡 支持图片（jpg/png/webp/gif/bmp 等）与视频（mp4/mov/mkv 等）；其他文件请改用 read_file 按文本读取。")
                                continue
                        if func_call.get("name") == "read_file":
                            file_name = func_call["parameters"]["file_name"].strip()
                            # P0-2: 可选按行翻页参数（大文件分段读取，避免全量内容撑爆上下文）
                            raw_start_line = func_call["parameters"].get("start_line")
                            raw_end_line = func_call["parameters"].get("end_line")
                            # 宿主层可能为未传的可选翻页参数注入空串，统一归一化为None，避免被误判为"已传参"
                            if isinstance(raw_start_line, str) and not raw_start_line.strip():
                                raw_start_line = None
                            if isinstance(raw_end_line, str) and not raw_end_line.strip():
                                raw_end_line = None
                            page_start, page_end = None, None
                            if raw_start_line is not None or raw_end_line is not None:
                                try:
                                    # 通配符*支持:双*=强制完整读取（显式传值可对抗宿主层对缺省参数自动注入历史行号）；
                                    # start数字+end*=从指定行读到文件末尾（由后续min(page_end,total_lines)钳制）；start*+end数字=1到N
                                    is_start_wild = isinstance(raw_start_line, str) and raw_start_line.strip() == "*"
                                    is_end_wild = isinstance(raw_end_line, str) and raw_end_line.strip() == "*"
                                    if is_start_wild and is_end_wild:
                                        # 双通配:保持None，走无分页完整读取分支
                                        page_start, page_end = None, None
                                    else:
                                        if raw_start_line is None or raw_end_line is None:
                                            raise ValueError("必须同时提供start_line和end_line")
                                        page_start = 1 if is_start_wild else int(raw_start_line)
                                        # 末尾通配给足够大的行号，由min(page_end, total_lines)钳制到真实末尾，翻页提示天然正常
                                        page_end = 10 ** 12 if is_end_wild else int(raw_end_line)
                                        if page_start < 1 or page_end < page_start:
                                            raise ValueError("行号范围非法")
                                except (TypeError, ValueError):
                                    all_exec_results.append("❌ 参数错误:read_file翻页参数非法，start_line/end_line必须同时为正整数且end_line≥start_line（行号从1开始）；需要完整读取文件时显式传start_line=*和end_line=*（可规避翻页参数被自动补全导致的超界错误），请修正参数后重试")
                                    continue
                            # 新增:记录AI读取文件日志
                            # 安全读取文件（优先读取当前选中项目下的文件，符合项目隔离要求）
                            def read_file_safe(fname, page_start=None, page_end=None):
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
                                    # P0-2: 按行翻页（严格行边界切片，保证edit_file整行锚点不被截断）
                                    if page_start is not None:
                                        all_lines = content.split("\n")
                                        total_lines = len(all_lines)
                                        if page_start > total_lines:
                                            add_operation_log("文件操作", f"⚠️ 翻页超出文件末尾:{fname}，共{total_lines}行")
                                            return f"❌ 参数错误:start_line={page_start}超出文件总行数{total_lines}，请用1-{total_lines}范围内的行号重新读取"
                                        seg_start = max(1, page_start)
                                        seg_end = min(page_end, total_lines)
                                        sliced = "\n".join(all_lines[seg_start - 1:seg_end])
                                        if CURRENT_PROJECT["project_root"] and target_file_path.startswith(os.path.normpath(CURRENT_PROJECT["project_root"]).replace("\\", "/")):
                                            page_log_msg = f"✅ 读取当前项目文件成功:{fname}（绝对路径:{target_file_path}）"
                                        else:
                                            page_log_msg = f"✅ 读取文件成功:{fname}（绝对路径:{target_file_path}）"
                                        step = seg_end - seg_start + 1
                                        prev_tip = f"上一段start_line={max(1, seg_start - step)}&end_line={seg_start - 1}" if seg_start > 1 else "已是文件开头"
                                        next_tip = f"下一段start_line={seg_end + 1}&end_line={min(total_lines, seg_end + step)}" if seg_end < total_lines else "已是文件末尾"
                                        add_operation_log("文件操作", page_log_msg + f"，翻页第{seg_start}-{seg_end}行/共{total_lines}行")
                                        return (f"{page_log_msg}\n📄 文件共{total_lines}行，当前显示第{seg_start}-{seg_end}行\n"
                                                f"📍 翻页提示:{prev_tip}；{next_tip}\n内容:\n{sliced}\n"
                                                f"📢 以上为文件第{seg_start}-{seg_end}行片段，需要其他段落用start_line/end_line继续翻页；根据读取信息执行下一步指令（注意:修改指令代码缩进要和原文匹配）。")
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
                            file_content = read_file_safe(file_name, page_start, page_end)
                            # P0-1: 进messages前统一截断+完整结果落盘（翻页片段通常不超长，截断为兜底）
                            all_exec_results.append(truncate_tool_output("read_file", len(all_exec_results) + 1, file_content))
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
                            # P0-1: 进messages前统一截断+完整结果落盘（RAG命中大文件片段时兜底）
                            all_exec_results.append(truncate_tool_output("rag_search", len(all_exec_results) + 1, exec_result))
                            continue
                        elif func_call.get("name") == "locate_symbol":
                            symbol = func_call["parameters"]["symbol"].strip()
                            file_arg = str(func_call["parameters"].get("file", "") or "").strip()
                            with_content = func_call["parameters"].get("with_content", True)
                            # 参数类型兜底:文本协议下布尔值可能以字符串传入
                            if isinstance(with_content, str):
                                with_content = with_content.strip().lower() not in ("false", "0", "no", "")
                            locate_result = ast_symbol_index.locate_symbol(symbol, file=file_arg or None, with_content=bool(with_content))
                            if not locate_result.get("found"):
                                exec_result = f"❌ 未定位到符号「{symbol}」:{locate_result.get('message', '')}"
                                add_operation_log("文件操作", exec_result, "error")
                                all_exec_results.append(exec_result)
                                continue
                            exec_result = f"✅ 符号定位结果（共 {locate_result['match_count']} 处，匹配方式:{locate_result.get('match_type')}）:\n"
                            add_operation_log("文件操作", f"✅ 符号定位结果:{symbol}\n")
                            for m in locate_result["matches"]:
                                header = (f"📄 符号:{m['qualified_name']}（类型:{m['type']}）\n"
                                          f"   文件:{m['file']}（绝对路径:{m['abs_path']}）\n"
                                          f"   行号:{m['start_line']}-{m['end_line']}\n"
                                          f"   签名:{m['signature']}\n")
                                exec_result += header
                                add_operation_log("文件操作", header)
                                if m.get("content"):
                                    exec_result += f"```\n{m['content']}\n```\n"
                            exec_result += "\n💡 已补齐文件绝对路径与精确行号:可直接用 read_file（start_line/end_line）读取，或用 edit_file（signature 整行作锚点）精确修改"
                            all_exec_results.append(truncate_tool_output("locate_symbol", len(all_exec_results) + 1, exec_result))
                            continue
                        elif func_call.get("name") == "exec_cmd":
                            cmd = func_call["parameters"]["cmd"].strip()
                            exec_result = ""
                            # P0-3: 危险命令判定改用段首程序名匹配，避免\bformat\b误杀Format-Table等PowerShell cmdlet
                            lower_cmd = cmd.lower()
                            is_dangerous = _contains_dangerous_command(cmd)
                            # 【2026-10-12 调整】按用户要求取消 & 命令拼接拦截（原「仅允许执行单条查询类命令」过严），
                            #   危险程序（rm/del/format/mkfs/dd 等）保护仍由 _contains_dangerous_command 段首匹配生效。
                            if is_dangerous:
                                exec_result = "❌ 禁止执行危险命令，仅允许执行查询类命令"
                                add_operation_log("AI执行命令", exec_result, "error")
                                all_exec_results.append(exec_result)
                                continue

                            # 域名白名单已于2026-09-15按用户要求取消:curl/wget允许访问任意网站
                            # P0-3: 超时时间从配置读取（默认60秒，前端配置中心可调）
                            try:
                                _exec_timeout = int(_get_tool_output_config().get("exec_cmd_timeout", 60))
                            except Exception:
                                _exec_timeout = 60
                            try:
                                # P0阶段:改用进程树执行器（Popen独立进程组+stdin=DEVNULL+stdout/stderr合并落盘），
                                # 超时后taskkill /F /T递归终止整棵进程树，杜绝孙进程持管道导致的永久阻塞
                                _tmp_task_id = "tmp_%s_%06d" % (time.strftime("%Y%m%d%H%M%S"),
                                                                 int.from_bytes(os.urandom(3), "big") % 1000000)
                                _handle = command_runner.start_command(cmd, cwd=None, task_id=_tmp_task_id)
                                _wait_r = command_runner.wait_or_promote(_handle, _exec_timeout)
                                if _wait_r.get("finished"):
                                    # 窗口内结束:读完整日志（runner内部双解码），继续走下方truncate_tool_output统一截断+完整落盘
                                    _output = command_runner.read_tail(_handle, lines=100000)
                                    _rc = _wait_r.get("returncode")
                                    # P0-3: returncode≠0必须如实报❌失败（原逻辑无视返回码永远报成功，AI拿着假成功继续干活导致任务跑偏）
                                    if _rc == 0:
                                        exec_result = f"✅ 命令执行成功:命令:{cmd} 标准输出:{_output} "
                                        add_operation_log("AI执行命令", f"执行命令成功:{cmd}")
                                    else:
                                        exec_result = (f"❌ 命令执行失败:命令:{cmd}，返回码:{_rc}\n"
                                                      f"输出（标准输出与标准错误按控制台顺序合并）:{_output}\n"
                                                      f"⚠️ 请根据返回码和错误信息分析失败原因、修正命令后重试，不要重复执行完全相同的失败命令")
                                        add_operation_log("AI执行命令", f"❌ 命令执行失败:{cmd}，返回码:{_rc}，错误:{_output[:200]}", "error")
                                else:
                                    # P1:等待窗口内未结束——自动提升为后台任务（不杀进程），对话当轮立即释放、任务继续跑完
                                    # 开关默认开；P2再下沉config.json的bg_task节点+设置页，此处读取失败一律按"开启"处理
                                    _bg_enabled = True
                                    try:
                                        _bg_enabled = bool(load_config().get("bg_task", {}).get("enabled", True))
                                    except Exception:
                                        _bg_enabled = True
                                    _bg_tid = None
                                    if _bg_enabled:
                                        _bg_tid = background_task_manager.background_task_manager.register_and_promote(
                                            _handle, cmd, req.session_id)
                                    if _bg_tid:
                                        # 提升成功:进程存活，返回§6.5结构化文案（含任务ID与两个工具用法、行为约束①-⑤）
                                        exec_result = background_task_manager.background_task_manager.build_promote_text(
                                            _bg_tid, cmd, _exec_timeout)
                                        add_operation_log("AI执行命令", f"🟢 命令已提升后台运行[{_bg_tid}]:{cmd}", "warning")
                                    else:
                                        # 开关关闭或同会话并发超限:回退P0行为，递归杀树并如实告知
                                        command_runner.terminate_tree(_handle)
                                        exec_result = (f"⏱️ 命令执行超时（超过{_exec_timeout}秒未结束），系统已递归终止整棵进程树（taskkill /F /T，cmd及其子进程、孙进程一并结束）:{cmd}\n"
                                                      f"终止前输出（最后200行）:{_wait_r.get('tail', '')}\n"
                                                      f"建议:①缩小输出范围（加过滤条件/head/tail/Select-Object -First等）；"
                                                      f"②改用read_file的start_line/end_line分页读取文件；"
                                                      f"③确属长耗时命令，可在配置tool_output.exec_cmd_timeout调大超时秒数")
                                        add_operation_log("AI执行命令", f"⏱️ 命令执行超时（{_exec_timeout}秒）已递归终止进程树:{cmd}", "warning")
                            except Exception as e:
                                exec_result = f"❌ 命令执行失败:{str(e)}向用户说明执行指令后得到结构化信息"
                                add_operation_log("AI执行命令",f"❌ 命令执行失败:{str(e)}")
                            # P0-1: 进messages前统一截断+完整结果落盘（超长终端输出的核心兜底）
                            all_exec_results.append(truncate_tool_output("exec_cmd", len(all_exec_results) + 1, exec_result))
                            continue

                        elif func_call.get("name") == "query_background_task":
                            # P1:查询后台任务状态/真实退出码/日志尾部（会话隔离，只能查本会话任务）
                            _bg_tid = (func_call["parameters"].get("task_id") or "").strip()
                            _snap = background_task_manager.background_task_manager.query(_bg_tid, req.session_id)
                            if not _snap:
                                exec_result = f"❌ 未找到属于当前会话的后台任务:{_bg_tid}（请核对任务ID，或该任务已过保留期被清理）"
                            else:
                                _tail = background_task_manager.background_task_manager.read_logs(_bg_tid, req.session_id, 200)
                                exec_result = background_task_manager.background_task_manager.build_query_text(_snap, _tail)
                            all_exec_results.append(exec_result)
                            continue

                        elif func_call.get("name") == "cancel_background_task":
                            # P1:用户手动终止——递归结束整棵进程树，文案明确"用户手动终止"
                            _bg_tid = (func_call["parameters"].get("task_id") or "").strip()
                            _snap = background_task_manager.background_task_manager.cancel(_bg_tid, req.session_id)
                            if not _snap:
                                exec_result = f"❌ 未找到属于当前会话的后台任务:{_bg_tid}，无法取消（请核对任务ID）"
                            else:
                                _tail = background_task_manager.background_task_manager.read_logs(_bg_tid, req.session_id, 200)
                                exec_result = background_task_manager.background_task_manager.build_cancel_text(_snap, _tail)
                                add_operation_log("AI执行命令", f"🛑 用户手动终止后台任务[{_bg_tid}]")
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
                                    # P0-1: 插件返回进messages前统一截断+完整结果落盘（插件输出不可控，必须兜底）
                                    plugin_exec_result = f"✅ 插件执行成功:{current_tool_name}\n{exec_result}"
                                    all_exec_results.append(truncate_tool_output(current_tool_name, len(all_exec_results) + 1, plugin_exec_result))
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
                            # 未知工具类型:本轮AI原文已在上方统一追加进response，此处不再重复追加
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
                # P1-9.3: 错误计数精细化——仅真正的执行失败（含❌且非参数/路径/格式纠正提示）才计数；
                # 路径拦截⚠️、参数错误、解析失败等给AI的纠正信号一律不计，避免长任务被连续3次误杀
                has_error = any(
                    "❌" in res and not any(marker in res for marker in _NON_FATAL_RESULT_MARKERS)
                    for res in all_exec_results
                )
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
                if remaining_calls == 1:
                    # 倒数第二次工具结果回灌时注入强制收尾指令（上限10即第9次工具后、上限20即第19次后，自动适配任意max_chat_rounds配置）
                    progress_info = (
                        f"\n🛑【系统强制提示】工具调用轮次已经用完，当前第{current_calls}次/当前轮次回复次数上限{max_tool_calls}次，仅剩1次回复机会。"
                        "下一轮禁止再出现【工具调用开始】等任何工具调用标记，必须立即停止调用工具，"
                        "直接输出当前任务的阶段性总结:①已完成的内容与执行结果；②未完成的事项明确告知用户，顺延到下一轮任务中执行。"
                    )
                elif remaining_calls <= 3:
                    progress_info = f"\n⚠️ 当前轮次回复次数即将用尽，当前第{current_calls}次/当前轮次回复次数上限{max_tool_calls}次（剩余{remaining_calls}次），请优先完成核心任务并准备收尾总结，收尾总结内容中向用户说明任务进度"
                else:
                    progress_info = f"\n📊 当前进度:第{current_calls}次/当前轮次回复次数上限{max_tool_calls}次（剩余{remaining_calls}次）"
                final_result += progress_info
                
                # ✅ 全量追加所有工具执行结果到结构化记忆
                structured_content += f"工具执行结果:{final_result}\n"
                messages.append({"role": "assistant", "content": current_response})
                messages.append({"role": "user", "content": final_result})
                # P0-6: 媒体像素补插——read_media 登记的图片/视频帧只能落在 user 角色多模态消息内（工具角色消息不接受 image_url 块）
                # 位置固定在 age_tool_messages 之前，否则刚插入的像素消息可能被老化归档；无登记则零开销跳过
                try:
                    import media_reader as _mr_push
                    _pending_media = _mr_push.take_media()
                    if _pending_media:
                        _media_cfg = _mr_push.get_media_config()
                        # 总量红线闸门:超出 media_total_max_mb 时按登记顺序裁剪（至少保留1项）
                        _total_limit = int(float(_media_cfg.get("media_total_max_mb", 2.0)) * 1024 * 1024)
                        _kept_media, _used_bytes, _dropped_cnt = [], 0, 0
                        for _item in _pending_media:
                            _item_bytes = int(len(_item.get("b64", "")) * 3 / 4)
                            if _kept_media and _used_bytes + _item_bytes > _total_limit:
                                _dropped_cnt += 1
                                continue
                            _kept_media.append(_item)
                            _used_bytes += _item_bytes
                        # 组装:第一块为文字说明，其后每项媒体一个 image_url 块
                        _media_lines = [f"📎 本次共读取 {len(_pending_media)} 项媒体，随本消息传入 {len(_kept_media)} 项:"]
                        _media_blocks = [{"type": "text", "text": ""}]
                        for _idx, _item in enumerate(_kept_media, 1):
                            _m = _item.get("meta") or {}
                            _kind_cn = "图片" if _item.get("kind") == "image" else "视频帧"
                            _media_lines.append(
                                f"{_idx}. [{_kind_cn}] {_item.get('path')}｜"
                                f"{_m.get('width')}x{_m.get('height')}｜输出 {_m.get('final_size_mb')}MB"
                            )
                            _media_blocks.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:{_m.get('mime', 'image/jpeg')};base64,{_item.get('b64')}"},
                            })
                        if _dropped_cnt:
                            _media_lines.append(f"⚠️ 受总量上限 {_media_cfg.get('media_total_max_mb')}MB 限制，已裁剪 {_dropped_cnt} 项未传入")
                        _media_blocks[0]["text"] = "\n".join(_media_lines)
                        messages.append({"role": "user", "content": _media_blocks})
                        add_operation_log("文件操作", f"✅ 已补插多模态消息:{len(_kept_media)} 项媒体像素传入模型")
                except Exception as _media_e:
                    # 补插失败不阻断主流程（工具文字结果里已说明读取情况），仅记录日志便于排查
                    add_operation_log("文件操作", f"⚠️ 媒体像素补插失败:{_media_e}", "error")
                # P0-5: 跨轮老化——messages总字符超60000时，把最老的工具结果（保护最近2代）原地替换为一行结论+落盘指针，单轮最多归档3条
                age_tool_messages(messages, current_round)
                continue
            # ========== 无工具调用直接停止 ==========
            # 【2026-10-13 根因修复·取消静默收尾（主控侧对齐次级侧已验证口径）】
            # 原逻辑:all_exec_results 为空 → 直接 break 收尾。存在一种盲区:
            #   模型输出里有工具调用开始标记（_a2b_tk_o），却因生成被截断（连"独占一行"的
            #   完整开始标记都没成形）→ 补全器够不着、A2B 切块也扫不到 → all_exec_results 为空
            #   → 被误判成"模型已给出总结" → 静默 break → 主控链路断开、用户永久失联。
            # 按用户口径:闭环只能由「模型不再调工具、给出总结」体现，代码不得代判。
            #   ① 输出里无开始标记 → 真·模型已给总结 → 正常 break（唯一合法闭环出口）;
            #   ② 输出里有开始标记但本轮零可执行块 → 截断异常，回灌纠错提示让模型重发。
            #   轮次上限（max_tool_calls，配置项）天然封顶;不设深度上限，回到模型自己判断。
            if _a2b_tk_o in current_response:
                print("[API] 检测到工具调用开始标记但本轮无完整可执行块，已回灌纠错提示要求模型重发")
                messages.append({"role": "assistant", "content": current_response})
                messages.append({"role": "user", "content": (
                    "⚠️【系统提示】你上一条回复中的工具调用块不完整:缺少"
                    "「工具名称」/「参数列表」/「" + _a2b_tk_c + "」中的一项或多项，系统无法执行。"
                    "请重新完整输出该工具调用块（四部分必须齐全），不要输出任何额外解释。")})
                continue
            # 没有任何工具执行结果，说明AI已经返回最终答案，直接停止循环
            # 本轮AI原文已在上方统一追加进response；此处仅在response为空时兜底，避免重复追加
            if not response.strip():
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
            # P0-4: 致命错误必须跳出while，否则下一轮带着异常上下文继续推理，造成任务假死/中途断流
            break

    # P0-4: done事件从循环内finally移到while外，整轮任务只推送一次
    # （原位置每轮工具调用都推done，前端误判任务结束提前关闭通道/熄灭能量条，是任务中断的核心原因之一）
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
        # 【P1·根因修复】上下文净化（顺序调整:摘要替换提前、裸JSON剥离与空行收敛后置）
        #   ① 保留「第N轮交互」轮次标记（结构化多轮，便于日后排查），仅去掉"AI输出:"前缀
        #   ② 去掉工具调用原文块（严格成对匹配「工具调用开始…工具调用结束」），工具结果摘要行保留
        #   ③ 空行收敛改到摘要替换之后统一执行（见下方后置净化）
        final_structured = re.sub(r'(【第\d+轮交互】)\s*\n?AI输出[::]\s*', r'\1\n', final_structured)
        # 标记拆分拼接:规避外层指令解析截断（源码中不出现连续完整标记）
        _TK_O = chr(0x3010) + "工具调用" + "开始" + chr(0x3011)
        _TK_C = chr(0x3010) + "工具调用" + "结束" + chr(0x3011)
        final_structured = re.sub(_TK_O + r'[\s\S]*?' + _TK_C + r'\s*', '', final_structured)
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
        # 【M2·根因修复·后置】剥离"无标记包裹的裸工具调用对象"（模板版本字段形态）:
        #   已后置到全部摘要替换之后（大段含 `{` 的原文已被压成一行），误命中率降到接近 0
        final_structured = _strip_naked_tool_json(final_structured)
        # 收敛连续空行，避免历史里出现大片空白（后置到净化最后一步）
        final_structured = re.sub(r'\n{3,}', '\n\n', final_structured).strip()
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
    # 同步更新全局持久化历史，自动按配置轮数轮动（取当前模型槽位 max_chat_rounds，缺失回退全局）
    from model_registry import get_slot_config as _get_slot_cfg_save
    _save_slot_cfg = _get_slot_cfg_save(int(getattr(req, "model_slot", 1) or 1)) or {}
    _save_hist_rounds = int(_save_slot_cfg.get("max_chat_rounds", 0) or 0) or memory_cache.config["history_context_rounds"]
    save_global_history(req.query, final_structured, _save_hist_rounds)

    # 记忆落盘后推送"整轮真正结束"信号:前端收到memory_saved事件才熄灭能量条
    # add_memory在全部工具链完成后同步执行，是比ai_output/done更晚的业务终态；
    # 置于if块外无条件发送（即使本轮无记忆写入），对话确实结束，能量条不会卡死
    push_sse_message(req.session_id, {
        "type": "memory_saved",
        "timestamp": time.time()
    })

    # T4: 解析主控回复中的 @角色 → 自动派发（对话驱动主线 甲-2/甲-2a/Q3）
    # 旁路派发:仅当主控回复命中可用角色 mention 时触发;任何异常只打印,绝不改原返回值
    # [DISPATCH-DIAG] 临时诊断日志（定位"回复带 @角色却没派发"真因，定位后删除本段）
    try:
        _resp_txt = str(response or "")
        # 【P2·根因修复 + R7 口径统一】派发前净化:检测与投递均改用净化版 _resp_txt_clean；
        #   目的:避免"轮次标记 + 工具调用原文 + 前几轮全文 + edit_file 可视化块"污染检测与次级对话窗口。
        import re as _re_disp
        _resp_txt_clean = _re_disp.sub(r'【第\d+轮交互】\s*\n?AI输出[::]\s*', '', _resp_txt)
        # 【R8·根因修复】剥离 edit_file 可视化块（🔧 修改操作标记 + 其后被改内容），避免块内含「行首@角色」的正文被派发检测误判；
        #   结束边界:下一个裸工具JSON块 / 下一可视化块 / 轮次标记 / 工具调用块 / 文末。
        #   ⚠️ 冒号用正则 Unicode 转义 [\uFF1A:]（全角 U+FF1A + 半角 :）—— 规避编辑工具对全角字符的归一化，真实生产者 L2224 用全角「:」必命中。
        _resp_txt_clean = _re_disp.sub(r'🔧 \*\*修改操作[\uFF1A:][^\n]*\*\*[\s\S]*?(?=\{\s*\n?\s*"(?:__template_version|name)"\s*:|🔧 \*\*修改操作[\uFF1A:]|【第\d+轮交互】|【工具调用|\Z)', '', _resp_txt_clean)
        _resp_txt_clean = _re_disp.sub(r'【工具调用[^\n]*】[\s\S]*?【工具调用[^\n]*】\s*', '', _resp_txt_clean)
        _resp_txt_clean = _re_disp.sub(r'\n{3,}', '\n\n', _resp_txt_clean).strip()
        # 【M3·根因修复】剥离"无标记包裹的裸工具调用对象"，避免其原样派发进次级对话窗口
        #   净化后为空则回退原文兜底，避免派发出空需求
        _resp_txt_clean = _strip_naked_tool_json(_resp_txt_clean).strip() or _resp_txt.strip()
        print(f"[DISPATCH-DIAG] enter sid={req.session_id} resp_len={len(_resp_txt)}")
        if _resp_txt.strip():
            _pool = _orch.build_role_pool()
            print(f"[DISPATCH-DIAG] pool_len={len(_pool)} slots={[it.get('slot') for it in _pool]}")
            # 【R7·根因修复】派发检测改用净化版 _resp_txt_clean（与 :3275 投递口径统一）:块内@角色不再误命中；块外合法派发行净化后保留，不误伤。
            _slot = _orch.extract_dispatch_mentions(_resp_txt_clean, _pool)
            print(f"[DISPATCH-DIAG] extract_slot={_slot} resp_head={_resp_txt_clean[:200]!r}")
            if _slot is not None:
                # 透传当前项目名，任务 meta 记录归属项目 → 次级对话按「项目 × 槽位」双维度隔离
                # 【P2·根因修复】投递净化版文本（不含轮次标记与工具调用原文块），避免次级被主控中间态污染
                _disp = _orch.submit_by_mention(_resp_txt_clean, req.session_id, forced_slot=_slot,
                                                project_name=current_project_name)
                print(f"[DISPATCH-DIAG] submit ok={_disp.get('ok')} msg={_disp.get('msg')} task_id={_disp.get('task_id')}")
                print(f"[Dispatch] mention派发 slot={_slot} ok={_disp.get('ok')} task_id={_disp.get('task_id')}")
        else:
            print(f"[DISPATCH-DIAG] empty response, skip dispatch")
    except Exception as _e:
        import traceback as _tb
        print(f"[DISPATCH-DIAG] EXCEPTION: {_e}")
        print(_tb.format_exc())
        print(f"[Dispatch] mention派发失败（已忽略，不影响对话）: {_e}")

    # 新增:记录AI回复完成日志
    return {"response": response, "recalled_memory_count": len(recall_result["memory_recall"]), "session_id": req.session_id}

@app.get("/api/chat/stream/{session_id}")
async def chat_stream(session_id: str, fast: bool = False):
    """SSE流式推送AI输出通道，完全独立于推理逻辑，实现显示与推理100%解耦

    【方案A·回放提速】fast 参数（query: ?fast=1）:
      · 仅影响「建连时的历史快照回放节奏」，与实时流式完全无关（实时 chunk 不受任何影响）；
      · fast=False（默认）:保持原 18ms/条 打字机节奏；
      · fast=True（前端切回/刷新时使用）:回放 0ms 快发，整体从秒级压到毫秒级；
      · 回放的内容 / 顺序 / 条数 100% 不变，仅改下发节奏 —— 前端气泡最终形态与逐字回放完全一致。
    """
    global global_event_loop
    import asyncio
    global_event_loop = asyncio.get_running_loop()
    queue = asyncio.Queue()
    # 订阅池模式:同一会话可挂多个窗口队列，实现双窗实时同达（对齐 RECALL_SUBSCRIBERS 范式）
    SSE_CONNECTIONS.setdefault(session_id, set()).add(queue)
    
    async def event_generator():
        # 【新增·根因级】连接建立时，对「次级通道 sec_{slot}」一次性重放当前轮快照。
        # 根因:次级事件由编排器在后台线程主动推送（先于浏览器 EventSource 建连），
        #      旧实现在"无订阅者"时直接丢弃 → 用户必须切页回读才能看到内容。
        # 范围:仅 sec_ 前缀通道；主控 default 保持原状（它已有 syncLastOutput 快照拉取兜底，
        #      若此处也重放会造成双通道重复显示，故显式排除）。
        if session_id.startswith("sec_"):
            try:
                _snap0 = SESSION_LAST_OUTPUT.get(session_id)
                _rev = list(_snap0.get("events") or []) if _snap0 else []
                if _rev:
                    # 【回放节奏真实化·新增】先下发"回放开始"标记与总条数，
                    # 前端据此进入"回放期"（期间不做整段重建式合并，保护逐字气泡不被旧落盘内容顶掉）。
                    _begin = json.dumps({"type": "sec_replay_begin", "total": len(_rev)},
                                        ensure_ascii=False).replace('\n', '\\n').replace('\r', '\\r')
                    yield f"data: {_begin}\n\n"
                    # 【回放节奏真实化·重写】按事件类型分速回放（替换原"固定 5ms / 超 300 条压到 1.5s"口径）:
                    #   · ai_output_stream / ai_reasoning / think（逐字正文与思考）→ 18ms/条（≈55 字/秒，接近真人打字节奏）；
                    #   · dispatch / report / ai_output / secondary_summary（结构性节点）→ 5ms/条；
                    #   · 总时长上限 12 秒:超出按比例整体压缩，单条下限保底 2ms（长任务回放不至于久等）。
                    # 【方案A·回放提速】节奏常量按 fast 参数分支（默认保持原口径不变）:
                    #   · 默认（fast=False）:18ms/5ms 打字机节奏 + 12s 总时长上限（实时任务进行中的流式观感不受影响）；
                    #   · fast=True:正文与元事件统一 0ms + 0.5s 总上限 → 回放瞬间铺完；
                    #     配合下方循环体的"每 50 条 sleep(0) 让出事件循环"，避免一次性大量 yield 堵住 asyncio 主循环。
                    if fast:
                        _IV_TEXT = 0.0
                        _IV_META = 0.0
                        _TOTAL_CAP = 0.5
                        _IV_FLOOR = 0.0
                    else:
                        _IV_TEXT = 0.018
                        _IV_META = 0.005
                        _TOTAL_CAP = 12.0
                        _IV_FLOOR = 0.002
                    _text_kinds = ("ai_output_stream", "ai_reasoning", "think")
                    _est_total = 0.0
                    for _ev in _rev:
                        _et0 = str(_ev.get("type") or "") if isinstance(_ev, dict) else ""
                        _est_total += _IV_TEXT if _et0 in _text_kinds else _IV_META
                    _scale = (_TOTAL_CAP / _est_total) if (_est_total > _TOTAL_CAP and _est_total > 0) else 1.0
                    # 【回放期排空实时队列·新增】每回放一条前，先排空一次 queue 并暂存到 _pending_live:
                    #   避免"回放期间生成器停在 for 循环里、不消费实时队列"，
                    #   导致回放期间新到的实时 chunk 全堆在 queue、回放结束时一次性涌出（又一次整段蹦出）。
                    _pending_live = []
                    # 【方案A·回放提速】_emitted:统计已下发条数，仅 fast 模式（_iv==0）时使用——
                    #   每 50 条主动 sleep(0) 让出事件循环一次，保证毫秒级铺完的同时不阻塞心跳/取消信号处理。
                    _emitted = 0
                    for _ev in _rev:
                        try:
                            while True:
                                try:
                                    _pending_live.append(queue.get_nowait())
                                except asyncio.QueueEmpty:
                                    break
                            _et = str(_ev.get("type") or "") if isinstance(_ev, dict) else ""
                            _base = _IV_TEXT if _et in _text_kinds else _IV_META
                            _iv = max(_IV_FLOOR, _base * _scale)
                            _es = json.dumps(_ev, ensure_ascii=False).replace('\n', '\\n').replace('\r', '\\r')
                            yield f"data: {_es}\n\n"
                            # 【方案A·回放提速】分发节奏分支:
                            #   · _iv > 0（默认 fast=False）→ 走原有单条 sleep 节奏，观感完全不变；
                            #   · _iv == 0（fast=True）→ 每 50 条 sleep(0)，避免一次性大量 yield 把
                            #     asyncio 事件循环堵住（否则心包/取消信号将无法及时处理）。
                            if _iv > 0:
                                await asyncio.sleep(_iv)
                            else:
                                _emitted += 1
                                if _emitted % 50 == 0:
                                    await asyncio.sleep(0)
                        except Exception:
                            continue
                    # 【回放期排空实时队列·新增】回放结束后，先把暂存的实时事件按原序补发，
                    #   再进入下方 while True 实时循环（既不堆积堆爆内存，也不丢事件）。
                    for _pd in _pending_live:
                        try:
                            _ps = json.dumps(_pd, ensure_ascii=False).replace('\n', '\\n').replace('\r', '\\r')
                            yield f"data: {_ps}\n\n"
                        except Exception:
                            continue
                    # 【回放节奏真实化·新增】下发"回放结束"标记，前端据此解除保护并做一次最终对齐。
                    _end = json.dumps({"type": "sec_replay_end"}, ensure_ascii=False).replace('\n', '\\n').replace('\r', '\\r')
                    yield f"data: {_end}\n\n"
                elif _snap0 and (_snap0.get("query") or _snap0.get("reasoning") or _snap0.get("output")):
                    # 兼容老会话（本次改动前产生的快照无 events 字段）→ 退回单条 sec_snapshot 补齐
                    _replay = {
                        "type": "sec_snapshot",
                        "query": _snap0.get("query") or "",
                        "reasoning": _snap0.get("reasoning") or "",
                        "output": _snap0.get("output") or "",
                        "done": bool(_snap0.get("done")),
                    }
                    _rs = json.dumps(_replay, ensure_ascii=False).replace('\n', '\\n').replace('\r', '\\r')
                    yield f"data: {_rs}\n\n"
            except Exception as _re:
                print(f"[SSE] 次级快照重放失败（已忽略，不影响实时流）: {_re}")
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
            # 无论正常还是异常，都清理本连接，避免残留无效队列导致消息丢失
            # 订阅池模式:仅移除本连接队列，不影响同会话其他窗口
            _qs = SSE_CONNECTIONS.get(session_id)
            if _qs is not None:
                _qs.discard(queue)
                if not _qs:
                    SSE_CONNECTIONS.pop(session_id, None)
    
    return EventSourceResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/chat/last_output/{session_id}")
async def get_last_output(session_id: str):
    """方案A:返回指定会话本轮输出的实时快照（query/reasoning/output/done），供前端切回后补齐断线期间丢弃的流式增量"""
    snap = SESSION_LAST_OUTPUT.get(session_id)
    if not snap:
        return {"code": 200, "data": None}
    return {"code": 200, "data": snap}
# ===== 会话消息持久化（方案A:重启后对话不丢，与 latest_chat_history_*.json 记忆文件完全隔离）=====
class ChatHistorySaveRequest(BaseModel):
    project: str = "default"
    messages: List[Dict[str, Any]] = []

def _safe_chat_history_file(project: str) -> str:
    """获取项目对应的会话消息持久化文件路径（sessions/chat_{项目}.json）"""
    safe = re.sub(r'[\\/*?:"<>|]', "_", project or "default")
    safe = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5_-]', "_", safe) or "default"
    sessions_dir = os.path.join(BASE_DIR, "sessions")
    os.makedirs(sessions_dir, exist_ok=True)
    return os.path.join(sessions_dir, f"chat_{safe}.json")

@app.post("/api/chat/history/save")
async def save_chat_history(req: ChatHistorySaveRequest):
    """方案A:持久化前端对话消息数组（user/ai/think/task），与 origin/端口无关，重启后前端可回读"""
    try:
        path = _safe_chat_history_file(req.project)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(req.messages, f, ensure_ascii=False, indent=2)
        return {"code": 200, "msg": "ok"}
    except (OSError, IOError) as e:
        return JSONResponse(status_code=500, content={"code": 500, "msg": f"保存失败:{e}"})

@app.get("/api/chat/history/load")
async def load_chat_history(project: str = "default"):
    """方案A:读取指定项目的会话消息数组，供前端启动时回读（localStorage 为空时的兜底）"""
    try:
        path = _safe_chat_history_file(project)
        if not os.path.exists(path):
            return {"code": 200, "data": []}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"code": 200, "data": data if isinstance(data, list) else []}
    except (json.JSONDecodeError, OSError, IOError):
        return {"code": 200, "data": []}

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
    
    # 上传后清理超量旧文件（保留最新 100 个）
    _cleanup_upload_dir()
    
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
        _cleanup_upload_dir()
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
                # 安全审核修复:command必须是非空字符串，杜绝数组/对象等异常类型透传
                if not command or not isinstance(command, str) or not command.strip():
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                    TASK_STORAGE[task_id]["progress"] = "❌ 参数错误:缺少command参数或参数类型非法"
                    return
                command = command.strip()
                # 安全审核修复:与对话链路exec_cmd同一防护标准——段首危险程序名匹配
                # 【2026-10-12 调整】按用户要求取消 & 命令拼接拦截，仅保留危险程序段首匹配保护。
                _lower_cmd = command.lower()
                if _contains_dangerous_command(command):
                    TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                    TASK_STORAGE[task_id]["progress"] = "❌ 禁止执行危险命令，仅允许执行查询类命令"
                    add_operation_log("AI执行命令", f"网页异步任务拦截危险命令:{command}", "error")
                    return
                # 安全审核修复:timeout整数归一+钳制到1~1800秒（上限与后台任务硬超时一致），非法值回退30秒
                try:
                    timeout = int(timeout)
                except (TypeError, ValueError):
                    timeout = 30
                timeout = max(1, min(timeout, 1800))
                try:
                    # P0阶段:网页异步任务同款缺陷一并修复，改走进程树执行器，超时递归终止整树
                    _web_task_id = "webtask_%s_%06d" % (time.strftime("%Y%m%d%H%M%S"),
                                                        int.from_bytes(os.urandom(3), "big") % 1000000)
                    _handle = command_runner.start_command(command, cwd=None, task_id=_web_task_id)
                    _wait_r = command_runner.wait_or_promote(_handle, timeout)
                    if not _wait_r.get("finished"):
                        command_runner.terminate_tree(_handle)
                        TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                        TASK_STORAGE[task_id]["progress"] = f"❌ 命令执行超时（超过{timeout}秒），系统已递归终止整棵进程树"
                        TASK_STORAGE[task_id]["result"] = {"command": command, "output": _wait_r.get("tail", ""), "returncode": None}
                    else:
                        output = command_runner.read_tail(_handle, lines=100000)
                        rc = _wait_r.get("returncode")
                        TASK_STORAGE[task_id]["result"] = {"command": command, "output": output, "returncode": rc}
                        if rc == 0:
                            TASK_STORAGE[task_id]["status"] = TASK_STATUS_SUCCESS
                            TASK_STORAGE[task_id]["progress"] = f"✅ 命令执行成功，返回{len(output)}字符输出"
                        else:
                            TASK_STORAGE[task_id]["status"] = TASK_STATUS_FAILED
                            TASK_STORAGE[task_id]["progress"] = f"❌ 命令执行失败，返回码:{rc}，错误信息:{output[:200]}"
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

# ==================== 阶段4 任务编排器接口（6态状态机 + 三条硬终止）====================
# 注意:与上方旧「工具任务」(/api/task/*) 路径严格分离,互不覆盖

class OrchestratorSubmitRequest(BaseModel):
    requirement: str  # 开发需求描述
    session_id: str = "default"


@app.post("/api/orch/submit")
async def orch_submit(req: OrchestratorSubmitRequest):
    """提交编排任务:建任务 + 异步派发（主控→开发→审查→裁决），立即返回 task_id（不阻塞）"""
    try:
        import orchestrator as orch
        result = orch.submit_task(req.requirement, req.session_id)
        if not result.get("ok"):
            add_operation_log("任务编排", f"❌ 提交失败:{result.get('msg')}", "error")
            return {"code": 400, "msg": result.get("msg", "提交失败"), "data": None}
        add_operation_log("任务编排", f"✅ 提交任务 #{result.get('task_id')}")
        return {"code": 200, "msg": "任务已提交", "data": result}
    except Exception as e:
        add_operation_log("任务编排", f"❌ 提交异常:{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"任务编排提交失败: {str(e)}")


@app.get("/api/orch/query")
async def orch_query(task_id: str):
    """查询编排任务:meta 快照（state/history）+ 开发/审查次级会话全文"""
    try:
        import orchestrator as orch
        result = orch.query_task(task_id)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("msg", "任务不存在"))
        return {"code": 200, "msg": "ok", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"编排任务查询失败: {str(e)}")


@app.get("/api/orch/list")
async def orch_list(session_id: str = "default"):
    """列出指定会话下全部编排任务（按 task_id 升序）"""
    try:
        import orchestrator as orch
        return {"code": 200, "msg": "ok", "data": orch.list_tasks(session_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"编排任务列表失败: {str(e)}")


@app.post("/api/orch/abort")
async def orch_abort(req: Request):
    """中止编排任务；body: {task_id}"""
    try:
        data = await req.json()
        task_id = (data.get("task_id") or "").strip()
        if not task_id:
            raise HTTPException(status_code=400, detail="缺少 task_id")
        import orchestrator as orch
        result = orch.abort_task(task_id)
        if not result.get("ok"):
            return {"code": 400, "msg": result.get("msg", "中止失败"), "data": None}
        add_operation_log("任务编排", f"🛑 用户中止任务 #{task_id}")
        return {"code": 200, "msg": "任务已中止", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"编排任务中止失败: {str(e)}")


@app.get("/api/orch/roles")
async def orch_roles():
    """当前可用角色池快照（槽位 / 人设 / 连通状态），供前端展示当前可接活儿的角色"""
    try:
        import orchestrator as orch
        return {"code": 200, "msg": "ok", "data": orch.get_role_pool_brief()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"角色池查询失败: {str(e)}")


@app.get("/api/orch/secondary_history")
async def orch_secondary_history(session_id: str = "default", slot: int = 0, project_name: str = ""):
    """次级对话页历史回读（方案A/B-1）:按会话+槽位筛选次级会话（dev/review）历史消息，补齐 SSE 无回溯缺口

    - project_name（新增,可选）:非空时按项目维度再多筛一层，实现「项目 × 槽位」双维度隔离；
      不传 → 保持原行为（旧调用零回归）。
    """
    try:
        import orchestrator as orch
        return {"code": 200, "msg": "ok", "data": orch.get_secondary_history(session_id, slot, project_name)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"次级会话历史回读失败: {str(e)}")
# ==================== P1 后台任务 HTTP 接口（供 P2 任务卡片/前端查询，核心对话链路不依赖）====================

@app.get("/api/bg_task/list")
async def bg_task_list(session_id: str = "default"):
    """列出指定会话的全部后台任务（不含进程句柄），按开始时间升序"""
    items = background_task_manager.background_task_manager.list_session(session_id)
    return {"code": 200, "data": items}


@app.post("/api/bg_task/cancel")
async def bg_task_cancel(req: Request):
    """手动取消后台任务（递归终止整棵进程树）；body: {session_id, task_id}"""
    data = await req.json()
    session_id = (data.get("session_id") or "default").strip() or "default"
    task_id = (data.get("task_id") or "").strip()
    if not task_id:
        raise HTTPException(status_code=400, detail="缺少 task_id")
    snap = background_task_manager.background_task_manager.cancel(task_id, session_id)
    if not snap:
        raise HTTPException(status_code=404, detail="未找到属于当前会话的后台任务")
    add_operation_log("AI执行命令", f"🛑 用户手动终止后台任务[{task_id}]")
    return {"code": 200, "data": snap, "msg": "任务已递归终止"}


@app.get("/api/bg_task/logs")
async def bg_task_logs(task_id: str, session_id: str = "default", lines: int = 200):
    """读取后台任务日志尾部（会话隔离，只能读本会话任务）"""
    tail = background_task_manager.background_task_manager.read_logs(task_id, session_id, lines)
    if tail is None:
        raise HTTPException(status_code=404, detail="未找到属于当前会话的后台任务")
    return {"code": 200, "data": {"task_id": task_id, "tail": tail}}


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
        # 文件树"只标记不过滤":被隔离条目照常返回，前端淡显+标注"已隔离"，
        # 保证用户仍可右键解除隔离（若此处直接隐藏会形成"无法解除"的死锁）
        file_list.append({
            "name": item,
            "path": os.path.relpath(item_path, REPOSITORY_PATH).replace("\\", "/"),
            "is_dir": is_dir,
            "size": stat.st_size if not is_dir else 0,
            "modify_time": stat.st_mtime,
            "is_isolated": file_filter_config.is_isolated_path(item_path)
        })
    sorted_list = sorted(file_list, key=lambda x: (-x["is_dir"], x["name"]))
    # 自动建议:条目数超过阈值时提示"建议隔离"（阈值统一来自 isolation_config.json，前端不硬编码）
    _iso_cfg = isolation_manager.list_paths()
    return {
        "code": 200,
        "data": sorted_list,
        "suggest_threshold": _iso_cfg.get("suggest_threshold", 300),
        "suggest_isolation": isolation_manager.check_suggest(len(sorted_list))
    }


class IsolationPathReq(BaseModel):
    """项目信息隔离接口请求体:统一承载单条路径"""
    path: str = ""


def _trigger_manual_resync():
    """隔离清单变更后立即触发一次当前项目手册同步

    作用:让手册第二/三章中"已被隔离路径"的原有条目在本次变更后立刻消失，
    而不是等到下一次文件事件才消失（无内容变化时内部短路，不会产生冗余写盘）。
    """
    try:
        project_root = (CURRENT_PROJECT or {}).get("project_root") or ""
        if not project_root or not os.path.isdir(project_root):
            return
        # 按命名约定在项目根目录查找项目手册（*项目手册.md）
        manual_file = ""
        for name in os.listdir(project_root):
            if name.endswith("项目手册.md"):
                manual_file = name
                break
        if not manual_file:
            return
        # 懒加载手册管理器，避免模块级循环依赖
        from project_manual_manager import ProjectManualManager
        manual_rel = os.path.relpath(
            os.path.join(project_root, manual_file), REPOSITORY_PATH
        ).replace("\\", "/")
        ProjectManualManager().update_manual_detail_table(manual_rel)
        add_operation_log("文件操作", "✅ 隔离清单变更后已同步项目手册")
    except Exception as e:
        print(f"⚠️ 隔离清单变更后同步手册失败:{str(e)}")


@app.get("/api/isolation/list")
async def get_isolation_list():
    """查询当前"项目信息隔离"清单、阈值与启用状态（供文件仓库页面加载时渲染）"""
    data = isolation_manager.list_paths()
    data["repository_path"] = REPOSITORY_PATH.replace("\\", "/")
    return {"code": 200, "data": data}


@app.post("/api/isolation/add")
async def add_isolation(req: IsolationPathReq):
    """把指定路径加入"项目信息隔离"清单（目录则整棵子树由前缀匹配自动命中）

    加入后:该路径及其全部子孙不再进入 AI 上下文/项目手册第二三章/RAG索引。
    """
    rel_path = (req.path or "").strip()
    if not rel_path:
        raise HTTPException(status_code=400, detail="路径不能为空")
    # 边界保护:禁止隔离仓库根目录（会导致手册二/三章被清空）
    _root_norm = os.path.normpath(REPOSITORY_PATH).replace("\\", "/").lower()
    _target_norm = os.path.normpath(os.path.join(REPOSITORY_PATH, rel_path)).replace("\\", "/").lower()
    if _target_norm == _root_norm:
        raise HTTPException(status_code=400, detail="不允许隔离仓库根目录")
    data = isolation_manager.add_path(rel_path)
    add_operation_log("文件操作", f"✅ 已加入项目信息隔离:{rel_path}")
    _trigger_manual_resync()
    return {"code": 200, "data": data, "msg": "已加入项目信息隔离"}


@app.post("/api/isolation/remove")
async def remove_isolation(req: IsolationPathReq):
    """解除"项目信息隔离"（同时清理该路径下的全部子路径，避免残留悬挂项）"""
    rel_path = (req.path or "").strip()
    if not rel_path:
        raise HTTPException(status_code=400, detail="路径不能为空")
    data = isolation_manager.remove_path(rel_path)
    add_operation_log("文件操作", f"✅ 已解除项目信息隔离:{rel_path}")
    _trigger_manual_resync()
    return {"code": 200, "data": data, "msg": "已解除项目信息隔离"}

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
@app.get("/api/file/open_repository")
async def open_repository_folder():
    """用系统资源管理器打开仓库根目录"""
    import subprocess
    repo_path = REPOSITORY_PATH
    if not repo_path or not os.path.exists(repo_path):
        raise HTTPException(status_code=404, detail="仓库目录不存在")
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(repo_path)
        elif system == "Darwin":
            subprocess.run(["open", repo_path], check=True, capture_output=True, timeout=5)
        else:
            subprocess.run(["xdg-open", repo_path], check=True, capture_output=True, timeout=5)
        add_file_operation_log("open_repository", repo_path, "success", f"打开仓库目录成功，路径:{repo_path}")
        return {"code": 200, "msg": "已用资源管理器打开仓库目录", "repo_path": repo_path}
    except Exception as e:
        err_msg = f"打开仓库目录失败: {str(e)}"
        add_file_operation_log("open_repository", repo_path, "fail", err_msg)
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


# -------------------------- 文件复制（粘贴）接口 --------------------------
class FileCopyRequest(BaseModel):
    src_path: str
    dest_dir: str


@app.post("/api/file/copy")
async def copy_file(request: FileCopyRequest):
    """复制文件或文件夹到指定目录（源保留），供文件仓库右键"复制/粘贴"使用"""
    repo_root = os.path.normpath(REPOSITORY_PATH)
    src_path = os.path.normpath(os.path.join(REPOSITORY_PATH, request.src_path))
    dest_dir = os.path.normpath(os.path.join(REPOSITORY_PATH, request.dest_dir))

    # 路径穿越校验:源与目标都必须位于仓库根目录内（dest_dir为空字符串时等于仓库根，允许粘到根目录）
    if src_path != repo_root and not src_path.startswith(repo_root + os.sep):
        raise HTTPException(status_code=400, detail="非法源路径，已拦截")
    if dest_dir != repo_root and not dest_dir.startswith(repo_root + os.sep):
        raise HTTPException(status_code=400, detail="非法目标路径，已拦截")
    if not os.path.exists(src_path):
        raise HTTPException(status_code=404, detail="源路径不存在")
    if not os.path.isdir(dest_dir):
        raise HTTPException(status_code=404, detail="目标文件夹不存在")

    # 自复制拦截:目标目录是源自身，或源为目录时目标在其内部，会造成递归复制
    if dest_dir == src_path or (os.path.isdir(src_path) and dest_dir.startswith(src_path + os.sep)):
        raise HTTPException(status_code=400, detail="不能复制到自身或自身的子目录中")

    # 同名冲突:明确报错，不覆盖（与 rename 接口"新路径已存在"风格一致）
    target_path = os.path.join(dest_dir, os.path.basename(src_path))
    if os.path.exists(target_path):
        raise HTTPException(status_code=400, detail=f"目标文件夹中已存在同名项:{os.path.basename(src_path)}")

    try:
        import shutil
        if os.path.isdir(src_path):
            shutil.copytree(src_path, target_path)
        else:
            shutil.copy2(src_path, target_path)
        # 异步更新RAG索引
        import asyncio
        asyncio.create_task(asyncio.to_thread(rag_manager.add_file, target_path))
        add_operation_log("文件操作", f"复制:{request.src_path} → {request.dest_dir}")
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
                print(f"自动同步手册异常:{str(e)}")
                pass
        asyncio.create_task(auto_sync_manual())
        # 自动更新当前项目文件清单缓存
        update_current_project_file_list()
        # 主动触发文件变动广播
        broadcast_file_change()
        return {"code": 200, "msg": "复制成功"}
    except Exception as e:
        add_operation_log("文件操作", f"复制失败:{request.src_path} → {request.dest_dir}，错误:{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"复制失败: {str(e)}")


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
        # 记录修改前的主题主色（用于判断是否需要热更新Qt外壳样式）
        old_theme_color = old_config.get("theme_primary_color", "")
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
        
        # 如果主题主色发生变化，实时通知Qt外壳重设样式表，无需重启立即生效
        new_theme_color = request.config.get("theme_primary_color", "")
        if new_theme_color and new_theme_color != old_theme_color:
            try:
                import main
                if main.browser_window:
                    # 复用QMetaObject.invokeMethod投递到UI主线程，避免跨线程操作Qt对象
                    from PySide6.QtCore import QMetaObject, Qt, Q_ARG
                    QMetaObject.invokeMethod(
                        main.browser_window,
                        "apply_theme",
                        Qt.QueuedConnection,
                        Q_ARG(str, new_theme_color)
                    )
                    add_operation_log("配置修改", f"主题主色已实时同步到外壳: {new_theme_color}")
            except Exception as e:
                print(f"⚠️ 同步主题主色到外壳失败: {str(e)}")
                add_operation_log("配置修改", f"主题主色已保存，但同步到外壳失败: {str(e)}", "warning")
        
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
        add_operation_log("安全配置", f"❌ 删除禁止路径失败:{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"删除禁止路径失败: {str(e)}")

# -------------------------- 9 槽位模型配置接口（阶段 2 新增） --------------------------
# 返回规范沿用既有 /api/config/*:{"code": 200, "msg": "...", "data": ...}
# 密钥处理:list 返回脱敏（前 4 位 + ****），get 返回明文（供编辑页回填），save 时空值不回写。

class ModelConfigSaveRequest(BaseModel):
    """单槽位模型配置保存请求体（字段与 models_config.json 槽位同构，全部可选）"""
    slot: int
    display_name: Optional[str] = None
    api_url: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    timeout: Optional[int] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    max_reply_rounds: Optional[int] = None
    max_chat_rounds: Optional[int] = None
    stream_output: Optional[bool] = None
    persona_name: Optional[str] = None
    persona_prompt: Optional[str] = None
    fixed_prompt_1: Optional[str] = None
    fixed_prompt_2: Optional[str] = None
    fixed_prompt_3: Optional[str] = None
    enabled_plugins: Optional[List[str]] = None


@app.get("/api/models/list")
async def list_models():
    """列出 9 槽位模型配置（api_key 脱敏返回，供列表页展示）"""
    try:
        data = _load_models_config()
        safe_list = []
        for m in data.get("models", []):
            item = dict(m)
            item["api_key"] = _mask_api_key(item.get("api_key"))
            safe_list.append(item)
        return {"code": 200, "data": safe_list}
    except Exception as e:
        add_operation_log("模型配置", f"❌ 读取模型列表失败:{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"读取模型列表失败: {str(e)}")


@app.get("/api/models/get")
async def get_model(slot: int):
    """读取指定槽位完整配置（api_key 明文返回，供编辑页回填）"""
    try:
        if slot < 1 or slot > 9:
            return {"code": 400, "msg": "slot 需为 1~9 的整数"}
        data = _load_models_config()
        for m in data.get("models", []):
            if int(m.get("slot", 0)) == slot:
                return {"code": 200, "data": m}
        return {"code": 404, "msg": f"未找到 slot={slot} 的配置"}
    except Exception as e:
        add_operation_log("模型配置", f"❌ 读取模型配置失败:{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"读取模型配置失败: {str(e)}")


@app.post("/api/models/save")
async def save_model(request: ModelConfigSaveRequest):
    """保存指定槽位配置（api_key 为空/脱敏形态时保留原值，防止误清空）"""
    try:
        slot = int(request.slot)
        if slot < 1 or slot > 9:
            return {"code": 400, "msg": "slot 需为 1~9 的整数"}
        data = _load_models_config()
        models = data.get("models", [])
        target = None
        for m in models:
            if int(m.get("slot", 0)) == slot:
                target = m
                break
        if target is None:
            target = _default_model_slot(slot)
            models.append(target)
        # 提交数据按字段合并；api_key 特殊处理（空值/脱敏形态 → 保留原值）
        payload = request.dict(exclude_unset=True)
        for k, v in payload.items():
            if k == "slot":
                continue
            if k == "api_key":
                if _is_masked_or_empty(v):
                    continue
                target["api_key"] = v
                continue
            if k in _MODEL_SLOT_FIELDS and v is not None:
                target[k] = v
        data["models"] = models
        _save_models_config(data)
        # 保存后清除该槽位客户端缓存（热更新范围隔离:只失效被改的 slot，其余槽位客户端不受影响）
        try:
            from model_registry import invalidate as _invalidate_slot
            _invalidate_slot(slot)
        except Exception as _inv_err:
            print(f"⚠️ 模型客户端缓存失效失败 slot={slot}:{_inv_err}")
        add_operation_log("模型配置", f"✅ 保存模型{slot}配置")
        safe = dict(target)
        safe["api_key"] = _mask_api_key(safe.get("api_key"))
        return {"code": 200, "msg": f"模型{slot}配置保存成功", "data": safe}
    except Exception as e:
        add_operation_log("模型配置", f"❌ 保存模型配置失败:{str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"保存模型配置失败: {str(e)}")


@app.get("/api/models/roles")
async def list_model_roles():
    """列出已填写 persona_name 的槽位（供任务模式选角色；只返回有内容的）"""
    try:
        data = _load_models_config()
        roles = [
            {"slot": m.get("slot"), "persona_name": m.get("persona_name", "")}
            for m in data.get("models", [])
            if m.get("persona_name")
        ]
        return {"code": 200, "data": roles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取角色列表失败: {str(e)}")

class ModelVerifyRequest(BaseModel):
    slot: int

@app.post("/api/models/verify")
async def verify_model(request: ModelVerifyRequest):
    """按 slot 发起一次极短真实请求:验证该槽位客户端可用（保存后确认可用），并支持并发隔离验收

    返回:ok / slot / model_name / api_url / api_key_prefix（前4位+脱敏）/ elapsed_ms / 错误摘要。
    独立走 model_registry.get_client 取客户端（不走全局单例），并发打多个 slot 时
    可直接比对 model_name 与密钥前缀是否各自正确，用于判定「是否串味」。
    """
    import time as _time
    base = None
    try:
        slot = int(request.slot)
        if slot < 1 or slot > 9:
            return {"code": 400, "msg": "slot 需为 1~9 的整数"}
        from model_registry import get_slot_config
        from llm_client import chat_with
        cfg = get_slot_config(slot)
        if not cfg:
            return {"code": 404, "msg": f"未找到 slot={slot} 的配置", "data": {"ok": False, "slot": slot}}
        api_key = str(cfg.get("api_key", "") or "")
        base = {
            "slot": slot,
            "model_name": cfg.get("model_name", ""),
            "api_url": cfg.get("api_url", ""),
            "api_key_prefix": (api_key[:4] + "****") if api_key else "",
        }
        started = _time.time()
        # 探针用极短输出（16 tokens）:不改变配置里 max_tokens=0=自动 的口径，仅验证连通性
        reply = chat_with(
            slot,
            [{"role": "user", "content": "hi"}],
            temperature=0.1,
            max_tokens=16,
            stream=False,
        )
        content = ""
        try:
            content = reply.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            content = ""
        base["ok"] = True
        base["elapsed_ms"] = int((_time.time() - started) * 1000)
        base["reply_preview"] = str(content or "")[:50]
        return {"code": 200, "msg": f"模型{slot}连接正常", "data": base}
    except Exception as e:
        if not base:
            base = {"slot": int(request.slot), "model_name": "", "api_url": "", "api_key_prefix": ""}
        base["ok"] = False
        base["error"] = str(e)[:200]
        return {"code": 500, "msg": f"模型连接失败:{str(e)[:200]}", "data": base}

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
    # 检测本地中文语义向量模型文件是否存在（与 memory_cache.py 加载口径对齐）
    model_candidates = [os.path.join(BASE_DIR, "gte-small-zh"), "./gte-small-zh"]
    if getattr(_sys, 'frozen', False):
        model_candidates.insert(1, os.path.join(_exe_dir, "gte-small-zh"))
    model_installed = any(
        os.path.exists(os.path.join(d, "pytorch_model.bin")) for d in model_candidates
    )
    result = {
        "python_version": f"{_sys.version_info.major}.{_sys.version_info.minor}",
        "python_matched": True,  # 打包后固定为True，开发环境也是True
        "torch_installed": False,
        "sentence_transformers_installed": False,
        "transformers_installed": False,
        "model_installed": model_installed,
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
            # 先清空索引（含增量更新时间缓存），再全量重建:确保"重建"是真正的全量，且顺带清掉历史存量重复条目
            rag_manager.clear_index()
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

@app.post("/api/rag/build/project")
async def build_rag_index_for_project(request: Request):
    """项目级RAG增量入库:仅扫描指定项目目录（不清空全库），供文件仓库右键"RAG项目入库"使用

    与全库"清空+重建"的区别:绝不调用 clear_index()，避免把其它项目索引一并清空；
    build_full_index 自带路径级增量缓存（LAST_UPDATE_CACHE），已入库且未修改的文件会自动跳过，
    因此"复制新项目进仓库 → 右键入库"只会处理这个新目录，不会触发全库重编码。
    """
    data = await request.json()
    project_dir = (data.get("path") or "").strip()
    if not project_dir:
        return {"code": 400, "msg": "❌ 缺少项目路径参数"}
    # 路径基准统一:前端传来的是相对仓库根目录的相对路径（如"AI可视化数据"），
    # 直接 os.path.abspath 会以进程工作目录（免安装exe形态下为程序安装目录）解析，
    # 拼出程序安装目录下的假路径导致校验失败，故相对路径先与仓库根 REPOSITORY_PATH 拼接补全
    if not os.path.isabs(project_dir):
        project_dir = os.path.join(REPOSITORY_PATH, project_dir)
    norm_dir = os.path.normpath(os.path.abspath(project_dir)).replace("\\", "/")
    if not os.path.isdir(norm_dir):
        return {"code": 400, "msg": f"❌ 路径不存在或不是文件夹: {norm_dir}"}

    def run_project_build():
        try:
            rag_manager.build_full_index(root_dir=norm_dir)
        except Exception:
            pass

    import threading
    threading.Thread(target=run_project_build, daemon=True).start()
    return {"code": 200, "msg": f"✅ 项目「{os.path.basename(norm_dir)}」RAG入库已启动，后台异步执行"}

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

# ===== 云端插件市场（MVP方案C:整仓archive分发，配置可改，不硬编码市场地址） =====
# 网络访问策略（2026-09-15用户拍板）:市场源/插件下载源不做域名白名单限制，允许任意网站
# 仅保留http/https协议校验，拦截file://、ftp://等非HTTP协议；200MB体积上限与zip-slip防护仍然生效
# 市场清单默认地址（公开仓库raw文件，匿名可访问）；可在config.json的plugin_market.manifest_url覆盖
DEFAULT_MARKET_MANIFEST_URL = "https://gitee.com/chen-bohan3000/ai-gzt-plugins/raw/main/market_manifest.json"
# 整仓archive下载体积上限（200MB），超过中止，防止异常超大响应占满磁盘
MARKET_ARCHIVE_MAX_BYTES = 200 * 1024 * 1024
# 清单内存缓存（避免每次打开市场页都请求远程），5分钟TTL
_plugin_market_cache = {"data": None, "ts": 0.0}
_PLUGIN_MARKET_CACHE_TTL = 300

def get_plugin_market_config() -> dict:
    """读取插件市场配置:config.json的plugin_market节点，缺省值兜底，不硬编码业务地址以外的内容"""
    cfg = load_config()
    market_cfg = cfg.get("plugin_market", {}) if isinstance(cfg.get("plugin_market"), dict) else {}
    return {
        "manifest_url": market_cfg.get("manifest_url") or DEFAULT_MARKET_MANIFEST_URL,
        "enabled": market_cfg.get("enabled", True)
    }

def _is_valid_http_url(url: str) -> bool:
    """校验市场请求URL:域名白名单已取消（允许任意网站），仅校验必须为http/https协议的合法URL"""
    return bool(re.match(r'^https?://[^/\s]+', url or ""))

def _compare_plugin_versions(v1: str, v2: str) -> int:
    """语义化版本号比较:返回-1(v1<v2)/0(相等)/1(v1>v2)；非标准版本号退化为字符串比较"""
    def parse(v):
        parts = re.findall(r'\d+', str(v or ""))
        return tuple(int(p) for p in parts[:3]) if parts else None
    p1, p2 = parse(v1), parse(v2)
    if p1 is None or p2 is None:
        return -1 if str(v1) < str(v2) else (1 if str(v1) > str(v2) else 0)
    # 补齐长度后按元组比较
    n = max(len(p1), len(p2))
    p1, p2 = p1 + (0,) * (n - len(p1)), p2 + (0,) * (n - len(p2))
    return -1 if p1 < p2 else (1 if p1 > p2 else 0)

def _safe_extract_zip(zip_path: str, target_dir: str) -> int:
    """
    统一安全解压函数:
    1. zip-slip防护:每个成员解压后的绝对路径必须落在target_dir内，拒绝../../路径穿越；
    2. 自动剥公共顶层目录:zip内所有文件若共享同一层顶层目录（如Gitee整仓包的ai-gzt-plugins-main/、
       手工打包多套的一层插件目录），自动剥掉，修复原extractall要求文件必须在zip根目录的隐患；
    返回成功解压的文件数。
    """
    import zipfile
    files = []
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            norm = info.filename.replace("\\", "/")
            parts = [p for p in norm.split("/") if p and p not in (".", "..")]
            if parts:
                files.append((info, parts))
        if not files:
            raise ValueError("压缩包内没有可解压的文件")
        # 判断是否共享唯一公共顶层目录（全部成员首段相同且至少有成员路径>=2段才剥离）
        first_segments = {parts[0] for _, parts in files}
        has_nested = any(len(parts) >= 2 for _, parts in files)
        strip_top = len(first_segments) == 1 and has_nested
        target_abs = os.path.abspath(target_dir)
        os.makedirs(target_abs, exist_ok=True)
        count = 0
        for info, parts in files:
            rel_parts = parts[1:] if strip_top else parts
            if not rel_parts:
                continue
            dest_abs = os.path.abspath(os.path.join(target_abs, *rel_parts))
            # zip-slip核心校验:目标路径必须是target_dir的子路径
            if dest_abs != target_abs and not dest_abs.startswith(target_abs + os.sep):
                raise ValueError(f"压缩包存在非法路径，已拦截:{info.filename}")
            os.makedirs(os.path.dirname(dest_abs), exist_ok=True)
            with zf.open(info) as src, open(dest_abs, "wb") as dst:
                dst.write(src.read())
            count += 1
    return count

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
            # 云端插件统一走独立的市场安装接口（支持整仓archive分发），旧入口给出明确引导
            return {"code": 400, "msg": "请使用插件市场「可安装」列表中的安装按钮（接口:/api/plugin/market/install）"}
    except Exception as e:
        return {"code": 500, "msg": f"安装失败:{str(e)}"}

class MarketInstallRequest(BaseModel):
    plugin_id: str # 云端市场插件ID

def _fetch_market_manifest(force_refresh: bool = False) -> dict:
    """
    拉取云端插件市场清单（同步阻塞函数，调用方须用asyncio.to_thread包裹）:
    5分钟内存缓存，force_refresh=True跳过缓存；域名白名单校验；返回manifest字典。
    """
    import requests
    now = time.time()
    if not force_refresh and _plugin_market_cache["data"] is not None:
        if now - _plugin_market_cache["ts"] < _PLUGIN_MARKET_CACHE_TTL:
            return _plugin_market_cache["data"]
    cfg = get_plugin_market_config()
    if not cfg.get("enabled", True):
        raise ValueError("插件市场已在配置中关闭（plugin_market.enabled=false）")
    url = cfg["manifest_url"]
    # 域名白名单已取消（允许任意网站），仅做http/https协议校验
    if not _is_valid_http_url(url):
        raise ValueError("插件市场清单地址必须是http/https开头的合法URL，已中止请求")
    resp = requests.get(url, timeout=10, headers={"User-Agent": "AI-GZT-PluginMarket/1.0"})
    resp.raise_for_status()
    manifest = resp.json()
    # 清单结构基础校验
    if not isinstance(manifest, dict) or not isinstance(manifest.get("plugins"), list):
        raise ValueError("市场清单格式无效:缺少plugins数组")
    for p in manifest["plugins"]:
        if not p.get("plugin_id") or not p.get("version"):
            raise ValueError("市场清单存在缺少plugin_id/version的插件条目")
    _plugin_market_cache["data"] = manifest
    _plugin_market_cache["ts"] = now
    return manifest

@app.get("/api/plugin/market/list")
async def get_market_plugin_list(force: bool = False):
    """获取云端市场插件清单，与本地已安装列表按plugin_id合并，输出未安装/可更新/已最新三态"""
    import asyncio
    try:
        manifest = await asyncio.to_thread(_fetch_market_manifest, force)
        # 本地已安装插件版本映射
        installed_versions = {
            pid: tpl["plugin_config"].get("version", "1.0.0")
            for pid, tpl in tool_template_manager._plugin_templates.items()
        }
        plugins = []
        for p in manifest["plugins"]:
            item = dict(p)
            pid = item["plugin_id"]
            installed_ver = installed_versions.get(pid)
            if installed_ver is None:
                item["status"] = "not_installed"
            elif _compare_plugin_versions(item["version"], installed_ver) > 0:
                item["status"] = "update_available"
                item["installed_version"] = installed_ver
            else:
                item["status"] = "installed"
                item["installed_version"] = installed_ver
            plugins.append(item)
        return {"code": 200, "data": {
            "market_name": manifest.get("market_name", "云端插件市场"),
            "distribution": manifest.get("distribution", ""),
            "updated_at": manifest.get("updated_at", ""),
            "plugins": plugins,
            "count": len(plugins)
        }}
    except Exception as e:
        # 市场拉取失败不影响已安装Tab，前端据此显示明确错误
        return {"code": 502, "msg": f"无法获取云端插件清单:{str(e)}"}
# 市场逐文件下载防护:单插件文件数上限，防止异常清单/递归失控
MARKET_PLUGIN_MAX_FILES = 500

def _parse_repo_info_from_manifest(manifest: dict) -> dict:
    """解析市场仓库信息:优先清单显式repo_url/ref，缺省从manifest_url推导，适配Gitee匿名contents API+raw通道"""
    cfg = get_plugin_market_config()
    manifest_url = cfg.get("manifest_url", "")
    repo_url = (manifest.get("repo_url") or "").rstrip("/")
    ref = manifest.get("ref") or "main"
    if not repo_url:
        # 形如 https://gitee.com/{owner}/{repo}/raw/{ref}/market_manifest.json
        m = re.match(r'^(https?://[^/]+/[^/]+/[^/]+)/raw/([^/]+)/', manifest_url)
        if m:
            repo_url, ref = m.group(1).rstrip("/"), m.group(2)
    if not repo_url:
        raise ValueError("市场清单缺少repo_url，且无法从manifest_url推导仓库地址")
    m = re.match(r'^(https?://[^/]+)/(.+?)(?:\.git)?$', repo_url)
    if not m:
        raise ValueError("市场清单repo_url格式无效")
    origin, slug = m.group(1), m.group(2).strip("/")
    return {
        "origin": origin,
        "slug": slug,
        "ref": ref,
        "raw_base": f"{repo_url}/raw/{ref}",
        "contents_api": f"{origin}/api/v5/repos/{slug}/contents",
    }

def _download_market_plugin_files(plugin_id: str, dest_parent_dir: str, manifest: dict) -> str:
    """
    方案C修复版（2026-09-15）:Gitee整仓archive端点对非浏览器会话返回405/HTML导致"File is not a zip file"，
    改用匿名contents API递归列出目标插件子目录 + raw地址逐文件下载，在临时目录还原插件结构。
    三重防护:文件数上限MARKET_PLUGIN_MAX_FILES、总体积上限MARKET_ARCHIVE_MAX_BYTES、路径穿越校验。
    返回还原后的插件目录绝对路径。
    """
    import requests
    repo = _parse_repo_info_from_manifest(manifest)
    dest_dir = os.path.abspath(os.path.join(dest_parent_dir, plugin_id))
    os.makedirs(dest_dir, exist_ok=True)
    api_headers = {"User-Agent": "AI-GZT-PluginMarket/1.0", "Accept": "application/json"}
    collected = []  # (插件内相对路径posix, 下载URL)
    queue = [plugin_id]
    visited = set()
    while queue:
        rel_dir = queue.pop(0)
        if rel_dir in visited:
            continue
        visited.add(rel_dir)
        api_url = f"{repo['contents_api']}/{rel_dir}?ref={repo['ref']}"
        resp = requests.get(api_url, timeout=30, headers=api_headers)
        if resp.status_code == 404:
            raise ValueError(f"远程仓库中不存在插件目录:{plugin_id}")
        resp.raise_for_status()
        items = resp.json()
        if not isinstance(items, list):
            raise ValueError("市场仓库目录接口返回格式无效")
        for it in items:
            typ, path = it.get("type"), it.get("path") or ""
            # 路径规范化:拒绝..穿越，且只接受plugin_id前缀内的条目
            parts = [p for p in path.replace("\\", "/").lstrip("/").split("/") if p and p not in (".", "..")]
            if not parts or parts[0] != plugin_id:
                continue
            safe_rel = "/".join(parts)
            if typ == "dir":
                queue.append(safe_rel)
            elif typ == "file":
                if len(collected) >= MARKET_PLUGIN_MAX_FILES:
                    raise ValueError(f"插件文件数超过{MARKET_PLUGIN_MAX_FILES}上限，已中止下载")
                dl = it.get("download_url") or f"{repo['raw_base']}/{safe_rel}"
                if not _is_valid_http_url(dl):
                    raise ValueError(f"文件下载地址非法:{safe_rel}")
                collected.append((safe_rel, dl))
    if not collected:
        raise ValueError(f"远程插件目录为空:{plugin_id}")
    # 逐文件下载并按原目录结构写入临时目录
    total_bytes = 0
    for safe_rel, dl in collected:
        r = requests.get(dl, timeout=60, headers={"User-Agent": "AI-GZT-PluginMarket/1.0"})
        r.raise_for_status()
        content = r.content
        total_bytes += len(content)
        if total_bytes > MARKET_ARCHIVE_MAX_BYTES:
            raise ValueError("插件总体积超过200MB上限，已中止下载")
        rel_parts = safe_rel.split("/")[1:]  # 去掉首段plugin_id，dest_dir本身已以plugin_id命名
        target_abs = os.path.abspath(os.path.join(dest_dir, *rel_parts))
        if target_abs != dest_dir and not target_abs.startswith(dest_dir + os.sep):
            raise ValueError(f"非法文件路径，已拦截:{safe_rel}")
        os.makedirs(os.path.dirname(target_abs), exist_ok=True)
        with open(target_abs, "wb") as f:
            f.write(content)
    return dest_dir

def _install_market_plugin(plugin_id: str) -> dict:
    """
    从云端市场安装/更新单个插件（同步阻塞函数，路由层用asyncio.to_thread包裹）:
    方案C修复版——contents API递归列目录+raw逐文件下载（Gitee archive端点匿名返回405/HTML）；
    全程http/https协议校验+文件数/总体积上限+路径穿越防护+plugin.json校验。
    """
    import requests
    import shutil
    import tempfile
    manifest = _fetch_market_manifest(False)
    plugin_info = next((p for p in manifest["plugins"] if p.get("plugin_id") == plugin_id), None)
    if not plugin_info:
        return {"code": 404, "msg": f"市场清单中不存在插件:{plugin_id}"}
    # 下载方式:插件级download_url独立zip包（未来Release形态）优先；缺省走仓库contents API逐文件通道
    plugin_pkg_url = plugin_info.get("download_url")
    tmp_zip = None
    tmp_extract_dir = None
    try:
        if plugin_pkg_url:
            # 独立zip包通道（预留）:http/https协议校验→流式下载(200MB上限)→安全解压(防zip-slip)
            if not _is_valid_http_url(plugin_pkg_url):
                return {"code": 400, "msg": "下载地址必须是http/https开头的合法URL，已中止下载"}
            with requests.get(plugin_pkg_url, stream=True, timeout=30,
                              headers={"User-Agent": "AI-GZT-PluginMarket/1.0"}) as resp:
                resp.raise_for_status()
                # 下载内容必须是zip，拦截HTML错误页（历史BUG:Gitee返回HTML导致File is not a zip file）
                ctype = (resp.headers.get("Content-Type") or "").lower()
                fd, tmp_zip = tempfile.mkstemp(suffix=".zip", prefix="aigt_plugin_")
                total = 0
                with os.fdopen(fd, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=64 * 1024):
                        if not chunk:
                            continue
                        total += len(chunk)
                        if total > MARKET_ARCHIVE_MAX_BYTES:
                            raise ValueError("插件包超过200MB体积上限，已中止下载")
                        f.write(chunk)
                if total < 2 or (total >= 2 and open(tmp_zip, "rb").read(2) != b"PK"):
                    raise ValueError("下载内容不是有效的zip包（远程可能返回了错误页面），已中止安装")
            tmp_extract_dir = tempfile.mkdtemp(prefix="aigt_plugin_extract_")
            _safe_extract_zip(tmp_zip, tmp_extract_dir)
            src_plugin_dir = os.path.join(tmp_extract_dir, plugin_id)
        else:
            # 默认通道:contents API递归列目录+raw逐文件下载，规避Gitee archive端点匿名405/HTML问题
            tmp_extract_dir = tempfile.mkdtemp(prefix="aigt_plugin_extract_")
            src_plugin_dir = _download_market_plugin_files(plugin_id, tmp_extract_dir, manifest)
        src_manifest_path = os.path.join(src_plugin_dir, "plugin.json")
        if not os.path.isfile(src_manifest_path):
            return {"code": 400, "msg": f"插件包中未找到{plugin_id}/plugin.json，安装中止"}
        with open(src_manifest_path, "r", encoding="utf-8") as f:
            pcfg = json.load(f)
        # 4.校验plugin.json必填字段与ID一致性
        for field in ("plugin_id", "name", "description", "parameters", "entry"):
            if field not in pcfg:
                return {"code": 400, "msg": f"插件plugin.json缺少必填字段:{field}"}
        if pcfg["plugin_id"] != plugin_id:
            return {"code": 400, "msg": f"插件ID不一致:目录为{plugin_id}，plugin.json为{pcfg['plugin_id']}"}
        # 5.备份旧版user_config.json（更新不丢配置），清理旧目录后移入新版
        target_dir = os.path.join(tool_template_manager.PLUGIN_DIR, plugin_id)
        user_config_backup = None
        if os.path.isdir(target_dir):
            old_user_cfg = os.path.join(target_dir, "user_config.json")
            if os.path.isfile(old_user_cfg):
                fd2, user_config_backup = tempfile.mkstemp(suffix=".json", prefix="aigt_usercfg_")
                with os.fdopen(fd2, "wb") as dst, open(old_user_cfg, "rb") as src:
                    dst.write(src.read())
            shutil.rmtree(target_dir)
        os.makedirs(tool_template_manager.PLUGIN_DIR, exist_ok=True)
        shutil.move(src_plugin_dir, target_dir)
        if user_config_backup:
            shutil.copy2(user_config_backup, os.path.join(target_dir, "user_config.json"))
        # 6.热重载并确认插件确实加载成功
        tool_template_manager.load_plugins()
        if plugin_id not in tool_template_manager._plugin_templates:
            return {"code": 500, "msg": "文件安装完成但插件加载失败，请检查插件依赖是否安装完整"}
        add_operation_log("插件管理", f"✅ 云端市场安装插件成功:{plugin_id} v{plugin_info.get('version')}")
        return {"code": 200, "msg": f"插件[{plugin_info.get('name', plugin_id)}]安装成功"}
    finally:
        # 7.无条件清理临时文件与临时解压目录
        if tmp_zip and os.path.exists(tmp_zip):
            try:
                os.remove(tmp_zip)
            except Exception:
                pass
        if tmp_extract_dir and os.path.exists(tmp_extract_dir):
            try:
                shutil.rmtree(tmp_extract_dir)
            except Exception:
                pass

@app.post("/api/plugin/market/install")
async def install_market_plugin(req: MarketInstallRequest):
    """从云端插件市场安装/更新插件（阻塞IO放线程池，不卡事件循环）"""
    import asyncio
    try:
        result = await asyncio.to_thread(_install_market_plugin, req.plugin_id)
        return result
    except Exception as e:
        return {"code": 500, "msg": f"安装失败:{str(e)}"}

@app.post("/api/plugin/install/local")
async def install_local_plugin(plugin_file: UploadFile = File(...)):
    """上传本地zip插件包安装（统一走_safe_extract_zip安全解压，防zip-slip并自动剥顶层目录）"""
    try:
        import shutil
        import tempfile
        # 1.上传内容写入临时zip（不使用用户文件名拼路径，避免文件名注入/中文路径问题）
        fd, temp_zip = tempfile.mkstemp(suffix=".zip", prefix="aigt_upload_")
        with os.fdopen(fd, "wb") as f:
            f.write(await plugin_file.read())
        # 2.安全解压到临时目录（zip-slip路径穿越校验+自动剥公共顶层目录）
        temp_extract_dir = tempfile.mkdtemp(prefix="aigt_upload_extract_")
        try:
            _safe_extract_zip(temp_zip, temp_extract_dir)
            # 3.读取plugin.json确定真实插件ID，不再用zip文件名作为安装目录名
            manifest_path = os.path.join(temp_extract_dir, "plugin.json")
            if not os.path.isfile(manifest_path):
                return {"code": 400, "msg": "压缩包根目录缺少plugin.json，请确认打包结构（插件文件需在zip根目录或同一层目录内）"}
            with open(manifest_path, "r", encoding="utf-8") as mf:
                pcfg = json.load(mf)
            plugin_name = pcfg.get("plugin_id")
            if not plugin_name or not all(k in pcfg for k in ("name", "description", "parameters", "entry")):
                return {"code": 400, "msg": "plugin.json缺少必填字段（plugin_id/name/description/parameters/entry）"}
            # 4.备份旧版user_config.json，更新安装不丢用户配置
            target_path = os.path.join(tool_template_manager.PLUGIN_DIR, plugin_name)
            user_config_backup = None
            if os.path.isdir(target_path):
                old_cfg = os.path.join(target_path, "user_config.json")
                if os.path.isfile(old_cfg):
                    fd2, user_config_backup = tempfile.mkstemp(suffix=".json", prefix="aigt_usercfg_")
                    with os.fdopen(fd2, "wb") as dst, open(old_cfg, "rb") as src:
                        dst.write(src.read())
                shutil.rmtree(target_path)
            os.makedirs(tool_template_manager.PLUGIN_DIR, exist_ok=True)
            shutil.move(temp_extract_dir, target_path)
            temp_extract_dir = None
            if user_config_backup:
                shutil.copy2(user_config_backup, os.path.join(target_path, "user_config.json"))
            # 5.重新加载插件并确认加载成功
            tool_template_manager.load_plugins()
            if plugin_name not in tool_template_manager._plugin_templates:
                return {"code": 500, "msg": "文件解压完成但插件加载失败，请检查plugin.json与插件依赖"}
            add_operation_log("插件管理", f"✅ 上传安装插件成功:{plugin_name}")
            return {"code": 200, "msg": "插件安装成功"}
        finally:
            # 6.无条件清理临时文件
            if os.path.exists(temp_zip):
                try:
                    os.remove(temp_zip)
                except Exception:
                    pass
            if temp_extract_dir and os.path.exists(temp_extract_dir):
                try:
                    shutil.rmtree(temp_extract_dir)
                except Exception:
                    pass
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
    # 插件开发默认目录复用统一仓库默认路径（Windows为D:/AI仓库文件夹），避免两处默认值不一致
    save_dir: str = os.path.join(get_default_repository_path(), "插件开发").replace("\\", "/")
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
            # 剪枝:排除虚拟环境/.git/打包产物等噪音目录，避免遍历数万依赖文件；
            # 传入 root 后叠加"项目信息隔离"判断，被隔离目录整棵子树直接跳过
            file_filter_config.prune_walk_dirs(dirs, root)
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
        
        # 截图后清理超量旧文件（保留最新 100 个）
        _cleanup_upload_dir()
        
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
    
    # 增量拉取逻辑:返回ID大于last_id的所有新日志
    if last_id > 0:
        filtered = [log for log in filtered if log["id"] > last_id]
        # 增量拉取不需要分页，最多返回100条；current_total为当前内存日志全量总数（滚动期精确，供前端覆盖分页器）
        return {
            "code": 200, 
            "data": {
                "list": filtered[:page_size], 
                "total": len(filtered),
                "current_total": len(OPERATION_LOGS),
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
    """清空所有操作日志（ID计数器不重置，杜绝ID回退重复），并立即落盘"""
    global OPERATION_LOGS
    OPERATION_LOGS = []
    add_operation_log("日志管理", "清空所有操作日志")
    _schedule_log_persist(0)
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
    # 【2026-10-13 新增】把运行时真实端口写入模块级变量，供 wake_main（次级 @主控 唤醒主控）读取，避免硬编码
    global _SERVER_PORT
    _SERVER_PORT = use_port
    
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
                # 剪枝:排除虚拟环境/.git/打包产物等噪音目录，避免遍历数万依赖文件；
                # 传入 root 后叠加"项目信息隔离"判断，被隔离目录整棵子树直接跳过
                file_filter_config.prune_walk_dirs(dirs, root)
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