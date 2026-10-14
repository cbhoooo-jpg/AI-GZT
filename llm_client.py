# -*- coding: utf-8 -*-
"""
统一模型调用客户端
仅支持云端OpenAI兼容接口模型，配置修改即时生效，无需重启
"""
import json
import os
import re
import hashlib
import base64
import io
from typing import Optional, List
from PIL import Image

# 配置路径
# 兼容PyInstaller打包环境:打包后统一使用EXE同级目录的config.json，和api_server.py读写路径完全对齐
import sys as _sys
if getattr(_sys, 'frozen', False):
    _exe_dir = os.path.dirname(_sys.executable)
    _internal_dir = os.path.join(_exe_dir, "_internal")
    # 用户配置统一读写EXE同级目录的config.json，和前端设置页保存路径完全一致
    CONFIG_PATH = os.path.join(_exe_dir, "config.json")
    # 兜底逻辑:如果EXE同级目录没有config.json，自动从_internal复制默认配置，避免首次启动读不到配置
    if not os.path.exists(CONFIG_PATH) and os.path.exists(_internal_dir):
        # 打包清单实际只含 config.example.json（_internal/config.json 不存在），故以其为兜底模板，否则 config.json 永不生成
        _internal_default_config = os.path.join(_internal_dir, "config.json")
        if not os.path.exists(_internal_default_config):
            _internal_default_config = os.path.join(_internal_dir, "config.example.json")
        if os.path.exists(_internal_default_config):
            import shutil
            try:
                shutil.copy2(_internal_default_config, CONFIG_PATH)
                print(f"[LLMClient] 首次启动自动从_internal复制默认配置到: {CONFIG_PATH}")
            except Exception as e:
                print(f"[LLMClient] 复制默认配置失败: {e}")
else:
    # 开发环境使用脚本所在目录的config.json
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CONFIG_PATH = os.path.join(_BASE_DIR, "config.json")
# 上次配置哈希，用于检测配置变更
_last_config_hash = ""
# 模型实例缓存
_model_instance = None
# 模型类型:cloud / mock（mock为兜底错误模型）
_model_type = "cloud"


# 兜底模型类，无可用模型时返回提示，彻底避免NoneType报错
class MockModel:
    def create_chat_completion(self, *args, **kwargs):
        stream = kwargs.get("stream", False)
        if stream:
            def generate_error_stream():
                yield {"choices": [{"delta": {"content": "⚠️ 模型初始化失败，请检查API配置或切换到其他云端模型"}, "finish_reason": "stop"}]}
            return generate_error_stream()
        return {"choices": [{"message": {"role": "assistant", "content": "⚠️ 模型初始化失败，请检查API配置或切换到其他云端模型"}}]}
    
    class chat:
        class completions:
            @staticmethod
            def create(*args, **kwargs):
                stream = kwargs.get("stream", False)
                if stream:
                    # 流式模式:返回生成器，完全兼容UnifiedLLM的流式解析逻辑
                    def generate_error_stream():
                        class MockDelta:
                            content = "⚠️ 模型初始化失败，请检查API配置或切换到其他云端模型"
                            reasoning_content = ""
                        class MockChoice:
                            delta = MockDelta()
                            finish_reason = "stop"
                        class MockChunk:
                            choices = [MockChoice()]
                        yield MockChunk()
                    return generate_error_stream()
                
                # 非流式模式:返回MockResponse对象
                class MockChoice:
                    message = type('obj', (object,), {'content': '⚠️ 模型初始化失败，请检查API配置或切换到其他云端模型'})
                class MockResponse:
                    choices = [MockChoice()]
                return MockResponse()

# 初始化默认兜底模型，确保永远不为None
_model_instance = MockModel()

def _get_config() -> dict:
    """读取最新配置；文件为空、损坏或解析失败时返回{}并尝试从_internal恢复默认配置，避免启动崩溃"""
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.strip():
            raise ValueError("配置文件为空(0字节或仅空白)")
        return json.loads(content)
    except Exception as e:
        print(f"[LLMClient] 配置文件读取失败，尝试恢复默认配置: {e}")
        # 打包环境下尝试从_internal目录恢复默认配置，避免空配置导致启动失败
        try:
            if getattr(_sys, 'frozen', False):
                _internal_default = os.path.join(_internal_dir, "config.json")
                if os.path.exists(_internal_default):
                    import shutil
                    shutil.copy2(_internal_default, CONFIG_PATH)
                    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                        return json.load(f)
        except Exception as e2:
            print(f"[LLMClient] 恢复默认配置失败: {e2}")
        return {}

