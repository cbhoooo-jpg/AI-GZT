# -*- coding: utf-8 -*-
"""
AI图片生成插件
作者:官方
版本:1.0.0
说明:调用云端AI模型生成高清图片，支持DALL-E 3/Stable Diffusion 3
"""
import os
import json
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# 全局插件配置（自动注入）
plugin_config = {}

def _default_save_dir() -> str:
    """跨平台默认保存目录:当前用户文档目录下的AI仓库文件夹/文件生成/图片生成"""
    return os.path.join(os.path.expanduser("~"), "Documents", "AI仓库文件夹", "文件生成", "图片生成")

def init(config: dict):
    """插件初始化方法，安装/启用/配置修改时自动调用"""
    global plugin_config
    plugin_config = config
    
    # 自动创建保存目录
    save_path = plugin_config.get("save_path", _default_save_dir()).strip()
    os.makedirs(save_path, exist_ok=True)
    return True

def run(params: dict):
    """
    插件主方法，生成图片入口
    :param params: 参数字典，包含prompt/size/style
    :return: 执行结果
    """
    # 校验配置
    ark_api_key = plugin_config.get("ark_api_key", "").strip()
    ark_api_url = plugin_config.get("ark_api_url", "").strip()
    ark_model_id = plugin_config.get("ark_model_id", "").strip()
    if not ark_api_key:
        return "❌ 请先在插件配置中填写火山方舟API密钥，配置完成后即可使用图片生成功能"
    if not ark_api_url or not ark_model_id:
        return "❌ 请检查插件配置中API接口地址和模型ID是否填写完整"
    
    # 获取参数，没有则用默认配置
    # ========== 调试日志：全量原始参数接收（100%定位参数解析问题） ==========
    print(f"[生图插件DEBUG] 入口原始params | 类型:{type(params)} | 所有键值对:")
    for k, v in params.items():
        val_preview = repr(v)[:200] + ('...' if len(repr(v))>200 else '')
        print(f"  - {k}: {val_preview} | 类型:{type(v)}")
    # ==================================================================
    prompt = params.get("prompt", "").strip()
    if not prompt:
        return "❌ 请输入图片生成的提示词，描述越详细生成效果越好哦~"
    
    # 尺寸预设：100%对齐豆包Seedream官方尺寸对照表，覆盖所有官方支持的档位和比例
    # 无需用户手动填写宽高像素值，仅需选择档位和比例即可，所有尺寸总像素≥400万，完全符合接口要求
    SIZE_PRESETS = {
        "3k": {
            "1:1": "3072x3072",
            "4:3": "3456x2592",
            "3:4": "2592x3456",
            "16:9": "4096x2304",
            "9:16": "2304x4096",
            "2:3": "2496x3744",
            "21:9": "4704x2016"
        },
        "4k": {
            "1:1": "4096x4096",
            "3:4": "3520x4704",
            "4:3": "4704x3520",
            "16:9": "5504x3040",
            "9:16": "3040x5504",
            "2:3": "3328x4992",
            "3:2": "4992x3328",
            "21:9": "6240x2656"
        }
    }
    # 参考图默认权重：0.7，值越高越贴近参考图（0-1之间）
    DEFAULT_REF_STRENGTH = 0.7
    size_level = params.get("size_level", "3k").strip().lower()
    size_ratio = params.get("size_ratio", "16:9").strip()
    # 非法档位/比例自动fallback到默认3K 16:9
    if size_level not in SIZE_PRESETS:
        size_level = "3k"
    if size_ratio not in SIZE_PRESETS[size_level]:
        size_ratio = "16:9"
    size = SIZE_PRESETS[size_level][size_ratio]
    style = params.get("style", "").strip()
    # 新增批量生成和卡片类型参数，增加空值容错
    count = params.get("count", 1)
    try:
        count = min(int(count), 4)
    except (ValueError, TypeError):
        count = 1
    card_type = params.get("card_type", "").strip()
    card_mode = params.get("card_mode", "normal").strip()
    # 合一模式强制固定3K 1:1尺寸，符合模型最小像素要求
    if card_mode == "unified" and card_type:
        size = SIZE_PRESETS["3k"]["1:1"]
        count = 4
    introduction = params.get("introduction", "").strip()
    angles = []
    # 内置统一前置质量提示词（默认生效，全品类覆盖，提升出图合格率，无开关）
    QUALITY_PREFIX = "你是高级图形设计师，适配任意风格:人物神态自然，物体材质还原准确；创作需遵循通用规则:1.人物/人形:比例正常，五指无畸形，五官对称自然，衣物穿着合理适配人物风格，身体动作符合力学设计，手上握持武器/工具握持时手指紧扣、指节清晰发力，无悬空半握、手指穿透等问题；2.动物:肢体数量符合物种特征，比例协调无畸形，毛发羽毛结构自然；3.机甲/机械:结构连接合理无悬空穿模，人员座舱符合工程原理设计合理，武器装备握持挂载符合常识，零件比例协调无多余结构；4.场景:透视正确，空间逻辑合理，元素比例协调，光影统一；5.食物:食材形态自然无融合变形，质感真实色泽自然，餐具无穿模；6.建筑:结构稳定符合力学逻辑，风格统一，细节比例正确。"
    # 内置统一负向提示词（默认生效，大幅降低常见错误出现概率）
    NEGATIVE_PROMPT = " "
    base_prompt = f"{QUALITY_PREFIX} {prompt}"
    # 参考图处理:支持本地路径/Base64/URL/JSON数组字符串，优先本地图片转Base64上传给模型，兼容URL格式
    reference_images = params.get("images", [])
    # ========== 调试日志：原始参数接收 ==========
    print(f"[生图插件DEBUG] 原始传入images参数 | 类型:{type(reference_images)} | 值:{repr(reference_images)[:500]}")
    # 兼容字符串格式的数组：支持标准JSON数组（双引号"path"格式）、Python字面量列表（单引号'path'格式，适配str(list)传参场景）
    if isinstance(reference_images, str):
        ref_str = reference_images.strip()
        # 第一步：优先尝试解析标准JSON格式
        try:
            import json as _json
            parsed = _json.loads(ref_str)
            if isinstance(parsed, list):
                reference_images = parsed
        except (_json.JSONDecodeError, ValueError):
            # JSON解析失败，第二步：尝试解析Python原生字面量格式（兼容单引号列表）
            try:
                import ast
                parsed = ast.literal_eval(ref_str)
                if isinstance(parsed, list):
                    reference_images = parsed
            except (ValueError, SyntaxError):
                # 两种格式都解析失败，判定为单个路径字符串，后续按单元素列表处理
                pass
    if not isinstance(reference_images, list):
        reference_images = [reference_images] if reference_images else []
    processed_ref_images = []
    import base64
    for img_item in reference_images:
        # 兼容三种传参格式：纯字符串路径/URL、附件字典对象、JSON字符串
        img_path = ""
        if isinstance(img_item, dict):
            # 字典类型附件：优先取local_path，其次取url
            img_path = img_item.get("local_path", "") or img_item.get("url", "")
        elif isinstance(img_item, str):
            img_path = img_item.strip()
        if not img_path:
            continue
        if img_path.startswith(("http://", "https://", "data:image/")):
            # URL或已编码Base64直接保留
            processed_ref_images.append(img_path)
        elif os.path.exists(img_path) and os.path.isfile(img_path):
            # 本地文件自动转Base64编码
            try:
                with open(img_path, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode("utf-8")
                    ext = os.path.splitext(img_path)[1].lower().lstrip(".")
                    mime_type = "png" if ext == "png" else "jpeg"
                    processed_ref_images.append(f"data:image/{mime_type};base64,{img_b64}")
            except Exception as e:
                # 单张图读取失败跳过，不中断主流程，打印错误方便排查
                print(f"参考图读取失败:{img_path}, 错误:{str(e)}")
                continue
    # 官方接口最多支持14张参考图，自动截断
    processed_ref_images = processed_ref_images[:14]
    # ========== 调试日志：参考图处理完成 ==========
    print(f"[生图插件DEBUG] 参考图处理完成 | 有效参考图数量:{len(processed_ref_images)} | 前2张预览:{[img[:100]+'...' if len(img)>100 else img for img in processed_ref_images[:2]]}")
    
    # 多角度卡片提示词自动补全，卡片类型自动强制count=4
    if card_type == "人物":
        count = 4
        angles = ["正面角度", "侧面角度", "45度斜侧角度", "局部特写角度"]
    elif card_type == "场景":
        count = 4
        angles = ["全景视角", "中景视角", "近景视角", "特写视角"]
    elif card_type in ["动物", "物体"]:
        count = 4
        angles = ["正面角度", "侧面角度", "顶部角度", "局部特写角度"]
    
    try:
        # 火山方舟豆包Seeddream-5.0-lite生图逻辑
        # 拆分尺寸，异常时自动fallback到3K 16:9默认值，符合接口最低像素要求
        try:
            width, height = map(int, size.split("x"))
        except:
            size = SIZE_PRESETS["3k"]["16:9"]
            width, height = 4096, 2304
        
        # 火山方舟接口兼容OpenAI格式，无需复杂签名
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ark_api_key}"
        }
        image_list = []
        reference_image = None
        for i in range(count):
            # 拼接当前轮次的提示词
            current_prompt = base_prompt
            if card_type:
                current_prompt += f"，{angles[i]}，统一风格，高清无水印，适合图生视频使用"
            if style:
                current_prompt = f"{current_prompt}，风格:{style}"
            
            # 构造当前请求的payload，移除无效参数，完全符合豆包Seedream接口规范
            payload = {
                "model": ark_model_id,
                "prompt": current_prompt,
                "negative_prompt": NEGATIVE_PROMPT,
                "size": size,
                "response_format": "url"
            }
            # 尺寸合法性兜底校验：确保总像素≥368万，符合接口最低要求
            w, h = map(int, size.split("x"))
            if w * h < 3680000:
                # 不符合要求自动fallback到3K 16:9
                size = SIZE_PRESETS["3k"]["16:9"]
                payload["size"] = size
            # 参考图逻辑：优先使用用户传入的参考图（本地转Base64/URL兼容），最多14张
            current_ref_images = processed_ref_images.copy()
            # 合一模式下第2张开始追加第一张生成的图作为风格参考，保证组图风格统一
            if card_mode == "unified" and i > 0 and reference_image is not None:
                current_ref_images.append(reference_image)
            if current_ref_images:
                # 豆包Seedream接口强制使用image字段传参考图，单张传字符串、多张传数组，完全符合官方规范
                ref_images = current_ref_images[:14]
                payload["image"] = ref_images[0] if len(ref_images) == 1 else ref_images
                payload["strength"] = DEFAULT_REF_STRENGTH
            
            try:
                # ========== 调试日志：发送给接口的请求参数 ==========
                has_image = "image" in payload
                image_info = "无"
                if has_image:
                    img_val = payload["image"]
                    if isinstance(img_val, str):
                        image_info = f"字符串类型，长度:{len(img_val)}，前缀:{img_val[:50]}..."
                    elif isinstance(img_val, list):
                        image_info = f"数组类型，共{len(img_val)}张，第一张长度:{len(img_val[0]) if img_val else 0}"
                print(f"[生图插件DEBUG] 第{i+1}张请求参数 | 模型:{payload['model']} | 尺寸:{payload['size']} | 是否携带参考图:{has_image} | 参考图信息:{image_info} | 提示词前50字:{payload['prompt'][:50]}...")
                
                response = requests.post(ark_api_url, 
                                        headers=headers, json=payload, timeout=60)
                # ========== 调试日志：接口返回结果 ==========
                print(f"[生图插件DEBUG] 第{i+1}张接口响应 | 状态码:{response.status_code} | 返回内容前500字:{response.text[:500]}...")
                response.raise_for_status()
                result = response.json()
                img_url = result["data"][0]["url"]
                if i == 0:
                    reference_image = img_url
                image_list.extend(result["data"])
            except Exception as e:
                error_detail = response.text if 'response' in locals() else str(e)
                return f"❌ 第{i+1}张图片生成失败:{str(e)}\n🔍 详细错误信息:{error_detail}\n💡 请检查API密钥是否正确、模型ID是否为带ep前缀的完整值、提示词是否包含违规内容"
        
        # 所有图片生成完成后统一保存和返回
        # 自动保存图片到配置的路径（双保险:生成前再校验路径，不存在自动创建）
        save_result = ""
        image_urls = []
        save_paths = []
        save_path = plugin_config.get("save_path", _default_save_dir()).strip()
        os.makedirs(save_path, exist_ok=True)
        base_time = datetime.now().strftime('%Y%m%d%H%M%S')
        
        for idx, item in enumerate(image_list):
            image_url = item["url"]
            image_urls.append(image_url)
            file_name = f"{base_time}_{idx}.png"
            full_path = os.path.join(save_path, file_name)
            try:
                img_response = requests.get(image_url, timeout=30)
                with open(full_path, "wb") as f:
                    f.write(img_response.content)
                save_paths.append(full_path)
                save_result += f"\n✅ 图片{idx+1}已自动保存到:{full_path}"
            except Exception as save_err:
                # 保存失败兜底:不影响主流程，优先返回在线链接
                save_result += f"\n⚠️ 图片{idx+1}本地保存失败（原因:{str(save_err)}），你可以直接点击上方图片链接下载哦"
        # 合一卡片模式合成逻辑
        if card_mode == "unified" and card_type:
            # 创建1920x2600空白画布，底部新增440px简介区域
            canvas = Image.new("RGB", (1920, 2600), (0, 0, 0))
            draw = ImageDraw.Draw(canvas)
            # 加载字体
            try:
                font = ImageFont.truetype("simhei.ttf", 32)
                title_font = ImageFont.truetype("simhei.ttf", 48)
            except:
                font = ImageFont.load_default(size=32)
                title_font = ImageFont.load_default(size=48)
            
            # 左上角添加标识
            draw.text((50, 30), "AI助手影视素材卡", font=title_font, fill=(255, 255, 255))
            
            # 2x2排列4张素材图
            positions = [(50, 120), (970, 120), (50, 1140), (970, 1140)]
            for idx, path in enumerate(save_paths[:4]):
                img = Image.open(path).resize((900, 900))
                canvas.paste(img, positions[idx])
                # 标注角度名称
                draw.text((positions[idx][0]+10, positions[idx][1]+910), angles[idx], font=font, fill=(255,255,255))
            # 底部简介区域绘制
            # 绘制顶部白色分隔线
            draw.line([(50, 2060), (1870, 2060)], fill=(255,255,255), width=1)
            # 绘制10%透明度浅灰色背景
            overlay = Image.new('RGBA', canvas.size, (0,0,0,0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle([(50, 2060), (1870, 2550)], fill=(255,255,255,25))
            canvas = Image.alpha_composite(canvas.convert('RGBA'), overlay).convert('RGB')
            draw = ImageDraw.Draw(canvas)
            
            # 绘制简介标题
            draw.text((70, 2080), "📝 素材简介", font=title_font, fill=(255,255,255))
            
            # 简介内容逻辑:用户传入>自动生成>默认提示
            if not introduction:
                introduction = f"本素材为{card_type}类专业影视素材，核心主题:{base_prompt.split('，')[0]}，全角度风格统一，高清无水印，可直接用于影视、游戏、动画、广告等商用制作场景。"
            # 自动换行处理，最多6行超出加省略号
            lines = []
            current_line = ""
            for char in introduction:
                if font.getlength(current_line + char) < 1700:
                    current_line += char
                else:
                    lines.append(current_line)
                    current_line = char
                    if len(lines) >= 6:
                        current_line += "..."
                        break
            lines.append(current_line)
            # 绘制简介内容
            y_offset = 2140
            for line in lines[:6]:
                draw.text((70, y_offset), line, font=font, fill=(255,255,255))
                y_offset += 48
            
            # 右下角绘制生成时间
            draw.text((1450, 2500), f"生成时间:{base_time}", font=font, fill=(200,200,200))
            
            # 保存合成卡片
            main_subject = base_prompt.split("，")[0].replace(" ", "")
            card_save_path = os.path.join(save_path, f"{main_subject}-{card_type}卡片介绍.png")
            canvas.save(card_save_path)
            # 生成属性TXT
            txt_save_path = os.path.join(save_path, f"{main_subject}-{card_type}卡片介绍.txt")
            with open(txt_save_path, "w", encoding="utf-8") as f:
                f.write(f"【卡片信息】\n名称:{main_subject}-{card_type}卡片介绍\n类型:{card_type}\n生成时间:{base_time}\n简介:{introduction}\n\n【生成提示词】\n{base_prompt}\n\n【素材地址】\n"+"\n".join([item["url"] for item in image_list]))
            # 替换返回结果为合成卡片
            image_list = [{"url": f"本地路径:{card_save_path}"}]
            save_paths = [card_save_path]
            save_result = f"\n✅ 合一卡片已自动保存到:{card_save_path}\n✅ 属性文件已自动保存到:{txt_save_path}"
            # 新增:自动上传合一卡片到对象存储，获取公网URL（容错处理，上传失败不影响本地生成）
            try:
                upload_api_url = "http://127.0.0.1:8000/api/v1/common/upload"
                # 上传卡片图片
                img_upload_res = requests.post(upload_api_url, data={
                    "local_path": card_save_path,
                    "file_type": "image",
                    "override": False
                }, timeout=10)
                if img_upload_res.status_code == 200:
                    img_data = img_upload_res.json()["data"]
                    public_img_url = img_data["public_url"]
                    # 追加公网URL到属性文件
                    with open(txt_save_path, "a", encoding="utf-8") as f:
                        f.write(f"\n\n【公网访问地址】\n卡片URL:{public_img_url}")
                    save_result += f"\n✅ 合一卡片已自动上传，公网URL:{public_img_url}"
                # 上传属性TXT文件
                txt_upload_res = requests.post(upload_api_url, data={
                    "local_path": txt_save_path,
                    "file_type": "other",
                    "override": False
                }, timeout=10)
                if txt_upload_res.status_code == 200:
                    txt_data = txt_upload_res.json()["data"]
                    public_txt_url = txt_data["public_url"]
                    with open(txt_save_path, "a", encoding="utf-8") as f:
                        f.write(f"\n属性文件URL:{public_txt_url}")
            except Exception as upload_err:
                # 上传失败兜底，不影响原有功能
                save_result += f"\n⚠️ 自动上传跳过（原因:{str(upload_err)}），已成功生成本地卡片，后续可手动上传"
        
        # 拼接返回结果
        return_str = f"🎉 豆包Seeddream图片生成成功！共生成{len(image_list)}张\n🔍 提示词:{prompt}"
        for idx, url in enumerate(image_urls):
            return_str += f"\n📸 图片{idx+1}地址:{url}"
        return_str += save_result
        return return_str
    
    except Exception as e:
        return f"❌ 图片生成失败:{str(e)}\n💡 请检查API密钥是否正确、网络是否正常、提示词是否包含违规内容"

def uninstall():
    """插件卸载时自动调用，可选清理资源"""
    # 这里可以选择是否删除生成的图片，默认不删除
    return True