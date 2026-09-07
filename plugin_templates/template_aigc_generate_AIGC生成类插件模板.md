---
template_id: aigc_generate
name: AIGC生成类插件模板
scene: 适合调用AI模型生成图片、视频、文案、文档、数字人等内容的插件
default_permission: network,write_file,read_file
default_config:
  - key: api_key
    label: 火山方舟API密钥
    type: password
    default: ""
    placeholder: 从火山方舟对应应用控制台密钥管理处获取
    required: true
  - key: api_url
    label: API接口地址
    type: input
    default: "https://ark.cn-beijing.volces.com/api/v3"
    placeholder: 第三方AI服务的API请求地址
    required: true
  - key: model_id
    label: 模型ID
    type: input
    default: "{{default_model_id}}"
    placeholder: 火山方舟部署的对应模型ID
    required: true
  - key: save_path
    label: 文件保存路径
    type: input
    default: "D:/AI仓库文件夹/文件生成/AI生成结果/{{plugin_id}}/"
    placeholder: 生成的文件保存的本地目录
    required: false
default_params:
  - name: prompt
    description: 生成描述提示词，越详细生成效果越好
    required: true
  - name: size
    description: 生成尺寸，支持1024x1024/1280x720/720x1280
    required: true
  - name: duration
    description: 生成时长，单位秒，支持5/10/15/30
    required: false
  - name: images
    description: 参考素材，支持本地文件路径/公网URL，多模态生成时传入
    required: false
