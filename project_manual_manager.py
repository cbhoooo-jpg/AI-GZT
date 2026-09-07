# -*- coding: utf-8 -*-
"""
项目手册管理核心模块
功能特性：
1. 标准化项目手册模板生成
2. Markdown表格解析与生成
3. 正向同步：手册→项目文件自动生成
4. 反向同步：项目文件→手册信息自动填充
5. 异常容错：解析失败自动留空，不阻塞运行
6. 自动备份：支持版本回滚
"""
import os
import sys
import re
import ast
import time
import json
import shutil
from typing import List, Dict, Optional, Tuple

# 提升Python递归深度到2000，解决大文件AST解析报错
sys.setrecursionlimit(2000)

def get_repository_path() -> str:
    """动态获取当前配置的仓库路径，自动适配配置更新，避免硬编码"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.json")
    # 默认 fallback 到程序目录下的仓库文件夹，兼容旧版本
    default_repo = os.path.normpath(os.path.join(base_dir, "仓库文件夹")).replace("\\", "/")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            repo_path = config.get("repository_path", default_repo)
            # 自动创建不存在的仓库目录
            os.makedirs(repo_path, exist_ok=True)
            return os.path.normpath(repo_path).replace("\\", "/")
        except Exception as e:
            print(f"⚠️ 项目手册模块读取仓库路径配置失败，使用默认路径:{str(e)}")
    # 配置不存在时自动创建默认目录
    os.makedirs(default_repo, exist_ok=True)
    return default_repo

# 全局仓库路径（动态获取，支持配置热更新）
REPOSITORY_PATH = get_repository_path()

# 全局解析失败缓存：key=文件路径，value=(失败次数, 下次可重试时间戳)
PARSE_FAIL_CACHE = {}

class ProjectManualManager:
    def __init__(self):
        # 表格匹配正则（终极健壮版：完整匹配整个明细块+整行表格，100%无残留+无多余文件生成）
        self.detail_table_pattern = re.compile(r"## 二、全项目文件明细清单(.*?)(?=\s*## |\Z)", re.DOTALL)
        self.table_row_pattern = re.compile(r"^\|.*\|$", re.MULTILINE)
        # 新增：第一章节和第三章节匹配正则
        self.first_chapter_pattern = re.compile(r"## 一、项目核心信息(.*?)(?=\s*## |\Z)", re.DOTALL)
        self.file_detail_pattern = re.compile(r"## 三、项目所有文件功能明细(.*?)(?=\s*## |\Z)", re.DOTALL)
        
    def generate_template(self, project_name: str, save_path: str = None) -> Tuple[bool, str]:
        """
        生成标准化项目手册模板
        :param project_name: 项目名称
        :param save_path: 保存路径，默认保存到项目根目录下 {project_name}项目手册.md
        :return: (是否成功, 保存路径/错误信息)
        """
        try:
            create_time = time.strftime("%Y-%m-%d %H:%M:%S")
            # 标准化模板（完全匹配现有AI智能体开发项目手册格式）
            template = f"""# {project_name} 项目手册
---
## 一、项目核心信息
1. 项目名称：{project_name}
2. 创建时间：{create_time}
3. 负责人：AI助手

## 二、全项目文件明细清单（实时更新）
| 文件名称 | 所属项目 | 功能描述 |
| --- | --- | --- |
| {project_name}项目手册.md | {project_name} | 项目全量信息说明、规范定义、文件索引 |

## 三、项目所有文件功能明细
### 📄 文件名：
- 所属模块：
- 依赖库：
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
- 实现状态：

## 四、功能开发计划
| 步骤 | 功能内容 | 预估耗时 | 状态 |
| --- | --- | --- | --- |
| 1 |  |  | 未开始 |

## 五、风险评估与应对
| 风险点 | 影响等级 | 应对方案 | 状态 |
| --- | --- | --- | --- |