def _get_config_hash(config: dict) -> str:
    """计算配置哈希，用于检测变更"""
    config_str = json.dumps(config, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(config_str.encode()).hexdigest()

def _extract_model_max_tokens(error_msg: str):
    """P0-4: 从max_tokens超限报错中提取模型支持的最大token数，兼容中英文厂商错误格式，提取失败返回None"""
    # 英文厂商: expected a value <= 128000 / must be <= 128000 / less than or equal to 128000 / maximum of 128000
    m = re.search(r'(?:<=|less than or equal to|no (?:more|larger) than|maximum[^0-9]{0,20}?)\s*(\d{3,7})', error_msg, re.IGNORECASE)
    if m:
        return int(m.group(1))
    # 中文厂商（火山方舟等）: 最大值为128000 / 不能超过128000 / 上限为128000 / 小于等于128000 / 最多128000
    m = re.search(r'(?:最大值?(?:为|是)?|不能超过|不得超过|不超过|上限(?:为|是)?|小于等于|最多(?:为|是)?|不能大于)\s*(\d{3,7})', error_msg)
    if m:
        return int(m.group(1))
    return None
def get_config() -> dict:
    """对外公开的配置读取接口，和内部逻辑完全一致，保证配置统一"""
    config = _get_config()
    # 补全默认值，和内部初始化逻辑完全对齐
    default_config = {
        "model_provider": "火山方舟",
        "api_url": "",
        "model_name": "",
        "api_key": "",
        "timeout": 200,
        "stream_output": True,
        "temperature": 0.5,
        "download_path": ""
    }
    # 合并配置，用户配置优先覆盖默认值
    merged_config = default_config.copy()
    merged_config.update(config)
    return merged_config

def image_to_base64(image_path: str, max_size_mb: float = 2.0) -> tuple[str, dict]:
    """
    通用图片转base64工具函数，支持自动压缩大图
    :param image_path: 本地图片文件路径
    :param max_size_mb: 最大允许大小（MB），超过自动等比压缩
    :return: (base64编码字符串, 图片元信息字典)
    """
    # 检查文件是否存在
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图片文件不存在: {image_path}")
    
    # 读取原始文件大小
    file_size = os.path.getsize(image_path) / (1024 * 1024)  # 转换为MB
    meta = {
        "path": image_path,
        "original_size_mb": round(file_size, 2),
        "compressed": False
    }
    
    # 打开图片
    with Image.open(image_path) as img:
        # 获取图片格式和尺寸
        img_format = img.format.lower() if img.format else "jpeg"
        meta["format"] = img_format
        meta["width"], meta["height"] = img.size
        
        # 自动压缩逻辑:超过最大大小则等比缩放
        max_bytes = max_size_mb * 1024 * 1024
        if file_size > max_size_mb:
            # 计算缩放比例，保持宽高比
            scale = (max_bytes / os.path.getsize(image_path)) ** 0.5
            new_width = int(img.width * scale)
            new_height = int(img.height * scale)
            # 最小尺寸限制，避免缩太小
            new_width = max(new_width, 100)
            new_height = max(new_height, 100)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            meta["compressed"] = True
            meta["compressed_width"] = new_width
            meta["compressed_height"] = new_height
        
        # 转换为base64
        buffer = io.BytesIO()
        # PNG格式保留透明通道，其他格式统一用JPEG压缩
        save_format = "PNG" if img_format == "png" else "JPEG"
        if save_format == "JPEG":
            img = img.convert("RGB")  # JPEG不支持透明通道，转RGB
            img.save(buffer, format=save_format, quality=85, optimize=True)
        else:
            img.save(buffer, format=save_format, optimize=True)
        
        b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        meta["final_size_mb"] = round(len(buffer.getvalue()) / (1024 * 1024), 2)
        
        return b64_str, meta


def _process_multimodal_messages(messages: List[dict]) -> List[dict]:
    """
    自动处理消息列表中的本地图片路径，转换为OpenAI标准多模态格式
    纯文本消息完全保留，无任何破坏性变更
    :param messages: 原始消息列表
    :return: 处理后的多模态兼容消息列表
    """
    # 支持的图片后缀
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
    processed = []
    
    for msg in messages:
        msg_copy = msg.copy()
        content = msg_copy.get("content", "")
        
        # 如果content已经是列表（已经是多模态格式），直接保留
        if isinstance(content, list):
            processed.append(msg_copy)
            continue
        
        # 如果是字符串，检查是否是本地图片路径
        if isinstance(content, str):
            content_stripped = content.strip()
            # 检查是否是存在的文件，且后缀是图片格式
            if os.path.exists(content_stripped):
                ext = os.path.splitext(content_stripped)[1].lower()
                if ext in IMAGE_EXTENSIONS:
                    try:
                        # 转换图片为base64
                        b64_str, img_meta = image_to_base64(content_stripped)
                        # 构造多模态内容
                        multimodal_content = [
                            {
                                "type": "text",
                                "text": f"[本地图片] 路径: {content_stripped}\n尺寸: {img_meta['width']}x{img_meta['height']}\n格式: {img_meta['format']}\n大小: {img_meta['original_size_mb']}MB"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{img_meta['format']};base64,{b64_str}"
                                }
                            }
                        ]
                        msg_copy["content"] = multimodal_content
                        print(f"🔍 自动识别图片路径并转换为多模态格式: {content_stripped}")
                    except Exception as e:
                        print(f"⚠️ 图片转换失败，按纯文本处理: {str(e)}")
                        # 转换失败保留原内容
                        pass
        
        processed.append(msg_copy)
    
    return processed


