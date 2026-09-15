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
# 文件扫描噪音过滤统一配置（虚拟环境/打包产物/.git/缓存目录等），所有扫盘链路复用同一黑名单
import file_filter_config

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
# ===== 第二阶段:多格式代码元数据提取统一配置（策略模式，新增格式只需注册提取器） =====
# 单文件类/函数条目上限，防止异常文件/第三方库灌爆手册第三章
MAX_METADATA_ITEMS = 80
# 独立JS/TS结构提取体积阈值（512KB），超过视为压缩/大文件，仅给文件描述不扫结构
MAX_SCAN_FILE_SIZE = 512 * 1024
# 第三方库目录名:其下的独立js/ts不做结构提取（本项目static下全是vue/element-ui/xlsx等压缩库）
THIRD_PARTY_DIR_NAMES = {"static", "node_modules", "dist", "lib", "libs", "vendor", "third_party"}
# 压缩库/打包产物文件名模式:*.min.js、*.bundle.js、*-vendor-*.js等跳过结构提取
MIN_JS_FILE_PATTERN = re.compile(r"\.min\.(js|ts)$|[.\-](bundle|pack|vendor|runtime)([.\-]|$)", re.IGNORECASE)
# JS语法保留字:扫描Vue methods对象键时排除，避免if/for/return等被误判为方法名
JS_RESERVED_WORDS = {"if", "for", "while", "switch", "catch", "function", "return", "else", "do",
                     "try", "new", "delete", "typeof", "in", "of", "let", "const", "var", "class",
                     "default", "export", "import", "break", "continue", "this", "super", "yield", "await"}


# 正则字面量允许出现位置的前置关键字（这些关键字后'/'是正则起点而非除号，如 return /x/）
REGEX_ALLOWED_KEYWORDS = {"return", "case", "typeof", "instanceof", "in", "of",
                          "delete", "void", "throw", "new", "else", "do", "yield", "await"}
# '/'前一个有效字符为这些符号时处于"期待表达式"位置，'/'视为正则字面量起点
REGEX_ALLOWED_CHARS = set("=(,:[!&|?{;}>+-*%~^<>")


def _is_regex_allowed(prev_char: str, prev_word: str) -> bool:
    """判定'/'在当前位置是正则字面量起点(True)还是除号(False)。
    依据JS词法:运算符/分隔符后、return等关键字后、文件开头为期待表达式位置→正则；
    标识符/数字/字符串/右括号/右方括号/点号后→除法。"""
    if not prev_char:
        return True
    if prev_char in REGEX_ALLOWED_CHARS:
        return True
    if prev_char in ")]'\"`.":
        return False
    if prev_char.isalnum() or prev_char in "_$":
        return prev_word in REGEX_ALLOWED_KEYWORDS
    # 其余罕见位置（如}后）按语句起点处理，允许正则
    return True


