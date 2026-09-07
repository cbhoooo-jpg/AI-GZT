"""
AI助手指令固化模块
"""
import json
import re
import os
import sys

class ToolTemplateManager:
    # 全局唯一模板版本标识，只有带这个标识的指令才会被执行
    TEMPLATE_VERSION = "1.0"
    # 内置固化模板（可支持外部配置文件兜底，优先读内部固化避免配置被篡改）
    FIXED_TEMPLATES = {
        "read_file": {
            "required_params": ["file_name"],
            "structure": {"__template_version": TEMPLATE_VERSION, "name": "read_file", "parameters": {"file_name": ""}}
        },
        "edit_file": {
            "required_params": ["file_name", "operation", "target_block", "content"],
            "structure": {"__template_version": TEMPLATE_VERSION, "name": "edit_file", "parameters": {"file_name": "", "operation": "", "target_block": "", "content": ""}}
        },
        "create_file": {
            "required_params": ["path"],
            "structure": {"__template_version": TEMPLATE_VERSION, "name": "create_file", "parameters": {"path": "", "is_dir": False, "content": ""}}
        },
        "exec_cmd": {
            "required_params": ["cmd"],
            "structure": {"__template_version": TEMPLATE_VERSION, "name": "exec_cmd", "parameters": {"cmd": ""}}
        },
        "delete_file": {
            "required_params": ["file_name"],
            "structure": {"__template_version": TEMPLATE_VERSION, "name": "delete_file", "parameters": {"file_name": ""}}
        },
        "get_project_tree": {
            "required_params": [],
            "structure": {"__template_version": TEMPLATE_VERSION, "name": "get_project_tree", "parameters": {}}
        },
        "rag_search": {
            "required_params": ["query"],
            "structure": {"__template_version": TEMPLATE_VERSION, "name": "rag_search", "parameters": {"query": ""}}
        },
        "rename_file": {
            "required_params": ["old_path", "new_name"],
            "structure": {"__template_version": TEMPLATE_VERSION, "name": "rename_file", "parameters": {"old_path": "", "new_name": ""}}
        },
        "write_file": {
            "required_params": ["file_name", "content"],
            "structure": {"__template_version": TEMPLATE_VERSION, "name": "write_file", "parameters": {"file_name": "", "content": "", "append": False}}
        }
    }
    # 插件配置
    # 兼容PyInstaller打包环境:打包后使用sys.executable所在目录，开发环境使用__file__所在目录
    if getattr(sys, 'frozen', False):
        _exe_dir = os.path.dirname(sys.executable)
        _internal_dir = os.path.join(_exe_dir, "_internal")
        _BASE_DIR = _internal_dir if os.path.exists(_internal_dir) else _exe_dir
    else:
        _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PLUGIN_DIR = os.path.join(_BASE_DIR, "plugins")
    _plugin_templates = {}
    _enabled_plugins = set()
    # 预制插件模板配置
    PLUGIN_TEMPLATE_DIR = os.path.join(_BASE_DIR, "plugin_templates")
    _preset_templates = {}

    @classmethod
    def load_plugins(cls):
        """扫描plugins目录加载所有已启用的插件"""
        cls._plugin_templates = {}
        cls._enabled_plugins = set() # 每次加载清空已启用插件缓存
        if not os.path.exists(cls.PLUGIN_DIR):
            os.makedirs(cls.PLUGIN_DIR, exist_ok=True)
            return
        # 遍历每个插件文件夹
        for plugin_dir in os.listdir(cls.PLUGIN_DIR):
            plugin_path = os.path.join(cls.PLUGIN_DIR, plugin_dir)
            if not os.path.isdir(plugin_path):
                continue
            config_path = os.path.join(plugin_path, "plugin.json")
            if not os.path.exists(config_path):
                continue
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                # 校验必填字段
                required_fields = ["plugin_id", "name", "description", "parameters", "entry"]
                if not all(field in config for field in required_fields):
                    continue
                # 读取用户自定义配置，合并到plugin配置中
                user_config_path = os.path.join(plugin_path, "user_config.json")
                if os.path.exists(user_config_path):
                    try:
                        with open(user_config_path, "r", encoding="utf-8") as f:
                            user_config = json.load(f)
                        # 合并配置:优先级 用户配置 > config数组默认值 > default_config系统默认值
                        config["merged_config"] = {}
                        # 第一步:加载插件顶层default_config系统级默认值
                        if "default_config" in config and isinstance(config["default_config"], dict):
                            config["merged_config"].update(config["default_config"])
                        # 第二步:加载config数组中显式定义的配置项默认值（优先级高于default_config）
                        if "config" in config:
                            for item in config["config"]:
                                config["merged_config"][item["key"]] = item["default"]
                            # 第三步:覆盖用户自定义配置（优先级最高）
                            for k, v in user_config.items():
                                if k in config["merged_config"]:
                                    config["merged_config"][k] = v
                    except:
                        # 用户配置读取失败，用默认配置
                        config["merged_config"] = {}
                        if "config" in config:
                            for item in config["config"]:
                                config["merged_config"][item["key"]] = item["default"]
                else:
                    # 没有用户配置，按优先级加载默认配置
                    config["merged_config"] = {}
                    # 第一步:加载插件顶层default_config系统级默认值
                    if "default_config" in config and isinstance(config["default_config"], dict):
                        config["merged_config"].update(config["default_config"])
                    # 第二步:加载config数组中显式定义的配置项默认值（优先级高于default_config）
                    if "config" in config:
                        for item in config["config"]:
                            config["merged_config"][item["key"]] = item["default"]
                # 从parameters中提取必填参数列表
                required_params = [p["name"] for p in config["parameters"] if p.get("required", False)]
                # 所有参数列表（必填+可选，全部加入结构支持传递）
                all_params = [p["name"] for p in config["parameters"]]
                # 转换为内置工具相同格式
                cls._plugin_templates[config["plugin_id"]] = {
                    "required_params": required_params,
                    "structure": {"__template_version": cls.TEMPLATE_VERSION, "name": config["plugin_id"], "parameters": {p: "" for p in all_params}},
                    "plugin_config": config
                }
                # 打印加载成功日志
                print(f"✅ 加载插件成功:{config['name']}({config['plugin_id']})")
                # 默认强制启用所有加载成功的插件
                cls._enabled_plugins.add(config["plugin_id"])
                # 处理后台常驻模式插件
                run_mode = config.get("run_mode", "lazy")
                if run_mode == "daemon":
                    try:
                        # 动态导入插件模块
                        module_name = f"plugins.{plugin_dir}.main"
                        import importlib
                        plugin_module = importlib.import_module(module_name)
                        # 获取插件实例（所有插件默认导出plugin全局实例）
                        if hasattr(plugin_module, "plugin"):
                            plugin_instance = getattr(plugin_module, "plugin")
                            # 调用on_load生命周期方法（如果存在）
                            if hasattr(plugin_instance, "on_load") and callable(getattr(plugin_instance, "on_load")):
                                plugin_instance.on_load()
                            print(f"✅ 后台常驻插件[{config['name']}]加载完成，已随主程序启动")
                    except Exception as e:
                        print(f"⚠️ 后台常驻插件[{config['name']}]加载失败，不影响其他功能: {str(e)}")
                        continue
            except Exception as e:
                print(f"❌ 加载插件失败:{plugin_dir}, 错误:{str(e)}")
                continue
    @classmethod
    def load_preset_templates(cls):
        """加载plugin_templates目录下所有预制MD模板，仅解析头部元数据，适配新[FILE]块模板体系，错误模板自动跳过不影响整体"""
        cls._preset_templates = {}
        try:
            if not os.path.exists(cls.PLUGIN_TEMPLATE_DIR):
                os.makedirs(cls.PLUGIN_TEMPLATE_DIR, exist_ok=True)
                return
            # 遍历所有MD模板文件
            for filename in os.listdir(cls.PLUGIN_TEMPLATE_DIR):
                if not filename.endswith(".md") or not filename.startswith("template_"):
                    continue
                file_path = os.path.join(cls.PLUGIN_TEMPLATE_DIR, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    # 仅解析头部元数据，不做任何多余格式校验
                    metadata = {}
                    if content.startswith("---"):
                        meta_end = content.find("---", 3)
                        if meta_end > 0:
                            meta_content = content[3:meta_end].strip()
                            for line in meta_content.split("\n"):
                                line = line.strip()
                                if not line or line.startswith("#"):
                                    continue
                                if ":" in line:
                                    k, v = line.split(":", 1)
                                    metadata[k.strip()] = v.strip()
                    # 只要有template_id就加载成功
                    template_id = metadata.get("template_id")
                    if not template_id:
                        print(f"⚠️ 跳过模板{filename}:缺少template_id元数据")
                        continue
                    # 存储元数据和原始模板内容，生成时直接使用
                    cls._preset_templates[template_id] = {
                        "template_id": template_id,
                        "name": metadata.get("name", template_id),
                        "scene": metadata.get("scene", ""),
                        "default_permission": metadata.get("default_permission", "none"),
                        "raw_content": content
                    }
                    print(f"✅ 加载预制插件模板成功:{metadata.get('name', template_id)}")
                except Exception as e:
                    print(f"❌ 加载预制模板失败:{filename}, 错误:{str(e)}")
                    continue
        except Exception as e:
            print(f"❌ 模板目录遍历失败，所有模板无法加载:{str(e)}")
            cls._preset_templates = {}
            return
    @classmethod
    def get_preset_template_list(cls):
        """获取所有预制模板列表，前端插件开发页面直接调用展示"""
        if not cls._preset_templates:
            cls.load_preset_templates()
        return list(cls._preset_templates.values())

    @classmethod
    def get_merged_tool_list(cls):
        """获取合并后的内置工具+已启用插件列表"""
        merged = cls.FIXED_TEMPLATES.copy()
        for plugin_id in cls._enabled_plugins:
            if plugin_id in cls._plugin_templates:
                merged[plugin_id] = cls._plugin_templates[plugin_id]
        return merged

    @classmethod
    def get_plugin_config(cls, plugin_id):
        """获取插件配置信息"""
        return cls._plugin_templates.get(plugin_id, {}).get("plugin_config", None)

    @classmethod
    def generate_command(cls, tool_name, params): 
        """生成工具指令，已取消所有白名单和参数校验，只要能解析就直接生成"""
        # 优先兼容插件名称映射
        for plugin_id, template in cls._plugin_templates.items():
            if template.get("plugin_config", {}).get("name") == tool_name:
                tool_name = plugin_id
                break
        # 已知工具优先用已有结构，未知工具直接生成默认结构，无任何校验
        merged_tools = cls.get_merged_tool_list()
        if tool_name in merged_tools:
            template = merged_tools[tool_name]
            result = template["structure"].copy()
            # 填充所有传入的参数，不限制参数范围
            # 保留原始类型，由json.dumps统一序列化，避免str()导致字典/列表格式错误
            for k, v in params.items():
                result["parameters"][k] = v
            return json.dumps(result, ensure_ascii=False)
        else:
            # 未知工具直接返回指令结构，完全取消校验
            command = {
                "__template_version": cls.TEMPLATE_VERSION,
                "name": tool_name,
                "parameters": params
            }
            return json.dumps(command, ensure_ascii=False)

    @classmethod
    def validate_command(cls, command_str):
        """校验指令是否为合法的模板生成指令，取消工具白名单校验，只要结构合法就通过"""
        try:
            command = json.loads(command_str)
            # 仅校验核心结构，不校验工具是否存在
            if command.get("__template_version") != cls.TEMPLATE_VERSION:
                return None
            if not isinstance(command.get("name"), str) or len(command["name"]) == 0:
                return None
            if not isinstance(command.get("parameters"), dict):
                return None
            return command
        except:
            return None
    @classmethod
    def generate_plugin_template(cls, plugin_info: dict, config_list: list = None, param_list: list = None, permission: str = "none", save_dir: str = "./plugins/", preset_template_id: str = None) -> dict:
        """
        一键生成符合规范的插件完整结构，适配新[FILE]块模板体系，无任何旧逻辑兼容
        :param plugin_info: 插件基础信息，必填字段:plugin_id、name、description、version、author、trigger_keyword
        :param save_dir: 插件保存的根目录，默认保存在./plugins/
        :param preset_template_id: 预制模板ID，必填
        :return: 生成结果，包含生成的文件路径和内容
        """
        # 1. 基础校验
        # 校验必填模板ID
        if not preset_template_id:
            return {"success": False, "msg": "缺少必填参数：预制模板ID"}
        # 校验插件必填基础信息
        required_plugin_fields = ["plugin_id", "name", "description", "version", "author", "trigger_keyword"]
        for field in required_plugin_fields:
            if field not in plugin_info or not str(plugin_info[field]).strip():
                return {"success": False, "msg": f"缺少插件必填基础信息:{field}"}
        # 校验模板是否存在
        if not cls._preset_templates:
            cls.load_preset_templates()
        if preset_template_id not in cls._preset_templates:
            return {"success": False, "msg": f"不存在的预制模板ID:{preset_template_id}"}
        template = cls._preset_templates[preset_template_id]
        
        # 2. 路径校验与创建
        plugin_id = plugin_info["plugin_id"].strip()
        save_dir = save_dir.strip()
        # 路径安全校验:调用系统统一路径校验规则（延迟导入避免循环依赖）
        from api_server import is_path_forbidden
        norm_save_dir = os.path.normpath(save_dir).replace("\\", "/")
        forbidden, reason = is_path_forbidden(norm_save_dir)
        if forbidden:
            return {"success": False, "msg": f"保存路径不合法:{reason}"}
        # 自动创建保存目录
        os.makedirs(save_dir, exist_ok=True)
        plugin_dir = os.path.join(save_dir, plugin_id)
        # 重名校验
        if os.path.exists(plugin_dir):
            return {"success": False, "msg": f"插件ID[{plugin_id}]在指定目录下已存在，请更换ID或保存路径后重试"}
        os.makedirs(plugin_dir, exist_ok=True)

        # 3. 构造占位符参数（自动扩展用户传入的所有参数）
        placeholders = {
            "plugin_id": plugin_id,
            "plugin_name": plugin_info["name"],
            "description": plugin_info["description"],
            "version": plugin_info["version"],
            "author": plugin_info["author"],
            "trigger_keyword": plugin_info["trigger_keyword"]
        }
        # 自动合并用户传入的所有额外参数到占位符
        for k, v in plugin_info.items():
            if k not in placeholders:
                placeholders[k] = str(v)

        # 4. 解析[FILE]块生成文件
        template_content = template["raw_content"]
        # 拆分所有[FILE]块
        file_blocks = re.split(r"### \[FILE\] ", template_content)
        generated_files = []

        for block in file_blocks[1:]:
            if not block.strip():
                continue
            # 提取文件名和内容
            lines = block.split("\n", 1)
            if len(lines) < 2:
                continue
            # 处理文件名，移除可能的代码块标记
            file_name = lines[0].strip().replace("```python", "").replace("```json", "").replace("```markdown", "").replace("```", "").strip()
            # 处理文件内容，移除可能的代码块标记
            file_content = lines[1].strip().replace("```python", "").replace("```json", "").replace("```markdown", "").replace("```", "").strip()
            if not file_name or not file_content:
                continue
            # 替换所有占位符
            for k, v in placeholders.items():
                file_content = file_content.replace(f"{{{{{k}}}}}", str(v))
            # 处理扩展参数占位符，没有值时连前面的逗号一起删除避免JSON格式错误
            extra_params = plugin_info.get("extra_parameters", "").strip()
            if not extra_params:
                file_content = file_content.replace(",\n    {{extra_parameters}}", "")
            else:
                file_content = file_content.replace("{{extra_parameters}}", extra_params)
            # 处理扩展依赖占位符
            file_content = file_content.replace("{{extra_dependencies}}", plugin_info.get("extra_dependencies", "").strip())
            # 写入文件
            file_path = os.path.join(plugin_dir, file_name)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(file_content)
            generated_files.append(file_path)

        # 5. 结果返回
        if not generated_files:
            # 没有生成任何文件，删除空目录
            import shutil
            shutil.rmtree(plugin_dir)
            return {"success": False, "msg": "模板解析失败：未找到任何[FILE]块定义，请检查模板格式"}
        
        return {
            "success": True,
            "msg": f"✅ 插件[{plugin_info['name']}]生成成功，路径:{plugin_dir}",
            "files": generated_files
        }

# 全局单例，直接导入使用
tool_template_manager = ToolTemplateManager()