---
### [FILE] main.py
```python
import os
import sys
import json
import requests
from datetime import datetime
# 火山方舟官方SDK
from volcenginesdkarkruntime import Ark
# 导入全局路径转换工具，对齐系统全局路径规则
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from api_server import get_real_physical_path, upload_file_to_tos

def upload_local_file_to_public_url(local_path: str, file_type: str = "video") -> str:
    """
    自动上传本地文件到公网并返回URL
    优先级:TOS对象存储 > 公共匿名托管API（零配置兜底）
    支持视频、音频、图片等所有文件类型，自动识别本地路径/公网URL/Base64
    """
    # 空值或已经是公网URL/Base64的直接返回
    if not local_path or not local_path.strip():
        return ""
    path_str = local_path.strip()
    if path_str.startswith(('http://', 'https://', 'data:')):
        return path_str
    
    # 转换为真实物理路径
    try:
        if os.path.isabs(path_str) and os.path.exists(path_str) and os.path.isfile(path_str):
            real_path = path_str
        else:
            real_path = get_real_physical_path(path_str)
        
        if not os.path.exists(real_path) or not os.path.isfile(real_path):
            print(f"⚠️ 本地文件[{path_str}]不存在，物理路径[{real_path}]，跳过上传")
            return ""
        
        # 文件大小校验（超过200MB给出警告但仍尝试上传）
        file_size = os.path.getsize(real_path)
        if file_size > 200 * 1024 * 1024:
            print(f"⚠️ 文件[{real_path}]大小{file_size // 1024 // 1024}MB，可能超出公共托管API限制")
        
        # 尝试TOS上传（需用户配置）
        public_url = upload_file_to_tos(real_path, file_type)
        if public_url:
            print(f"✅ 文件[{real_path}]已上传到TOS对象存储，公网URL:{public_url}")
            return public_url
        
        print(f"⚠️ 文件[{real_path}]TOS上传失败或未配置，将由插件层降级处理")
        return ""
    except Exception as e:
        print(f"❌ 文件[{path_str}]上传异常:{str(e)}")
        return ""


# 全局插件配置
plugin_config = {}

def init(config: dict):
    """插件初始化方法，安装/启用/配置修改时自动调用"""
    global plugin_config
    plugin_config = config

    # 初始化逻辑:可根据需要自定义，比如自动创建目录、校验配置等
    # 示例:如果有存储路径配置，自动创建目录
    for k, v in plugin_config.items():
        if 'path' in k.lower() and str(v).strip():
            os.makedirs(os.path.dirname(os.path.abspath(str(v).strip())), exist_ok=True)

    return True

def run(params: dict):
    """插件入口方法，接收LLM传入的参数，返回执行结果"""
    try:
        import time
        # 1. 读取插件元信息
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plugin.json'), 'r', encoding='utf-8') as f:
            plugin_info = json.load(f)
        config_list = plugin_info.get('config', [])
        param_list = plugin_info.get('parameters', [])
        
        # 2. 配置校验
        for item in config_list:
            if item.get('required', False) and not plugin_config.get(item['key'], '').strip():
                return f"❌ 请先在插件配置中填写[{item['label']}]，配置完成后即可使用{plugin_info['name']}功能"

        # 3. 参数校验
        for item in param_list:
            if item.get('required', False) and not params.get(item['name'], '').strip():
                return f"❌ 缺少必填参数:{item['description']}"
                
        # 4. 提取参数
        prompt = params['prompt']
        size = params['size']
        duration = params['duration']
        api_key = plugin_config['api_key']
        api_url = plugin_config['api_url']
        model_id = plugin_config['model_id']
        save_path = plugin_config.get('save_path', './仓库文件夹/视频生成/')
        os.makedirs(save_path, exist_ok=True)

        # --------------------------
        # 核心业务逻辑:视频生成（官方SDK实现）
        # --------------------------
        # 初始化Ark客户端
        client = Ark(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=api_key,
        )
        
        # 拼接完整提示词，携带参数
        # size参数格式转换（适配doubao-seedance-2-0-pro模型要求，转ratio参数）
        ratio_map = {
            "1280x720": "16:9",
            "720x1280": "9:16",
            "1024x1024": "1:1"
        }
        ratio = ratio_map.get(size, "16:9")
        # duration参数校验兼容（适配doubao-seedance-2-0-pro模型要求，支持5/10/15/30秒）
        supported_durations = [5, 10, 15, 30]
        # 先统一转换为int类型，避免字符串参数类型报错，非法值默认转5秒
        try:
            duration = int(duration)
        except:
            duration = 5
        if duration not in supported_durations:
            # 自动向下取最近的支持值，避免参数错误
            duration = max([d for d in supported_durations if d <= duration], default=5)
        # 提取可选多模态参数
        images = params.get('images', [])
        # ========== 调试日志:原始参数接收 ==========
        print(f"[视频生成插件DEBUG] 原始传入images参数 | 类型:{type(images)} | 值:{repr(images)[:500]}")
        # 兼容字符串格式的数组:支持标准JSON数组（双引号"path"格式）、Python字面量列表（单引号'path'格式，适配str(list)传参场景）
        if isinstance(images, str):
            ref_str = images.strip()
            # 第一步:优先尝试解析标准JSON格式
            try:
                import json as _json
                parsed = _json.loads(ref_str)
                if isinstance(parsed, list):
                    images = parsed
            except (_json.JSONDecodeError, ValueError):
                # JSON解析失败，第二步:尝试解析Python原生字面量格式（兼容单引号列表）
                try:
                    import ast
                    parsed = ast.literal_eval(ref_str)
                    if isinstance(parsed, list):
                        images = parsed
                except (ValueError, SyntaxError):
                    # 两种格式都解析失败，判定为单个路径字符串，后续按单元素列表处理
                    pass
        if not isinstance(images, list):
            images = [images] if images else []
        # 新增:本地图片路径自动转换为公网URL逻辑
        processed_images = []
        import base64
        for img_item in images:
            # 兼容三种传参格式:纯字符串路径/URL、附件字典对象、嵌套列表（自动展开）
            img_path = ""
            if isinstance(img_item, list):
                # 嵌套列表自动展开取第一个元素（修复LLM传参嵌套列表问题）
                if img_item and len(img_item) > 0:
                    img_path = str(img_item[0]).strip()
            elif isinstance(img_item, dict):
                # 字典类型附件:优先取local_path，其次取url
                img_path = img_item.get("local_path", "") or img_item.get("url", "")
            elif isinstance(img_item, str):
                img_path = img_item.strip()
            if not img_path:
                continue
            # 如果已经是公网URL或Base64直接保留
            if img_path.startswith(('http://', 'https://', 'data:image/')):
                processed_images.append(img_path)
                continue
            # 本地路径直接转Base64格式，完全本地处理无需云端存储，100%安全零成本
            try:
                # 先判断是否已经是绝对路径且文件存在（对齐图片生成插件逻辑，优先直接读取）
                if os.path.isabs(img_path) and os.path.exists(img_path) and os.path.isfile(img_path):
                    local_img_path = img_path
                else:
                    # 对齐全局路径规则，自动转换为真实物理路径
                    local_img_path = get_real_physical_path(img_path)
                # 校验文件是否存在
                if not os.path.exists(local_img_path) or not os.path.isfile(local_img_path):
                    print(f"⚠️ 本地图片[{img_path}]不存在，拼接后真实路径为[{local_img_path}]，请检查路径是否正确")
                    continue
                # 读取文件二进制内容
                with open(local_img_path, 'rb') as f:
                    img_data = f.read()
                # 自动识别图片后缀
                ext = os.path.splitext(local_img_path)[1].lower().lstrip('.')
                if ext not in ['png', 'jpg', 'jpeg', 'webp']:
                    ext = 'png' # 兜底格式
                # 转Base64生成data URI
                base64_data = base64.b64encode(img_data).decode('utf-8')
                base64_url = f"data:image/{ext};base64,{base64_data}"
                processed_images.append(base64_url)
                print(f"✅ 本地图片[{local_img_path}]转Base64成功，直接传入模型")
            except Exception as upload_err:
                print(f"⚠️ 本地图片[{img_item}]转换失败:{str(upload_err)}，可直接使用公网图片URL，纯提示词生成功能不受影响")
        # 替换为处理后的公网URL列表
        images = processed_images
        reference_video = params.get('reference_video', '')
        reference_audio = params.get('reference_audio', '')
        generate_audio = params.get('generate_audio', True)
        # 转换为布尔值避免参数类型错误
        if isinstance(generate_audio, str):
            generate_audio = generate_audio.lower() in ['true', '1', '是']
        # 导演视角质量增强:核心内容放最前面提升权重，规则放后面作为约束，避免内容偏离需求
        # 核心生成内容优先级最高，放在最前面保证模型优先识别，禁止修改内容主题
        core_content = f"### 核心生成内容（优先级最高，必须100%还原，必须严格遵循核心内容主题）:{prompt}"
        # 有参考图时追加强制参考约束，优先级仅次于核心内容
        reference_constraint = ""
        if images:
            reference_constraint = """
---
### 参考图强制约束（优先级仅次于核心生成内容，100%强制执行）
所有角色/场景的造型、配色、材质100%严格参考提供的参考图，不得随意修改外观，必须和参考图中的外观一致，专属特征必须完整保留，参考图如有物体人物简介说明在视频生成时必须进行参考。
"""
        # 生成约束规则，仅规范生成效果，不改变内容本身
        director_rules = """
---
你是经验丰富的顶级专业导演，精通各类视频内容的镜头设计与细节刻画，能根据输入内容自动完善所有细节，生成的视频拥有丰富的光影层次、细腻的物体纹理、自然的人物/物品动态表现，全程符合专业影视制作标准；
生成内容会根据实际情况和运动物理逻辑进行优化，人物和动物的动态运动轨迹会进行相应的变化设计，运动物体会对障碍物的避让和撞击反应进行轨迹变化，打斗和战斗逻辑会考虑实际因素，进行相应的避让，被击中会受到伤害，同时根据剧本简介设计相应的数值，例如防御高的受到的伤害相应变小，恢复高的受伤时会进行相应的恢复；
被击中的会根据伤害来源产生相应的轨迹变化。
严格按以下正向规则优化视频效果，所有规则强制执行，无需额外确认:
1. 镜头语言规则:视频采用多视角切换呈现，按20%特写（人物微表情/动作细节/产品核心特征）、50%中景（人物完整动作+环境/产品完整形态+使用场景）、30%远景（整体场景氛围/品牌全局展示）分配镜头比例，通过平滑的视角切换、镜头推拉运镜提升内容层次感；
2. 节奏设计规则:每5秒视频至少包含2个镜头切换，每10秒视频至少包含4个镜头切换，单个镜头停留时长控制在2-3秒，适配短视频观看节奏；
3. 人物和动物内容专属刻画规则:针对人物动物剧情类内容，必须完整刻画人物动物的表情、动作、着装细节，通过镜头推进、角度切换补充展现人物性格特征与情绪状态（开心/愤怒/悲伤/悠闲等各种情绪），主要出场人物动物至少包含2个局部特写镜头（面部表情/手部动作/专属配饰细节），动作自然流畅无僵硬感；
4. 物体外观刻画规则：生成的物体（包含人物，动物）的外观形态必须比例协调，尺寸大小和细节根据剧本内容和实际情况进行适配，不同物品人物在同一画面的生成比例要参考剧本内容和简介内容中的相应尺寸，肢体设计必须正常并符合逻辑，除非剧本中出现相应的设计，例如畸形，三头六臂（神话特征），这些情况；
5. 产品内容专属刻画规则:针对产品展示类内容，必须完整刻画产品的材质纹理、功能细节、使用场景，通过镜头旋转、特写聚焦展现产品核心卖点，核心产品至少包含2个功能/材质特写镜头，产品形态清晰无变形；
6. 内容补全规则:当输入的核心内容信息不足、缺少分镜/动作/场景描述时，自动补全合理的过渡情节、运镜设计、场景动态细节（风吹/光影移动/粒子特效等），保证内容完整流畅有故事感，所有补全内容必须与核心主题高度匹配；
7. 画质呈现规则:输出4K超清画质，24帧/秒，色彩层次分明，无变形无模糊，全程无水印；
8. 内容一致性规则:必须100%还原核心剧情、人物设定、产品属性，所有优化、补全内容不得偏离核心主题，所有镜头设计必须符合场景逻辑；
9. 细分场景自动适配规则：科幻/星际/机甲这类场景生成内容「金属纹理增强、光影对比度提升、爆炸/激光粒子特效丰富」，古风/古装/国风这类场景「色彩饱和度适中、服化道符合朝代特征、运镜舒缓有氛围感」，产品/展示/广告这类场景「背景简洁、产品打光均匀、无多余杂物干扰核心卖点」。
"""
        full_prompt = f"{core_content}{reference_constraint}{director_rules}"
        
        # 构建多模态content数组，按优先级排序
        content = []
# 1. 参考视频（优先级最高）
        if reference_video and reference_video.strip():
            # 尝试TOS上传获取公网URL（模型不支持Base64格式视频，必须上传获取公网链接）
            video_url = upload_local_file_to_public_url(reference_video, "video")
            if video_url:
                content.append({
                    "type": "video_url",
                    "video_url": {
                        "url": video_url
                    },
                    "role": "reference_video"
                })
            else:
                print(f"⚠️ 参考视频[{reference_video}]TOS上传失败或未配置，模型不支持Base64格式视频，已跳过。请配置TOS对象存储获取公网URL")
# 2. 参考音频
        if reference_audio and reference_audio.strip():
            # 尝试TOS上传获取公网URL（模型不支持Base64格式音频，必须上传获取公网链接）
            audio_url = upload_local_file_to_public_url(reference_audio, "audio")
            if audio_url:
                content.append({
                    "type": "audio_url",
                    "audio_url": {
                        "url": audio_url
                    },
                    "role": "reference_audio"
                })
            else:
                print(f"⚠️ 参考音频[{reference_audio}]TOS上传失败或未配置，模型不支持Base64格式音频，已跳过。请配置TOS对象存储获取公网URL")
        # 3. 参考图片
        for img_url in images:
            if img_url and img_url.strip():
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": img_url.strip()
                    },
                    "role": "reference_image"
                })
        # 4. 文本提示词（最低优先级，不覆盖前面的多模态内容）
        content.append({
            "type": "text",
            "text": full_prompt
        })
        
        # 第一步:提交视频生成任务（适配Seedance 2.0 Pro接口参数）
        create_result = client.content_generation.tasks.create(
            model=model_id,
            content=content,
            generate_audio=generate_audio,
            ratio=ratio,
            duration=duration,
            watermark=False
        )
        task_id = create_result.id
        
        # 第二步:异步轮询任务结果
        max_poll_times = 60
        poll_interval = 10
        for i in range(max_poll_times):
            get_result = client.content_generation.tasks.get(task_id=task_id)
            status = get_result.status
            
            if status == "succeeded":
                # 提取视频地址（多属性全场景兼容适配，修复属性不存在错误）
                try:
                    # 尝试不同属性名适配SDK返回结构
                    if hasattr(get_result, 'video_url'):
                        # 适配直接挂载在根对象的视频地址
                        video_url = get_result.video_url
                    elif hasattr(get_result, 'result'):
                        video_url = get_result.result.video_url
                    elif hasattr(get_result, 'output'):
                        video_url = get_result.output.video_url
                    elif hasattr(get_result, 'data'):
                        video_url = get_result.data.get('video_url') or get_result.data.get('output', {}).get('video_url')
                    elif hasattr(get_result, 'content'):
                        # 适配content属性存储视频地址的结构
                        if hasattr(get_result.content, 'video_url'):
                            video_url = get_result.content.video_url
                        else:
                            # 兜底转字典查找
                            content_dict = get_result.content.model_dump() if hasattr(get_result.content, 'model_dump') else dict(get_result.content)
                            video_url = content_dict.get('video_url') or content_dict.get('url')
                    else:
                        # 兜底打印完整对象结构方便定位
                        full_data = get_result.model_dump() if hasattr(get_result, 'model_dump') else {}
                        raise Exception(f"返回对象属性列表:{dir(get_result)}，完整返回内容:{full_data}")
                    # 校验是否获取到有效视频地址
                    if not video_url or not isinstance(video_url, str) or not video_url.startswith(('http://', 'https://')):
                        raise Exception(f"获取到的视频地址无效:{video_url}")
                except Exception as e:
                    return f"❌ 读取视频地址失败，无法找到有效视频字段:{str(e)}"
                # 第三步:下载视频保存到本地
                video_resp = requests.get(video_url, timeout=120)
                video_resp.raise_for_status()
                file_name = f"视频生成_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp4"
                full_path = os.path.join(save_path, file_name)
                with open(full_path, 'wb') as f:
                    f.write(video_resp.content)
                return f"✅ 视频生成成功，已保存到:{full_path}\n视频在线地址:{video_url}"
            elif status == "failed":
                error_msg = get_result.error.message if get_result.error else "未知错误"
                return f"❌ 视频生成失败:{error_msg}"
            
            # 等待后继续轮询
            time.sleep(poll_interval)
        
        return f"❌ 视频生成超时，已等待{max_poll_times * poll_interval // 60}分钟，请稍后重试"
    except Exception as e:
        return f"❌ 插件执行失败:{str(e)}"
```
### [FILE] plugin.json
```json
{
  "plugin_id": "{{plugin_id}}",
  "name": "{{plugin_name}}",
  "description": "{{description}}",
  "version": "{{version}}",
  "author": "{{author}}",
  "trigger_keyword": "{{trigger_keyword}}",
  "entry": "main.py",
  "permissions": [
    "network",
    "write_file",
    "read_file"
  ],
  "enabled": true,
  "config": [
    {
      "key": "api_key",
      "label": "火山方舟API密钥",
      "type": "password",
      "default": "",
      "placeholder": "从火山方舟对应应用控制台密钥管理处获取",
      "required": true
    },
    {
      "key": "api_url",
      "label": "API接口地址",
      "type": "input",
      "default": "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks",
      "placeholder": "第三方AI视频生成服务的API请求地址",
      "required": true
    },
    {
      "key": "model_id",
      "label": "模型ID",
      "type": "input",
      "default": "doubao-seedance-2-0-260128",
      "placeholder": "火山方舟视频生成模型ID，默认Seedance 2.0 Pro版（请勿使用fast版本，当前账号未开通fast权限）",
      "required": true
    },
    {
      "key": "save_path",
      "label": "文件保存路径",
      "type": "input",
      "default": "D:/AI仓库文件夹/文件生成/视频生成/",
      "placeholder": "生成的视频文件保存的本地目录",
      "required": false
    },
    {
      "key": "open_volc_ark", 
      "label": "前往开通模型", 
      "type": "button", 
      "action": "openUrl", 
      "url": "https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement", 
      "description": "点击直达火山方舟控制台，可开通Seedream生图模型、获取API密钥、复制模型ID", 
      "default": "", "required": false
    }
  ],
  "parameters": [
    {
      "name": "prompt",
      "description": "视频生成描述提示词，越详细生成效果越好",
      "required": true
    },
    {
      "name": "size",
      "description": "视频尺寸，支持1024x1024/1280x720/720x1280",
      "required": true
    },
    {
      "name": "duration",
      "description": "视频时长，单位秒，支持5/10/15",
      "required": true
    },
    {
      "name": "images",
      "description": "参考图片，支持本地文件路径/公网URL/列表/单字符串，图生视频时传入，用户提供参考图/本地卡片路径时必须优先使用该素材，禁止重新生成",
      "required": false
    },
    {
      "name": "reference_video",
      "description": "参考视频URL，视频生视频时传入",
      "required": false
    },
    {
      "name": "reference_audio",
      "description": "参考音频URL，自定义背景音乐/配音时传入",
      "required": false
    },
    {
      "name": "generate_audio",
      "description": "是否自动生成音频，默认true",
      "required": false
    },
    {{extra_parameters}}
  ]
}
```
### [FILE] README.md
```markdown
# {{plugin_name}}
## 插件说明
{{description}}

## 版本信息
- 版本:{{version}}
- 作者:{{author}}
- 触发关键词:{{trigger_keyword}}

## ⚙️ 配置说明
| 配置项 | 说明 | 类型 | 默认值 | 必填 |
| --- | --- | --- | --- | --- |
| api_key | 火山方舟API密钥 | password | 无 | 是 |
| api_url | API接口地址 | input | https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks | 是 |
| model_id | 模型ID | input | doubao-seedance-2-0-260128 | 是 |
| save_path | 文件保存路径 | input | D:/AI仓库文件夹/文件生成/视频生成/ | 否 |
| open_volc_ark | 前往开通模型 | button | 无 | 否 |

## 自定义修改指南
### 1. 模型更换说明
#### 火山方舟生态模型更换
- 直接在插件配置页修改`model_id`为对应部署的模型ID即可（需填写带ep前缀的完整ID）
- 不同模型支持的参数差异请自行适配核心逻辑中参数映射部分，适配参考：
  - 图片生成模型（如Doubao-seedream）：无需ratio转换，直接传入size参数即可
  - 音频生成模型：删除视频/图片相关参数，新增audio_prompt、voice_type等模型专属参数
  - 文案生成模型：无需多模态素材处理逻辑，直接调用chat.completions接口即可
#### 第三方AI服务模型更换
- 修改`api_url`为对应服务的官方接口地址
- 替换核心逻辑中Ark客户端初始化代码为对应服务的SDK/HTTP请求逻辑
- 同步修改`requirements.txt`添加对应服务的依赖包
### 2. 参数调整说明
#### 新增/删除参数
- 先修改`plugin.json`中`parameters`数组，添加/删除对应参数配置
- 同步修改`main.py`中参数校验、参数提取部分代码
- 同步更新本README.md中使用说明和示例部分
#### 参数规则修改
- 如调整尺寸支持列表、时长范围、提示词长度限制等，需同步修改3处：
  1. `main.py`中参数校验适配逻辑
  2. `plugin.json`中对应参数的description说明
  3. 本README.md中配置/参数说明文档
### 3. 核心业务逻辑修改说明
- 所有自定义业务逻辑请写在`{{core_business_logic}}`标记的核心逻辑区间内
- 通用多模态素材预处理逻辑、配置校验逻辑、结果下载保存逻辑无需修改，已对齐全局系统规范
- 如果生成结果不是音视频/图片类文件，请修改结果保存逻辑的文件后缀判断部分适配对应格式
---
## 常见问题&注意事项
1. **API报错401/无效密钥**：请检查`api_key`是否正确，账号是否有对应模型的调用权限
2. **API报错400/参数无效**：请检查传入参数是否符合模型要求，尺寸/时长是否在支持范围内
3. **生成超时**：可适当调整`max_poll_times`和`poll_interval`参数，适配长耗时生成任务
4. **本地素材上传失败**：请检查本地文件路径是否正确，当前支持的素材格式为png/jpg/jpeg/webp/mp3/wav/mp4
5. **参数兼容注意**：所有模型专属参数请添加到`plugin.json`的`extra_parameters`占位符位置，不要修改通用默认参数结构

## 🔌 插件再开发说明
### 1. plugin.json 完整格式规范
#### 顶层必填字段
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| plugin_id | string | 是 | 插件全局唯一ID，仅支持小写字母、数字、下划线，不能和其他插件重复 |
| name | string | 是 | 插件显示名称，会展示在插件市场和配置页 |
| description | string | 是 | 插件功能描述，会自动注入AI上下文帮助识别触发场景 |
| version | string | 是 | 版本号，遵循semver规范（x.y.z），例如1.0.0 |
| author | string | 是 | 插件作者信息 |
| trigger_keyword | string/array | 是 | 触发关键词，支持字符串或字符串数组，AI会匹配用户消息中的关键词自动调用插件 |
| entry | string | 是 | 插件入口文件，固定为main.py |
| permissions | array | 是 | 插件所需权限列表，可选值:`network`（网络访问）、`file_read`（文件读取）、`file_write`（文件写入） |
| enabled | boolean | 是 | 插件默认启用状态，固定为true |
| config | array | 否 | 插件配置项列表，会渲染到前端配置页面，用户可修改 |
| parameters | array | 是 | 插件调用参数列表，AI会根据这些说明自动生成调用参数 |
| dependencies | array | 否 | 插件依赖的Python包列表，安装插件时会自动安装 |

#### config配置项字段规范
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| key | string | 是 | 配置项唯一键，代码中通过`plugin_config.get(key)`读取 |
| label | string | 是 | 配置项显示名称，展示在前端页面 |
| type | string | 是 | 配置项类型，支持:`input`（输入框）、`password`（密码框）、`select`（下拉选择）、`switch`（开关）、`textarea`（多行文本）、`button`（按钮） |
| default | any | 否 | 配置项默认值 |
| placeholder | string | 否 | 输入框占位提示文字 |
| required | boolean | 否 | 是否必填，默认false |
| options | array | 条件必填 | 当type为select时必填，下拉选项列表，格式为`[{"label":"显示名","value":"值"}]` |
| action | string | 条件必填 | 当type为button时必填，按钮动作类型，目前支持`openUrl` |
| url | string | 条件必填 | 当action为openUrl时必填，按钮点击后跳转的地址 |

#### parameters参数项字段规范
| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 是 | 参数名，代码中通过`params.get(name)`读取 |
| type | string | 否 | 参数类型，支持string/integer/boolean/array/object，默认string |
| required | boolean | 是 | 是否必填，AI调用时会自动校验必填参数 |
| description | string | 是 | 参数说明，会注入AI上下文，帮助AI理解参数含义和生成规则 |
| default | any | 否 | 参数默认值 |

---
### 2. 功能变更配置更新 Checklist
#### ✅ 新增功能时
1.  在`plugin.json`的`parameters`数组中添加新参数的配置（name/type/required/description）
2.  如果需要用户配置全局参数，在`config`数组中添加对应的配置项
3.  在`main.py`的`run`方法中添加参数读取、校验和对应业务逻辑
4.  如果新增了依赖包，同步更新`dependencies`字段和`requirements.txt`
5.  更新本README.md中的参数说明、使用示例部分
6.  如果新增了触发场景，补充`trigger_keyword`关键词

#### ✅ 删除功能时
1.  从`plugin.json`的`parameters`数组中移除对应参数
2.  清理`main.py`中对应的参数读取、校验和业务逻辑代码
3.  如果有对应的全局配置项，从`config`数组中移除
4.  检查`requirements.txt`，移除不再使用的依赖包
5.  更新README.md，删除对应功能的说明和示例

#### ✅ 修改现有功能时
1.  如果修改了参数规则，同步更新`plugin.json`中对应参数的description
2.  同步修改`main.py`中的参数校验和业务逻辑
3.  更新README.md中的对应说明
4.  升级`version`版本号（小修改升补丁版本，功能新增升次版本，不兼容修改升主版本）

---
### 3. 上下文自动注入说明
系统启动时会自动读取所有插件的`plugin.json`信息，注入到AI上下文中，AI会自动识别:
1.  插件的`name`和`description`:理解插件功能和适用场景
2.  `trigger_keyword`:匹配用户消息中的触发词，自动决定是否调用插件
3.  `parameters`列表:理解每个参数的含义、类型、是否必填，自动从用户消息中提取参数生成调用请求
4.  `config`配置项:用户在前端配置的所有值会自动注入到`plugin_config`全局变量中，插件代码可直接读取，无需额外处理

**注意**:修改`plugin.json`后需要重启插件/重启程序才能让新的配置信息生效，注入到AI上下文。

---
### 4. 配置校验规则&常见错误
1.  `plugin_id`必须全局唯一，不能包含中文、特殊字符，只能用小写字母、数字、下划线，否则插件无法加载
2.  `version`必须符合x.y.z的数字格式，不能带v前缀等其他字符
3.  `permissions`必须根据插件实际需要申请，多余的权限不要申请，最小权限原则
4.  所有`required: true`的配置项，必须在`init`方法中做校验，缺失时给出友好提示
5.  `parameters`中的参数说明要清晰准确，AI完全依赖description理解参数用途，描述模糊会导致参数提取错误
6.  新增的自定义参数必须放在`{{extra_parameters}}`占位符之前，不要修改默认的通用参数结构，避免后续模板升级冲突
## 使用示例
### 触发指令
{{trigger_keyword}} [你的需求]

### 调用示例
```
用户:{{trigger_keyword}} 帮我生成{{example_usage}}
助手:✅ {{plugin_name}}成功，已保存到D:/AI仓库文件夹/文件生成/AI生成结果/{{plugin_id}}/xxx.mp4
在线地址:https://xxx.xxx.com/xxx.mp4
```
```
### [FILE] requirements.txt
```
requests>=2.31.0
volcengine-python-sdk[ark]>=1.0.0
{{extra_dependencies}}
```