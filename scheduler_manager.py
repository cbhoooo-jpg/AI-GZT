import os
import json
import uuid
import time
import threading
import traceback
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore

# 任务持久化文件路径（改为用户目录，避免打包后程序目录无写权限）
_TASKS_DIR = os.path.join(os.path.expanduser("~"), ".ai_assistant")
os.makedirs(_TASKS_DIR, exist_ok=True)
TASKS_FILE = os.path.join(_TASKS_DIR, "scheduler_tasks.json")
# 执行锁，避免并发冲突
EXECUTION_LOCK = threading.Lock()

class SchedulerManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SchedulerManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.scheduler = BackgroundScheduler(jobstores={'default': MemoryJobStore()})
        self.tasks = []
        self.server_port = 8000  # 动态端口，默认8000，由api_server启动时注入，避免硬编码导致跨工作台误触发
        self.load_tasks()
    
    def set_server_port(self, port: int):
        """设置API服务端口，由api_server启动时动态注入，避免硬编码导致跨工作台误触发"""
        self.server_port = port
    
    def start(self):
        """启动调度器，恢复所有活跃任务"""
        if self.scheduler.running:
            return
        self.scheduler.start()
        # 恢复所有活跃任务
        active_tasks = [t for t in self.tasks if t.get("status") == "active"]
        for task in active_tasks:
            try:
                self._add_job_to_scheduler(task)
            except Exception as e:
                print(f"❌ 恢复任务【{task['name']}】失败: {str(e)}")
        print(f"✅ 调度器已启动，共恢复 {len(active_tasks)} 个活跃任务")
    
    def shutdown(self):
        """关闭调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
    
    def load_tasks(self):
        """从JSON文件加载任务列表"""
        if os.path.exists(TASKS_FILE):
            try:
                with open(TASKS_FILE, "r", encoding="utf-8") as f:
                    self.tasks = json.load(f)
            except Exception as e:
                print(f"❌ 加载任务文件失败: {str(e)}")
                self.tasks = []
        else:
            self.tasks = []
    
    def save_tasks(self):
        """保存任务列表到JSON文件"""
        try:
            with open(TASKS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存任务文件失败: {str(e)}")
    
    def get_all_tasks(self):
        """获取所有任务"""
        return self.tasks
    
    def get_task(self, task_id):
        """获取单个任务"""
        for task in self.tasks:
            if task["id"] == task_id:
                return task
        return None
    
    def create_task(self, data):
        """创建新任务"""
        task = {
            "id": str(uuid.uuid4())[:8],
            "name": data["name"],
            "type": data["type"],
            "schedule": data["schedule"],
            "prompt": data["prompt"],
            "status": "active",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_executed": None,
            "next_run_time": None,
            "history": []
        }
        self.tasks.append(task)
        self.save_tasks()
        self._add_job_to_scheduler(task)
        return task
    
    def update_task(self, task_id, data):
        """更新任务"""
        task = self.get_task(task_id)
        if not task:
            return None
        # 先移除旧的调度任务
        self._remove_job_from_scheduler(task_id)
        # 更新任务数据
        task["name"] = data["name"]
        task["type"] = data["type"]
        task["schedule"] = data["schedule"]
        task["prompt"] = data["prompt"]
        if task["status"] != "active":
            task["status"] = "active"
        self.save_tasks()
        # 重新添加调度任务
        self._add_job_to_scheduler(task)
        return task
    
    def cancel_task(self, task_id):
        """取消任务"""
        task = self.get_task(task_id)
        if not task:
            return False
        task["status"] = "cancelled"
        self._remove_job_from_scheduler(task_id)
        self.save_tasks()
        return True
    
    def delete_task(self, task_id):
        """删除任务"""
        task = self.get_task(task_id)
        if not task:
            return False
        self._remove_job_from_scheduler(task_id)
        self.tasks.remove(task)
        self.save_tasks()
        return True
    
    def _add_job_to_scheduler(self, task):
        """将任务添加到APScheduler"""
        if task["status"] != "active":
            return
        try:
            if task["type"] == "long_term":
                s = task["schedule"]
                trigger = CronTrigger(
                    hour=s["hour"],
                    minute=s["minute"],
                    day_of_week=s.get("day_of_week"),
                    day=s.get("day"),
                    month=s.get("month")
                )
            else:
                run_date = datetime.strptime(task["schedule"]["run_date"], "%Y-%m-%dT%H:%M")
                trigger = DateTrigger(run_date=run_date)
            
            self.scheduler.add_job(
                func=self._execute_task,
                trigger=trigger,
                args=[task["id"]],
                id=task["id"],
                replace_existing=True
            )
            # 更新下次执行时间
            job = self.scheduler.get_job(task["id"])
            if job:
                next_run = getattr(job, 'next_run_time', None)
                task["next_run_time"] = next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else None
            self.save_tasks()
        except Exception as e:
            print(f"❌ 添加调度任务失败: {str(e)}")
    
    def _remove_job_from_scheduler(self, task_id):
        """从APScheduler移除任务"""
        try:
            self.scheduler.remove_job(task_id)
        except Exception:
            pass
    
    def _execute_task(self, task_id):
        """执行任务（被APScheduler回调）"""
        with EXECUTION_LOCK:
            task = self.get_task(task_id)
            if not task or task["status"] != "active":
                return
            
            print(f"⏰ 开始执行定时任务: {task['name']}")
            executed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status = "success"
            error_msg = ""
            
            try:
                # 调用内部对话处理，使用动态端口，避免硬编码导致跨工作台误触发
                import httpx
                response = httpx.post(
                    f"http://127.0.0.1:{self.server_port}/api/chat",
                    json={
                        "query": f"【定时任务触发】{task['prompt']}",
                        "session_id": "scheduler_task",
                        "system_prompt": "",
                        "attachments": []
                    },
                    timeout=300
                )
                if response.status_code != 200:
                    status = "fail"
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            except Exception as e:
                status = "fail"
                error_msg = str(e)
                traceback.print_exc()
            
            # 更新任务执行记录
            task["last_executed"] = executed_at
            task["history"].insert(0, {
                "executed_at": executed_at,
                "status": status,
                "error": error_msg
            })
            # 只保留最近20条记录
            if len(task["history"]) > 20:
                task["history"] = task["history"][:20]
            
            # 如果是一次性任务，执行后标记为已完成
            if task["type"] == "one_time":
                task["status"] = "completed"
                self._remove_job_from_scheduler(task_id)
            
            # 更新下次执行时间
            job = self.scheduler.get_job(task_id)
            if job:
                next_run = getattr(job, 'next_run_time', None)
                task["next_run_time"] = next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else None
            else:
                task["next_run_time"] = None
            
            self.save_tasks()
            print(f"✅ 定时任务执行完成: {task['name']} ({status})")

# 全局单例
scheduler_manager = SchedulerManager()