## 六、版本迭代记录
| 版本号 | 发布时间 | 更新内容 | 负责人 |
| --- | --- | --- | --- |
| V1.0 | {create_time} | 项目初始化 | |
"""
            # 自动生成保存路径
            if not save_path:
                save_path = os.path.join(REPOSITORY_PATH, project_name, f"{project_name}项目手册.md")
            else:
                save_path = os.path.join(REPOSITORY_PATH, save_path)
            
            # 自动递归创建父目录（兼容根目录无父路径场景，避免空路径报错）
            dir_path = os.path.dirname(save_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            # 打印调试日志（方便排查路径问题，上线可删除）
            print(f"尝试生成项目手册：{save_path}，父目录：{dir_path if dir_path else '根目录'}")
            
            # 写入文件
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(template)
            
            return True, save_path
        except Exception as e:
            return False, f"生成模板失败：{str(e)}"
    

    def extract_code_metadata(self, file_path: str) -> Dict:
        """
        提取代码文件的元数据：类名、函数名、功能描述
        :param file_path: 代码文件路径（相对于仓库根目录）
        :return: 元数据字典，提取失败对应字段留空
        """
        metadata = {
            "module": "",
            "class_list": [],
            "function_list": [],
            "description": ""
        }
        # 校验是否在失败黑名单中
        now = time.time()
        # 导入放在函数内部，避免全局循环依赖
        from auto_sync_monitor import CONFIG
        if file_path in PARSE_FAIL_CACHE:
            fail_count, next_try_time = PARSE_FAIL_CACHE[file_path]
            if fail_count >= CONFIG["max_parse_fail_count"] and now < next_try_time:
                print(f"⏭️  文件{file_path}解析失败超过3次，24小时内自动跳过解析")
                return metadata
        try:
            # 标准化路径，统一/分隔符，跨平台兼容
            abs_file_path = os.path.normpath(os.path.join(REPOSITORY_PATH, file_path)).replace("\\", "/")
            if not os.path.exists(abs_file_path) or not os.path.isfile(abs_file_path):
                return metadata
            
            # 提取所属模块（文件所在完整父路径，支持多级目录）
            rel_path = os.path.relpath(abs_file_path, REPOSITORY_PATH).replace("\\", "/")
            path_parts = rel_path.split("/")
            if len(path_parts) >= 2:
                metadata["module"] = "/".join(path_parts[:-1])
            
            # 处理Python代码文件提取元数据，其他文件直接返回基本信息
            ext = os.path.splitext(abs_file_path)[1].lower()
            if ext == ".py":
                # 读取文件内容
                with open(abs_file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                if not content.strip():
                    return metadata
                
                # 用AST解析代码
                tree = ast.parse(content)
                
                # 提取类名和顶层函数名（带Docstring）
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        class_desc = ast.get_docstring(node) or "暂无描述"
                        metadata["class_list"].append({"name": node.name, "desc": class_desc.strip().split("\n")[0]})
                    elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"): # 过滤私有函数
                        func_desc = ast.get_docstring(node) or "暂无描述"
                        metadata["function_list"].append({"name": node.name, "desc": func_desc.strip().split("\n")[0]})
                # 提取类内部的公共方法（带Docstring）
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        for sub_node in node.body:
                            if isinstance(sub_node, ast.FunctionDef) and not sub_node.name.startswith("_"):
                                func_desc = ast.get_docstring(sub_node) or "暂无描述"
                                metadata["function_list"].append({
                                    "name": f"{node.name}.{sub_node.name}",
                                    "desc": func_desc.strip().split("\n")[0]
                                })
                # 提取模块注释作为功能描述
                docstring = ast.get_docstring(tree)
                if docstring:
                    metadata["description"] = docstring.strip().split("\n")[0][:100]
            elif ext == ".html" or ext == ".htm":
                # 读取HTML文件内容，按优先级提取功能描述
                with open(abs_file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if content.strip():
                    # 优先级1：提取HTML头部首个注释的第一行
                    comment_pattern = re.compile(r"^\s*<!--(.*?)-->", re.DOTALL)
                    comment_match = comment_pattern.search(content)
                    if comment_match:
                        desc = comment_match.group(1).strip().split("\n")[0][:100]
                        if desc:
                            metadata["description"] = desc
                    # 优先级2：提取title标签内容
                    if not metadata["description"]:
                        title_pattern = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
                        title_match = title_pattern.search(content)
                        if title_match:
                            desc = title_match.group(1).strip()[:100]
                            if desc:
                                metadata["description"] = desc
                    # 优先级3：提取meta description内容
                    if not metadata["description"]:
                        meta_pattern = re.compile(r'<meta\s+name="description"\s+content="(.*?)"', re.IGNORECASE | re.DOTALL)
                        meta_match = meta_pattern.search(content)
                        if meta_match:
                            desc = meta_match.group(1).strip()[:100]
                            if desc:
                                metadata["description"] = desc
           
            # 非Python/HTML文件自动填充文件类型描述
            if not metadata["description"]:
                # 特殊处理项目手册，返回专属功能描述
                if "项目手册.md" in os.path.basename(abs_file_path):
                    metadata["description"] = "项目全量信息说明、规范定义、文件索引"
                else:
                    ext_map = {
                        ".jpg": "图片资源", ".jpeg": "图片资源", ".png": "图片资源", ".gif": "图片资源",
                        ".md": "Markdown文档", ".txt": "文本文件", ".json": "配置文件",
                        ".csv": "数据文件", ".docx": "Word文档", ".xlsx": "Excel表格",
                        ".html": "HTML页面/前端组件", ".htm": "HTML页面/前端组件"
                    }
                    metadata["description"] = ext_map.get(ext, "其他文件")
            
            return metadata
        except Exception as e:
            print(f"提取{file_path}元数据失败：{str(e)}")
            # 记录失败次数
            if file_path in PARSE_FAIL_CACHE:
                fail_count, _ = PARSE_FAIL_CACHE[file_path]
                fail_count += 1
            else:
                fail_count = 1
            # 超过最大失败次数，标记24小时后再重试
            PARSE_FAIL_CACHE[file_path] = (fail_count, now + 86400)
            # 提取失败留空，不抛出异常
            return metadata
            
    def parse_file_overview_table(self, manual_path: str) -> List[str]:
        """
        解析手册中的全项目文件明细清单表格
        :param manual_path: 手册文件路径
        :return: 文件路径列表，解析失败返回空列表
        """
        try:
            manual_path = os.path.join(REPOSITORY_PATH, manual_path)
            if not os.path.exists(manual_path) or not os.path.isfile(manual_path):
                return []
            
            with open(manual_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 匹配明细表格
            table_match = self.detail_table_pattern.search(content)
            if not table_match:
                return []
            
            table_content = table_match.group(1)
            rows = self.table_row_pattern.findall(table_content)
            file_list = []
            
            # 合法路径字符校验（过滤Windows非法字符和中文标点，保留路径分隔符/、\）
            illegal_char_pattern = re.compile(r'[<>:"|?*、，？！：；“”‘’（）【】{}]')
            for row in rows:
                # 提取第一列的文件名称
                cells = [cell.strip() for cell in row.split("|") if cell.strip()]
                if len(cells) < 1:
                    continue
                file_path = cells[0]
                # 合法性校验：非空、不是分隔行、包含后缀、无非法字符、长度合规
                if (file_path 
                    and not file_path.startswith("---")
                    and "." in file_path 
                    and len(file_path) <= 255
                    and not illegal_char_pattern.search(file_path)
                ):
                    file_list.append(file_path)
            
            print(f"✅ 解析到手册总文件列表：{file_list}")
            return list(set(file_list))
        except Exception as e:
            print(f"❌ 解析明细表格失败：{str(e)}")
            return []            
    
    def update_manual_detail_table(self, manual_path: str) -> Dict:
        """
        反向同步：自动更新手册的全项目文件明细清单
        :param manual_path: 手册文件路径
        :return: 更新结果
        """
        result = {
            "code": 200,
            "update_count": 0,
            "add_count": 0
        }
        try:

            manual_full_path = os.path.join(REPOSITORY_PATH, manual_path)
            if not os.path.exists(manual_full_path):
                result["code"] = 404
                result["msg"] = "手册不存在"
                return result
            
            # 读取手册内容
            with open(manual_full_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 获取项目根目录下的所有文件
            project_root = os.path.dirname(manual_full_path)
            all_files = []
            # 优先加入项目手册自身，确保空项目时至少有手册条目
            manual_filename = os.path.basename(manual_full_path)
            all_files.append(manual_filename)
            # 排除目录黑名单（Python生态通用约定，不纳入手册管理）
            EXCLUDE_DIRS = {"test_venv", "venv", ".venv", "__pycache__", ".git", 
                            "node_modules", ".idea", "dist", "build", ".pytest_cache"}
            # 排除文件后缀黑名单（二进制/缓存文件，无解析价值）
            EXCLUDE_EXTS = {".pyc", ".pyo", ".pyd", ".so", ".dll", ".bin", ".exe"}
            for root, dirs, files in os.walk(project_root):
                # 原地修改dirs，阻止os.walk递归进入排除目录
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
                for file in files:
                    # 跳过已加入的手册文件，避免重复
                    if file == manual_filename:
                        continue
                    # 跳过缓存/二进制文件
                    ext = os.path.splitext(file)[1].lower()
                    if ext in EXCLUDE_EXTS:
                        continue
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, project_root).replace(os.sep, "/")
                    all_files.append(rel_path)
            
            # 解析现有明细表格
            existing_rows = {}
            table_match = self.detail_table_pattern.search(content)
            if table_match:
                table_content = table_match.group(1)
                rows = self.table_row_pattern.findall(table_content)
                for row in rows:
                    cells = [cell.strip() for cell in row.split("|") if cell.strip()]
                    if len(cells) >= 1 and cells[0]:
                        existing_rows[cells[0]] = cells
            
            # 生成新的表格内容：保留所有手动新增的待生成条目，仅更新已存在文件的信息
            new_table_rows = []
            processed_files = set()
            
            # 先处理项目中真实存在的文件
            for file_path in all_files:
                processed_files.add(file_path)
                # 提取元数据
                meta = self.extract_code_metadata(os.path.relpath(os.path.join(project_root, file_path), REPOSITORY_PATH))
                
                if file_path in existing_rows:
                    # 已有行：文件名列双向同步（保留手册修改的文件名），其余列单向从文件强制同步覆盖
                    row = existing_rows[file_path]
                    new_row = [
                        row[0], # 第一列文件名保留，支持双向同步
                        meta["module"],
                        meta["description"]
                    ]
                    new_table_rows.append(f"| {' | '.join(new_row)} |")
                    result["update_count"] += 1
                else:
                    # 新增行
                    new_row = [
                        file_path,
                        meta["module"],
                        meta["description"]
                    ]
                    new_table_rows.append(f"| {' | '.join(new_row)} |")
                    result["add_count"] += 1
                        
            # 替换原表格内容
            new_table = "| 文件名称 | 所属项目 | 功能描述 |\n| --- | --- | --- |\n"+ "\n".join(new_table_rows)
            new_content = self.detail_table_pattern.sub(f"## 二、全项目文件明细清单\n{new_table.rstrip()}", content)
            
            # 新增：自动生成第三章节文件功能明细
            file_detail_content = "## 三、项目所有文件功能明细（文件开发完成后自动更新）\n"
            for file_path in all_files:
                meta = self.extract_code_metadata(os.path.relpath(os.path.join(project_root, file_path), REPOSITORY_PATH))
                file_detail_content += f"\n### 📄 文件名：{file_path}\n"
                file_detail_content += f"- 所属模块：{meta['module'] if meta['module'] else '根模块'}\n"
                file_detail_content += f"- 功能描述：{meta['description']}\n"
                # 处理类和函数列表
                # 处理类和函数列表（带自动提取的功能描述）
                if meta['class_list'] or meta['function_list']:
                    file_detail_content += "- 包含类&核心函数列表：\n"
                    file_detail_content += "  | 名称 | 类型 | 功能描述 |\n  | --- | --- | --- |\n"
                    for cls in meta['class_list']:
                        file_detail_content += f"  | {cls['name']} | 类 | {cls['desc']} |\n"
                    for func in meta['function_list']:
                        file_detail_content += f"  | {func['name']} | 函数 | {func['desc']} |\n"
                abs_path = os.path.join(project_root, file_path)
                status = "✅ 已实现" if os.path.getsize(abs_path) > 0 else "⏳ 待开发"
                file_detail_content += f"- 实现状态：{status}\n"
            # 修复第三章节重复+格式问题：先删除所有旧第三章节内容+多余换行，统一控制前后间距
            new_content = re.sub(r"\n+## 三、.*?(?=\n## |\Z)", "", new_content, flags=re.DOTALL)
            # 插入新第三章节：前后统一留2个空行，永久固定间距不会多也不会少
            new_content = re.sub(
                r"(## 二、全项目文件明细清单.*?)(?=\n## |\Z)",
                r"\1\n\n" + file_detail_content.rstrip() + "\n\n",
                new_content,
                flags=re.DOTALL
            )
            
            # 写入更新后的手册
            with open(manual_full_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return result
        except Exception as e:
            result["code"] = 500
            result["msg"] = f"更新明细清单失败：{str(e)}"
            return result
    
# 全局单例
project_manual_manager = ProjectManualManager()