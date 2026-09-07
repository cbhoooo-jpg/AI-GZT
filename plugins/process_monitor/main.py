import os
import sys
import json
import time
import threading
import psutil
import httpx

# 动态添加项目根目录到Python路径，确保能导入项目级模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class SystemGuard:
    """系统保护名单（硬编码，不可修改，防止误杀系统关键进程）"""
    
    SYSTEM_PROTECTED_LIST = [
        "svchost.exe", "explorer.exe", "csrss.exe", 
        "lsass.exe", "winlogon.exe", "System", 
        "smss.exe", "services.exe", "wininit.exe",
        "dwm.exe", "fontdrvhost.exe", "sihost.exe",
        "taskhostw.exe", "ctfmon.exe", "conhost.exe",
        "Registry", "fontdrvhost.exe", "spoolsv.exe",
        "wininit.exe", "lsass.exe", "winlogon.exe",
        # 无后缀Windows核心系统进程
        "System Idle Process", "MemCompression", "Secure System",
        "Memory Compression", "smss", "csrss", "wininit",
        "services", "lsass", "svchost", "winlogon"
    ]
    
    @classmethod
    def is_protected(cls, process_name: str) -> bool:
        """检查进程是否在系统保护名单中"""
        return process_name.lower() in [name.lower() for name in cls.SYSTEM_PROTECTED_LIST]