def _init_model(config: dict):
    """根据配置初始化模型实例"""
    global _model_instance, _model_type, OpenAI, CLOUD_MODEL_AVAILABLE
    # 延迟导入openai，确保外部依赖路径注入完成后再加载，避免提前导入找不到依赖
    try:
        from openai import OpenAI
        CLOUD_MODEL_AVAILABLE = True
    except ImportError as e:
        CLOUD_MODEL_AVAILABLE = False
        print(f"⚠️ 云模型依赖导入失败: {str(e)}，请安装openai库及其依赖后使用")
        _model_instance = MockModel()
        _model_type = "mock"
        return
    

    # 第三步:云模型初始化（所有支持OpenAI兼容接口的厂商通用）
    if CLOUD_MODEL_AVAILABLE:
        _model_type = "cloud"
        api_key = config.get("api_key", "")
        # 已剥离旧单模型链路的配置打印:模型相关字段统一由 models_config.json 9 槽位承载，
        # 保留此打印会误导排查（启动日志显示的模型名并不等于当前生效槽位）
        try:
            # 🔹 AI自动补全:URL自动去重逻辑，自动识别并去除末尾的/chat/completions后缀
            base_url = config.get("api_url", "https://ark.cn-beijing.volces.com/api/v3")
            # 去除末尾斜杠后统一处理
            base_url = base_url.rstrip("/")
            # 自动去除重复的/chat/completions后缀
            if base_url.endswith("/chat/completions"):
                base_url = base_url[:-len("/chat/completions")]
                print(f"🔧 自动修正接口地址:已自动去除末尾重复的/chat/completions后缀")
            
            # 自定义httpx客户端，彻底解决不同openai版本proxies参数兼容问题，避免自动读取系统代理导致初始化失败
            import httpx
            custom_http_client = httpx.Client(
                timeout=config.get("request_timeout", 200),
                trust_env=False  # 禁用自动读取系统代理/环境变量配置，全版本httpx兼容，彻底解决proxies参数跨版本不兼容问题
            )
            _model_instance = OpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=custom_http_client
            )
            print("✅ 云模型初始化成功")
            # 已剥离模型可用性预校验（旧单模型链路遗留:启动即向 config.json 里的模型发测试请求，
            # 模型字段迁走后必然失败并刷屏 401/404 噪音；实际调用时 OpenAI 会自然重试，无需预检）
            return
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "authentication" in error_msg.lower() or "invalid_api_key" in error_msg:
                print(f"❌ 云模型初始化失败:【认证错误】API密钥无效，请检查密钥是否正确")
            elif "connection" in error_msg.lower() or "proxy" in error_msg.lower() or "dns" in error_msg.lower():
                print(f"❌ 云模型初始化失败:【连接错误】无法连接云端接口，请检查网络/接口地址是否正确")
            elif "timeout" in error_msg.lower():
                print(f"❌ 云模型初始化失败:【超时错误】接口响应超时，请调大超时时间")
            elif "400" in error_msg or "parameter" in error_msg.lower() or "invalid" in error_msg.lower():
                print(f"❌ 云模型初始化失败:【参数错误】请求参数非法，请检查模型名/参数配置")
            else:
                print(f"❌ 云模型初始化失败:【其他错误】{error_msg}")
            _model_instance = MockModel()
            _model_type = "mock"
            return


