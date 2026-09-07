import os
import sys
import json

# 动态添加项目根目录到Python路径，确保能导入项目级模块，和现有插件路径计算逻辑完全一致
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入现有稳定的智能文件编辑器核心逻辑，100%复用锚点匹配、自动备份、安全校验能力，无重复开发
from tools.intelligent_file_editor import IntelligentFileEditor

class SafeFileEditorPlugin:
    """安全文件编辑插件主类，仅做参数名映射，核心编辑逻辑完全复用现有成熟能力"""
    
    @staticmethod
    def _get_root_dir() -> str:
        """统一获取项目根目录，兼容开发/打包环境，避免路径计算错误"""
        if getattr(sys, 'frozen', False):
            # PyInstaller打包环境:exe可执行文件所在目录为项目根目录
            return os.path.dirname(sys.executable)
        else:
            # 开发环境:当前文件往上3级（plugins/safe_file_editor/main.py → 项目根目录）
            return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    def __init__(self):
        self.config = self._load_config()
        # 初始化编辑器实例，复用所有现有能力
        self.editor = IntelligentFileEditor()
        # 用户配置文件热加载相关:记录最后修改时间
        self._user_config_mtime = 0
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        user_config_path = os.path.join(plugin_dir, "user_config.json")
        if os.path.exists(user_config_path):
            self._user_config_mtime = os.path.getmtime(user_config_path)
        print(f"[SafeFileEditor] 安全文件编辑插件初始化完成，配置:自动检测截断={self.config.get('auto_detect_truncation', True)}, 自动备份={self.config.get('auto_backup', True)}")

    def _load_config(self) -> dict:
        """加载插件配置，优先读取user_config.json用户配置，合并plugin.json默认配置，和现有插件配置逻辑一致"""
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(plugin_dir, "plugin.json")
        user_config_path = os.path.join(plugin_dir, "user_config.json")
        
        try:
            # 先加载默认配置
            with open(config_path, "r", encoding="utf-8") as f:
                raw_config = json.load(f)
            
            parsed_config = {}
            if "config" in raw_config and isinstance(raw_config["config"], list):
                for item in raw_config["config"]:
                    key = item.get("key")
                    value = item.get("default")
                    parsed_config[key] = value
            
            # 再加载用户自定义配置，覆盖默认值
            if os.path.exists(user_config_path):
                try:
                    with open(user_config_path, "r", encoding="utf-8") as f:
                        user_config = json.load(f)
                    for key, value in user_config.items():
                        parsed_config[key] = value
                except Exception as e:
                    print(f"[SafeFileEditor] 加载用户配置失败，使用默认配置: {e}")
            
            return parsed_config
        except Exception as e:
            print(f"[SafeFileEditor] 加载配置失败，使用默认配置: {e}")
            return {
                "auto_detect_truncation": True,
                "auto_backup": True
            }

    def _reload_config_if_changed(self):
        """热加载配置:检查user_config.json是否被外部修改，自动加载最新配置无需重启"""
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        user_config_path = os.path.join(plugin_dir, "user_config.json")
        try:
            if os.path.exists(user_config_path):
                current_mtime = os.path.getmtime(user_config_path)
                if current_mtime > self._user_config_mtime:
                    print(f"[SafeFileEditor] 检测到用户配置文件被外部修改，自动热加载最新配置")
                    self.config = self._load_config()
                    self._user_config_mtime = current_mtime
        except Exception as e:
            print(f"[SafeFileEditor] 热加载配置失败: {e}")

    def _save_config(self):
        """持久化保存当前配置到user_config.json"""
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        user_config_path = os.path.join(plugin_dir, "user_config.json")
        try:
            with open(user_config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            self._user_config_mtime = os.path.getmtime(user_config_path)
        except Exception as e:
            print(f"[SafeFileEditor] 保存配置失败: {e}")

    def execute_edit(self, edit_file_path: str, op_type: str, anchor_text: str = None, replace_text: str = None) -> dict:
        """
        执行安全编辑，核心逻辑:将插件独立参数映射为原生编辑器参数，完全走独立参数通道，100%避免截断
        参数名和原生edit_file完全不重名，从机制上杜绝参数解析截断问题
        """
        # 参数基础校验
        if not edit_file_path or not edit_file_path.strip():
            return {"success": False, "msg": "缺少必填参数:edit_file_path（要修改的文件路径）"}
        if op_type not in ["replace", "insert_before", "insert_after", "delete"]:
            return {"success": False, "msg": f"不支持的操作类型:{op_type}，仅支持replace/insert_before/insert_after/delete"}
        if op_type != "delete":
            if not anchor_text or not anchor_text.strip():
                return {"success": False, "msg": f"{op_type}操作缺少必填参数:anchor_text（定位锚点内容）"}
            if not replace_text and op_type != "delete":
                return {"success": False, "msg": f"{op_type}操作缺少必填参数:replace_text（要替换/插入的新内容）"}
        
        try:
            # 参数映射:插件独立参数 → 原生编辑器参数，完全走独立参数通道，100%避免截断
            # 因为参数是在插件内部直接传递给Python函数，不经过外层文本参数解析，所以哪怕内容里有再多content:/target_block:关键词也绝对不会截断
            edit_params = {
                "file_path": edit_file_path.strip(),
                "operation": op_type,
                "target_block": anchor_text,
                "content": replace_text
            }
            
            # 自动备份配置同步到编辑器
            self.editor.auto_backup = self.config.get("auto_backup", True)
            
            # 调用现有编辑器执行实际修改，适配现有编辑器方法名和返回值格式
            success, msg = self.editor.edit_file(**edit_params)
            
            # 从返回信息中提取匹配相似度
            match_score = 1.0
            if "匹配相似度:" in msg:
                try:
                    score_part = msg.split("匹配相似度:")[1].split("，")[0]
                    match_score = float(score_part)
                except:
                    pass
            
            if success:
                return {
                    "success": True,
                    "msg": "✅ 安全编辑执行成功",
                    "file_path": edit_file_path,
                    "op_type": op_type,
                    "match_score": match_score,
                    "detail": msg
                }
            else:
                return {
                    "success": False,
                    "msg": f"❌ 编辑失败:{msg}",
                    "detail": msg
                }
        except Exception as e:
            error_msg = f"安全编辑执行异常:{str(e)}"
            print(f"[SafeFileEditor] {error_msg}")
            return {"success": False, "msg": error_msg}

# 全局插件单例，全局唯一，避免多实例配置冲突
_plugin_instance = SafeFileEditorPlugin()

# 插件标准入口
def init(config: dict = None):
    """插件初始化方法，安装/启用/配置修改时自动调用"""
    global _plugin_instance
    _plugin_instance._reload_config_if_changed()
    print("[SafeFileEditor] 插件初始化完成，可正常使用防截断安全编辑功能")
    return _plugin_instance

def run(params: dict = None):
    """插件主方法，接收插件独立参数，执行安全编辑"""
    global _plugin_instance
    
    # 每次执行前热加载最新配置
    _plugin_instance._reload_config_if_changed()
    
    params = params or {}
    
    # 提取插件独立参数（和原生edit_file参数名完全不重名，从根源避免截断）
    edit_file_path = params.get("edit_file_path", "").strip()
    op_type = params.get("op_type", "").strip()
    anchor_text = params.get("anchor_text", None)
    replace_text = params.get("replace_text", None)
    
    # 支持自然语言query解析（简单场景）
    query = params.get("query", "").strip()
    if query and not edit_file_path:
        # 简单自然语言解析预留，后续可扩展，当前优先使用显式参数
        return {"success": False, "msg": "请使用显式参数调用:edit_file_path(文件路径)、op_type(操作类型)、anchor_text(锚点)、replace_text(新内容)，避免自然语言解析出错"}
    
    # 执行编辑
    return _plugin_instance.execute_edit(
        edit_file_path=edit_file_path,
        op_type=op_type,
        anchor_text=anchor_text,
        replace_text=replace_text
    )

def uninstall():
    """插件卸载时自动调用"""
    print("[SafeFileEditor] 安全文件编辑插件已卸载，恢复为原生编辑工具")