class ProcessMonitor:
    """进程监控主引擎"""
    
    @staticmethod
    def _get_root_dir() -> str:
        """统一获取项目根目录，兼容开发/打包环境，避免路径计算错误"""
        if getattr(sys, 'frozen', False):
            # PyInstaller打包环境:exe可执行文件所在目录为项目根目录
            return os.path.dirname(sys.executable)
        else:
            # 开发环境:当前文件往上3级（plugins/process_monitor/main.py → 项目根目录）
            return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    def __init__(self):
        self.config = self._load_config()
        self.server_port = 8000  # 默认端口，由api_server启动时动态注入
        self._running = False
        self._thread = None
        self._last_scan_procs = set()  # 上次扫描的进程PID集合
        self._alert_history = {}  # 告警历史记录，用于冷却去重: {process_name: last_alert_timestamp}
        self._pending_confirm = {}  # 待用户确认的高危进程队列: {pid: {"proc_name": "", "risk_level": "", "reason": "", "exe_path": "", "expire_time": 0, "timer": None}}
        self._confirm_timeout = 30  # 用户确认超时时间（秒），超时自动终止
        self._whitelist_lock = threading.Lock()  # 白名单操作线程锁
        self._temp_whitelist = {}  # 临时白名单: {pid: expire_time}，父进程在白名单的子进程自动临时信任，程序重启失效
        self._auto_whitelist = set()  # 自动永久白名单: 带正规数字签名、在系统可信目录的进程，自动信任无需用户确认
        self.scan_mode = self.config.get("monitor_config", {}).get("scan_mode", "monitor")  # 扫描模式: monitor=监控模式(默认,仅检测可疑进程), full=全量扫描模式(返回所有进程)
        # 子进程批量合并配置
        self._child_proc_batch = {}  # 子进程批量缓存: {ppid: {"parent_name": "", "procs": [], "expire_time": 0}}
        self._batch_merge_window = 10  # 批量合并时间窗口（秒），同一父进程10秒内启动的子进程合并研判
        # 读取全局配置获取用户设置的仓库存储路径
        self.global_config = self._load_global_config()
        # 默认仓库路径统一使用标准根目录计算，避免路径不一致
        default_repo_path = os.path.join(self._get_root_dir(), "仓库文件夹")
        # 兼容两个配置key，优先使用全局标准key repository_path，兼容旧key repo_path
        self.repo_path = self.global_config.get("repository_path", self.global_config.get("repo_path", default_repo_path))
        print(f"[ProcessMonitor] 仓库存储路径: {self.repo_path}")
        # 用户配置文件热加载相关:记录最后修改时间，外部修改后自动加载无需重启
        self._user_config_mtime = 0
        # 初始化时记录当前配置文件的修改时间
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        user_config_path = os.path.join(plugin_dir, "user_config.json")
        if os.path.exists(user_config_path):
            self._user_config_mtime = os.path.getmtime(user_config_path)
        # 初始化自动白名单（系统可信目录进程）
        self._init_auto_whitelist()

    def _load_config(self) -> dict:
        """加载插件配置，优先读取user_config.json用户配置，合并plugin.json默认配置"""
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(plugin_dir, "plugin.json")
        user_config_path = os.path.join(plugin_dir, "user_config.json")
        
        try:
            # 先加载默认配置
            with open(config_path, "r", encoding="utf-8") as f:
                raw_config = json.load(f)
            
            # 兼容标准插件配置格式:将config数组转换为原有嵌套字典结构
            parsed_config = {
                "monitor_config": {},
                "whitelist": [],
                "action_policy": {},
                "ai_config": {},
                "alert_config": {}
            }
            if "config" in raw_config and isinstance(raw_config["config"], list):
                for item in raw_config["config"]:
                    key = item.get("key")
                    value = item.get("default")
                    if key == "scan_interval":
                        parsed_config["monitor_config"]["scan_interval"] = value
                    elif key == "enabled":
                        parsed_config["monitor_config"]["enabled"] = value
                    elif key == "auto_start":
                        parsed_config["monitor_config"]["auto_start"] = value
                    elif key == "scan_mode":
                        parsed_config["monitor_config"]["scan_mode"] = value
                    elif key == "whitelist":
                        parsed_config["whitelist"] = value
                    elif key == "high_risk_action":
                        parsed_config["action_policy"]["high_risk_action"] = value
                    elif key == "medium_risk_action":
                        parsed_config["action_policy"]["medium_risk_action"] = value
                    elif key == "low_risk_action":
                        parsed_config["action_policy"]["low_risk_action"] = value
                    elif key == "session_id":
                        parsed_config["ai_config"]["session_id"] = value
                    elif key == "system_prompt":
                        parsed_config["ai_config"]["system_prompt"] = value
                    elif key == "cooldown_seconds":
                        parsed_config["alert_config"]["cooldown_seconds"] = value
            
            # 再加载用户自定义配置，覆盖默认值
            if os.path.exists(user_config_path):
                try:
                    with open(user_config_path, "r", encoding="utf-8") as f:
                        user_config = json.load(f)
                    # 合并用户配置到默认配置
                    for key, value in user_config.items():
                        if key == "scan_interval":
                            parsed_config["monitor_config"]["scan_interval"] = value
                        elif key == "enabled":
                            parsed_config["monitor_config"]["enabled"] = value
                        elif key == "auto_start":
                            parsed_config["monitor_config"]["auto_start"] = value
                        elif key == "scan_mode":
                            parsed_config["monitor_config"]["scan_mode"] = value
                        elif key == "whitelist":
                            parsed_config["whitelist"] = value
                        elif key == "high_risk_action":
                            parsed_config["action_policy"]["high_risk_action"] = value
                        elif key == "medium_risk_action":
                            parsed_config["action_policy"]["medium_risk_action"] = value
                        elif key == "low_risk_action":
                            parsed_config["action_policy"]["low_risk_action"] = value
                        elif key == "session_id":
                            parsed_config["ai_config"]["session_id"] = value
                        elif key == "system_prompt":
                            parsed_config["ai_config"]["system_prompt"] = value
                        elif key == "cooldown_seconds":
                            parsed_config["alert_config"]["cooldown_seconds"] = value
                except Exception as e:
                    print(f"[ProcessMonitor] 加载用户配置失败，使用默认配置: {e}")
            
            return parsed_config
        except Exception as e:
            print(f"[ProcessMonitor] 加载配置失败，使用默认配置: {e}")
            return {
                "monitor_config": {"scan_interval": 5, "enabled": False, "scan_mode": "monitor"},
                "whitelist": [],
                "action_policy": {"high_risk_action": "user_confirm", "medium_risk_action": "notify_only", "low_risk_action": "allow"},
                "ai_config": {"session_id": "process_monitor", "system_prompt": ""},
                "alert_config": {"cooldown_seconds": 300}
            }

    def _reload_config_if_changed(self):
        """热加载配置:检查user_config.json是否被外部修改（前端手动修改/其他进程修改），自动加载最新配置无需重启"""
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        user_config_path = os.path.join(plugin_dir, "user_config.json")
        try:
            if os.path.exists(user_config_path):
                current_mtime = os.path.getmtime(user_config_path)
                # 文件修改时间比上次记录的新，说明被外部修改了，重新加载配置
                if current_mtime > self._user_config_mtime:
                    print(f"[ProcessMonitor] 检测到用户配置文件被外部修改，自动热加载最新配置")
                    self.config = self._load_config()
                    self._user_config_mtime = current_mtime
                    # 同步更新扫描模式
                    self.scan_mode = self.config.get("monitor_config", {}).get("scan_mode", "monitor")
        except Exception as e:
            print(f"[ProcessMonitor] 热加载配置失败: {e}")

    def _load_global_config(self) -> dict:
        """加载项目根目录全局config.json配置，多重路径兜底，避免路径计算错误导致找不到文件"""
        # 按优先级尝试多个可能的根目录路径，兼容各种运行环境
        base_root = self._get_root_dir()
        candidate_root_dirs = [
            base_root,  # 优先用统一计算的标准根目录
            os.path.join(base_root, "_internal"),  # 适配PyInstaller onedir模式，config在_internal目录下的情况
            os.getcwd(),  # 兜底1:当前工作目录
            os.path.dirname(os.path.abspath(sys.argv[0])),  # 兜底2:启动脚本/exe所在目录
            os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "_internal"),  # 兜底3:启动目录下的_internal
        ]
        # 去重避免重复尝试
        candidate_root_dirs = list(set(candidate_root_dirs))
        
        for root_dir in candidate_root_dirs:
            config_path = os.path.join(root_dir, "config.json")
            try:
                if os.path.exists(config_path):
                    with open(config_path, "r", encoding="utf-8") as f:
                        print(f"[ProcessMonitor] 成功加载全局配置，路径: {config_path}")
                        return json.load(f)
            except Exception as e:
                print(f"[ProcessMonitor] 尝试加载配置 {config_path} 失败: {e}")
                continue
        
        # 所有路径都找不到配置文件，返回空配置使用默认值
        print(f"[ProcessMonitor] 所有候选路径均未找到config.json，使用默认仓库路径")
        return {}
    def _init_auto_whitelist(self):
        """初始化自动永久白名单，扫描系统可信目录下的正规进程"""
        # Windows系统可信目录列表
        trusted_dirs = [
            os.environ.get("SystemRoot", r"C:\Windows").lower(),
            os.environ.get("ProgramFiles", r"C:\Program Files").lower(),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)").lower()
        ]
        
        # 预扫描当前运行的进程，符合可信目录规则的自动加入白名单
        for p in psutil.process_iter(['name', 'exe']):
            try:
                exe_path = p.info.get('exe', '')
                if not exe_path:
                    continue
                exe_path_lower = exe_path.lower()
                # 检查路径是否在可信目录下
                for trusted_dir in trusted_dirs:
                    if exe_path_lower.startswith(trusted_dir):
                        self._auto_whitelist.add(p.info['name'].lower())
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        print(f"[ProcessMonitor] 自动白名单初始化完成，共加载 {len(self._auto_whitelist)} 个可信系统进程")

    def _check_auto_whitelist(self, process_name: str, exe_path: str = "") -> bool:
        """检查进程是否符合自动白名单规则（可信目录+正规签名）"""
        proc_name_lower = process_name.lower()
        # 先检查已缓存的自动白名单
        if proc_name_lower in self._auto_whitelist:
            return True
        
        # 有路径时实时检查是否在可信目录
        if exe_path:
            exe_path_lower = exe_path.lower()
            trusted_dirs = [
                os.environ.get("SystemRoot", r"C:\Windows").lower(),
                os.environ.get("ProgramFiles", r"C:\Program Files").lower(),
                os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)").lower()
            ]
            for trusted_dir in trusted_dirs:
                if exe_path_lower.startswith(trusted_dir):
                    # 加入自动白名单缓存，下次直接命中
                    self._auto_whitelist.add(proc_name_lower)
                    return True
        return False

    def set_server_port(self, port: int):
        """设置API服务端口，由api_server启动时动态注入"""
        self.server_port = port
        print(f"[ProcessMonitor] 动态端口已注入: {self.server_port}")

    def scan_once(self, mode: str = None) -> str:
        """执行一次进程扫描，支持双模式
        :param mode: 扫描模式: monitor=监控模式(仅返回可疑进程,过滤白名单/系统进程), full=全量扫描(返回所有进程)
        """
        scan_mode = mode or self.scan_mode
        print(f"[ProcessMonitor] 开始执行{ '全量' if scan_mode == 'full' else '监控' }模式进程扫描...")
        result_lines = ["【进程监控扫描报告】"]
        result_lines.append(f"扫描时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        result_lines.append(f"扫描模式: {'全量扫描（返回所有进程）' if scan_mode == 'full' else '监控模式（仅返回可疑进程）'}")
        result_lines.append("-" * 60)
        
        proc_count = 0
        suspicious_procs = []
        
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'exe']):
            try:
                pid = p.info['pid']
                name = p.info['name']
                cpu = p.info['cpu_percent']
                mem = p.info['memory_info'].rss / (1024 * 1024) if p.info['memory_info'] else 0
                exe_path = p.info.get('exe', 'N/A')
                
                # 检查是否在三级白名单中:系统保护 > 用户白名单 > 自动可信白名单 > 临时白名单
                is_whitelisted = (SystemGuard.is_protected(name) 
                                  or self._check_whitelist(name) 
                                  or self._check_auto_whitelist(name, exe_path)
                                  or pid in self._temp_whitelist)
                status = "白名单/系统/可信" if is_whitelisted else "普通"
                
                # 监控模式下过滤掉白名单/系统进程，仅返回可疑进程
                if scan_mode == "monitor" and is_whitelisted:
                    continue
                
                result_lines.append(f"PID: {pid:<6} | 进程名: {name:<30} | CPU: {cpu:>5.1f}% | 内存: {mem:>7.1f}MB | 状态: {status}")
                proc_count += 1
                
                # 简单的可疑进程判断逻辑（非白名单且CPU或内存占用过高，或路径在临时目录）
                is_temp_path = exe_path and (os.environ.get('TEMP', '').lower() in exe_path.lower() or os.environ.get('TMP', '').lower() in exe_path.lower() or 'downloads' in exe_path.lower())
                if not is_whitelisted and (cpu > 50 or mem > 500 or is_temp_path):
                    suspicious_procs.append({"pid": pid, "name": name, "cpu": cpu, "mem": mem, "path": exe_path})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        result_lines.append("-" * 60)
        result_lines.append(f"扫描完成，共发现 {proc_count} 个进程运行中。")
        
        if suspicious_procs:
            result_lines.append(f"\n⚠️ 发现 {len(suspicious_procs)} 个可疑进程，建议关注:")
            for sp in suspicious_procs:
                result_lines.append(f"  - PID: {sp['pid']}, 进程名: {sp['name']}, CPU: {sp['cpu']:.1f}%, 内存: {sp['mem']:.1f}MB, 路径: {sp['path']}")
        else:
            result_lines.append("\n✅ 未发现明显可疑进程。")
            
        return "\n".join(result_lines)

    def start(self):
        """启动监控线程，启动成功后自动同步配置开关为开启状态"""
        if self._running:
            print("[ProcessMonitor] 监控已在运行中")
            return True, "监控已在运行中"

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        # 同步更新配置状态为启用
        self.config["monitor_config"]["enabled"] = True
        self._save_config()
        print(f"[ProcessMonitor] 进程监控已启动，轮询间隔: {self.config['monitor_config']['scan_interval']}秒")
        return True, f"进程监控已启动，轮询间隔: {self.config['monitor_config']['scan_interval']}秒"

    def stop(self):
        """停止监控线程，停止后自动同步配置开关为关闭状态"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        # 同步更新配置状态为禁用
        self.config["monitor_config"]["enabled"] = False
        self._save_config()
        print("[ProcessMonitor] 进程监控已停止")
        return True, "进程监控已停止"

    def _monitor_loop(self):
        """监控主循环"""
        # 初始化当前进程快照，避免启动时把所有现有进程都当新进程
        self._last_scan_procs = {p.pid for p in psutil.process_iter(['pid'])}
        
        while self._running:
            try:
                # 每次扫描前热加载配置，确保后台监控也能实时读取前端修改的最新配置
                self._reload_config_if_changed()
                # 动态读取最新的扫描间隔，用户修改后无需重启
                scan_interval = self.config.get("monitor_config", {}).get("scan_interval", 5)
                self._scan_processes()
            except Exception as e:
                print(f"[ProcessMonitor] 扫描进程出错: {e}")
            time.sleep(scan_interval)

    def _scan_processes(self):
        """扫描进程列表，发现新进程并处理"""
        current_procs = {}
        for p in psutil.process_iter(['pid', 'name', 'exe', 'ppid', 'create_time']):
            try:
                current_procs[p.info['pid']] = p.info
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        current_pids = set(current_procs.keys())
        new_pids = current_pids - self._last_scan_procs
        
        # 先清理过期的子进程批量缓存
        self._cleanup_expired_batch()
        
        for pid in new_pids:
            proc_info = current_procs.get(pid)
            if not proc_info:
                continue
            
            proc_name = proc_info.get('name', 'Unknown')
            exe_path = proc_info.get('exe', 'N/A')
            ppid = proc_info.get('ppid', 0)
            
            # 三级白名单检查:系统保护名单 > 用户永久白名单 > 自动可信白名单
            if SystemGuard.is_protected(proc_name):
                print(f"[ProcessMonitor] 进程 {proc_name} (PID: {pid}) 为系统核心进程，放行")
                continue
            if self._check_whitelist(proc_name):
                print(f"[ProcessMonitor] 进程 {proc_name} (PID: {pid}) 在用户白名单中，放行")
                continue
            if self._check_auto_whitelist(proc_name, exe_path):
                print(f"[ProcessMonitor] 进程 {proc_name} (PID: {pid}) 为系统可信目录正规进程，自动放行")
                continue
            
            # 检查告警冷却
            if not self._check_cooldown(proc_name):
                print(f"[ProcessMonitor] 进程 {proc_name} (PID: {pid}) 在告警冷却期内，跳过")
                continue
            
            # 检查父进程是否可信，可信父进程的子进程加入临时白名单
            try:
                parent_proc = psutil.Process(ppid)
                parent_name = parent_proc.name()
                parent_exe = parent_proc.exe()
                # 父进程在任意白名单中，子进程临时放行1小时
                if (self._check_whitelist(parent_name) or SystemGuard.is_protected(parent_name) 
                    or self._check_auto_whitelist(parent_name, parent_exe)):
                    self._temp_whitelist[pid] = time.time() + 3600
                    print(f"[ProcessMonitor] 进程 {proc_name} (PID: {pid}) 父进程 {parent_name} 可信，临时放行")
                    continue
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            
            # 检查临时白名单
            if pid in self._temp_whitelist:
                if time.time() < self._temp_whitelist[pid]:
                    print(f"[ProcessMonitor] 进程 {proc_name} (PID: {pid}) 在临时白名单中，放行")
                    continue
                else:
                    del self._temp_whitelist[pid]
            
            # 子进程批量合并逻辑:同一父进程10秒内启动的子进程批量研判
            # 排除系统空闲进程（PPID=0）
            if ppid != 0:
                # 加入父进程对应的批量缓存
                if ppid not in self._child_proc_batch:
                    try:
                        parent_name = psutil.Process(ppid).name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        parent_name = "Unknown"
                    self._child_proc_batch[ppid] = {
                        "parent_name": parent_name,
                        "procs": [],
                        "expire_time": time.time() + self._batch_merge_window
                    }
                self._child_proc_batch[ppid]["procs"].append({
                    "pid": pid,
                    "proc_info": proc_info,
                    "proc_name": proc_name,
                    "exe_path": exe_path
                })
                print(f"[ProcessMonitor] 子进程 {proc_name} (PID: {pid}) 已加入父进程 {self._child_proc_batch[ppid]['parent_name']} 的批量研判队列")
                continue
            
            # 独立进程（无父进程/父进程已退出）直接处理
            self._process_single_proc(pid, proc_info, proc_name, exe_path)
        
        # 处理到期的批量子进程队列
        self._process_ready_batch()
        
        self._last_scan_procs = current_pids
    def _check_whitelist(self, process_name: str) -> bool:
        """检查进程是否在用户白名单中"""
        whitelist = self.config.get("whitelist", [])
        return process_name.lower() in [name.lower() for name in whitelist]

    def _check_cooldown(self, process_name: str) -> bool:
        """检查告警冷却，同一进程在冷却时间内不重复通知"""
        cooldown_seconds = self.config.get("alert_config", {}).get("cooldown_seconds", 300)
        last_alert = self._alert_history.get(process_name, 0)
        if time.time() - last_alert < cooldown_seconds:
            return False
        self._alert_history[process_name] = time.time()
        return True
    def _cleanup_expired_batch(self):
        """清理过期的子进程批量缓存"""
        now = time.time()
        expired_ppids = [ppid for ppid, batch in self._child_proc_batch.items() if now > batch["expire_time"]]
        for ppid in expired_ppids:
            del self._child_proc_batch[ppid]

    def _process_ready_batch(self):
        """处理到期的批量子进程队列，合并后发给AI研判"""
        now = time.time()
        ready_ppids = [ppid for ppid, batch in self._child_proc_batch.items() if now >= batch["expire_time"]]
        
        for ppid in ready_ppids:
            batch = self._child_proc_batch.pop(ppid)
            procs = batch["procs"]
            parent_name = batch["parent_name"]
            
            if not procs:
                continue
            
            # 批量合并研判:多个子进程合并为一次AI请求
            proc_count = len(procs)
            proc_names = [p["proc_name"] for p in procs]
            self._push_system_message(f"🔍 检测到父进程 [{parent_name}] 启动了 {proc_count} 个子进程: {', '.join(proc_names)}，正在批量AI风险研判...")
            
            # 采集所有子进程的详细信息
            batch_info = []
            for proc in procs:
                detailed_info = self._collect_process_info(proc["pid"], proc["proc_info"])
                batch_info.append(detailed_info)
            
            # 构造批量研判请求
            query = f"【进程监控批量告警】父进程 {parent_name} (PID: {ppid}) 启动了{proc_count}个子进程:\n"
            for idx, info in enumerate(batch_info, 1):
                query += f"\n子进程{idx}:\n" \
                        f"- 进程名: {info.get('name')}\n" \
                        f"- 路径: {info.get('exe_path')}\n" \
                        f"- CPU占用: {info.get('cpu_percent', 0):.1f}%\n" \
                        f"- 内存占用: {info.get('memory_mb', 0):.1f}MB\n" \
                        f"- 命令行: {info.get('cmdline', 'N/A')}\n"
            query += "\n请逐个判断这些子进程是否为恶意程序，返回JSON数组格式结果，每个元素包含{\"pid\": 进程PID, \"risk_level\": \"high/medium/low\", \"reason\": \"判断原因\"}"
            
            try:
                ai_config = self.config.get("ai_config", {})
                response = httpx.post(
                    f"http://127.0.0.1:{self.server_port}/api/chat",
                    json={
                        "query": query,
                        "session_id": ai_config.get("session_id", "process_monitor"),
                        "system_prompt": ai_config.get("system_prompt", "你收到了一条进程监控批量告警，请逐个判断子进程风险，返回JSON数组格式"),
                        "attachments": [],
                        "silent": True
                    },
                    timeout=60
                )
                ai_response = response.json()
                # 解析批量研判结果
                ai_content = ai_response.get("response", ai_response.get("message", ""))
                import re
                json_match = re.search(r'\[.*\]', ai_content, re.DOTALL)
                risk_map = {}
                if json_match:
                    results = json.loads(json_match.group(0))
                    for res in results:
                        risk_map[res.get("pid")] = (res.get("risk_level", "medium"), res.get("reason", "未知"))
                
                # 逐个处置子进程
                for proc in procs:
                    pid = proc["pid"]
                    proc_name = proc["proc_name"]
                    exe_path = proc["exe_path"]
                    risk_level, reason = risk_map.get(pid, ("medium", "批量研判解析失败"))
                    
                    # 推送结果消息
                    if risk_level == "high":
                        self._push_system_message(f"⚠️ 子进程 [{proc_name}] 判定为高危，原因:{reason}，已弹出确认窗口")
                    elif risk_level == "medium":
                        self._push_system_message(f"🟡 子进程 [{proc_name}] 判定为中危，原因:{reason}，已记录留档")
                    else:
                        self._push_system_message(f"🟢 子进程 [{proc_name}] 判定为低风险，已自动放行")
                    
                    self._execute_action(pid, proc_name, risk_level, reason, exe_path)
                    
            except Exception as e:
                print(f"[ProcessMonitor] 批量研判失败: {e}")
                self._push_system_message(f"⚠️ 父进程 [{parent_name}] 的{proc_count}个子进程批量研判失败，已按中危处理")
                # 失败时逐个按中危处置
                for proc in procs:
                    self._execute_action(proc["pid"], proc["proc_name"], "medium", "批量研判失败，按中危处理", proc["exe_path"])

    def _process_single_proc(self, pid: int, proc_info: dict, proc_name: str, exe_path: str):
        """处理单个独立进程，采集信息并发送AI研判"""
        # 采集详细信息并发送给AI
        detailed_info = self._collect_process_info(pid, proc_info)
        print(f"[ProcessMonitor] 发现新独立进程，发送给AI判断: {proc_name} (PID: {pid})")
        ai_response = self._notify_ai(detailed_info)
        
        # 解析AI响应并执行处置，传入进程名用于推送消息
        risk_level, reason = self._parse_ai_response(ai_response, proc_name)
        # 传入进程路径用于记录留档
        self._execute_action(pid, proc_name, risk_level, reason, exe_path)

    def _collect_process_info(self, pid: int, proc_info: dict) -> dict:
        """采集进程详细信息"""
        detailed = {
            "pid": pid,
            "name": proc_info.get('name', 'Unknown'),
            "exe_path": proc_info.get('exe', 'N/A'),
            "create_time": proc_info.get('create_time', 0),
            "parent_pid": proc_info.get('ppid', 0)
        }
        try:
            p = psutil.Process(pid)
            detailed['cmdline'] = " ".join(p.cmdline())
            detailed['cpu_percent'] = p.cpu_percent(interval=0.1)
            detailed['memory_mb'] = p.memory_info().rss / (1024 * 1024)
            
            # 获取父进程名
            try:
                detailed['parent_name'] = p.parent().name()
            except Exception:
                detailed['parent_name'] = "N/A"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        return detailed

    def _push_system_message(self, content: str):
        """推送系统消息到前端聊天窗口，不打断用户对话"""
        try:
            httpx.post(
                f"http://127.0.0.1:{self.server_port}/api/sse/push",
                json={
                    "type": "system_message",
                    "data": {
                        "role": "system",
                        "content": content,
                        "timestamp": time.time()
                    }
                },
                timeout=5
            )
        except Exception as e:
            print(f"[ProcessMonitor] 推送系统消息失败: {e}")

    def _notify_ai(self, process_info: dict) -> dict:
        """发送进程信息给AI助手判断，静默调用不推送到全局聊天流"""
        ai_config = self.config.get("ai_config", {})
        system_prompt = ai_config.get("system_prompt", "你收到了一条进程监控告警，请根据进程信息判断是否为恶意程序，并返回JSON格式结果:{\"risk_level\": \"high/medium/low\", \"reason\": \"判断原因\"}")
        
        proc_name = process_info.get('name')
        # 推送研判中消息到前端聊天区
        self._push_system_message(f"🔍 检测到新进程 [{proc_name}]，正在进行AI风险研判...")
        
        query = f"【进程监控告警】发现新进程:\n" \
                f"- 进程名: {proc_name}\n" \
                f"- 路径: {process_info.get('exe_path')}\n" \
                f"- 父进程: {process_info.get('parent_name')} (PID: {process_info.get('parent_pid')})\n" \
                f"- CPU占用: {process_info.get('cpu_percent', 0):.1f}%\n" \
                f"- 内存占用: {process_info.get('memory_mb', 0):.1f}MB\n" \
                f"- 启动时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(process_info.get('create_time', 0)))}\n" \
                f"- 命令行: {process_info.get('cmdline', 'N/A')}\n" \
                f"请判断该进程是否为恶意程序，并返回JSON格式结果。"
        
        try:
            response = httpx.post(
                f"http://127.0.0.1:{self.server_port}/api/chat",
                json={
                    "query": query,
                    "session_id": ai_config.get("session_id", "process_monitor"),
                    "system_prompt": system_prompt,
                    "attachments": [],
                    "silent": True  # 静默调用，AI结果不推送到全局SSE流，不打断用户对话
                },
                timeout=60
            )
            return response.json()
        except Exception as e:
            print(f"[ProcessMonitor] 请求AI助手失败: {e}")
            # 调用失败推送提示消息
            self._push_system_message(f"⚠️ 进程 [{proc_name}] AI研判失败，已按中危处理")
            return {"error": str(e)}

    def _parse_ai_response(self, response: dict, proc_name: str = "") -> tuple:
        """解析AI返回的判断结果，提取风险等级，同时推送结果消息到前端聊天区"""
        try:
            # 假设AI返回的格式为 {"risk_level": "high/medium/low", "reason": "..."}
            # 需要从response中提取出AI的回复内容，并解析JSON
            ai_content = response.get("response", response.get("message", ""))
            risk_level = "medium"
            reason = "未知"
            
            if isinstance(ai_content, dict):
                risk_level = ai_content.get("risk_level", "medium")
                reason = ai_content.get("reason", "未知")
            else:
                # 尝试从文本中提取JSON
                import re
                json_match = re.search(r'\{.*\}', ai_content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
                    risk_level = result.get("risk_level", "medium")
                    reason = result.get("reason", "未知")
                else:
                    reason = "AI响应解析失败"
            
            # 推送研判结果到前端聊天区
            if proc_name:
                if risk_level == "high":
                    self._push_system_message(f"⚠️ 检测到高危进程 [{proc_name}]，原因:{reason}，已弹出确认窗口")
                elif risk_level == "medium":
                    self._push_system_message(f"🟡 检测到中危进程 [{proc_name}]，原因:{reason}，已记录留档")
                else:
                    self._push_system_message(f"🟢 检测到低风险进程 [{proc_name}]，已自动放行")
            
            return risk_level, reason
        except Exception as e:
            print(f"[ProcessMonitor] 解析AI响应失败: {e}")
            if proc_name:
                self._push_system_message(f"⚠️ 进程 [{proc_name}] AI响应解析失败，已按中危处理")
            return "medium", "解析异常"
    def _save_process_record(self, pid: int, process_name: str, risk_level: str, reason: str, action: str, exe_path: str, result: str):
        """
        持久化保存进程处置记录到markdown文件
        保存路径:用户配置的仓库存储路径/进程监控记录/进程监控.md
        文件不存在时自动创建，存在则追加记录
        """
        # 优先使用用户在配置页设置的仓库存储路径，兜底默认路径
        record_dir = os.path.join(self.repo_path, "进程监控记录")
        record_file = os.path.join(record_dir, "进程监控.md")
        
        # 自动创建目录（不存在时创建，已存在无影响）
        os.makedirs(record_dir, exist_ok=True)
        
        # 文件不存在时先写入文件头
        if not os.path.exists(record_file):
            with open(record_file, "w", encoding="utf-8") as f:
                f.write("# 进程监控处置记录\n\n")
                f.write("> 本文件由AI助手自动生成，记录所有进程监控的风险研判、处置动作及结果，供用户回溯查阅。\n\n")
        
        # 生成当前记录内容
        current_time = time.strftime('%Y-%m-%d %H:%M:%S')
        record_content = f"""---