def chat(prompt: str, history: Optional[List[dict]] = None) -> str:
    """
    统一聊天调用接口，自动切换本地/云模型
    :param prompt: 用户提问
    :param history: 对话历史，格式[{"role":"user","content":"xxx"}, {"role":"assistant","content":"xxx"}]
    :return: 模型返回结果
    """
    global _last_config_hash, _model_instance, _model_type
    history = history or []
    max_retries = 1
    current_retry = 0
    
    while current_retry <= max_retries:
        # 1. 检测配置是否变更，变更则重新初始化模型
        config = _get_config()
        current_hash = _get_config_hash(config)
        if current_hash != _last_config_hash or _model_instance is None:
            _init_model(config)
            _last_config_hash = current_hash
        
        # 检查模型实例是否可用，不可用自动重新初始化
        if _model_instance is None or not hasattr(_model_instance, "chat"):
            _init_model(config)
            # 初始化后仍不可用返回错误提示
            if _model_instance is None or not hasattr(_model_instance, "chat"):
                return "⚠️ 模型初始化失败，请检查API配置/网络是否正常"
        try:
            # 3. 云模型调用逻辑
            if _model_type == "cloud":
                messages = history + [{"role": "user", "content": prompt}]
                # 自动处理多模态消息，识别本地图片路径
                messages = _process_multimodal_messages(messages)
                response = _model_instance.chat.completions.create(
                    model=config.get("model_name", "doubao-seed-2-1-pro-260628"),
                    messages=messages,
                    temperature=config.get("temperature", 0.5),
                    stream=False
                )
                return response.choices[0].message.content
        
        except Exception as e:
            print(f"❌ 模型调用失败（第{current_retry+1}次）:{str(e)}")
            current_retry += 1
            # 超过重试次数抛出异常
            if current_retry > max_retries:
                raise Exception(f"❌ 所有模型调用失败:{str(e)}")
