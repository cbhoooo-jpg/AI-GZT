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
        _internal_default_config = os.path.join(_internal_dir, "config.json")
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
    """读取最新配置"""
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _get_config_hash(config: dict) -> str:
    """计算配置哈希，用于检测变更"""
    config_str = json.dumps(config, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(config_str.encode()).hexdigest()
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
    # 第一步:先获取模型厂商，修复变量未定义问题
    model_provider = config.get("model_provider", "火山引擎·豆包")
    

    # 第三步:云模型初始化（所有支持OpenAI兼容接口的厂商通用）
    if CLOUD_MODEL_AVAILABLE:
        _model_type = "cloud"
        api_key = config.get("api_key", "")
        # 脱敏打印配置，定位配置加载问题
        masked_key = api_key[:4] + "*" * (len(api_key)-4) if len(api_key) > 4 else "未配置"
        print(f"🔧 加载配置:API密钥={masked_key} 接口地址={config.get('api_url', '默认豆包地址')} 模型名={config.get('model_name', 'default')} 超时时间={config.get('request_timeout',200)}s")
        print(f"🔧 初始化云模型:{model_provider} - {config.get('model_name', 'default')}")
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
            
            # 🔹 AI自动补全:模型可用性预校验，发送轻量测试请求提前发现问题
            try:
                test_model = config.get("model_name", "")
                if test_model:
                    # 发送一个极短的测试请求，验证模型是否可用
                    _model_instance.chat.completions.create(
                        model=test_model,
                        messages=[{"role": "user", "content": "hi"}],
                        max_tokens=1,
                        timeout=30
                    )
                    print(f"✅ 模型可用性校验通过:模型「{test_model}」可正常调用")
            except Exception as test_err:
                error_msg = str(test_err)
                print(f"⚠️ 模型可用性预校验失败:")
                if "401" in error_msg or "authentication" in error_msg.lower() or "invalid_api_key" in error_msg:
                    print("   原因:API密钥无效，请检查密钥是否正确")
                elif "404" in error_msg or "model_not_found" in error_msg.lower() or "not found" in error_msg.lower():
                    print("   原因:模型不存在，请确认模型名称是否正确，或该模型是否已在对应平台激活")
                elif "connection" in error_msg.lower() or "proxy" in error_msg.lower() or "dns" in error_msg.lower():
                    print("   原因:无法连接接口地址，请检查网络或接口地址是否正确")
                elif "timeout" in error_msg.lower():
                    print("   原因:接口响应超时，请检查网络或调大超时时间")
                else:
                    print(f"   原因:{error_msg[:150]}")
                print("   提示:仍可继续使用，实际调用时会自动重试")
            
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

    def create_chat_completion(self, messages, temperature=0.5, max_tokens=250000, stream=False, **kwargs):
        """完全兼容原有调用接口，纯云端模型调用，支持流式/非流式、配置热更新、自动重试"""
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
                response = _model_instance.chat.completions.create(
                    model=self.config.get("model_name", "doubao-seed-2-1-pro-260628"),
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream,
                    timeout=dynamic_timeout
                )

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
                
                # 🔹 AI自动补全:max_tokens超出上限自动容错，自动提取模型支持的最大值并重试
                if "max_tokens" in error_msg.lower() and ("above maximum" in error_msg.lower() or "invalid" in error_msg.lower() or "exceed" in error_msg.lower()):
                    # 尝试从错误信息中提取最大支持的token数
                    max_match = re.search(r'expected a value <=\s*(\d+)', error_msg)
                    if max_match:
                        model_max_tokens = int(max_match.group(1))
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
                    
# 全局统一LLM实例，延迟初始化（必须在外部依赖路径注入完成后调用init_llm()初始化）
llm = None

def init_llm():
    """初始化全局LLM实例，必须在依赖路径注入完成后调用，避免提前导入依赖失败"""
    global llm
    if llm is None:
        llm = UnifiedLLM()
    return llm
