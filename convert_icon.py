# -*- coding: utf-8 -*-
"""
PNG转ICO超清圆形图标转换脚本
优化点:抗锯齿边缘、锐化增强、适配Windows ICO格式规范，彻底解决模糊问题
"""
from PIL import Image, ImageDraw, ImageFilter
import os

# 源PNG文件路径（默认使用项目内logo.png，可按需替换为其他素材）
src_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
# 目标ICO文件路径（输出到脚本所在目录的app_icon.ico）
dst_ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")

# 读取PNG图片（用户已处理好透明背景，无需额外抠图）
img = Image.open(src_png)
img = img.convert("RGBA")
# 自动裁剪为正方形，居中截取机器人主体，避免拉伸变形
width, height = img.size
square_size = min(width, height)
left = (width - square_size) // 2
top = (height - square_size) // 2
img = img.crop((left, top, left + square_size, top + square_size))
size = square_size

# --------------------------
# 第一步:抗锯齿圆形裁剪，用户已自行抠好透明背景，无需额外背景处理
# --------------------------
# 先放大2倍做蒙版再缩小，实现抗锯齿效果
supersample = 2
mask_large = Image.new('L', (size * supersample, size * supersample), 0)
draw_large = ImageDraw.Draw(mask_large)
draw_large.ellipse((0, 0, size * supersample, size * supersample), fill=255)
# 缩小回原尺寸，自动做平滑抗锯齿
mask = mask_large.resize((size, size), Image.Resampling.LANCZOS)
# 应用圆形蒙版，圆形外完全透明，保留用户已经抠好的内部透明效果
result = Image.new('RGBA', (size, size), (0, 0, 0, 0))
result.paste(img, (0, 0), mask=mask)

# 边缘轻微羽化，避免生硬锯齿
result = result.filter(ImageFilter.SMOOTH_MORE)

# --------------------------
# 第二步:生成全分辨率图标，从大到小排序适配Windows/PyInstaller规则
# --------------------------
icon_sizes = [(1024, 1024), (512, 512), (256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
icon_images = []
for icon_size in icon_sizes:
    resized = result.resize(icon_size, Image.Resampling.LANCZOS)
    # 小尺寸图标专项优化:强化核心轮廓，减少细节避免糊成一团
    if icon_size[0] <= 32:
        # 32x32及以下:增强边缘+双重锐化，只保留男孩头部+闪电核心特征
        resized = resized.filter(ImageFilter.EDGE_ENHANCE_MORE)
        resized = resized.filter(ImageFilter.SHARPEN)
    elif icon_size[0] <= 64:
        # 64x64:普通锐化，保留适度细节
        resized = resized.filter(ImageFilter.SHARPEN)
    icon_images.append(resized)

# --------------------------
# 第三步:按Windows ICO规范保存，100%保留透明通道，适配PyInstaller打包
# --------------------------
# 强制所有分辨率使用PNG无损压缩，彻底解决高分辨率档位透明通道丢失问题
icon_images[0].save(
    dst_ico,
    format="ICO",
    sizes=icon_sizes,
    append_images=icon_images[1:],
    bits=32,  # 32位真彩色+透明通道
    png=True,  # 强制所有档位使用PNG压缩，大于256x256也保留透明通道
    optimize=False  # 禁用压缩优化，保证画质无损
)

print(f"超清圆形图标转换完成，已保存到: {dst_ico}")
print(f"包含分辨率: {', '.join([f'{s[0]}x{s[1]}' for s in icon_sizes])}")