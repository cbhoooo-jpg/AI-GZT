# 文件格式转换插件

## 功能说明
本地文件格式转换工具，分三期迭代实现常见格式互转，所有转换均在本地完成，不上传任何文件。

### 第一期（已实现）:图片格式互转
- 支持格式:PNG、JPG/JPEG、WebP、BMP、ICO、GIF
- 支持单文件转换和目录批量转换
- 支持自定义压缩质量（1-100）
- 自动处理透明通道（PNG转JPG自动添加白色背景）
- 同名文件自动加序号后缀，不覆盖原文件
- 零新增依赖，复用主项目Pillow库

### 第二期（规划中）:文档格式转换
- TXT/Markdown ↔ DOCX互转
- 图片转PDF
- 可选依赖自动检测

### 第三期（规划中）:表格格式转换
- CSV ↔ XLSX互转
- XLSX转JSON/CSV

## 参数说明
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| input_path | string | 是 | 源文件路径或目录路径 |
| output_format | string | 是 | 目标格式，如png/jpg/webp等 |
| output_dir | string | 否 | 输出目录，默认和源文件同目录 |
| quality | integer | 否 | 图片压缩质量，默认80，范围1-100 |

## 使用示例
### 单文件转换
将PNG图片转为JPG:
```
input_path: "C:/Pictures/test.png"
output_format: "jpg"
quality: 90
```

### 批量转换
将目录下所有图片转为WebP:
```
input_path: "C:/Pictures/batch/"
output_format: "webp"
output_dir: "C:/Pictures/converted/"
```

## 注意事项
1.  转换前会自动保留原文件，不会修改或删除源文件
2.  批量转换时单个文件失败不会中断整体任务，会在结果中返回失败原因
3.  大文件转换可能需要几秒时间，请耐心等待
4.  ICO格式转换会自动生成多尺寸图标，适配不同场景需求