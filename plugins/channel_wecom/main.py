# -*- coding: utf-8 -*-
"""
企业微信远程通道插件
基于企业微信自建应用实现双向消息桥接，无需公网IP，复用本地所有AI能力
"""
import os
import sys
import time
import json
import hmac
import hashlib
import logging
import threading
import requests
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

# 复用项目现有模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


class WeComChannelPlugin:
    def __init__(self, config: Dict[str, Any]):
        # 初始化日志记录器
        self.logger = logging.getLogger(__name__)
        # 延迟导入主程序已初始化的记忆单例，和核心模块共用同一实例，避免时序问题和重复实例化
        from main import memory_cache
        self.memory_cache = memory_cache
        self.plugin_id = "channel_wecom"
        self.name = "企业微信远程通道"
        self.version = "1.0.0"
        
        # 配置参数
        self.corp_id = config.get("corp_id", "")
        # 自动转换AgentID为整型，兼容字符串格式配置输入，符合企业微信API要求
        agent_id_val = config.get("agent_id", "")
        try:
            self.agent_id = int(agent_id_val) if agent_id_val != "" else ""
        except (ValueError, TypeError):
            self.agent_id = agent_id_val
        self.corp_secret = config.get("corp_secret", "")
        self.allowed_users = config.get("allowed_users", [])
        self.api_base_url = config.get("api_base_url", "https://qyapi.weixin.qq.com/cgi-bin/")
        self.poll_interval = config.get("poll_interval", 3)
        self.stream_output = config.get("stream_output", True)
        self.enable_remote_file_read = config.get("enable_remote_file_read", True)
        self.rate_limit_per_minute = config.get("rate_limit_per_minute", 20)
        self.high_risk_requires_local_confirm = config.get("high_risk_requires_local_confirm", True)
        
        # 运行状态
        self.running = False
        self.poll_thread: Optional[threading.Thread] = None
        self.access_token: Optional[str] = None
        self.token_expire_time: float = 0
        self.next_cursor: int = 0
        self.processed_msg_ids: Dict[str, float] = {}  # 消息ID幂等校验，5分钟过期
        self.user_rate_limit: Dict[str, List[float]] = {}  # 用户请求时间记录
        self.audit_logs: List[Dict[str, Any]] = []  # 审计日志
        
        # 会话绑定:企业微信用户ID -> 本地session_id
        self.session_mapping: Dict[str, str] = {}
        
    def _get_access_token(self) -> Optional[str]:
        """获取并缓存Access Token，提前5分钟刷新"""
        current_time = time.time()
        if self.access_token and current_time < self.token_expire_time - 300:
            return self.access_token
            
        try:
            url = urljoin(self.api_base_url, "gettoken")
            params = {
                "corpid": self.corp_id,
                "corpsecret": self.corp_secret
            }
            resp = requests.get(url, params=params, timeout=10).json()
            if resp.get("errcode") == 0:
                self.access_token = resp.get("access_token")
                self.token_expire_time = current_time + resp.get("expires_in", 7200)
                self.logger.info("企业微信Access Token刷新成功")
                return self.access_token
            else:
                self.logger.error(f"获取Access Token失败: {resp}")
                return None
        except Exception as e:
            self.logger.error(f"获取Access Token异常: {str(e)}")
            return None
            
    def _verify_user(self, user_id: str) -> bool:
        """校验用户是否在白名单中"""
        return user_id in self.allowed_users
        
    def _check_rate_limit(self, user_id: str) -> bool:
        """检查用户请求频率是否超限"""
        current_time = time.time()
        if user_id not in self.user_rate_limit:
            self.user_rate_limit[user_id] = []
            
        # 清理1分钟前的记录
        self.user_rate_limit[user_id] = [
            t for t in self.user_rate_limit[user_id] 
            if current_time - t < 60
        ]
        
        if len(self.user_rate_limit[user_id]) >= self.rate_limit_per_minute:
            return False
            
        self.user_rate_limit[user_id].append(current_time)
        return True
        
    def _is_duplicate_msg(self, msg_id: str) -> bool:
        """检查消息是否重复处理（5分钟内的相同消息ID）"""
        current_time = time.time()
        # 清理过期记录
        self.processed_msg_ids = {
            mid: t for mid, t in self.processed_msg_ids.items()
            if current_time - t < 300
        }
        if msg_id in self.processed_msg_ids:
            return True
        self.processed_msg_ids[msg_id] = current_time
        return False
        
    def _add_audit_log(self, user_id: str, action: str, content: str, result: str, file_path: str = None):
        """添加审计日志"""
        log = {
            "time": time.time(),
            "user_id": user_id,
            "action": action,
            "content": content,
            "result": result,
            "file_path": file_path
        }
        self.audit_logs.append(log)
        # 最多保留1000条日志
        if len(self.audit_logs) > 1000:
            self.audit_logs = self.audit_logs[-1000:]
        self.logger.info(f"审计日志: {json.dumps(log, ensure_ascii=False)}")
        
    def send_text_message(self, user_id: str, content: str) -> tuple[bool, str]:
        """发送文本消息到企业微信，返回(是否成功, 错误信息)"""
        token = self._get_access_token()
        if not token:
            return False, "获取Access Token失败，请检查CorpID和CorpSecret配置"
            
        try:
            url = urljoin(self.api_base_url, "message/send")
            params = {"access_token": token}
            data = {
                "touser": user_id,
                "msgtype": "text",
                "agentid": self.agent_id,
                "text": {"content": content},
                "safe": 0
            }
            resp = requests.post(url, params=params, json=data, timeout=10).json()
            if resp.get("errcode") == 0:
                return True, ""
            else:
                err_msg = f"企业微信接口错误: errcode={resp.get('errcode')}, errmsg={resp.get('errmsg', '未知错误')}"
                self.logger.error(f"发送消息失败: {err_msg}")
                return False, err_msg
        except Exception as e:
            err_msg = f"发送消息网络异常: {str(e)}"
            self.logger.error(err_msg)
            return False, err_msg
            
    def upload_file(self, file_path: str, file_type: str = "file") -> Optional[str]:
        """上传本地文件到企业微信，返回media_id"""
        token = self._get_access_token()
        if not token or not os.path.exists(file_path):
            return None
            
        try:
            url = urljoin(self.api_base_url, "media/upload")
            params = {
                "access_token": token,
                "type": file_type
            }
            with open(file_path, "rb") as f:
                files = {"media": (os.path.basename(file_path), f)}
                resp = requests.post(url, params=params, files=files, timeout=30).json()
            if resp.get("errcode") == 0:
                return resp.get("media_id")
            else:
                self.logger.error(f"上传文件失败: {resp}")
                return None
        except Exception as e:
            self.logger.error(f"上传文件异常: {str(e)}")
            return None
            
    def send_file_message(self, user_id: str, file_path: str, file_type: str = "file") -> bool:
        """发送文件/图片消息"""
        media_id = self.upload_file(file_path, file_type)
        if not media_id:
            return False
            
        token = self._get_access_token()
        try:
            url = urljoin(self.api_base_url, "message/send")
            params = {"access_token": token}
            data = {
                "touser": user_id,
                "msgtype": file_type,
                "agentid": self.agent_id,
                file_type: {"media_id": media_id}
            }
            resp = requests.post(url, params=params, json=data, timeout=10).json()
            return resp.get("errcode") == 0
        except Exception as e:
            self.logger.error(f"发送文件消息异常: {str(e)}")
            return False
            
    def _poll_messages(self):
        """轮询获取企业微信消息"""
        while self.running:
            try:
                token = self._get_access_token()
                if not token:
                    time.sleep(self.poll_interval * 2)
                    continue
                    
                # 调用企业微信消息拉取接口（官方接口:获取应用消息）
                url = urljoin(self.api_base_url, "message/get")
                params = {
                    "access_token": token,
                    "cursor": self.next_cursor,
                    "limit": 10
                }
                resp = requests.get(url, params=params, timeout=10).json()
                
                if resp.get("errcode") == 0:
                    self.next_cursor = resp.get("next_cursor", self.next_cursor)
                    messages = resp.get("messages", [])
                    for msg in messages:
                        self._process_message(msg)
                else:
                    self.logger.error(f"拉取消息失败: {resp}")
                    
            except Exception as e:
                self.logger.error(f"轮询消息异常: {str(e)}")
                
            time.sleep(self.poll_interval)
            
    def _process_message(self, msg: Dict[str, Any]):
        """处理单条企业微信消息"""
        msg_id = str(msg.get("msg_id", ""))
        user_id = msg.get("from", {}).get("userid", "")
        msg_type = msg.get("msgtype", "")
        content = ""
        
        if msg_type == "text":
            content = msg.get("text", {}).get("content", "").strip()
            
        # 基础校验
        if not user_id or not msg_id or not content:
            return
            
        # 幂等校验
        if self._is_duplicate_msg(msg_id):
            return
            
        # 白名单校验
        if not self._verify_user(user_id):
            self._add_audit_log(user_id, "access_denied", content, "非白名单用户")
            return
            
        # 频率限制
        if not self._check_rate_limit(user_id):
            self.send_text_message(user_id, "⚠️ 请求过于频繁，请稍后再试")
            self._add_audit_log(user_id, "rate_limited", content, "触发频率限制")
            return
            
        self._add_audit_log(user_id, "message_received", content, "处理中")
        
        try:
            # 获取或创建绑定的本地会话
            if user_id not in self.session_mapping:
                self.session_mapping[user_id] = f"wecom_{user_id}_{int(time.time())}"
            session_id = self.session_mapping[user_id]
            
            # 调用本地对话核心处理逻辑（后续对接核心链路）
            # TODO: 对接现有chat_completion核心函数，传入session_id和content
            response = f"✅ 已收到消息:{content}\n🔧 企业微信通道插件已启动，对话链路对接中..."
            
            # 发送响应
            if len(response) > 2000:
                # 超长内容分段发送
                chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                for chunk in chunks:
                    self.send_text_message(user_id, chunk)
            else:
                self.send_text_message(user_id, response)
                
            self._add_audit_log(user_id, "message_processed", content, "成功")
            
        except Exception as e:
            error_msg = f"❌ 处理消息失败:{str(e)}"
            self.send_text_message(user_id, error_msg)
            self._add_audit_log(user_id, "process_failed", content, str(e))
            
    def test_connection(self) -> Dict[str, Any]:
        """测试企业微信API连接是否正常"""
        if not all([self.corp_id, self.agent_id, self.corp_secret]):
            return {"success": False, "message": "请先填写完整的CorpID、AgentID和Secret"}
            
        token = self._get_access_token()
        if not token:
            return {"success": False, "message": "获取Access Token失败，请检查参数和网络连接"}
            
        # 尝试发送测试消息给第一个白名单用户
        if self.allowed_users:
            test_user = self.allowed_users[0]
            send_success, send_err = self.send_text_message(
                test_user, 
                "✅ 企业微信远程通道连接测试成功！\n您现在可以通过企业微信远程操作本地AI助手了。"
            )
            if send_success:
                return {"success": True, "message": "连接测试成功，测试消息已发送到您的企业微信"}
            else:
                return {"success": False, "message": f"Token获取成功，但发送测试消息失败:{send_err}"}
        else:
            return {"success": True, "message": "Token获取成功，请添加白名单用户后测试消息发送"}
            
    def get_channel_status(self) -> Dict[str, Any]:
        """获取通道运行状态"""
        return {
            "running": self.running,
            "online": self.running and self.access_token is not None,
            "bound_users": len(self.session_mapping),
            "allowed_users_count": len(self.allowed_users),
            "next_cursor": self.next_cursor,
            "processed_messages": len(self.processed_msg_ids),
            "audit_logs_count": len(self.audit_logs),
            "last_token_refresh": self.token_expire_time - 7200 if self.token_expire_time else 0
        }
        
    def start(self):
        """启动插件后台轮询"""
        if self.running:
            return
        if not all([self.corp_id, self.agent_id, self.corp_secret, self.allowed_users]):
            self.logger.error("企业微信配置不完整，无法启动")
            return False
            
        self.running = True
        self.poll_thread = threading.Thread(target=self._poll_messages, daemon=True)
        self.poll_thread.start()
        self.logger.info("企业微信远程通道插件启动成功")
        return True
        
    def stop(self):
        """停止插件"""
        self.running = False
        if self.poll_thread:
            self.poll_thread.join(timeout=5)
        self.logger.info("企业微信远程通道插件已停止")
        return True
        
    def run(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """插件统一入口"""
        params = params or {}
        if action == "test_connection":
            return self.test_connection()
        elif action == "get_status":
            return self.get_channel_status()
        elif action == "send_message":
            user_id = params.get("user_id", "")
            content = params.get("content", "")
            success, err_msg = self.send_text_message(user_id, content)
            return {"success": success, "message": err_msg}
        elif action == "get_audit_logs":
            limit = params.get("limit", 100)
            return {"logs": self.audit_logs[-limit:]}
        else:
            return {"success": False, "message": f"不支持的操作: {action}"}


# 插件实例化入口（兼容旧逻辑）
def init_plugin(config: Dict[str, Any]):
    return WeComChannelPlugin(config)


# 插件标准入口函数（供主程序api_server统一调用）
def test_connection():
    """模块级测试连接入口，主程序加载插件时自动注入plugin_config配置"""
    config = globals().get("plugin_config", {})
    plugin = WeComChannelPlugin(config)
    result = plugin.test_connection()
    # 转换为主程序期望的(success: bool, msg: str)二元组格式
    return result.get("success", False), result.get("message", "未知错误")


def run(params):
    """模块级统一执行入口，主程序加载插件时自动注入plugin_config配置"""
    config = globals().get("plugin_config", {})
    plugin = WeComChannelPlugin(config)
    params = params or {}
    action = params.pop("action", "")
    return plugin.run(action, params)