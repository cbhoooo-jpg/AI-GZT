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