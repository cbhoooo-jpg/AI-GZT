# -*- coding: utf-8 -*-
"""
双向自动同步监听模块
功能特性：
1. 监听仓库文件夹下所有文件变动，自动更新对应子项目手册明细
2. 监听所有*项目手册.md文件的明细清单变动
3. 内置防抖、循环拦截、异常兜底，无需确认直接执行
4. 完全复用现有project_manual_manager核心能力，无侵入式开发
"""
import os
import time
import re
import json
from typing import Optional
from collections import deque
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from project_manual_manager import project_manual_manager
import logging
import sys
import ctypes
import threading

# Windows COM初始化常量（仅Windows系统生效，解决watchdog打包环境COM线程冲突）
COINIT_MULTITHREADED = 0x0
ole32 = None
if sys.platform == "win32":
    try:
        ole32 = ctypes.windll.ole32
    except Exception:
        ole32 = None

def get_repository_path() -> str:
    """动态获取当前配置的仓库路径，自动适配配置更新，避免硬编码"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.json")
    # 默认 fallback 到程序目录下的仓库文件夹，兼容旧版本
    default_repo = os.path.normpath(os.path.join(base_dir, "仓库文件夹")).replace("\\", "/")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            repo_path = config.get("repository_path", default_repo)
            # 自动创建不存在的仓库目录
            os.makedirs(repo_path, exist_ok=True)
            return os.path.normpath(repo_path).replace("\\", "/")
        except Exception as e:
            logging.warning(f"⚠️ 自动同步模块读取仓库路径配置失败，使用默认路径:{str(e)}")
    # 配置不存在时自动创建默认目录
    os.makedirs(default_repo, exist_ok=True)
    return default_repo

# 全局仓库路径（启动时动态获取，避免硬编码）
REPOSITORY_PATH = get_repository_path()

# 日志配置:同时输出到控制台和持久化文件
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/auto_sync_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 全局配置
CONFIG = {
    "debounce_time": 2,  # 防抖时间：2秒内多次变动仅执行一次
    "trace_window": 2,  # 溯源时间窗口：2秒内的操作链才会判定为关联
    "ignore_dirs": {".git", ".idea", "__pycache__", "logs", "temp", "dist", ".vscode", "code_rag", "backup"},  # 忽略的目录:新增RAG目录过滤+编辑器备份目录（备份文件创建/清理不再触发手册重写）
    "ignore_exts": {".tmp", ".log", ".swp", ".~lock", ".crdownload", ".index", ".db", ".DS_Store", ".zip", ".rar", ".7z", ".exe"},  # 忽略的文件后缀：新增RAG索引文件过滤
    "manual_suffix": "项目手册.md",  # 项目手册文件名后缀
    "max_parse_fail_count": 3 # 单个文件最大解析失败次数，超过后24小时内不再重试
}

# 全局缓存，用于防抖、溯源防循环
CACHE = {
    "last_process_by_path": {},  # 按文件路径单独记录最后处理时间，解决重复触发
    "last_manual_table_content": {},  # 每个手册上次的明细表格内容，用于增量对比
    "recent_operations": deque(maxlen=20)  # 最近操作记录环形队列，最多存20条用于溯源
}

# 全局文件变动事件触发函数，通知前端刷新
def trigger_file_change_notify():
    try:
        # 延迟导入避免循环依赖
        from api_server import broadcast_file_change
        broadcast_file_change()
    except ImportError:
        logging.warning("⚠️  导入api_server失败，无法发送文件变动通知")
    except Exception as e:
        logging.warning(f"⚠️  发送文件变动通知失败：{str(e)}")
# ============================================================
# 手册更新串行调度器（根治并发重写交叉覆盖+自激风暴）
# 1.文件事件只登记"某手册待处理"标记，不直接执行重写；
# 2.唯一工作线程串行消费，同一手册同一时刻只有一轮扫描；
# 3.trailing防抖合并密集事件；4.仅内容真实变化才广播SSE
# ============================================================
_MANUAL_PENDING = {}  # key=手册绝对路径, value=最近一次登记时间戳
_MANUAL_SCHED_LOCK = threading.Lock()
_MANUAL_WAKEUP = threading.Event()

def request_manual_update(manual_abs_path: str):
    """文件事件线程调用:登记手册待处理（仅轻量赋值+唤醒，重写由工作线程串行执行）"""
    manual_abs_path = os.path.normpath(manual_abs_path)
    with _MANUAL_SCHED_LOCK:
        _MANUAL_PENDING[manual_abs_path] = time.time()
    _MANUAL_WAKEUP.set()


def _manual_update_worker():
    """唯一工作线程:串行消费待处理手册，彻底消除并发重写交叉覆盖"""
    TRAILING_WAIT = 1.0   # trailing防抖:登记后静默1秒，吸收密集事件
    SETTLE_WAIT = 1.0     # 处理完静默1秒复查，无新事件才收工（防止处理期间事件丢失）
    while True:
        # 等待待处理队列非空
        _MANUAL_WAKEUP.wait(timeout=30)
        _MANUAL_WAKEUP.clear()
        time.sleep(TRAILING_WAIT)
        # 快照当前所有待处理手册（处理期间新来的事件会留在队列里，下一轮兜底）
        with _MANUAL_SCHED_LOCK:
            pending_snapshot = dict(_MANUAL_PENDING)
            _MANUAL_PENDING.clear()
        for manual_abs_path, register_ts in list(pending_snapshot.items()):
            try:
                if not os.path.exists(manual_abs_path):
                    continue  # 手册已被删除，跳过
                rel_manual_path = os.path.relpath(manual_abs_path, REPOSITORY_PATH)
                logging.info(f"🔄 串行调度:更新项目手册 {rel_manual_path}")
                update_result = project_manual_manager.update_manual_detail_table(rel_manual_path)
                # 记录自动操作到溯源队列
                CACHE["recent_operations"].append({
                    "time": time.time(), "type": "auto_update_manual", "path": manual_abs_path
                })
                # 乐观锁冲突（409）:说明扫描期间手册被外部手写，放弃本轮，登记一次让下个事件兜底合并
                if update_result.get("code") == 409:
                    logging.info(f"⏳ 手册扫描期间被外部修改，等待下个事件合并:{rel_manual_path}")
                    continue
                # 仅内容真实变化才广播SSE，消除前端刷新风暴及次生JS解析报错
                if update_result.get("code") == 200 and update_result.get("changed"):
                    logging.info(f"✅ 手册内容已更新:{rel_manual_path}")
                    trigger_file_change_notify()
            except Exception as e:
                logging.error(f"❌ 串行更新手册失败 {manual_abs_path}:{str(e)}")
        # 处理完静默复查:若等待期间又有新手册/新事件登记，立刻再跑一轮，保证不丢事件
        time.sleep(SETTLE_WAIT)
        with _MANUAL_SCHED_LOCK:
            has_more = bool(_MANUAL_PENDING)
        if has_more:
            _MANUAL_WAKEUP.set()


class FileChangeHandler(FileSystemEventHandler):
    """普通文件变动事件处理器：反向同步 → 文件变动更新对应项目手册"""
    def _find_nearest_manual(self, file_path: str) -> Optional[str]:
        """向上递归查找最近一级的项目手册，修复目录不存在报错"""
        current_dir = os.path.normpath(os.path.dirname(file_path)).replace("\\", "/")
        repo_root = get_repository_path()
        while current_dir.startswith(repo_root):
            # 修复：目录不存在直接终止
            try:
                if not os.path.isdir(current_dir):
                    break
                for file in os.listdir(current_dir):
                    if file.endswith(CONFIG["manual_suffix"]):
                        return os.path.join(current_dir, file)
            except (FileNotFoundError, OSError):
                # 多线程下目录被删除/无权限，直接终止查找，避免报错
                break
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:  # 到根目录了
                break
            current_dir = parent_dir
        return None

    def _should_ignore(self, event) -> bool:
        """判断是否需要忽略该变动"""
        # 仅忽略非新增的目录变动，目录新增需要处理（自动创建项目手册）
        if event.is_directory and event.event_type != 'created':
            return True
        # 忽略指定目录
        for ignore_dir in CONFIG["ignore_dirs"]:
            if f"{os.sep}{ignore_dir}{os.sep}" in event.src_path or event.src_path.endswith(f"{os.sep}{ignore_dir}"):
                return True
        # 忽略指定后缀
        ext = os.path.splitext(event.src_path)[1].lower()
        if ext in CONFIG["ignore_exts"]:
            return True
        # 忽略项目手册本身（手册变动走单独的处理器）
        if os.path.basename(event.src_path).endswith(CONFIG["manual_suffix"]):
            return True
        return False

    def on_any_event(self, event):
        """统一处理所有文件变动事件"""
        if self._should_ignore(event):
            return
        
        # 按路径单独防抖，解决同一文件多次触发问题
        now = time.time()
        if event.src_path in CACHE["last_process_by_path"] and now - CACHE["last_process_by_path"][event.src_path] < CONFIG["debounce_time"]:
            return
        CACHE["last_process_by_path"][event.src_path] = now

        # 【溯源防循环】：如果是自动操作引发的文件变动，直接终止
        def is_auto_triggered(check_path: str, op_type: str) -> bool:
            for op in list(CACHE["recent_operations"]):
                if now - op["time"] > CONFIG["trace_window"]:
                    continue
                if op["type"] == op_type and op["path"] == check_path:
                    return True
            return False

        # 处理项目文件夹新增：自动创建项目手册
        if event.is_directory:
            # 判断是不是仓库下的一级子文件夹（项目根文件夹）
            rel_dir_path = os.path.relpath(event.src_path, REPOSITORY_PATH)
            if os.sep not in rel_dir_path and not rel_dir_path.startswith('.'):
                project_name = os.path.basename(event.src_path)
                manual_file_name = f"{project_name}项目手册.md"
                target_manual_path = os.path.join(event.src_path, manual_file_name)
                if not os.path.exists(target_manual_path):
                    logging.info(f"📝 检测到新项目文件夹【{project_name}】，自动创建项目手册：{manual_file_name}")
                    # 调用现有接口创建标准项目手册
                    project_manual_manager.generate_template(project_name, f"{rel_dir_path}/{project_name}项目手册.md")
                    # 记录操作到溯源队列
                    CACHE["recent_operations"].append({
                        "time": now, "type": "auto_create_manual", "path": target_manual_path
                    })
                    # 缓存新手册的表格内容
                    CACHE["last_manual_table_content"][target_manual_path] = ManualChangeHandler()._parse_table_content(target_manual_path)
                    # 触发文件变动通知，前端自动刷新
                    trigger_file_change_notify()
            return

        # 【溯源判断】：如果是自动生成文件引发的变动，直接跳过
        if is_auto_triggered(event.src_path, "auto_generate_file"):
            return

        # 普通文件变动逻辑：查找对应项目手册更新
        manual_path = self._find_nearest_manual(event.src_path)
        if not manual_path:
            return  # 不属于任何项目，忽略
        
        # 【根治改造】事件线程只做"登记待处理"，绝不直接执行重写:
        # 由唯一串行工作线程 _manual_update_worker 统一 trailing 防抖、串行 AST 扫描、
        # mtime 乐观锁合并，且仅内容真实变化才广播 SSE——
        # 彻底消除并发重写交叉覆盖与"重写→触发监听→再重写"的自激风暴
        request_manual_update(manual_path)

class ManualChangeHandler(FileSystemEventHandler):
    """项目手册变动事件处理器"""
    def _parse_table_content(self, manual_path: str) -> str:
        """解析手册的明细表格内容，用于增量对比"""
        try:
            with open(manual_path, "r", encoding="utf-8") as f:
                content = f.read()
            table_match = project_manual_manager.detail_table_pattern.search(content)
            return table_match.group(1) if table_match else ""
        except Exception as e:
            logging.error(f"❌ 解析手册表格内容失败 {manual_path}：{str(e)}")
            return ""

    def _should_ignore(self, event) -> bool:
        """判断是否需要忽略该变动"""
        if event.is_directory:
            return True
        # 仅处理项目手册文件
        if not os.path.basename(event.src_path).endswith(CONFIG["manual_suffix"]):
            return True
        return False
    
def start_monitor():
    """启动双向监听服务"""
    # 校验仓库路径存在
    # Windows系统下显式初始化COM多线程公寓，解决PyInstaller打包环境watchdog COM线程冲突
    com_initialized = False
    if ole32 is not None:
        hr = ole32.CoInitializeEx(None, COINIT_MULTITHREADED)
        # 0 或 RPC_E_CHANGED_MODE(0x80010106) 都视为初始化成功
        com_initialized = (hr == 0 or hr == -2147417850)
        if com_initialized:
            logging.info("✅ Windows COM环境初始化完成，已规避0x8001010d线程冲突")
        else:
            logging.warning(f"⚠️ COM环境初始化返回码:{hr}，不影响基础运行")
    if not os.path.exists(REPOSITORY_PATH):
        logging.error(f"❌ 仓库路径不存在：{REPOSITORY_PATH}，请先创建仓库文件夹")
        return
    
    # 【初始化1】扫描所有一级项目文件夹，没有手册的自动创建
    logging.info("🔍 初始化扫描项目文件夹...")
    for dir_name in os.listdir(REPOSITORY_PATH):
        dir_path = os.path.join(REPOSITORY_PATH, dir_name)
        if os.path.isdir(dir_path) and not dir_name.startswith('.'):
            manual_file_name = f"{dir_name}项目手册.md"
            target_manual_path = os.path.join(dir_path, manual_file_name)
            if not os.path.exists(target_manual_path):
                logging.info(f"📝 初始化检测到项目【{dir_name}】缺少手册，自动创建：{manual_file_name}")
                project_manual_manager.generate_template(dir_name, f"{dir_name}/{dir_name}项目手册.md")
                # 记录操作到溯源队列
                CACHE["recent_operations"].append({
                "time": time.time(), "type": "auto_create_manual", "path": target_manual_path
                })
    
    # 【初始化2】缓存所有现有手册的表格内容
    for root, dirs, files in os.walk(REPOSITORY_PATH):
        for file in files:
            if file.endswith(CONFIG["manual_suffix"]):
                manual_path = os.path.join(root, file)
                CACHE["last_manual_table_content"][manual_path] = ManualChangeHandler()._parse_table_content(manual_path)

    # 启动监听
    observer = Observer()
    # 普通文件变动监听（正向绑定保留：文件变动更新手册）
    observer.schedule(FileChangeHandler(), path=REPOSITORY_PATH, recursive=True)
    observer.start()

    logging.info(f"🚀 双向自动同步服务已启动，监听路径：{REPOSITORY_PATH}")
    logging.info(f"⚙️  配置：防抖{CONFIG['debounce_time']*1000}ms，自动执行无需确认")
    logging.info("📢 按Ctrl+C停止服务")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # 退出前等待500ms，让当前正在处理的任务执行完成，避免pending任务报错
        time.sleep(0.5)
    finally:
        observer.stop()
        observer.join(timeout=3)
        # 释放COM环境
        if com_initialized and ole32 is not None:
            ole32.CoUninitialize()
            logging.info("✅ COM环境已释放")

# 模块被主程序/api_server导入时即启动唯一串行工作线程（守护线程，主进程退出自动结束）
_MANUAL_WORKER_THREAD = threading.Thread(target=_manual_update_worker, name="manual-sync-worker", daemon=True)
_MANUAL_WORKER_THREAD.start()

if __name__ == "__main__":
    start_monitor()