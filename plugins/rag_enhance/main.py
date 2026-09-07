import os
import re
import sqlite3
import time
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# 复用现有核心模块
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# RAG模块降级容错:faiss/numpy兼容问题不影响核心功能
rag_available = False
rag_manager = None
try:
    from rag_manager import rag_manager
    rag_available = True
except Exception as e:
    print(f"[RAG增强插件] RAG模块加载失败，语义索引功能暂时不可用: {str(e)}")

class RAGEnhancePlugin:
    def __init__(self, config: Dict = None):
        # 合并默认配置和传入配置，缺失项自动使用默认值
        default_config = self._load_default_config()
        if config:
            default_config.update(config)
        self.config = default_config
        self.db_path = Path.home() / ".ai_assistant" / "file_index.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self.note_dir = Path(os.path.expanduser(self.config["note_dir"]))
        self.note_dir.mkdir(parents=True, exist_ok=True)
        # 插件加载状态标志，on_load由主程序加载完成后调用
        self._loaded = False

    def on_load(self):
        """插件完全加载完成后由主程序调用，执行后台任务初始化，避免导入阶段启动线程被中断"""
        if self._loaded:
            return
        self._loaded = True
        # 注册每日自动扫描任务（凌晨3点执行，间隔24小时）
        self._register_auto_scan_job()
        # 首次启动索引为空时自动后台初始化扫描
        self._init_first_scan()

    def _register_auto_scan_job(self):
        """注册24小时自动全量扫描定时任务，内部任务不在前端显示"""
        try:
            from scheduler_manager import scheduler_manager
            # 直接调用APScheduler实例添加内部任务，不写入任务列表，不在前端显示
            scheduler_manager.scheduler.add_job(
                func=self.scan_directory,
                trigger="cron",
                hour=3,
                minute=0,
                id="rag_enhance_daily_scan",
                replace_existing=True,
                max_instances=1,
                coalesce=True
            )
        except Exception as e:
            print(f"[RAG增强插件] 自动扫描定时任务注册失败: {str(e)}")

    def _init_first_scan(self):
        """首次启动索引为空时自动后台执行全量扫描，不阻塞初始化，受auto_index开关控制"""
        try:
            # 未开启自动索引则跳过
            if not self.config.get("auto_index", True):
                return
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM files")
            count = cursor.fetchone()[0]
            conn.close()
            if count == 0:
                import threading
                def bg_scan():
                    try:
                        self.scan_directory()
                    except Exception as e:
                        print(f"[RAG增强插件] 首次全量扫描失败: {str(e)}")
                threading.Thread(target=bg_scan, daemon=True, name="rag_first_scan").start()
        except Exception as e:
            print(f"[RAG增强插件] 首次扫描初始化失败: {str(e)}")

    def _load_default_config(self) -> Dict:
        """加载默认配置"""
        # 自动枚举所有可用磁盘根目录作为默认索引目录
        index_dirs = []
        if os.name == "nt":  # Windows系统
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                drive_path = f"{letter}:\\"
                if os.path.exists(drive_path):
                    index_dirs.append(drive_path)
        else:
            # 非Windows系统默认索引用户目录
            index_dirs = ["~/Desktop", "~/Documents", "~/Downloads"]
        
        default_config = {
            "index_dirs": index_dirs,
            "exclude_patterns": [
                "*.tmp", "*.temp", "*.log", "*.cache", "~$*", "*.chk", "*.old",
                "*/Windows/*", "*/Program Files/*", "*/Program Files (x86)/*", "*/ProgramData/*",
                "*/$Recycle.Bin/*", "*/System Volume Information/*", "*/Recovery/*",
                "*/node_modules/*", "*/.git/*", "*/.svn/*", "*/__pycache__/*",
                "*/AppData/Local/Temp/*", "*/AppData/Local/Microsoft/Windows/INetCache/*"
            ],
            "note_dir": "~/Documents/AI知识库",
            "auto_index": True,
            "enable_web_clip": True,
            "low_priority_only": True,
            "auto_save_collect_content": True,
            "auto_save_trigger_keywords": ["存到知识库", "保存为笔记", "加入知识库"],
            "exclude_auto_save_keywords": ["开发总结", "修复结果", "工具调用日志", "报错信息"]
        }
        return default_config

    def _init_db(self):
        """初始化文件名索引SQLite数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                file_path TEXT UNIQUE NOT NULL,
                file_type TEXT,
                size INTEGER,
                mtime REAL,
                index_time REAL
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_name ON files(file_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mtime ON files(mtime)')
        conn.commit()
        conn.close()

    def _is_excluded(self, file_path: str) -> bool:
        """判断文件是否在排除列表中"""
        path_str = str(file_path).replace("\\", "/")
        for pattern in self.config["exclude_patterns"]:
            if re.search(pattern.replace(".", r"\.").replace("*", ".*"), path_str, re.IGNORECASE):
                return True
        return False

    def scan_directory(self, dir_path: str = None) -> Tuple[int, int, int]:
        """扫描指定目录，全量同步文件名索引缓存，自动清理已删除文件的无效记录
        返回: (新增文件数, 更新文件数, 删除无效索引数)
        """
        scan_dirs = [dir_path] if dir_path else self.config["index_dirs"]
        added = 0
        updated = 0
        deleted = 0
        existing_paths = set()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for scan_dir in scan_dirs:
            full_dir = Path(os.path.expanduser(scan_dir))
            if not full_dir.exists() or not full_dir.is_dir():
                continue
            scan_dir_str = str(full_dir).replace("\\", "/").rstrip("/")

            for root, _, files in os.walk(full_dir):
                for file in files:
                    file_path = Path(root) / file
                    if self._is_excluded(str(file_path)):
                        continue
                    try:
                        stat = file_path.stat()
                        file_path_str = str(file_path)
                        existing_paths.add(file_path_str)
                        # 插入或更新记录（全量同步，不跳过未变更文件）
                        file_type = file_path.suffix.lower().lstrip(".")
                        cursor.execute("SELECT id FROM files WHERE file_path = ?", (file_path_str,))
                        existing = cursor.fetchone()
                        if existing:
                            cursor.execute('''
                                UPDATE files SET file_name=?, file_type=?, size=?, mtime=?, index_time=?
                                WHERE file_path=?
                            ''', (file, file_type, stat.st_size, stat.st_mtime, time.time(), file_path_str))
                            updated += 1
                        else:
                            cursor.execute('''
                                INSERT INTO files (file_name, file_path, file_type, size, mtime, index_time)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (file, file_path_str, file_type, stat.st_size, stat.st_mtime, time.time()))
                            added += 1
                    except Exception:
                        continue
            
            # 清理当前扫描目录下已不存在的无效索引
            cursor.execute("SELECT id, file_path FROM files WHERE file_path LIKE ?", (f"{scan_dir_str}%",))
            for row_id, db_path in cursor.fetchall():
                if db_path not in existing_paths:
                    cursor.execute("DELETE FROM files WHERE id = ?", (row_id,))
                    deleted += 1

        conn.commit()
        conn.close()
        return added, updated, deleted

    def search_files(self, keyword: str, file_type: str = None, time_range: Tuple[float, float] = None, limit: int = 50) -> List[Dict]:
        """按文件名搜索文件
        Args:
            keyword: 搜索关键词（支持模糊匹配）
            file_type: 可选，文件后缀过滤（如docx/pdf）
            time_range: 可选，(开始时间戳, 结束时间戳)修改时间范围
            limit: 返回结果最大数量
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM files WHERE file_name LIKE ?"
        params = [f"%{keyword}%"]

        if file_type:
            query += " AND file_type = ?"
            params.append(file_type.lower().lstrip("."))
        if time_range:
            query += " AND mtime BETWEEN ? AND ?"
            params.extend(time_range)

        query += " ORDER BY mtime DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append({
                "file_name": row["file_name"],
                "file_path": row["file_path"],
                "file_type": row["file_type"],
                "size": row["size"],
                "mtime": row["mtime"],
                "size_display": self._format_size(row["size"]),
                "mtime_display": time.strftime("%Y-%m-%d %H:%M", time.localtime(row["mtime"]))
            })
        return results

    def read_file_content(self, file_path: str) -> Optional[str]:
        """读取任意支持格式的文件内容，自动适配格式解析"""
        if not Path(file_path).exists():
            return None
        file_suffix = Path(file_path).suffix.lower()
        # 纯文本/代码文件直接读取
        if file_suffix in [".txt", ".md", ".py", ".js", ".html", ".css", ".json", ".csv", ".xml", ".yaml", ".yml", ".ini", ".conf"]:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception as e:
                return f"文本文件读取失败: {str(e)}"
        # Word文档解析
        elif file_suffix in [".docx", ".doc"]:
            try:
                from docx import Document
                doc = Document(file_path)
                full_text = []
                for para in doc.paragraphs:
                    if para.text.strip():
                        full_text.append(para.text)
                # 提取表格内容
                for table in doc.tables:
                    for row in table.rows:
                        row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                        if row_text:
                            full_text.append(" | ".join(row_text))
                return "\n".join(full_text)
            except ImportError:
                return "Word文档解析失败:缺少python-docx依赖，请安装后重试"
            except Exception as e:
                return f"Word文档读取失败: {str(e)}"
        # Excel表格解析
        elif file_suffix in [".xlsx", ".xls"]:
            try:
                from openpyxl import load_workbook
                wb = load_workbook(file_path, read_only=True, data_only=True)
                full_text = []
                for sheet_name in wb.sheetnames:
                    sheet = wb[sheet_name]
                    full_text.append(f"===== 工作表: {sheet_name} =====")
                    for row in sheet.iter_rows(values_only=True):
                        row_text = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
                        if row_text:
                            full_text.append(" | ".join(row_text))
                wb.close()
                return "\n".join(full_text)
            except ImportError:
                return "Excel文档解析失败:缺少openpyxl依赖，请安装后重试"
            except Exception as e:
                return f"Excel文档读取失败: {str(e)}"
        # PDF文档解析
        elif file_suffix == ".pdf":
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                full_text = []
                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text and text.strip():
                        full_text.append(f"===== 第{page_num+1}页 =====")
                        full_text.append(text.strip())
                return "\n".join(full_text)
            except ImportError:
                return "PDF文档解析失败:缺少PyPDF2依赖，请安装后重试"
            except Exception as e:
                return f"PDF文档读取失败: {str(e)}"
        # 不支持的格式
        else:
            return f"不支持的文件格式: {file_suffix}"

    def should_auto_save(self, content: str, source: str) -> bool:
        """判断内容是否需要自动存入知识库
        规则:仅info_collector采集的内容，或用户明确触发存到知识库的内容才入库
        """
        # 信息采集类内容自动入库
        if source == "info_collector" and self.config["auto_save_collect_content"]:
            # 排除包含排除关键词的内容
            for exclude_keyword in self.config["exclude_auto_save_keywords"]:
                if exclude_keyword in content:
                    return False
            return True
        # 用户明确触发存到知识库
        for trigger_keyword in self.config["auto_save_trigger_keywords"]:
            if trigger_keyword in content:
                return True
        # 其他情况默认不入库
        return False

    def save_note(self, title: str, content: str, tags: List[str] = None, source_url: str = None) -> Dict:
        """保存Markdown笔记到知识库，自动加入RAG索引"""
        tags = tags or []
        timestamp = time.strftime("%Y-%m-%d %H:%M", time.localtime())
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
        note_path = self.note_dir / f"{safe_title}.md"

        # 拼接元数据头
        meta = f"""---
title: {title}
create_time: {timestamp}
tags: {', '.join(tags)}
source_url: {source_url or ''}
---

"""
        full_content = meta + content
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(full_content)

        # 自动加入RAG索引（RAG模块可用时执行）
        if rag_available and rag_manager:
            try:
                rag_manager.add_file(str(note_path))
            except Exception:
                pass

        return {
            "success": True,
            "note_path": str(note_path),
            "title": title,
            "tags": tags
        }

    def search_notes(self, keyword: str, tags: List[str] = None, limit: int = 20) -> List[Dict]:
        """搜索知识库中的Markdown笔记
        Args:
            keyword: 搜索关键词，同时匹配标题、标签、正文内容
            tags: 可选，标签过滤列表，匹配任意一个标签即可
            limit: 返回结果最大数量
        Returns:
            匹配的笔记列表，包含标题、路径、标签、创建时间、匹配片段
        """
        results = []
        keyword_lower = keyword.lower().strip()
        tags = tags or []
        
        if not self.note_dir.exists():
            return results

        # 遍历所有md文件
        for note_path in self.note_dir.glob("*.md"):
            try:
                with open(note_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                
                # 解析YAML元数据头
                meta = {}
                body = content
                if content.startswith("---"):
                    end_idx = content.find("---", 3)
                    if end_idx != -1:
                        meta_content = content[3:end_idx].strip()
                        body = content[end_idx+3:].strip()
                        # 简单解析元数据
                        for line in meta_content.split("\n"):
                            if ":" in line:
                                key, value = line.split(":", 1)
                                meta[key.strip()] = value.strip()
                
                note_title = meta.get("title", note_path.stem)
                note_tags = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]
                create_time = meta.get("create_time", "")
                source_url = meta.get("source_url", "")
                
                # 标签过滤
                if tags:
                    tag_match = any(t in note_tags for t in tags)
                    if not tag_match:
                        continue
                
                # 关键词匹配（标题+标签+正文）
                title_match = keyword_lower in note_title.lower()
                tag_match = keyword_lower in " ".join(note_tags).lower()
                body_match = keyword_lower in body.lower()
                
                if not (title_match or tag_match or body_match):
                    continue
                
                # 提取匹配片段（关键词前后100字）
                snippet = ""
                if body_match:
                    match_idx = body.lower().find(keyword_lower)
                    start = max(0, match_idx - 100)
                    end = min(len(body), match_idx + len(keyword) + 100)
                    snippet = body[start:end].replace("\n", " ")
                    if start > 0:
                        snippet = "..." + snippet
                    if end < len(body):
                        snippet = snippet + "..."
                elif title_match:
                    snippet = body[:200].replace("\n", " ") + "..."
                else:
                    snippet = body[:200].replace("\n", " ") + "..."
                
                # 计算匹配度排序权重（标题匹配>标签匹配>正文匹配）
                weight = 0
                if title_match:
                    weight += 3
                if tag_match:
                    weight += 2
                if body_match:
                    weight += 1
                
                results.append({
                    "title": note_title,
                    "note_path": str(note_path),
                    "tags": note_tags,
                    "create_time": create_time,
                    "source_url": source_url,
                    "snippet": snippet,
                    "weight": weight,
                    "size": note_path.stat().st_size
                })
            except Exception:
                continue
        
        # 按匹配权重倒序、创建时间倒序排列
        results.sort(key=lambda x: (-x["weight"], x["create_time"]), reverse=False)
        return results[:limit]

    def _format_size(self, size: int) -> str:
        """格式化文件大小显示"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

# 插件全局实例
plugin = RAGEnhancePlugin()

def run(*args, **kwargs) -> Dict:
    """插件统一入口，兼容两种调用方式:
    1. 主程序标准调用:run(参数字典)，参数字典包含action字段
    2. 单元测试调用:run(action字符串, 参数字典)
    """
    # 解析参数，兼容两种调用格式
    if len(args) == 1 and isinstance(args[0], dict):
        # 主程序标准调用:传入完整参数字典
        params = args[0].copy()
        action = params.pop("action", "")
    elif len(args) >= 1 and isinstance(args[0], str):
        # 旧版单元测试调用:action单独作为第一个参数
        action = args[0]
        params = args[1] if len(args) > 1 else {}
    else:
        # 关键字参数调用
        params = kwargs.copy()
        action = params.pop("action", "")
    params = params or {}
    # 双重保险:首次调用插件接口时自动触发加载逻辑，兼容未调用on_load的场景
    if not plugin._loaded:
        plugin.on_load()
    if action == "search_files":
        return {
            "success": True,
            "results": plugin.search_files(
                keyword=params.get("keyword", ""),
                file_type=params.get("file_type"),
                time_range=params.get("time_range"),
                limit=params.get("limit", 50)
            )
        }
    elif action == "scan_directory":
        added, updated, deleted = plugin.scan_directory(params.get("dir_path"))
        return {
            "success": True,
            "added": added,
            "updated": updated,
            "deleted": deleted
        }
    elif action == "read_file_content":
        content = plugin.read_file_content(params.get("file_path", ""))
        return {
            "success": content is not None,
            "content": content,
            "file_path": params.get("file_path")
        }
    elif action == "save_note":
        result = plugin.save_note(
            title=params.get("title", "未命名笔记"),
            content=params.get("content", ""),
            tags=params.get("tags", []),
            source_url=params.get("source_url")
        )
        return result
    elif action == "should_auto_save":
        return {
            "should_save": plugin.should_auto_save(
                content=params.get("content", ""),
                source=params.get("source", "")
            )
        }
    elif action == "search_knowledge_base":
        results = plugin.search_notes(
            keyword=params.get("keyword", ""),
            tags=params.get("tags", []),
            limit=params.get("limit", 20)
        )
        return {
            "success": True,
            "results": results,
            "total": len(results)
        }
    else:
        return {"success": False, "error": f"不支持的操作: {action}"}