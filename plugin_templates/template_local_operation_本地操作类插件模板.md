---
template_id: local_operation
name: 本地操作类插件模板
scene: 适合本地文件处理、数据统计、格式转换、定时任务等纯本地操作类插件，无网络依赖，数据100%本地处理
default_permission: file_read,file_write
default_config:
  - key: output_dir
    label: 默认输出目录
    type: input
    default: ""
    placeholder: 转换后文件的默认保存目录，留空则和源文件同目录
    required: false
  - key: default_quality
    label: 默认图片质量
    type: input
    default: "80"
    placeholder: 图片压缩质量（1-100），仅对jpg/webp等有损格式生效
    required: false
default_params:
  - name: input_path
    description: 源文件路径或目录路径（目录则批量转换所有支持的文件）
    required: true
  - name: output_format
    description: 目标格式，支持图片格式:png/jpg/jpeg/webp/bmp/ico/gif，文档格式:docx（Word）、xlsx（Excel）
    required: true
  - name: output_dir
    description: 输出目录，默认和源文件同目录
    required: false
  - name: quality
    description: 图片压缩质量（1-100），仅对jpg/webp等有损格式生效
    required: false
---
### [FILE] main.py
```python
# -*- coding: utf-8 -*-
"""
{{plugin_name}}
{{description}}
"""
import os
import uuid
from PIL import Image

# 支持的图片格式映射
SUPPORTED_IMAGE_FORMATS = {
    'png': 'PNG',
    'jpg': 'JPEG',
    'jpeg': 'JPEG',
    'webp': 'WebP',
    'bmp': 'BMP',
    'ico': 'ICO',
    'gif': 'GIF'
}

# 各格式默认保存参数
DEFAULT_SAVE_KWARGS = {
    'JPEG': {'quality': 80, 'optimize': True},
    'WebP': {'quality': 80, 'lossless': False},
    'PNG': {'optimize': True},
    'BMP': {},
    'ICO': {'sizes': [(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)]},
    'GIF': {'optimize': True}
}
# 支持的文档格式映射
SUPPORTED_DOC_FORMATS = {
    'docx': 'Word文档',
    'xlsx': 'Excel表格'
}

# 全局插件配置
plugin_config = {}

def init(config: dict):
    """插件初始化方法，安装/启用/配置修改时自动调用"""
    global plugin_config
    plugin_config = config
    try:
        import PIL
        all_supported = list(SUPPORTED_IMAGE_FORMATS.keys()) + list(SUPPORTED_DOC_FORMATS.keys())
        return {
            'success': True,
            'message': '{{plugin_name}}初始化成功',
            'supported_formats': all_supported
        }
    except ImportError:
        return {
            'success': False,
            'message': '依赖缺失:Pillow库未安装，请执行pip install Pillow==10.3.0后重启插件'
        }

def _normalize_markdown_content(md_content):
    """轻量容错处理:自动修正MD偶发格式瑕疵，无感知处理模型输出问题"""
    lines = md_content.splitlines()
    processed_lines = []
    in_table = False
    
    for line in lines:
        stripped = line.strip()
        # 处理表格分隔线缺失问题
        if stripped.startswith('|') and stripped.endswith('|'):
            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            # 是表头行，自动补全缺失的分隔线
            if not in_table and len(cells) >= 1:
                in_table = True
                processed_lines.append(line)
                separator = '|' + '|'.join(['---'] * len(cells)) + '|'
                processed_lines.append(separator)
                continue
            # 跳过分隔线行
            if all(set(c.strip()) <= {'-', ':'} for c in cells if c.strip()):
                continue
        else:
            in_table = False
        
        # 处理标题跳级问题（自动修正为连续层级）
        if stripped.startswith('#'):
            level = len(stripped) - len(stripped.lstrip('#'))
            if level > 1:
                # 查找最近的上一级标题
                has_parent = False
                for prev_line in reversed(processed_lines[-10:]):
                    prev_stripped = prev_line.strip()
                    if prev_stripped.startswith('#' * (level-1) + ' '):
                        has_parent = True
                        break
                if not has_parent:
                    line = '## ' + stripped.lstrip('#').strip()
        
        processed_lines.append(line)
    
    return '\n'.join(processed_lines)

def _validate_output_file(file_path, expected_format, expected_table_count=None):
    """兜底校验:检查输出文件是否有效"""
    try:
        if not os.path.isfile(file_path) or os.path.getsize(file_path) == 0:
            return False
        
        if expected_format == 'docx':
            # 校验docx文件头（PK zip格式）
            with open(file_path, 'rb') as f:
                header = f.read(2)
                return header == b'PK'
        elif expected_format == 'xlsx':
            from openpyxl import load_workbook
            wb = load_workbook(file_path, read_only=True)
            if expected_table_count is not None:
                return len(wb.sheetnames) == expected_table_count
            return True
        return True
    except Exception:
        return False

def _set_docx_table_borders(docx_path):
    """强制给Word文档中所有表格添加0.5磅黑色实线边框，兼容手机端显示"""
    try:
        from docx import Document
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement

        doc = Document(docx_path)
        
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    tc = cell._tc
                    tcPr = tc.get_or_add_tcPr()
                    
                    tcBorders = tcPr.find(qn('w:tcBorders'))
                    if tcBorders is None:
                        tcBorders = OxmlElement('w:tcBorders')
                        tcPr.append(tcBorders)
                    
                    for border_name in ['top', 'left', 'bottom', 'right']:
                        border = tcBorders.find(qn(f'w:{border_name}'))
                        if border is None:
                            border = OxmlElement(f'w:{border_name}')
                            tcBorders.append(border)
                        border.set(qn('w:val'), 'single')
                        border.set(qn('w:sz'), '4')
                        border.set(qn('w:color'), '000000')
                        border.set(qn('w:space'), '0')
        
        doc.save(docx_path)
        return True
    except Exception as e:
        print(f"设置表格边框失败: {str(e)}")
        return False
def _get_unique_output_path(output_dir, base_name, target_ext):
    """生成唯一的输出路径，同名文件自动加序号后缀，不覆盖原文件"""
    counter = 1
    output_path = os.path.join(output_dir, f"{base_name}.{target_ext}")
    while os.path.exists(output_path):
        output_path = os.path.join(output_dir, f"{base_name}({counter}).{target_ext}")
        counter += 1
    return output_path

def _convert_md_to_docx(input_path, output_dir=None):
    """MD转Word文档，使用内置Pandoc绿色版默认模板"""
    try:
        import pypandoc
        from pypandoc.pandoc_download import download_pandoc
        
        # 校验源文件
        if not os.path.isfile(input_path) or not input_path.lower().endswith('.md'):
            return {'success': False, 'input_path': input_path, 'message': '源文件不是有效的Markdown文件'}
        
        # 解析输出路径
        input_dir, input_filename = os.path.split(input_path)
        base_name, _ = os.path.splitext(input_filename)
        if not output_dir:
            output_dir = plugin_config.get('output_dir', '') or input_dir
        os.makedirs(output_dir, exist_ok=True)
        output_path = _get_unique_output_path(output_dir, base_name, 'docx')
        
        # 读取并预处理MD内容
        with open(input_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        processed_content = _normalize_markdown_content(md_content)
        
        # 自动检测Pandoc，缺失则自动下载绿色版
        try:
            pypandoc.get_pandoc_path()
        except OSError:
            download_pandoc()
        
        # 转换，带1次自动重试
        for retry in range(2):
            try:
                pypandoc.convert_text(
                    processed_content,
                    'docx',
                    format='md',
                    outputfile=output_path,
                    extra_args=['--standalone']
                )
                # 校验文件有效性
                if _validate_output_file(output_path, 'docx'):
                    # 强制设置表格实线边框，兼容手机端显示
                    _set_docx_table_borders(output_path)
                    return {
                        'success': True,
                        'input_path': input_path,
                        'output_path': output_path,
                        'file_size': os.path.getsize(output_path),
                        'message': 'Word文档转换成功'
                    }
            except Exception:
                if retry == 1:
                    raise
                continue
        
        return {'success': False, 'input_path': input_path, 'message': '转换失败:生成的文件无效'}
        
    except ImportError:
        return {'success': False, 'message': '依赖缺失:pypandoc-binary未安装，请执行pip install pypandoc-binary==1.13后重试'}
    except Exception as e:
        return {'success': False, 'input_path': input_path, 'message': f'Word转换失败:{str(e)}'}
def _convert_md_to_xlsx(input_path, output_dir=None):
    """提取MD中所有表格转换为Excel，每个表格对应一个Sheet"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment
        from openpyxl.utils import get_column_letter
        
        # 校验源文件
        if not os.path.isfile(input_path) or not input_path.lower().endswith('.md'):
            return {'success': False, 'input_path': input_path, 'message': '源文件不是有效的Markdown文件'}
        
        # 解析输出路径
        input_dir, input_filename = os.path.split(input_path)
        base_name, _ = os.path.splitext(input_filename)
        if not output_dir:
            output_dir = plugin_config.get('output_dir', '') or input_dir
        os.makedirs(output_dir, exist_ok=True)
        output_path = _get_unique_output_path(output_dir, base_name, 'xlsx')
        
        # 读取并预处理MD内容
        with open(input_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        processed_content = _normalize_markdown_content(md_content)
        
        # 提取所有MD表格
        lines = processed_content.splitlines()
        tables = []
        current_table = []
        current_title = f"表格{len(tables)+1}"
        
        for line in lines:
            stripped = line.strip()
            # 检测表格前的标题作为Sheet名
            if stripped.startswith('#'):
                if current_table:
                    tables.append((current_title, current_table))
                    current_table = []
                current_title = stripped.lstrip('#').strip()[:31]  # Excel Sheet名最长31字符
                continue
            # 识别表格行
            if stripped.startswith('|') and stripped.endswith('|'):
                cells = [c.strip() for c in stripped.split('|')[1:-1]]
                # 跳过分隔线行
                if all(set(c) <= {'-', ':'} for c in cells if c):
                    continue
                current_table.append(cells)
            else:
                if current_table:
                    tables.append((current_title, current_table))
                    current_table = []
                    current_title = f"表格{len(tables)+2}"
        # 处理最后一个表格
        if current_table:
            tables.append((current_title, current_table))
        
        if not tables:
            return {'success': False, 'input_path': input_path, 'message': '未在Markdown中识别到任何有效二维表格'}
        
        # 生成Excel
        wb = Workbook()
        # 删除默认Sheet
        wb.remove(wb.active)
        
        for sheet_name, table_data in tables:
            # 处理重复Sheet名
            existing_names = wb.sheetnames
            final_sheet_name = sheet_name
            counter = 1
            while final_sheet_name in existing_names:
                final_sheet_name = f"{sheet_name[:28]}_{counter}"
                counter += 1
            
            ws = wb.create_sheet(title=final_sheet_name)
            # 写入数据
            for row_idx, row_data in enumerate(table_data, 1):
                for col_idx, cell_value in enumerate(row_data, 1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=cell_value)
                    # 表头加粗
                    if row_idx == 1:
                        cell.font = Font(bold=True)
                    cell.alignment = Alignment(vertical='center', wrap_text=True)
            
            # 自适应列宽
            for col_idx in range(1, len(table_data[0]) + 1):
                max_length = 0
                column_letter = get_column_letter(col_idx)
                for row_idx in range(1, len(table_data) + 1):
                    cell_value = str(ws.cell(row=row_idx, column=col_idx).value or '')
                    # 中文按2字符宽度计算
                    length = sum(2 if '\u4e00' <= c <= '\u9fff' else 1 for c in cell_value)
                    if length > max_length:
                        max_length = length
                ws.column_dimensions[column_letter].width = min(max_length + 2, 50)
        
        # 保存并重试验证
        for retry in range(2):
            try:
                wb.save(output_path)
                if _validate_output_file(output_path, 'xlsx', expected_table_count=len(tables)):
                    return {
                        'success': True,
                        'input_path': input_path,
                        'output_path': output_path,
                        'file_size': os.path.getsize(output_path),
                        'table_count': len(tables),
                        'message': f'Excel转换成功，共提取{len(tables)}个表格'
                    }
            except Exception:
                if retry == 1:
                    raise
                continue
        
        return {'success': False, 'input_path': input_path, 'message': '转换失败:生成的文件无效'}
        
    except ImportError:
        return {'success': False, 'message': '依赖缺失:openpyxl未安装，请执行pip install openpyxl==3.1.5后重试'}
    except Exception as e:
        return {'success': False, 'input_path': input_path, 'message': f'Excel转换失败:{str(e)}'}
def _convert_single_image(input_path, output_format, output_dir=None, quality=80):
    """转换单个图片文件"""
    try:
        # 校验源文件存在
        if not os.path.isfile(input_path):
            return {'success': False, 'input_path': input_path, 'message': '源文件不存在'}

        # 校验目标格式支持
        target_format = SUPPORTED_IMAGE_FORMATS.get(output_format.lower())
        if not target_format:
            return {'success': False, 'input_path': input_path, 'message': f'不支持的目标格式:{output_format}'}

        # 解析输出目录和文件名
        input_dir, input_filename = os.path.split(input_path)
        base_name, _ = os.path.splitext(input_filename)
        if not output_dir:
            output_dir = plugin_config.get('output_dir', '') or input_dir
        os.makedirs(output_dir, exist_ok=True)

        # 生成唯一输出路径
        output_path = _get_unique_output_path(output_dir, base_name, output_format.lower())

        # 打开图片并处理模式
        with Image.open(input_path) as img:
            # 处理透明通道:转JPG/BMP等不支持透明的格式时，添加白色背景
            if target_format in ['JPEG', 'BMP'] and img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif target_format == 'ICO' and img.mode not in ('RGBA', 'RGB'):
                img = img.convert('RGBA')
            elif target_format == 'GIF' and img.mode not in ('P', 'RGB', 'RGBA'):
                img = img.convert('P', palette=Image.ADAPTIVE)

            # 组装保存参数
            save_kwargs = DEFAULT_SAVE_KWARGS.get(target_format, {}).copy()
            if target_format in ['JPEG', 'WebP'] and 1 <= quality <= 100:
                save_kwargs['quality'] = quality

            # 保存文件
            img.save(output_path, format=target_format, **save_kwargs)

        # 获取文件大小
        file_size = os.path.getsize(output_path)
        return {
            'success': True,
            'input_path': input_path,
            'output_path': output_path,
            'file_size': file_size,
            'message': '转换成功'
        }

    except Exception as e:
        return {
            'success': False,
            'input_path': input_path,
            'message': f'转换失败:{str(e)}'
        }

def run(params: dict):
    """插件主入口"""
    input_path = params.get('input_path', '').strip()
    output_format = params.get('output_format', '').strip()
    output_dir = params.get('output_dir', '').strip()
    quality = params.get('quality', plugin_config.get('default_quality', 80))
    
    # 转换质量为整数
    try:
        quality = int(quality)
    except:
        quality = 80

    # 参数校验
    if not input_path:
        return {'success': False, 'message': '参数错误:input_path不能为空'}
    if not output_format:
        return {'success': False, 'message': '参数错误:output_format不能为空'}
    
    output_format_lower = output_format.lower()
    all_supported_formats = list(SUPPORTED_IMAGE_FORMATS.keys()) + list(SUPPORTED_DOC_FORMATS.keys())
    if output_format_lower not in all_supported_formats:
        return {'success': False, 'message': f'不支持的目标格式，当前支持:{", ".join(all_supported_formats)}'}

    # 文档格式转换分支（仅支持单MD文件）
    if output_format_lower in SUPPORTED_DOC_FORMATS:
        if not os.path.isfile(input_path):
            return {'success': False, 'message': '文档转换仅支持单个Markdown文件，不支持目录批量转换'}
        if output_format_lower == 'docx':
            result = _convert_md_to_docx(input_path, output_dir or None)
        else:
            result = _convert_md_to_xlsx(input_path, output_dir or None)
        return {
            'success': result['success'],
            'total': 1,
            'success_count': 1 if result['success'] else 0,
            'fail_count': 0 if result['success'] else 1,
            'results': [result],
            'message': result['message']
        }

    results = []
    success_count = 0
    fail_count = 0

    # 处理单文件
    if os.path.isfile(input_path):
        result = _convert_single_image(input_path, output_format, output_dir or None, quality)
        results.append(result)
        if result['success']:
            success_count += 1
        else:
            fail_count += 1

    # 处理目录批量转换
    elif os.path.isdir(input_path):
        for filename in os.listdir(input_path):
            file_path = os.path.join(input_path, filename)
            if not os.path.isfile(file_path):
                continue
            # 检查文件扩展名是否为支持的图片格式
            ext = os.path.splitext(filename)[1].lower().lstrip('.')
            if ext in SUPPORTED_IMAGE_FORMATS:
                result = _convert_single_image(file_path, output_format, output_dir or None, quality)
                results.append(result)
                if result['success']:
                    success_count += 1
                else:
                    fail_count += 1

    else:
        return {'success': False, 'message': f'输入路径不存在:{input_path}'}

    return {
        'success': True,
        'total': len(results),
        'success_count': success_count,
        'fail_count': fail_count,
        'results': results,
        'message': f'转换完成:成功{success_count}个，失败{fail_count}个'
    }

def uninstall():
    """插件卸载时调用"""
    return {'success': True, 'message': '{{plugin_name}}卸载成功'}
```
### [FILE] plugin.json
```json
{
  "plugin_id": "{{plugin_id}}",
  "name": "{{plugin_name}}",
  "description": "{{description}}",
  "version": "{{version}}",
  "author": "{{author}}",
  "trigger_words": ["{{trigger_keyword}}"],
  "entry": "main.py",
  "permissions": [
    "file_read",
    "file_write"
  ],
  "enabled": true,
  "config": [
    {
      "key": "output_dir",
      "label": "默认输出目录",
      "type": "input",
      "default": "",
      "placeholder": "转换后文件的默认保存目录，留空则和源文件同目录",
      "required": false
    },
    {
      "key": "default_quality",
      "label": "默认图片质量",
      "type": "input",
      "default": "80",
      "placeholder": "图片压缩质量（1-100），仅对jpg/webp等有损格式生效",
      "required": false
    }
  ],
  "parameters": [
    {
      "name": "input_path",
      "type": "string",
      "required": true,
      "description": "源文件路径或目录路径（目录则批量转换所有支持的文件）"
    },
    {
      "name": "output_format",
      "type": "string",
      "required": true,
      "description": "目标格式，支持图片格式:png/jpg/jpeg/webp/bmp/ico/gif，文档格式:docx（Word）、xlsx（Excel）"
    },
    {
      "name": "output_dir",
      "type": "string",
      "required": false,
      "description": "输出目录，默认和源文件同目录"
    },
    {
      "name": "quality",
      "type": "integer",
      "required": false,
      "default": 80,
      "description": "图片压缩质量（1-100），仅对jpg/webp等有损格式生效"
    },
    {{extra_parameters}}
  ],
  "dependencies": [
    "Pillow==10.3.0",
    "pypandoc-binary==1.13",
    "openpyxl==3.1.5",
    "python-docx==1.1.2"
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
| output_dir | 默认输出目录 | input | 无 | 否 |
| default_quality | 默认图片压缩质量（1-100） | input | 80 | 否 |

## 支持格式
### 图片格式
PNG ↔ JPG ↔ JPEG ↔ WebP ↔ BMP ↔ ICO ↔ GIF
### 文档格式
- Markdown转Word（docx）:自动保留排版、强制表格实线边框兼容手机端
- Markdown转Excel（xlsx）:自动提取所有表格，每个表格对应一个Sheet

## 自定义修改指南
### 1. 新增格式支持
- 在`SUPPORTED_IMAGE_FORMATS`/`SUPPORTED_DOC_FORMATS`中添加新的格式映射
- 新增对应的转换处理函数，在`run`方法中添加分支逻辑
- 同步更新`plugin.json`中参数说明和依赖列表
### 2. 参数调整说明
#### 新增/删除参数
- 先修改`plugin.json`中`parameters`数组，添加/删除对应参数配置
- 同步修改`main.py`中参数校验、参数提取部分代码
- 同步更新本README.md中使用说明
### 3. 核心业务逻辑修改说明
- 所有自定义业务逻辑请写在核心逻辑区间内
- 通用文件校验、路径处理、格式兼容逻辑无需修改，已对齐全局系统规范
- 纯本地处理，无网络依赖，所有数据均在用户本地完成处理
---
## 常见问题&注意事项
1. **转换失败提示依赖缺失**:请执行`pip install Pillow==10.3.0 pypandoc-binary==1.13 openpyxl==3.1.5 python-docx==1.1.2`安装完整依赖
2. **Word表格手机端不显示边框**:插件已自动强制添加0.5磅黑色实线边框，无需额外设置
3. **Excel转换提示未找到表格**:请检查Markdown表格格式是否正确，表头分隔线是否完整
4. **批量转换图片**:传入目录路径即可自动批量转换目录下所有支持的图片文件
5. **同名文件处理**:自动生成带序号的文件名，不会覆盖原有文件

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
| permissions | array | 是 | 插件所需权限列表，本地操作类插件默认仅需要`file_read`（文件读取）、`file_write`（文件写入），无特殊需求不要申请network权限 |
| enabled | boolean | 是 | 插件默认启用状态，固定为true |
| config | array | 否 | 插件配置项列表，会渲染到前端配置页面，用户可修改（如默认输出目录、默认质量等） |
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
| name | string | 是 | 参数名，代码中通过`params.get(name)`读取，本地操作类插件固定包含input_path/output_format等通用参数 |
| type | string | 否 | 参数类型，支持string/integer/boolean/array/object，默认string |
| required | boolean | 是 | 是否必填，AI调用时会自动校验必填参数 |
| description | string | 是 | 参数说明，会注入AI上下文，帮助AI理解参数含义和生成规则，特别是支持的格式、路径规则必须写清楚 |
| default | any | 否 | 参数默认值 |

---
### 2. 功能变更配置更新 Checklist
#### ✅ 新增功能/格式支持时
1.  在`main.py`中新增对应的处理函数（如新增格式转换函数、新增数据处理逻辑）
2.  在`run`方法的分支逻辑中添加新功能的路由判断
3.  在`plugin.json`的`parameters`中更新对应参数的description，补充新支持的格式/功能说明
4.  如果需要新增参数，在`parameters`数组中添加对应参数配置
5.  如果需要用户配置全局参数（如默认输出目录、默认质量等），在`config`数组中添加对应的配置项
6.  如果新增了依赖包，同步更新`dependencies`字段和`requirements.txt`
7.  更新本README.md中的支持格式说明、参数说明、使用示例部分
8.  如果新增了触发场景，补充`trigger_keyword`关键词

#### ✅ 删除功能时
1.  从`run`方法中移除对应功能的分支逻辑
2.  删除`main.py`中对应的处理函数
3.  更新`plugin.json`中对应参数的description，移除已删除的格式/功能说明
4.  清理不再使用的参数、配置项
5.  检查`requirements.txt`，移除不再使用的依赖包
6.  更新README.md，删除对应功能的说明和示例

#### ✅ 修改现有功能时
1.  如果修改了参数规则、支持的格式范围，同步更新`plugin.json`中对应参数的description
2.  同步修改`main.py`中对应处理函数的逻辑
3.  更新README.md中的对应说明
4.  升级`version`版本号（小修改升补丁版本，功能新增升次版本，不兼容修改升主版本）

---
### 3. 上下文自动注入说明
系统启动时会自动读取所有插件的`plugin.json`信息，注入到AI上下文中，AI会自动识别:
1.  插件的`name`和`description`:理解插件功能和适用场景，本地操作类插件会被识别为纯本地处理，不会走网络请求逻辑
2.  `trigger_keyword`:匹配用户消息中的触发词（如“转格式”“文件转换”等），自动决定是否调用插件
3.  `parameters`列表:理解每个参数的含义、类型、是否必填，自动从用户消息中提取文件路径、目标格式等参数生成调用请求
4.  `config`配置项:用户在前端配置的所有值会自动注入到`plugin_config`全局变量中，插件代码可直接读取，无需额外处理

**注意**:修改`plugin.json`后需要重启插件/重启程序才能让新的配置信息生效，注入到AI上下文。本地操作类插件所有数据均在用户本地处理，不会上传任何文件到云端，符合数据安全要求。

---
### 4. 配置校验规则&常见错误
1.  `plugin_id`必须全局唯一，不能包含中文、特殊字符，只能用小写字母、数字、下划线，否则插件无法加载
2.  `version`必须符合x.y.z的数字格式，不能带v前缀等其他字符
3.  `permissions`遵循最小权限原则，纯本地操作插件禁止申请network权限，仅申请实际需要的文件读写权限即可
4.  所有`required: true`的配置项，必须在`init`方法中做校验，缺失时给出友好提示
5.  `parameters`中的参数说明必须清晰列出支持的格式、路径规则，AI完全依赖description理解参数用途，描述模糊会导致参数提取错误
6.  新增的自定义参数必须放在`{{extra_parameters}}`占位符之前，不要修改默认的通用参数结构，避免后续模板升级冲突
7.  所有文件操作必须做路径校验，禁止路径穿越漏洞，同名文件必须自动加序号不覆盖原文件，符合系统全局文件处理规范
8.  处理大文件时必须做异常捕获和进度提示，避免插件崩溃导致工作台无响应
## 使用示例
### 触发指令
{{trigger_keyword}} [文件路径] 转 [目标格式]

### 调用示例
```
用户:{{trigger_keyword}} 把测试文档.md转成Word
助手:✅ {{plugin_name}}成功，已保存到D:/xxx/测试文档.docx
```
```
### [FILE] requirements.txt
```
Pillow==10.3.0
pypandoc-binary==1.13
openpyxl==3.1.5
python-docx==1.1.2
{{extra_dependencies}}
```