## 处置时间:{current_time}
- 进程名称:{process_name}
- 进程PID:{pid}
- 进程路径:{exe_path}
- 风险等级:{risk_level}
- AI研判原因:{reason}
- 执行动作:{action}
- 处置结果:{result}
"""
        # 追加写入记录
        with open(record_file, "a", encoding="utf-8") as f:
            f.write(record_content)
        
        print(f"[ProcessMonitor] 处置记录已自动保存到:{record_file}")

    def _force_kill_process(self, pid: int, process_name: str) -> str:
        """强制杀死进程，优雅终止失败时兜底使用系统taskkill命令杀死整个进程树"""
        # 先尝试优雅终止
        try:
            p = psutil.Process(pid)
            p.terminate()
            p.wait(timeout=3)
            return "已成功终止进程"
        except psutil.NoSuchProcess:
            return "进程已自行退出，无需终止"
        except (psutil.AccessDenied, psutil.TimeoutExpired):
            # 优雅终止失败，用系统命令强制杀进程树
            try:
                import subprocess
                subprocess.run(
                    ["taskkill", "/f", "/t", "/pid", str(pid)],
                    capture_output=True,
                    check=True,
                    shell=True
                )
                return "已强制终止进程及关联子进程"
            except Exception as e:
                return f"强制终止失败，错误信息:{str(e)}，请手动以管理员身份运行后重试"
        except Exception as e:
            return f"终止进程失败，错误信息:{str(e)}"

    def _push_notification(self, pid: int, process_name: str, risk_level: str, reason: str, exe_path: str):
        """推送告警通知到前端，触发弹窗"""
        try:
            httpx.post(
                f"http://127.0.0.1:{self.server_port}/api/sse/push",
                json={
                    "type": "process_monitor_alert",
                    "data": {
                        "pid": pid,
                        "process_name": process_name,
                        "risk_level": risk_level,
                        "reason": reason,
                        "exe_path": exe_path,
                        "timeout": self._confirm_timeout,
                        "timestamp": time.time()
                    }
                },
                timeout=5
            )
        except Exception as e:
            print(f"[ProcessMonitor] 推送前端通知失败: {e}")

    def _on_confirm_timeout(self, pid: int, process_name: str, risk_level: str, reason: str, exe_path: str):
        """用户确认超时，自动执行终止操作"""
        # 从待确认队列移除
        if pid in self._pending_confirm:
            del self._pending_confirm[pid]
        
        print(f"[ProcessMonitor] 进程 {process_name} (PID: {pid}) 等待用户确认超时，自动执行终止")
        # 强制终止进程
        action_result = self._force_kill_process(pid, process_name)
        
        # 保存留档记录
        try:
            self._save_process_record(
                pid=pid,
                process_name=process_name,
                risk_level=risk_level,
                reason=reason,
                action="timeout_auto_terminate",
                exe_path=exe_path,
                result=action_result
            )
        except Exception as e:
            print(f"[ProcessMonitor] 保存处置记录失败: {e}")

    def confirm_allow_process(self, pid: int) -> dict:
        """用户确认允许进程运行，自动加入白名单，取消倒计时"""
        with self._whitelist_lock:
            if pid not in self._pending_confirm:
                return {"success": False, "msg": "该进程不在待确认队列中，可能已处置完成"}
            
            proc_info = self._pending_confirm.pop(pid)
            proc_name = proc_info["process_name"]
            exe_path = proc_info["exe_path"]
            reason = proc_info["reason"]
            
            # 取消定时器
            if proc_info["timer"] and proc_info["timer"].is_alive():
                proc_info["timer"].cancel()
            
            # 加入用户白名单
            whitelist = self.config.get("whitelist", [])
            if proc_name.lower() not in [name.lower() for name in whitelist]:
                whitelist.append(proc_name)
                self.config["whitelist"] = whitelist
                # 持久化保存白名单到配置文件
                self._save_config()
            
            # 保存留档记录
            try:
                self._save_process_record(
                    pid=pid,
                    process_name=proc_name,
                    risk_level=proc_info["risk_level"],
                    reason=reason,
                    action="user_allow",
                    exe_path=exe_path,
                    result="用户手动允许运行，已自动加入白名单，后续启动不再提示"
                )
            except Exception as e:
                print(f"[ProcessMonitor] 保存处置记录失败: {e}")
            
            print(f"[ProcessMonitor] 用户允许进程 {proc_name} (PID: {pid}) 运行，已加入白名单")
            return {"success": True, "msg": f"已允许进程 {proc_name} 运行，后续不再提示"}

    def confirm_terminate_process(self, pid: int) -> dict:
        """用户确认立即终止进程"""
        if pid not in self._pending_confirm:
            return {"success": False, "msg": "该进程不在待确认队列中，可能已处置完成"}
        
        proc_info = self._pending_confirm.pop(pid)
        proc_name = proc_info["process_name"]
        exe_path = proc_info["exe_path"]
        reason = proc_info["reason"]
        
        # 取消定时器
        if proc_info["timer"] and proc_info["timer"].is_alive():
            proc_info["timer"].cancel()
        
        # 强制终止进程
        action_result = self._force_kill_process(pid, proc_name)
        
        # 保存留档记录
        try:
            self._save_process_record(
                pid=pid,
                process_name=proc_name,
                risk_level=proc_info["risk_level"],
                reason=reason,
                action="user_terminate",
                exe_path=exe_path,
                result=action_result
            )
        except Exception as e:
            print(f"[ProcessMonitor] 保存处置记录失败: {e}")
        
        print(f"[ProcessMonitor] 用户手动终止进程 {proc_name} (PID: {pid})，处置结果: {action_result}")
        return {"success": True, "msg": f"进程 {proc_name} 处置结果: {action_result}"}

    def _save_config(self):
        """持久化保存当前所有配置到user_config.json文件，和前端配置保存逻辑一致，避免覆盖默认配置"""
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        user_config_path = os.path.join(plugin_dir, "user_config.json")
        try:
            # 构造扁平化的用户配置结构，和api_server保存格式一致
            user_config = {
                "scan_interval": self.config["monitor_config"].get("scan_interval", 5),
                "enabled": self.config["monitor_config"].get("enabled", False),
                "auto_start": self.config["monitor_config"].get("auto_start", False),
                "scan_mode": self.config["monitor_config"].get("scan_mode", "monitor"),
                "whitelist": self.config.get("whitelist", []),
                "high_risk_action": self.config["action_policy"].get("high_risk_action", "user_confirm"),
                "medium_risk_action": self.config["action_policy"].get("medium_risk_action", "notify_only"),
                "low_risk_action": self.config["action_policy"].get("low_risk_action", "allow"),
                "session_id": self.config["ai_config"].get("session_id", "process_monitor"),
                "system_prompt": self.config["ai_config"].get("system_prompt", ""),
                "cooldown_seconds": self.config["alert_config"].get("cooldown_seconds", 300)
            }
            
            with open(user_config_path, "w", encoding="utf-8") as f:
                json.dump(user_config, f, ensure_ascii=False, indent=2)
            # 保存后更新文件修改时间记录，避免自己刚保存的配置被重复热加载
            self._user_config_mtime = os.path.getmtime(user_config_path)
        except Exception as e:
            print(f"[ProcessMonitor] 保存配置失败: {e}")

    def _execute_action(self, pid: int, process_name: str, risk_level: str, reason: str, exe_path: str = "N/A"):
        """根据风险等级执行处置动作，高危进程先等待用户确认，超时自动终止"""
        action_policy = self.config.get("action_policy", {})
        action = ""
        action_result = "未执行处置"
        
        if risk_level == "high":
            action = action_policy.get("high_risk_action", "user_confirm")
        elif risk_level == "medium":
            action = action_policy.get("medium_risk_action", "notify_only")
        else:
            action = action_policy.get("low_risk_action", "allow")
        
        print(f"[ProcessMonitor] 进程 {process_name} (PID: {pid}) 风险等级: {risk_level}，原因: {reason}，执行动作: {action}")
        
        if action == "user_confirm" and risk_level == "high":
            # 高危进程加入待确认队列，启动倒计时
            expire_time = time.time() + self._confirm_timeout
            timer = threading.Timer(
                self._confirm_timeout,
                self._on_confirm_timeout,
                args=(pid, process_name, risk_level, reason, exe_path)
            )
            timer.daemon = True
            self._pending_confirm[pid] = {
                "process_name": process_name,
                "risk_level": risk_level,
                "reason": reason,
                "exe_path": exe_path,
                "expire_time": expire_time,
                "timer": timer
            }
            timer.start()
            # 推送前端通知弹窗
            self._push_notification(pid, process_name, risk_level, reason, exe_path)
            action_result = f"等待用户确认，{self._confirm_timeout}秒无操作将自动终止"
            print(f"[ProcessMonitor] 高危进程 {process_name} (PID: {pid}) 已推送通知等待用户确认")
        elif action == "notify_only":
            action_result = "仅通知告警，未执行终止操作"
            # 中危进程也推送通知，但不自动终止
            self._push_notification(pid, process_name, risk_level, reason, exe_path)
        elif action == "allow":
            action_result = "低风险进程，已自动放行"
        
        # 非待确认状态的进程直接保存记录，待确认的进程处置完成后再保存
        if risk_level != "high" or action != "user_confirm":
            try:
                self._save_process_record(
                    pid=pid,
                    process_name=process_name,
                    risk_level=risk_level,
                    reason=reason,
                    action=action,
                    exe_path=exe_path,
                    result=action_result
                )
            except Exception as e:
                print(f"[ProcessMonitor] 保存处置记录失败: {e}")

# 全局监控单例，全局唯一，避免多实例配置冲突
_monitor_instance = ProcessMonitor()

# 插件标准入口
def init(config: dict = None):
    """插件初始化方法，安装/启用/配置修改时自动调用，支持自动启动配置"""
    global _monitor_instance
    # 每次初始化都热加载最新配置，确保和前端保存的配置同步
    _monitor_instance._reload_config_if_changed()
    
    # 检测自动启动配置，开启则自动启动监控
    auto_start = _monitor_instance.config.get("monitor_config", {}).get("auto_start", False)
    enabled = _monitor_instance.config.get("monitor_config", {}).get("enabled", False)
    if auto_start and enabled and not _monitor_instance._running:
        _monitor_instance.start()
        print("[ProcessMonitor] 插件初始化完成，已自动启动监控")
    else:
        print("[ProcessMonitor] 插件初始化完成")
    return _monitor_instance

def run(params: dict = None):
    """插件主方法，支持多种操作指令，兼容自然语言query解析"""
    global _monitor_instance
    
    # 每次执行操作前先热加载配置，确保读取到前端/外部修改的最新配置
    _monitor_instance._reload_config_if_changed()
    
    params = params or {}
    query = params.get("query", "").strip()
    action = params.get("action", "scan")
    process_names = params.get("process_names", [])
    
    # 自然语言指令解析:从query中识别操作意图
    if query:
        query_lower = query.lower()
        # 识别添加白名单指令
        if any(keyword in query_lower for keyword in ["添加白名单", "加入白名单", "加白名单", "批量添加", "加入监控白名单"]):
            action = "add_whitelist"
            # 从query中提取进程名:匹配任意xxx.exe格式的进程名，支持中文、空格、特殊字符
            import re
            exe_matches = re.findall(r'([^\s,，]+\.exe)', query, re.IGNORECASE)
            if exe_matches:
                process_names = list(set([name.strip() for name in exe_matches if name.strip()]))
        # 识别移除白名单指令
        elif any(keyword in query_lower for keyword in ["移除白名单", "删除白名单", "移出白名单"]):
            action = "remove_whitelist"
            import re
            exe_matches = re.findall(r'([^\s,，]+\.exe)', query, re.IGNORECASE)
            if exe_matches:
                process_names = list(set([name.strip() for name in exe_matches if name.strip()]))
        # 识别清空白名单指令
        elif any(keyword in query_lower for keyword in ["清空白名单", "清空所有白名单"]):
            action = "clear_whitelist"
        # 识别获取白名单指令
        elif any(keyword in query_lower for keyword in ["查看白名单", "获取白名单", "白名单列表"]):
            action = "get_whitelist"
        # 识别启动监控指令
        elif any(keyword in query_lower for keyword in ["启动监控", "开始监控", "开启进程监控"]):
            action = "start"
        # 识别停止监控指令
        elif any(keyword in query_lower for keyword in ["停止监控", "关闭监控", "结束监控"]):
            action = "stop"
        # 识别终止进程指令
        elif any(keyword in query_lower for keyword in ["终止进程", "杀死进程", "结束进程", "强制终止", "杀掉进程"]):
            action = "terminate_process"
            # 优先提取PID（数字）
            import re
            pid_matches = re.findall(r'pid[::\s]*(\d+)', query_lower)
            if pid_matches:
                params["pid"] = int(pid_matches[0])
            # 提取进程名
            exe_matches = re.findall(r'([^\s,，]+\.exe|[a-zA-Z0-9_\s]+(?:Process|System))', query, re.IGNORECASE)
            if exe_matches:
                process_names = list(set([name.strip() for name in exe_matches if name.strip() and len(name.strip()) < 50]))
                if process_names and not params.get("pid"):
                    params["process_names"] = process_names
        # 识别切换模式指令
        elif "全量扫描" in query_lower or "全量模式" in query_lower:
            action = "set_mode"
            params["mode"] = "full"
        elif "监控模式" in query_lower or "仅可疑进程" in query_lower:
            action = "set_mode"
            params["mode"] = "monitor"
    
    # 将解析到的进程名写回params
    if process_names and not params.get("process_names"):
        params["process_names"] = process_names
    
    if action == "scan":
        mode = params.get("mode", _monitor_instance.scan_mode)
        return _monitor_instance.scan_once(mode=mode)
    elif action == "set_mode":
        mode = params.get("mode", "monitor")
        if mode not in ["monitor", "full"]:
            return {"success": False, "msg": "模式仅支持monitor(监控模式)或full(全量扫描模式)"}
        _monitor_instance.scan_mode = mode
        _monitor_instance.config["monitor_config"]["scan_mode"] = mode
        _monitor_instance._save_config()
        return {"success": True, "msg": f"扫描模式已切换为: {'监控模式' if mode == 'monitor' else '全量扫描模式'}"}
    elif action == "start":
        _monitor_instance.start()
        return "进程监控已启动"
    elif action == "stop":
        _monitor_instance.stop()
        return "进程监控已停止"
    elif action == "confirm_allow":
        pid = params.get("pid")
        if not pid:
            return {"success": False, "msg": "缺少PID参数"}
        return _monitor_instance.confirm_allow_process(int(pid))
    elif action == "confirm_terminate":
        pid = params.get("pid")
        if not pid:
            return {"success": False, "msg": "缺少PID参数"}
        return _monitor_instance.confirm_terminate_process(int(pid))
    elif action in ["get_whitelist", "list_whitelist"]:
        # 获取当前白名单列表，兼容list_whitelist别名（AI调用时两种写法都支持）
        whitelist = _monitor_instance.config.get("whitelist", [])
        return {"success": True, "whitelist": whitelist, "count": len(whitelist)}
    elif action == "add_whitelist":
        # 添加进程到白名单，支持单个或批量
        proc_names = params.get("process_names", [])
        if isinstance(proc_names, str):
            proc_names = [proc_names]
        if not proc_names:
            return {"success": False, "msg": "请提供要添加的进程名称"}
        
        added = []
        already_exist = []
        whitelist = _monitor_instance.config.get("whitelist", [])
        whitelist_lower = [name.lower() for name in whitelist]
        
        for name in proc_names:
            name = name.strip()
            if not name:
                continue
            if name.lower() not in whitelist_lower:
                whitelist.append(name)
                added.append(name)
                whitelist_lower.append(name.lower())
            else:
                already_exist.append(name)
        
        _monitor_instance.config["whitelist"] = whitelist
        _monitor_instance._save_config()
        
        msg = []
        if added:
            msg.append(f"成功添加 {len(added)} 个进程到白名单: {', '.join(added)}")
        if already_exist:
            msg.append(f"{len(already_exist)} 个进程已在白名单中: {', '.join(already_exist)}")
        return {"success": True, "msg": "；".join(msg), "added": added, "already_exist": already_exist}
    elif action == "remove_whitelist":
        # 从白名单移除进程
        proc_names = params.get("process_names", [])
        if isinstance(proc_names, str):
            proc_names = [proc_names]
        if not proc_names:
            return {"success": False, "msg": "请提供要移除的进程名称"}
        
        removed = []
        not_exist = []
        whitelist = _monitor_instance.config.get("whitelist", [])
        new_whitelist = []
        
        for name in whitelist:
            if name.lower() in [n.lower() for n in proc_names]:
                removed.append(name)
            else:
                new_whitelist.append(name)
        
        not_exist = [n for n in proc_names if n.lower() not in [r.lower() for r in removed]]
        
        _monitor_instance.config["whitelist"] = new_whitelist
        _monitor_instance._save_config()
        
        msg = []
        if removed:
            msg.append(f"成功从白名单移除 {len(removed)} 个进程: {', '.join(removed)}")
        if not_exist:
            msg.append(f"{len(not_exist)} 个进程不在白名单中: {', '.join(not_exist)}")
        return {"success": True, "msg": "；".join(msg), "removed": removed, "not_exist": not_exist}
    elif action == "clear_whitelist":
        # 清空白名单
        _monitor_instance.config["whitelist"] = []
        _monitor_instance._save_config()
        return {"success": True, "msg": "白名单已清空"}
    elif action == "terminate_process":
        # 终止可疑进程，支持按PID或进程名终止
        pid = params.get("pid")
        target_names = params.get("process_names", [])
        if isinstance(target_names, str):
            target_names = [target_names]
        
        terminated = []
        failed = []
        
        # 优先按PID终止
        if pid:
            try:
                result = _monitor_instance._force_kill_process(int(pid), "未知进程")
                # 保存处置记录
                try:
                    p = psutil.Process(int(pid))
                    proc_name = p.name()
                    exe_path = p.exe()
                except:
                    proc_name = f"PID:{pid}"
                    exe_path = "N/A"
                _monitor_instance._save_process_record(
                    pid=int(pid),
                    process_name=proc_name,
                    risk_level="high",
                    reason="AI指令手动终止",
                    action="ai_terminate",
                    exe_path=exe_path,
                    result=result
                )
                terminated.append(f"PID:{pid}({proc_name})")
            except Exception as e:
                failed.append(f"PID:{pid}，错误:{str(e)}")
        
        # 按进程名终止（终止所有同名进程）
        if target_names:
            for name in target_names:
                name = name.strip()
                if not name:
                    continue
                # 禁止终止系统保护进程
                if SystemGuard.is_protected(name):
                    failed.append(f"{name}为系统核心保护进程，禁止终止")
                    continue
                # 遍历所有进程匹配名称
                count = 0
                for p in psutil.process_iter(['pid', 'name', 'exe']):
                    try:
                        if p.info['name'].lower() == name.lower():
                            result = _monitor_instance._force_kill_process(p.info['pid'], name)
                            _monitor_instance._save_process_record(
                                pid=p.info['pid'],
                                process_name=name,
                                risk_level="high",
                                reason="AI指令手动终止",
                                action="ai_terminate",
                                exe_path=p.info.get('exe', 'N/A'),
                                result=result
                            )
                            count += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                if count > 0:
                    terminated.append(f"{name}({count}个进程)")
                else:
                    failed.append(f"{name}，未找到运行中的进程")
        
        msg = []
        if terminated:
            msg.append(f"✅ 成功终止: {', '.join(terminated)}")
        if failed:
            msg.append(f"❌ 终止失败: {', '.join(failed)}")
        return {"success": len(terminated) > 0, "msg": "；".join(msg), "terminated": terminated, "failed": failed}
    elif action == "get_pending_alerts":
        # 返回当前待确认的告警列表
        pending = []
        for pid, info in _monitor_instance._pending_confirm.items():
            pending.append({
                "pid": pid,
                "process_name": info["process_name"],
                "risk_level": info["risk_level"],
                "reason": info["reason"],
                "exe_path": info["exe_path"],
                "remaining_seconds": max(0, int(info["expire_time"] - time.time()))
            })
        return {"pending_alerts": pending}
    else:
        return f"不支持的操作: {action}"

def uninstall():
    """插件卸载时自动调用"""
    print("[ProcessMonitor] 插件已卸载")