# 【纯云端版】统一大模型封装，完全兼容原有Llama类接口，上层零修改
class UnifiedLLM:
    def __init__(self, model_path=None, n_ctx=32768, **kwargs):
        global _model_instance, _model_type
        self.config = get_config()
        self.last_config_hash = _get_config_hash(self.config)

        # 保留全部原有状态属性，云端场景下自动适配默认值，确保上层访问不报错
        self.is_loaded = False
        self.current_model_name = ""
        self.current_model_path = ""  # 云端模型无本地路径，固定为空
        self.vram_usage = "不适用"    # 云端模型不占用本地显存
        self.is_gguf_model = False    # 纯云端模式，固定为False

        # 初始化云端API客户端
        _init_model(self.config)
        self.last_config_hash = _get_config_hash(self.config)
        self._sync_status()

    def _sync_status(self):
        """同步模型实例状态到当前实例属性，修复原状态字段形同虚设的问题"""
        global _model_instance
        self.is_loaded = _model_instance is not None and hasattr(_model_instance, "chat")
        if self.is_loaded:
            self.current_model_name = self.config.get("model_name", "doubao-seed-2-1-pro-260628")

    def create_chat_completion(self, messages, temperature=0.5, max_tokens=None, stream=False, **kwargs):
        """完全兼容原有调用接口，纯云端模型调用，支持流式/非流式、配置热更新、自动重试
        P0-4: max_tokens默认None——不传该字段，由模型端使用其支持的最大输出长度；仅上层显式传入正整数时才携带"""
        global _model_instance, _model_type
        max_retries = 1
        current_retry = 0

        while current_retry <= max_retries:
            # 每次调用自动检测配置变更，支持运行时切换模型/密钥/接口地址
            current_config = _get_config()
            current_hash = _get_config_hash(current_config)
            if current_hash != self.last_config_hash:
                self.config = current_config
                self.last_config_hash = current_hash
                _init_model(current_config)
                self._sync_status()

            # 检查云端客户端可用性，异常自动重新初始化
            if _model_instance is None or not hasattr(_model_instance, "chat"):
                _init_model(current_config)
                self._sync_status()
                # 初始化失败返回格式对齐的错误信息，上层无需额外异常判断
                if _model_instance is None or not hasattr(_model_instance, "chat"):
                    error_msg = "⚠️ 云端模型初始化失败，请检查API配置/网络是否正常"
                    if stream:
                        def generate_error_stream():
                            yield {"choices": [{"delta": {"content": error_msg}, "finish_reason": "stop"}]}
                        return generate_error_stream()
                    else:
                        return {"choices": [{"message": {"role": "assistant", "content": error_msg}}]}

            try:
                # 统一走云端API调用逻辑
                # 动态计算超时时间：根据上下文长度自动适配，长上下文自动延长超时，避免首包超时
                total_content_length = sum(len(str(msg.get("content", ""))) for msg in messages)
                estimated_tokens = int(total_content_length * 1.5)  # 中文场景1字符≈1.5token
                base_timeout = self.config.get("request_timeout", 200)
                dynamic_timeout = min(base_timeout + (estimated_tokens // 10000) * 30, 600)
                # 自动处理多模态消息，识别本地图片路径
                messages = _process_multimodal_messages(messages)
                # P0-4: 默认不传max_tokens（None），由模型端使用其支持的最大输出长度；
                # 仅当上层显式传入正整数时才携带该字段，彻底避免硬编码250000超过部分模型上限导致首轮直接400
                request_kwargs = {
                    "model": self.config.get("model_name", "doubao-seed-2-1-pro-260628"),
                    "messages": messages,
                    "temperature": temperature,
                    "stream": stream,
                    "timeout": dynamic_timeout
                }
                if max_tokens:
                    request_kwargs["max_tokens"] = max_tokens
                response = _model_instance.chat.completions.create(**request_kwargs)

                # 流式模式：包装为统一格式迭代器，全链路异常捕获，避免流迭代异常向上抛出导致连接断开
                if stream:
                    def generate_cloud_stream():
                        try:
                            for chunk in response:
                                # 跳过无choices的统计类数据包，避免偶发索引越界
                                if not chunk.choices:
                                    continue
                                choice = chunk.choices[0]
                                delta = choice.delta
                                delta_data = {}
                                if delta.content:
                                    delta_data["content"] = delta.content
                                # 兼容深度思考模型的推理过程字段
                                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                                    delta_data["reasoning_content"] = delta.reasoning_content
                                # 先处理内容，确保最后一个数据块的内容不丢失
                                if delta_data:
                                    yield {"choices": [{"delta": delta_data, "finish_reason": None}]}
                                # 再处理结束信号
                                if choice.finish_reason == "stop":
                                    yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}
                                    break
                        except Exception as stream_err:
                            err_msg = str(stream_err)
                            print(f"❌ 流式响应接收异常:{err_msg}")
                            # 识别不同错误类型，返回友好提示
                            if "context_length_exceeded" in err_msg or "context length" in err_msg.lower() or "maximum context" in err_msg.lower():
                                error_tip = "\n\n⚠️ 当前上下文长度超出模型窗口限制，请减少对话轮数或关闭部分记忆召回后重试"
                            elif "timeout" in err_msg.lower() or "timed out" in err_msg.lower():
                                error_tip = "\n\n⚠️ 模型响应超时，请稍后重试或调大超时时间"
                            elif "connection" in err_msg.lower() or "reset" in err_msg.lower() or "network" in err_msg.lower():
                                error_tip = "\n\n⚠️ 网络连接中断，请检查网络后重试"
                            else:
                                error_tip = f"\n\n⚠️ 响应接收异常：{err_msg[:100]}，请稍后重试"
                            # 输出错误提示，正常结束流，不向上抛出异常
                            yield {"choices": [{"delta": {"content": error_tip}, "finish_reason": "stop"}]}
                            return
                    return generate_cloud_stream()

                # 非流式模式：返回格式与原Llama类完全一致
                else:
                    msg = response.choices[0].message
                return {"choices": [{"message": {
                        "role": "assistant",
                        "content": msg.content,
                        "reasoning_content": getattr(msg, "reasoning_content", "")
                    }}]}

            except Exception as e:
                error_msg = str(e)
                print(f"❌ 云端模型调用失败（第{current_retry+1}次）:{error_msg}")
                
                # 🔹 P0-4: max_tokens超出模型上限自动容错，兼容中英文错误信息，提取模型支持的最大值后按90%重试
                _msg_low = error_msg.lower()
                _is_max_tokens_err = ("max_tokens" in _msg_low) and any(
                    k in error_msg for k in ("above maximum", "invalid", "exceed", "less than",
                                            "超过", "上限", "最大", "不能大于", "小于等于")
                )
                if _is_max_tokens_err:
                    model_max_tokens = _extract_model_max_tokens(error_msg)
                    if model_max_tokens:
                        # 取上限的90%作为实际使用值，预留安全余量
                        safe_max_tokens = int(model_max_tokens * 0.9)
                        print(f"🔧 自动修正max_tokens:模型最大支持{model_max_tokens}，自动调整为{safe_max_tokens}并重试")
                        # 覆盖当前max_tokens参数，下次循环用新值重试
                        max_tokens = safe_max_tokens
                        # 不增加重试计数，这次属于自动修正，不算失败重试
                        continue
                
                current_retry += 1
                # 超过重试次数抛出统一异常
                if current_retry > max_retries:
                    raise Exception(f"❌ 所有云端模型调用失败:{error_msg}")
                    
def chat_with(
    slot: int,
    messages: List[dict],
    temperature: float = 0.5,
    max_tokens: Optional[int] = None,
    stream: bool = False,
    **kwargs,
):
    """按 slot 调用独立模型客户端（替代全局单例）；不依赖全局态，供 orchestrator 与 verify 复用"""
    from model_registry import get_client, get_slot_config, get_runtime, get_semaphore

    cfg = get_slot_config(slot)
    if not cfg:
        err = f"⚠️ 未找到 slot={slot} 的模型配置"
        if stream:
            def _err_stream():
                yield {"choices": [{"delta": {"content": err}, "finish_reason": "stop"}]}
            return _err_stream()
        return {"choices": [{"message": {"role": "assistant", "content": err}}]}

    client = get_client(slot)
    messages = _process_multimodal_messages(messages)
    total_content_length = sum(len(str(m.get("content", ""))) for m in messages)
    estimated_tokens = int(total_content_length * 1.5)
    try:
        base_timeout = int(cfg.get("timeout", 200))
    except (TypeError, ValueError):
        base_timeout = 200
    dynamic_timeout = min(base_timeout + (estimated_tokens // 10000) * 30, 600)
    max_retries = int(get_runtime().get("retry", 1))
    if max_retries < 0:
        max_retries = 0
    sem = get_semaphore()
    current_retry = 0
    while current_retry <= max_retries:
        try:
            request_kwargs = {
                "model": cfg.get("model_name", ""),
                "messages": messages,
                "temperature": temperature,
                "stream": stream,
                "timeout": dynamic_timeout,
            }
            if max_tokens:
                request_kwargs["max_tokens"] = max_tokens
            request_kwargs.update(kwargs)
            with sem:
                response = client.chat.completions.create(**request_kwargs)
                if stream:
                    def _stream_gen():
                        try:
                            for chunk in response:
                                if not chunk.choices:
                                    continue
                                choice = chunk.choices[0]
                                delta = choice.delta
                                delta_data = {}
                                if delta.content:
                                    delta_data["content"] = delta.content
                                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                                    delta_data["reasoning_content"] = delta.reasoning_content
                                if delta_data:
                                    yield {"choices": [{"delta": delta_data, "finish_reason": None}]}
                                if choice.finish_reason == "stop":
                                    yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}
                                    break
                        except Exception as stream_err:
                            yield {"choices": [{"delta": {"content": f"\n\n⚠️ 响应接收异常:{str(stream_err)[:100]}"}, "finish_reason": "stop"}]}
                    return _stream_gen()
                msg = response.choices[0].message
                return {"choices": [{"message": {
                    "role": "assistant",
                    "content": msg.content,
                    "reasoning_content": getattr(msg, "reasoning_content", "")
                }}]}
        except Exception as e:
            error_msg = str(e)
            _msg_low = error_msg.lower()
            _is_max_tokens_err = ("max_tokens" in _msg_low) and any(
                k in error_msg for k in ("above maximum", "invalid", "exceed", "less than",
                                        "超过", "上限", "最大", "不能大于", "小于等于")
            )
            if _is_max_tokens_err:
                model_max_tokens = _extract_model_max_tokens(error_msg)
                if model_max_tokens:
                    max_tokens = int(model_max_tokens * 0.9)
                    continue
            current_retry += 1
            if current_retry > max_retries:
                raise Exception(f"❌ slot={slot} 模型调用失败:{error_msg}")


# 全局统一LLM实例，延迟初始化（必须在外部依赖路径注入完成后调用init_llm()初始化）
llm = None

def init_llm():
    """初始化全局LLM实例，必须在依赖路径注入完成后调用，避免提前导入依赖失败"""
    global llm
    if llm is None:
        llm = UnifiedLLM()
    return llm