def mask_js_comments_strings(code: str) -> str:
    """保守状态机:把JS/TS类代码中的注释、字符串、模板串、正则字面量内容替换为空格
    （保留换行与引号/斜杠位置，保证行号与花括号配平不错位）。
    后续结构正则只在真实代码上匹配，避免字符串/注释里的"function"等被误提。
    第二阶段BUG修复:识别正则字面量，避免正则体内的引号或/*被误判为字符串/块注释起点，
    导致其后整段代码被掩码（web_file_repo.html第477行 inputPattern: /^[^\\/:*?"<>|]+$/ 即此问题，
    曾使477行到文件尾全部被掩码，3个方法漏提）。"""
    out = []
    i, n = 0, len(code)
    state = "normal"
    prev_char = ""    # normal态下最近一个有效（非空白）字符，用于区分正则/除号
    prev_word = ""    # normal态下最近一个标识符单词，用于return /x/等关键字场景
    while i < n:
        ch = code[i]
        nxt = code[i + 1] if i + 1 < n else ""
        if state == "normal":
            if ch == "/" and nxt == "/":
                out.append("  ")
                i += 2
                state = "line_comment"
                continue
            if ch == "/" and nxt == "*":
                out.append("  ")
                i += 2
                state = "block_comment"
                continue
            if ch == "/" and _is_regex_allowed(prev_char, prev_word):
                # 正则字面量起点:整体掩码，内部引号/*不再误导状态机
                out.append(" ")
                i += 1
                state = "regex"
                continue
            if ch in ("'", '"', "`"):
                out.append(ch)
                i += 1
                state = "sq" if ch == "'" else ("dq" if ch == '"' else "tpl")
                prev_char = ch
                prev_word = ""
                continue
            if ch in ("\n", " ", "\t", "\r"):
                # 空白不改变上一个有效token
                out.append(ch)
                i += 1
                continue
            if ch.isalpha() or ch in "_$":
                # 标识符整体消费并记录单词（供return/case等关键字后的正则判定）
                j = i + 1
                while j < n and (code[j].isalnum() or code[j] in "_$"):
                    j += 1
                word = code[i:j]
                out.append(word)
                i = j
                prev_char = word[-1]
                prev_word = word
                continue
            # 数字/标点等普通字符
            out.append(ch)
            i += 1
            prev_char = ch
            if not (ch.isalnum() or ch in "_$"):
                prev_word = ""
        elif state == "line_comment":
            out.append("\n" if ch == "\n" else " ")
            if ch == "\n":
                state = "normal"
            i += 1
        elif state == "block_comment":
            if ch == "*" and nxt == "/":
                out.append("  ")
                i += 2
                state = "normal"
                continue
            out.append("\n" if ch == "\n" else " ")
            i += 1
        elif state == "regex":
            # 正则字面量体:转义符整体跳过；[..]字符类内部的/与引号无语法意义，进入专属状态
            if ch == "\\":
                out.append("  " if nxt else " ")
                i += 2
                continue
            if ch == "[":
                out.append(" ")
                i += 1
                state = "regex_class"
                continue
            if ch == "/":
                # 正则结束，继续掩码flags字母（g/i/m/s/u/y/d）
                out.append(" ")
                i += 1
                while i < n and code[i].isalpha():
                    out.append(" ")
                    i += 1
                state = "normal"
                # 正则整体是一个原子值，后续'/'按除法处理
                prev_char = ")"
                prev_word = ""
                continue
            # JS正则字面量不允许裸换行，出现说明判定异常，回退普通态保安全
            if ch == "\n":
                out.append(ch)
                i += 1
                state = "normal"
                prev_char = "\n"
                continue
            out.append(" ")
            i += 1
        elif state == "regex_class":
            # 正则字符类[...]:仅]结束，转义符整体跳过，其余（含引号/*）一律掩码
            if ch == "\\":
                out.append("  " if nxt else " ")
                i += 2
                continue
            if ch == "]":
                out.append(" ")
                i += 1
                state = "regex"
                continue
            if ch == "\n":
                out.append(ch)
                i += 1
                state = "normal"
                prev_char = "\n"
                continue
            out.append(" ")
            i += 1
        else:
            # 字符串态（sq/dq/tpl）:转义符整体掩码，换行保留以保证行号不错位
            if ch == "\\":
                out.append(" ")
                if nxt:
                    out.append("\n" if nxt == "\n" else " ")
                    i += 2
                else:
                    i += 1
                continue
            if ((state == "sq" and ch == "'") or (state == "dq" and ch == '"')
                    or (state == "tpl" and ch == "`")):
                out.append(ch)
                i += 1
                state = "normal"
                prev_char = ch
                prev_word = ""
                continue
            out.append("\n" if ch == "\n" else " ")
            i += 1
    return "".join(out)

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
    

    # ==================== 第二阶段:多格式提取器（策略模式，统一返回metadata结构） ====================

    def _read_text_with_fallback(self, abs_file_path: str) -> Optional[str]:
        """文本读取统一入口:优先UTF-8，失败回退GBK（bat/ps1老文件常见GBK编码），全失败返回None"""
        for enc in ("utf-8", "gbk"):
            try:
                with open(abs_file_path, "r", encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        # 最终兜底:忽略非法字节，保证不抛异常阻塞同步
        with open(abs_file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def _is_third_party_js(self, rel_path: str, file_size: int) -> bool:
        """独立JS/TS三重排除判定:压缩库文件名 / 第三方目录 / 超大文件，命中任一不做结构提取"""
        lower_path = rel_path.lower()
        base_name = lower_path.split("/")[-1]
        if MIN_JS_FILE_PATTERN.search(base_name):
            return True
        path_parts = set(lower_path.split("/")[:-1])
        if path_parts & THIRD_PARTY_DIR_NAMES:
            return True
        if file_size > MAX_SCAN_FILE_SIZE:
            return True
        return False

    def _append_capped(self, bucket: List[Dict], name: str, desc: str = "暂无描述",
                       item_type: str = "函数") -> None:
        """按上限追加条目（保序去重），防止异常文件灌爆手册第三章"""
        if len(bucket) >= MAX_METADATA_ITEMS:
            return
        if any(item["name"] == name for item in bucket):
            return
        bucket.append({"name": name, "desc": desc, "type": item_type})

    def _scan_vue_option_methods(self, clean_code: str, option_name: str, prefix: str,
                                 function_list: List[Dict]) -> None:
        """扫描Vue选项对象（methods/computed）内一层方法名。
        第二阶段BUG修复:废弃"固定缩进上限\\s{2,16}"过滤（web_log.html的methods键嵌在第16列、
        方法键在第20列，曾被一刀切误杀导致10个方法全部漏提），改为:
        花括号配平取块体→严格方法形态匹配收集候选→只收"相对option键缩进深一级（最浅层）"的方法键；
        方法体内的if(...)、setTimeout(...)等因缩进更深天然排除，CSS属性因不在script段不会进入这里。"""
        match = re.search(r"(?m)^([ \t]*)\b" + option_name + r"\s*:\s*\{", clean_code)
        if not match:
            return
        # option键自身缩进（tab按4空格折算），直接子方法键必须比它深
        base_indent = len(match.group(1).expandtabs(4))
        # 从'{'开始做花括号配平，定位该选项对象的闭合'}'
        start = match.end() - 1
        depth, i, n = 0, start, len(clean_code)
        while i < n:
            if clean_code[i] == "{":
                depth += 1
            elif clean_code[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = clean_code[start + 1:i]
        # 严格方法键形态（不限制缩进上限）:简写name(){ / async name(){ / name: function / name: (..)=> / name: arg=>
        key_pattern = re.compile(
            r"^([ \t]*)(?:async\s+)?([A-Za-z_$][\w$]*)\s*"
            r"(?:\([^)]*\)\s*\{|:\s*(?:async\s+)?function\b|:\s*(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>)"
        )
        candidates = []
        for line in body.splitlines():
            key_match = key_pattern.match(line)
            if not key_match:
                continue
            indent = len(key_match.group(1).expandtabs(4))
            name = key_match.group(2)
            if name in JS_RESERVED_WORDS or indent <= base_indent:
                continue
            candidates.append((indent, name))
        if not candidates:
            return
        # 最浅层即option键的直接子键，只收这一层；深层回调内的同名方法不进入手册
        first_layer_indent = min(indent for indent, _ in candidates)
        for indent, name in candidates:
            if indent == first_layer_indent:
                self._append_capped(function_list, f"{prefix}.{name}")

    def _prev_comment_desc(self, lines: List[str], idx: int, markers: Tuple[str, ...]) -> str:
        """向上跳过空行，取最近一条注释行的清理文本（ps1的#、bat的rem、pascal的//），无则暂无描述"""
        j = idx - 1
        while j >= 0 and not lines[j].strip():
            j -= 1
        if j >= 0:
            stripped = lines[j].strip()
            low = stripped.lower()
            for mk in markers:
                if low.startswith(mk):
                    desc = stripped[len(mk):].strip(" *").split("\n")[0][:80]
                    return desc or "暂无描述"
        return "暂无描述"

    def _js_leading_desc(self, raw: str) -> str:
        """提取JS/TS文件头部注释首行作为文件描述:优先块注释，其次连续行注释"""
        block = re.match(r"\s*/\*(.*?)\*/", raw, re.DOTALL)
        if block:
            for line in block.group(1).splitlines():
                text = line.strip().lstrip("*").strip()
                if text:
                    return text[:100]
        line_comment = re.match(r"\s*//(.*)", raw)
        if line_comment:
            return line_comment.group(1).strip()[:100]
        return ""

    def _extract_python(self, abs_file_path: str, metadata: Dict) -> None:
        """Python提取器:AST解析类/顶层函数/类方法+docstring（第二阶段从原逻辑原样搬迁，判定规则零改动）"""
        content = self._read_text_with_fallback(abs_file_path)
        if not content or not content.strip():
            return
        tree = ast.parse(content)
        # 提取类名和顶层函数名（带Docstring）
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_desc = ast.get_docstring(node) or "暂无描述"
                metadata["class_list"].append({"name": node.name, "desc": class_desc.strip().split("\n")[0], "type": "类"})
            elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):  # 过滤私有函数
                func_desc = ast.get_docstring(node) or "暂无描述"
                metadata["function_list"].append({"name": node.name, "desc": func_desc.strip().split("\n")[0], "type": "函数"})
        # 提取类内部的公共方法（带Docstring）
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for sub_node in node.body:
                    if isinstance(sub_node, ast.FunctionDef) and not sub_node.name.startswith("_"):
                        func_desc = ast.get_docstring(sub_node) or "暂无描述"
                        metadata["function_list"].append({
                            "name": f"{node.name}.{sub_node.name}",
                            "desc": func_desc.strip().split("\n")[0], "type": "函数"
                        })
        # 提取模块注释作为功能描述
        docstring = ast.get_docstring(tree)
        if docstring:
            metadata["description"] = docstring.strip().split("\n")[0][:100]

    def _extract_js_ts(self, abs_file_path: str, rel_path: str, metadata: Dict) -> None:
        """独立JS/TS提取器:三重排除第三方库后，提顶层function/class，TS顺带interface/type，不深入回调"""
        if self._is_third_party_js(rel_path, os.path.getsize(abs_file_path)):
            return
        raw = self._read_text_with_fallback(abs_file_path)
        if not raw or not raw.strip():
            return
        metadata["description"] = self._js_leading_desc(raw)
        clean = mask_js_comments_strings(raw)
        # 顶层函数:function foo / async function / export function（强制行首，避开回调内匿名函数）
        for m in re.finditer(r"(?m)^[ \t]*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)", clean):
            self._append_capped(metadata["function_list"], m.group(1), item_type="函数")
        # 顶层类:class Foo / export class / abstract class
        for m in re.finditer(r"(?m)^[ \t]*(?:export\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)", clean):
            self._append_capped(metadata["class_list"], m.group(1), item_type="类")
        # TS专属结构:interface（归入结构声明列表）、type别名
        for m in re.finditer(r"(?m)^[ \t]*(?:export\s+)?interface\s+([A-Za-z_$][\w$]*)", clean):
            self._append_capped(metadata["class_list"], m.group(1), desc="TypeScript接口", item_type="接口")
        for m in re.finditer(r"(?m)^[ \t]*(?:export\s+)?type\s+([A-Za-z_$][\w$]*)\s*=", clean):
            self._append_capped(metadata["class_list"], m.group(1), desc="TypeScript类型别名", item_type="类型别名")

    def _extract_html(self, abs_file_path: str, metadata: Dict) -> None:
        """HTML提取器:描述沿用 注释→title→meta 优先级；结构只扫内联<script>段（先剥<style>天然规避CSS误匹配），
        提Vue methods/computed方法与顶层function/class；外链src脚本无内容自动跳过"""
        raw = self._read_text_with_fallback(abs_file_path)
        if not raw or not raw.strip():
            return
        # 优先级1:HTML头部首个注释第一行
        comment_match = re.search(r"^\s*<!--(.*?)-->", raw, re.DOTALL)
        if comment_match:
            desc = comment_match.group(1).strip().split("\n")[0][:100]
            if desc:
                metadata["description"] = desc
        # 优先级2:title标签
        if not metadata["description"]:
            title_match = re.search(r"<title>(.*?)</title>", raw, re.IGNORECASE | re.DOTALL)
            if title_match:
                metadata["description"] = title_match.group(1).strip()[:100]
        # 优先级3:meta description
        if not metadata["description"]:
            meta_match = re.search(r'<meta\s+name="description"\s+content="(.*?)"', raw, re.IGNORECASE | re.DOTALL)
            if meta_match:
                metadata["description"] = meta_match.group(1).strip()[:100]
        # 只收集内联脚本段:开标签带src=的外链库（vue/element-ui CDN）整段跳过
        script_blocks = []
        for tag_match in re.finditer(r"<script([^>]*)>(.*?)</script>", raw, re.IGNORECASE | re.DOTALL):
            attrs, body = tag_match.group(1), tag_match.group(2)
            if re.search(r"\bsrc\s*=", attrs, re.IGNORECASE):
                continue
            if body.strip():
                script_blocks.append(body)
        if not script_blocks:
            return
        clean = mask_js_comments_strings("\n;\n".join(script_blocks))
        # Vue选项对象方法（methods/computed），花括号配平只取一层
        self._scan_vue_option_methods(clean, "methods", "methods", metadata["function_list"])
        self._scan_vue_option_methods(clean, "computed", "computed", metadata["function_list"])
        # 内联脚本顶层函数/类
        for m in re.finditer(r"(?m)^[ \t]*(?:async\s+)?function\s+([A-Za-z_$][\w$]*)", clean):
            self._append_capped(metadata["function_list"], m.group(1), item_type="函数")
        for m in re.finditer(r"(?m)^[ \t]*class\s+([A-Za-z_$][\w$]*)", clean):
            self._append_capped(metadata["class_list"], m.group(1), item_type="类")

    def _extract_powershell(self, abs_file_path: str, metadata: Dict) -> None:
        """PowerShell提取器:提 function Name / Name-Verb（含参数行），描述取上方#行或<##>块注释首行"""
        raw = self._read_text_with_fallback(abs_file_path)
        if not raw or not raw.strip():
            return
        lines = raw.splitlines()
        for idx, line in enumerate(lines):
            m = re.match(r"^\s*function\s+([A-Za-z_][\w-]*)", line, re.IGNORECASE)
            if not m:
                continue
            desc = "暂无描述"
            j = idx - 1
            while j >= 0 and not lines[j].strip():
                j -= 1
            if j >= 0:
                stripped = lines[j].strip()
                if stripped.startswith("#") and not stripped.startswith("#>"):
                    desc = stripped.lstrip("#").strip()[:80] or "暂无描述"
                elif stripped.startswith("#>"):
                    # 向上定位<#块注释起点，取块内第一条非空文本
                    k = j - 1
                    while k >= 0 and not lines[k].strip().startswith("<#"):
                        k -= 1
                    for text_line in lines[k + 1:j]:
                        text = text_line.strip().lstrip("#").strip()
                        if text:
                            desc = text[:80]
                            break
            self._append_capped(metadata["function_list"], m.group(1), desc, item_type="函数")

    def _extract_batch(self, abs_file_path: str, metadata: Dict) -> None:
        """BAT/CMD提取器:提 :label 子程序（::注释行天然排除），描述取上方rem注释；bat无真正函数概念"""
        raw = self._read_text_with_fallback(abs_file_path)
        if not raw or not raw.strip():
            return
        lines = raw.splitlines()
        for idx, line in enumerate(lines):
            # 标签独占一行，冒号后必须是标识符首字符，::开头的注释行不匹配
            m = re.match(r"^[ \t]*:([A-Za-z_]\w*)\s*(?:rem\b|$)", line, re.IGNORECASE)
            if not m:
                m = re.match(r"^[ \t]*:([A-Za-z_]\w*)\s*$", line, re.IGNORECASE)
            if m:
                desc = self._prev_comment_desc(lines, idx, ("rem",))
                self._append_capped(metadata["function_list"], m.group(1), desc, item_type="子程序")

    def _extract_inno_setup(self, abs_file_path: str, metadata: Dict) -> None:
        """Inno Setup脚本提取器:仅扫描[Code]段内的Pascal function/procedure，无[Code]段则无结构元数据"""
        raw = self._read_text_with_fallback(abs_file_path)
        if not raw or not raw.strip():
            return
        code_match = re.search(r"(?mi)^\s*\[Code\]\s*$", raw)
        if not code_match:
            return
        code_part = raw[code_match.end():]
        lines = code_part.splitlines()
        for idx, line in enumerate(lines):
            m = re.match(r"^\s*(?:function|procedure)\s+([A-Za-z_]\w*)", line, re.IGNORECASE)
            if m:
                desc = self._prev_comment_desc(lines, idx, ("//",))
                self._append_capped(metadata["function_list"], m.group(1), desc, item_type="函数")

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
            
            # ===== 第二阶段:按扩展名从提取器注册表分发（新增格式只需在此注册一个分支） =====
            ext = os.path.splitext(abs_file_path)[1].lower()
            if ext == ".py":
                # Python:AST提取（原逻辑原样搬迁到_extract_python，判定规则零改动）
                self._extract_python(abs_file_path, metadata)
            elif ext in (".html", ".htm"):
                # HTML:描述沿用注释→title→meta，结构只扫内联<script>段
                self._extract_html(abs_file_path, metadata)
            elif ext in (".js", ".mjs", ".ts"):
                # 独立JS/TS:三重排除第三方库后提顶层function/class（TS顺带interface/type）
                self._extract_js_ts(abs_file_path, rel_path, metadata)
            elif ext == ".ps1":
                # PowerShell:function Name + 上方注释
                self._extract_powershell(abs_file_path, metadata)
            elif ext in (".bat", ".cmd"):
                # BAT/CMD::label子程序 + rem注释
                self._extract_batch(abs_file_path, metadata)
            elif ext == ".iss":
                # Inno Setup:仅[Code]段Pascal function/procedure
                self._extract_inno_setup(abs_file_path, metadata)

            # 无结构元数据/无描述的文件统一兜底文件类型描述
            if not metadata["description"]:
                # 特殊处理项目手册，返回专属功能描述
                if "项目手册.md" in os.path.basename(abs_file_path):
                    metadata["description"] = "项目全量信息说明、规范定义、文件索引"
                else:
                    ext_map = {
                        ".jpg": "图片资源", ".jpeg": "图片资源", ".png": "图片资源", ".gif": "图片资源",
                        ".md": "Markdown文档", ".txt": "文本文件", ".json": "配置文件",
                        ".csv": "数据文件", ".docx": "Word文档", ".xlsx": "Excel表格",
                        ".html": "HTML页面/前端组件", ".htm": "HTML页面/前端组件",
                        ".js": "JavaScript脚本", ".mjs": "JavaScript模块", ".ts": "TypeScript脚本",
                        ".css": "CSS样式表", ".ps1": "PowerShell脚本",
                        ".bat": "Windows批处理脚本", ".cmd": "Windows命令脚本",
                        ".iss": "Inno Setup安装脚本"
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
            "add_count": 0,
            "changed": False  # 内容是否真实发生变化（无变化不写盘，供监听层决定是否广播SSE）
        }
        try:

            manual_full_path = os.path.join(REPOSITORY_PATH, manual_path)
            if not os.path.exists(manual_full_path):
                result["code"] = 404
                result["msg"] = "手册不存在"
                return result
            
            # 读取手册内容，同时记录读取时刻的mtime作为乐观锁基线
            # （全量AST扫描耗时较长，若期间手册被外部手写修改，写回前会检测到mtime变化并放弃本轮）
            with open(manual_full_path, "r", encoding="utf-8") as f:
                content = f.read()
            base_mtime_ns = os.stat(manual_full_path).st_mtime_ns

            # 获取项目根目录下的所有文件
            project_root = os.path.dirname(manual_full_path)
            all_files = []
            # 优先加入项目手册自身，确保空项目时至少有手册条目
            manual_filename = os.path.basename(manual_full_path)
            all_files.append(manual_filename)
            # 文件后缀黑名单:复用统一后缀黑名单（.pyc/.log/.tmp/.bak等），
            # 另加手册解析场景特有的二进制后缀（.pyd/.so/.dll等，无文本解析价值）
            MANUAL_EXCLUDE_EXTS = set(file_filter_config.EXCLUDE_FILE_EXTS) | {".pyd", ".so", ".dll", ".bin", ".exe"}
            for root, dirs, files in os.walk(project_root):
                # 剪枝:复用统一噪音目录黑名单（.venv/venv/env/dist/build/.git/缓存等，精确匹配），
                # 另排除手册场景特有的 test_venv（测试用虚拟环境目录），阻止os.walk递归进入
                file_filter_config.prune_walk_dirs(dirs)
                dirs[:] = [d for d in dirs if d != "test_venv"]
                for file in files:
                    # 跳过已加入的手册文件，避免重复
                    if file == manual_filename:
                        continue
                    # 跳过缓存/二进制/噪音文件（统一文件名+后缀黑名单，含Thumbs.db等系统垃圾）
                    ext = os.path.splitext(file)[1].lower()
                    if ext in MANUAL_EXCLUDE_EXTS or file_filter_config.is_noise_file(file):
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
            
            # 根治点1:内容完全相同则短路，不写盘（消除"重写→触发监听→再重写"的自激死循环）
            if new_content == content:
                return result

            # 根治点2:乐观锁校验——AST全量扫描期间手册若被外部手写/其他进程修改，放弃本轮，
            # 等下一个文件事件重新扫描合并，杜绝慢处理把新内容覆盖回旧内容
            try:
                current_mtime_ns = os.stat(manual_full_path).st_mtime_ns
            except OSError:
                result["code"] = 404
                result["msg"] = "手册在处理过程中被删除"
                return result
            if current_mtime_ns != base_mtime_ns:
                result["code"] = 409
                result["msg"] = "手册在扫描期间被外部修改，本轮放弃，等待下次事件合并"
                print(f"⚠️ {result['msg']}:{manual_path}")
                return result

            # 根治点3:原子写——先写同目录临时文件再os.replace原子替换，
            # 避免半写状态被监听线程/其他进程读到
            tmp_path = f"{manual_full_path}.{os.getpid()}.tmp"
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                os.replace(tmp_path, manual_full_path)
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
            result["changed"] = True
            return result
        except Exception as e:
            result["code"] = 500
            result["msg"] = f"更新明细清单失败:{str(e)}"
            return result
    
# 全局单例
project_manual_manager = ProjectManualManager()