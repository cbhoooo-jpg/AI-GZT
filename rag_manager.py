# -*- coding: utf-8 -*-
"""
添加文件到RAG库，自动提取项目归属标签
"""
import os
import json
import threading
import functools
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict
# 文件扫描噪音过滤统一配置（虚拟环境/打包产物/.git/缓存目录等），所有扫盘链路复用同一黑名单
import file_filter_config

# 容错导入:打包后可能缺少torch/sentence_transformers/faiss等RAG大体积依赖，降级运行避免启动崩溃
try:
    import faiss
    import torch
    from sentence_transformers import SentenceTransformer
    HAS_RAG_DEPENDENCIES = True
except ImportError:
    HAS_RAG_DEPENDENCIES = False
    faiss = None
    torch = None
    SentenceTransformer = None

# 全局文件更新缓存:key=文件绝对路径，value=最后修改时间戳，用于增量校验
LAST_UPDATE_CACHE = {}

# 全局配置
# 兼容PyInstaller打包环境:打包后使用sys.executable所在目录，开发环境使用__file__所在目录
import sys
if getattr(sys, 'frozen', False):
    _exe_dir = os.path.dirname(sys.executable)
    _internal_dir = os.path.join(_exe_dir, "_internal")
    _BASE_DIR = _internal_dir if os.path.exists(_internal_dir) else _exe_dir
    # 兜底逻辑:如果EXE同级目录没有config.json，自动从_internal复制默认配置，和其他模块路径对齐
    _config_path = os.path.join(_exe_dir, "config.json")
    if not os.path.exists(_config_path) and os.path.exists(_internal_dir):
        _internal_default_config = os.path.join(_internal_dir, "config.json")
        if os.path.exists(_internal_default_config):
            import shutil
            try:
                shutil.copy2(_internal_default_config, _config_path)
                print(f"[RAGManager] 首次启动自动从_internal复制默认配置到: {_config_path}")
            except Exception as e:
                print(f"[RAGManager] 复制默认配置失败: {e}")
else:
    _exe_dir = os.path.dirname(os.path.abspath(__file__))
    _BASE_DIR = _exe_dir
# 向量数据库路径改为程序/安装目录下，避免中文用户路径问题
RAG_DIR = os.path.join(_exe_dir, "code_rag")
INDEX_PATH = os.path.join(RAG_DIR, "code.index")
META_PATH = os.path.join(RAG_DIR, "code_meta.json")
CACHE_PATH = os.path.join(RAG_DIR, "last_update_cache.json")
# 嵌入模型路径改为基于程序目录的绝对路径
EMB_MODEL_NAME = os.path.join(_BASE_DIR, "gte-small-zh")
MAX_SLICE_LENGTH = 1024  # 每个代码片段最大长度（配合gte-small-zh约512token上限，兼顾长函数完整入库）
TOP_K = 5  # 每次检索返回最相关的5个片段


def get_repository_path() -> str:
    """动态获取当前配置的仓库路径，自动适配配置更新，避免硬编码，配置路径和其他模块完全对齐"""
    # 打包环境使用EXE同级目录，开发环境使用脚本所在目录，统一读取EXE同级的config.json
    if getattr(sys, 'frozen', False):
        base_dir = _exe_dir
    else:
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
            print(f"[RAG]模块读取仓库路径配置失败，使用默认路径:{str(e)}")
    # 配置不存在时自动创建默认目录
    os.makedirs(default_repo, exist_ok=True)
    return default_repo


def get_max_file_size_bytes() -> int:
    """动态获取单文件入库大小上限（字节），超限文件在扫描阶段直接跳过。

    阈值来自 config.json 的 rag_max_file_size_kb（默认512KB），配置缺失/异常时回退默认值，
    统一配置入口原则，禁止把阈值硬编码进扫描逻辑。
    """
    if getattr(sys, 'frozen', False):
        base_dir = _exe_dir
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.json")
    default_kb = 512
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            kb = int(config.get("rag_max_file_size_kb", default_kb))
            if kb <= 0:
                kb = default_kb
            return kb * 1024
    except Exception:
        pass
    return default_kb * 1024


def get_rag_cpu_threads() -> int:
    """计算RAG向量编码线程数:读取config.json的rag_cpu_threads(0=自动默认上限8，>0=手动上限，1=单线程保命)
    实际线程=max(1,min(上限,逻辑核心数-1))，与main.py的RAG_CPU_THREADS算法完全保持一致，唯一配置入口。
    """
    if getattr(sys, 'frozen', False):
        base_dir = _exe_dir
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.json")
    default_limit = 8
    limit = 0
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            limit = int(config.get("rag_cpu_threads", 0))
    except Exception:
        limit = 0
    if limit == 1:
        return 1
    if limit <= 0:
        limit = default_limit
    cores = os.cpu_count() or 1
    return max(1, min(limit, max(1, cores - 1)))


def _load_update_cache():
    """启动时加载持久化的文件更新时间缓存，使增量更新跨进程重启依然有效"""
    global LAST_UPDATE_CACHE
    try:
        if os.path.exists(CACHE_PATH):
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                LAST_UPDATE_CACHE = data
    except Exception:
        LAST_UPDATE_CACHE = {}


def _save_update_cache():
    """把当前文件更新时间缓存落盘，供下次启动增量复用"""
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(LAST_UPDATE_CACHE, f, ensure_ascii=False)
    except Exception:
        pass


def _with_write_lock(method):
    """写操作互斥装饰器:等价于 'with self._write_lock:' 包住整个方法体

    用于 add_file/delete_file/delete_project/build_full_index 四个写方法，根治
    "删旧→编码(耗时窗口)→写新"非原子 + 并发触发导致的同文件重复入库竞态。
    使用 RLock（可重入）:add_file 内部会调用 delete_file，同线程必须能重复拿锁，否则死锁。
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._write_lock:
            return method(self, *args, **kwargs)
    return wrapper


class CodeRAGManager:
    def __init__(self):
        # 写操作互斥锁（可重入）:根治"同文件被并发入库导致内容重复多份"的竞态问题
        self._write_lock = threading.RLock()
        # 自动创建RAG目录
        os.makedirs(RAG_DIR, exist_ok=True)
        # 加载持久化的文件更新时间缓存，使增量更新跨进程重启依然有效（避免每次重启全量重算）
        _load_update_cache()
        
        # 降级模式:无外部依赖时不初始化模型，直接返回空壳
        if not HAS_RAG_DEPENDENCIES:
            print("[RAG] 未检测到torch/sentence_transformers依赖，代码RAG知识库功能已降级禁用")
            self.emb_model = None
            self.emb_dim = 0
            self.index = None
            self.meta = {}
            self.next_id = 0
            return
        
        try:
            # 加载embedding模型，默认用CPU，要GPU的话去掉device参数
            self.emb_model = SentenceTransformer(EMB_MODEL_NAME, device="cpu")
            # 按config.json的rag_cpu_threads设置PyTorch CPU线程数，与main.py保持一致，低配自动降、高配自动升
            torch.set_num_threads(get_rag_cpu_threads())
            # 动态获取模型实际输出维度，适配所有模型
            if hasattr(self.emb_model, 'get_sentence_embedding_dimension'):
                self.emb_dim = self.emb_model.get_sentence_embedding_dimension()
            else:
                self.emb_dim = self.emb_model.get_embedding_dimension()

            # 加载/初始化索引，新增损坏自动重建容错
            # 索引载荷:IndexIDMap(支持按id精确删除) + 底层 IndexFlatIP(向量已L2归一化，内积即余弦相似度)，meta 为 id->切片 字典
            try:
                if os.path.exists(INDEX_PATH) and os.path.exists(META_PATH):
                    loaded_index = faiss.read_index(INDEX_PATH)
                    with open(META_PATH, "r", encoding="utf-8") as f:
                        loaded_meta = json.load(f)
                    # 不再做旧格式判断:索引文件存在即直接加载，索引的清空/重建一律由用户在界面手动操作
                    self.index = loaded_index
                    self.meta = loaded_meta
                else:
                    # 索引文件不存在（首次启动或用户手动清空）→ 仅在内存新建空索引，绝不删除任何文件
                    self.index = faiss.IndexIDMap(faiss.IndexFlatIP(self.emb_dim))
                    self.meta = {}
            except Exception as e:
                # 索引读取失败（文件损坏/格式错）→ 绝不删除任何文件，仅在内存使用空索引，提示用户手动重建
                print(f"[RAG] 索引读取失败:{str(e)}，已在内存使用空索引；如需重建请在界面手动清空后重建")
                self.index = faiss.IndexIDMap(faiss.IndexFlatIP(self.emb_dim))
                self.meta = {}
            # next_id 取现存最大id+1，保证新增切片id不与存量冲突（空库为0）
            self.next_id = max((int(k) for k in self.meta.keys()), default=-1) + 1
        except Exception as e:
            # 模型加载失败时降级为空壳，避免启动崩溃
            print(f"[RAG] 模型加载失败，代码RAG知识库功能已降级禁用:{str(e)}")
            self.emb_model = None
            self.emb_dim = 0
            self.index = None
            self.meta = {}
            self.next_id = 0
    
    def _save_index(self):
        """保存索引和元数据到本地"""
        faiss.write_index(self.index, INDEX_PATH)
        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump(self.meta, f, ensure_ascii=False, indent=2)
    def _encode(self, texts: List[str], batch_size: int = None) -> np.ndarray:
        """统一向量编码入口:产出 L2 归一化向量（与 IndexFlatIP 索引配套，内积即余弦相似度）

        所有编码链路（增量入库/全量入库/查询）都必须走这里，避免向量量纲不一致导致检索塌陷；
        旧版 sentence-transformers 不支持 normalize_embeddings 参数时自动回退，并统一手动归一化兜底。
        """
        kwargs = {}
        if batch_size:
            kwargs["batch_size"] = batch_size
        try:
            embs = self.emb_model.encode(texts, normalize_embeddings=True, **kwargs)
        except TypeError:
            # 依赖版本过旧时不支持该参数，回退后再手动归一化（数学结果一致）
            embs = self.emb_model.encode(texts, **kwargs)
        embs = np.asarray(embs, dtype=np.float32)
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return embs / norms
    
    def _slice_code(self, content: str, file_name: str, project_name: str = "default") -> List[Dict]:
        """代码切片:按函数/类边界拆分（含类内方法），超长片段按行二次切分并保留15%重叠，新增项目归属标签

        本轮检索质量增强:
        1) 类头碎片合并:形如「class XXX: + 文档字符串」且内部没有任何 def 的短片段不再独立成片，
           自动并入紧随其后的下一片（通常是该类的第一个方法），消除语义空洞的噪声源；
        2) 语义前缀:每片附带 embed_text＝[文件]+[符号路径]+原文，把文件名/类名/方法名送入向量编码，
           解决 add_file、get_rag_cpu_threads 这类标识符查询丢失唯一线索的问题（embed_text 只用于编码，不落盘）。
        """
        import re
        result = []
        slice_idx = 0

        def _emit(text: str, symbol: str = ""):
            """写入一片结果，并生成用于向量编码的语义前缀文本"""
            nonlocal slice_idx
            text = text.strip("\n")
            if not text.strip():
                return
            prefix = "[文件] " + os.path.basename(file_name or "")
            if symbol:
                prefix += " [符号] " + symbol
            result.append({
                "content": text,
                "embed_text": prefix + "\n" + text,
                "file_name": file_name,
                "project_name": project_name,
                "slice_idx": slice_idx
            })
            slice_idx += 1

        def _extract_symbol(text: str) -> str:
            """提取切片内的符号路径（类名.方法名），供编码前缀使用"""
            names = []
            for line in text.split("\n")[:60]:
                m = re.match(r"^([ \t]*)(class|def)\s+([A-Za-z_][A-Za-z0-9_]*)", line)
                if m:
                    names.append((m.group(2), m.group(3)))
            if not names:
                return ""
            class_name = next((n for k, n in names if k == "class"), "")
            methods = [n for k, n in names if k == "def"]
            # 跳过 __init__ 这类通用方法名，优先用业务方法名提高区分度
            method = next((n for n in methods if not n.startswith("__")), (methods[0] if methods else ""))
            if class_name and method:
                return class_name + "." + method
            return class_name or method

        # 文档类（.md）:按标题层级切章节，标题作语义前缀，替代 def/class 切分与 1024 硬切（5.1/5.4 必做项）
        if (file_name or "").lower().endswith(".md"):
            lines = content.split("\n")
            sections = []
            cur_title, cur_buf = "", []
            for line in lines:
                if re.match(r"^#{1,6}\s", line):
                    if cur_buf:
                        sections.append((cur_title, "\n".join(cur_buf).strip("\n")))
                    cur_title, cur_buf = line.strip(), [line]
                else:
                    cur_buf.append(line)
            if cur_buf:
                sections.append((cur_title, "\n".join(cur_buf).strip("\n")))
            md_overlap = max(1, int(MAX_SLICE_LENGTH * 0.15))
            for title, text in sections:
                if not text.strip():
                    continue
                if len(text) <= MAX_SLICE_LENGTH:
                    _emit(text, title)
                    continue
                buf = ""
                for line in text.split("\n"):
                    while len(line) > MAX_SLICE_LENGTH:
                        if buf:
                            _emit(buf, title); buf = ""
                        _emit(line[:MAX_SLICE_LENGTH], title)
                        line = line[MAX_SLICE_LENGTH:]
                    candidate = line if not buf else buf + "\n" + line
                    if len(candidate) > MAX_SLICE_LENGTH:
                        _emit(buf, title); buf = buf[-md_overlap:] + "\n" + line
                    else:
                        buf = candidate
                if buf.strip():
                    _emit(buf, title)
            return result

        # 按行首（允许任意缩进）的 def/class 定义行作为切分点，既保留类内方法，又避免文件头被重复切出
        parts = re.split(r"(?m)(?=^[ \t]*(?:def|class)\s)", content)
        raw_slices = [p for p in parts if p and p.strip()]

        # 类头碎片合并:类声明后不含任何 def 的短片段并入下一片，避免这类碎片被所有查询"吸"出来挤占榜单
        merged_slices = []
        pending_head = ""
        for s in raw_slices:
            if pending_head:
                s = pending_head + s
                pending_head = ""
            is_class_head = bool(re.match(r"^[ \t]*class\s", s)) and not re.search(r"(?m)^[ \t]*def\s", s)
            if is_class_head and len(s) < MAX_SLICE_LENGTH // 2:
                pending_head = s
                continue
            merged_slices.append(s)
        if pending_head:
            # 文件末尾的类头没有后继片段可合并，单独保留，避免内容丢失
            merged_slices.append(pending_head)
        overlap_chars = max(1, int(MAX_SLICE_LENGTH * 0.15))
        for s in merged_slices:
            # 同一片二次切分出的子片沿用同一符号前缀，保证编码语义一致
            symbol = _extract_symbol(s)
            if len(s) <= MAX_SLICE_LENGTH:
                _emit(s, symbol)
                continue
            # .py 摘要片（阶段5瘦身）:超长函数/类不再二次切分成多片，仅保留"签名+文档+前若干行"一片
            if (file_name or "").lower().endswith(".py"):
                head = ""
                for line in s.split("\n"):
                    candidate = line if not head else head + "\n" + line
                    if len(candidate) > MAX_SLICE_LENGTH:
                        break
                    head = candidate
                _emit(head if head.strip() else s[:MAX_SLICE_LENGTH], symbol)
                continue
            # 超长片段:按行累加二次切分，片间保留约15%字符重叠，避免关键语句正好落在切口处漏检
            buf = ""
            for line in s.split("\n"):
                # 单行本身超过上限时先硬切，防止死循环
                while len(line) > MAX_SLICE_LENGTH:
                    if buf:
                        _emit(buf, symbol)
                        buf = ""
                    _emit(line[:MAX_SLICE_LENGTH], symbol)
                    line = line[MAX_SLICE_LENGTH:]
                candidate = line if not buf else buf + "\n" + line
                if len(candidate) > MAX_SLICE_LENGTH:
                    _emit(buf, symbol)
                    # 用上一片尾部约15%字符作为重叠，拼接当前行开启新片
                    buf = buf[-overlap_chars:] + "\n" + line
                else:
                    buf = candidate
            if buf.strip():
                _emit(buf, symbol)
        return result
    
    @_with_write_lock
    def add_file(self, file_path: str):
        """添加单个文件到RAG库，自动提取项目归属标签"""
        # 降级模式:无依赖时直接返回False，不执行向量操作
        if not HAS_RAG_DEPENDENCIES or self.emb_model is None:
            return False
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return False
        # 只处理代码文件和文档文件
        ext = os.path.splitext(file_path)[1].lower()
        # HTML已从RAG入库白名单移除:HTML含大量中文界面文本，可由findstr/read_file直接检索，无符号硬切碎片会稀释向量top_k
        if ext not in [".py", ".md", ".js", ".java", ".cpp", ".go", ".rs", ".txt", ".json", ".yaml", ".yml"]:
            return False
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except:
            return False
        
        # 提取项目名称:仓库根目录下的第一级文件夹为项目名
        repo_root = get_repository_path()
        abs_file_path = os.path.normpath(os.path.abspath(file_path)).replace("\\", "/")
        project_name = "default"
        if abs_file_path.startswith(repo_root):
            rel_path = os.path.relpath(abs_file_path, repo_root)
            if "/" in rel_path or os.sep in rel_path:
                project_name = rel_path.replace("\\", "/").split("/")[0]

        # 统一使用规范化的绝对正斜杠路径，避免同一文件因正/反斜杠差异重复入库
        self.delete_file(abs_file_path)
        # 切片并添加新索引
        slices = self._slice_code(content, abs_file_path, project_name)
        if not slices:
            return False
        # 生成embedding:使用带[文件][符号]前缀的 embed_text，并统一走 L2 归一化（与 IndexFlatIP 索引配套）
        texts = [s.get("embed_text") or s["content"] for s in slices]
        embs = self._encode(texts)
        # 按id写入索引与meta（IndexIDMap支持按id精确删除，id与meta key一一对应）
        ids = list(range(self.next_id, self.next_id + len(slices)))
        self.next_id += len(slices)
        self.index.add_with_ids(np.array(embs, dtype=np.float32), np.array(ids, dtype=np.int64))
        for _id, _slice in zip(ids, slices):
            # embed_text 体积大且只用于编码，落盘前剔除，避免索引文件膨胀
            self.meta[str(_id)] = {k: v for k, v in _slice.items() if k != "embed_text"}
        self._save_index()
        return True
    
    @_with_write_lock
    def delete_file(self, file_path: str):
        """删除单个文件的索引"""
        # 降级模式:无依赖时直接返回，不执行向量操作
        if not HAS_RAG_DEPENDENCIES or self.emb_model is None:
            return
        if not self.meta:
            return
        # 统一规范化为绝对正斜杠路径后比对，正/反斜杠差异的旧索引也能被正确删除
        norm_path = os.path.normpath(os.path.abspath(file_path)).replace("\\", "/")
        # 找出该文件对应的所有条目id，按id精确删除，避免对保留切片重新编码
        ids_to_remove = [int(k) for k, m in self.meta.items() if os.path.normpath(os.path.abspath(m["file_name"])).replace("\\", "/") == norm_path]
        if not ids_to_remove:
            return
        self.index.remove_ids(np.array(ids_to_remove, dtype=np.int64))
        for _id in ids_to_remove:
            self.meta.pop(str(_id), None)
        self._save_index()

    @_with_write_lock
    def delete_project(self, project_name: str):
        """删除指定项目的所有RAG索引"""
        # 降级模式:无依赖时直接返回，不执行向量操作
        if not HAS_RAG_DEPENDENCIES or self.emb_model is None:
            return
        if not self.meta:
            return
        # 过滤出所有属于该项目的片段id
        ids_to_remove = [int(k) for k, m in self.meta.items() if m.get("project_name", "default") == project_name]
        if not ids_to_remove:
            # 没有该项目的索引，直接返回
            return
        # 按id精确删除，避免对保留切片重新编码
        self.index.remove_ids(np.array(ids_to_remove, dtype=np.int64))
        for _id in ids_to_remove:
            self.meta.pop(str(_id), None)
        self._save_index()

    def clear_index(self):
        """清空RAG索引（供"清空+重建"复用）:重置内存空索引+清空meta+重置next_id+清空增量更新时间缓存并落盘

        关键:必须同时清掉 LAST_UPDATE_CACHE，否则重建时build_full_index会误判"所有文件均未修改"而跳过全部文件，得到空索引。
        """
        if not HAS_RAG_DEPENDENCIES or self.emb_model is None:
            return False
        with self._write_lock:
            self.index = faiss.IndexIDMap(faiss.IndexFlatIP(self.emb_dim))
            self.meta = {}
            self.next_id = 0
            LAST_UPDATE_CACHE.clear()
            self._save_index()
            _save_update_cache()
            return True

    @_with_write_lock
    def build_full_index(self, root_dir: str = None) -> Dict:
        """全量扫描项目目录构建索引，返回统计结果（优化版:增量校验+多线程预处理+批量生成向量）"""
        # 降级模式:无依赖时直接返回空结果，不执行向量操作
        if not HAS_RAG_DEPENDENCIES or self.emb_model is None:
            return {
                "code": 200,
                "success": 0,
                "fail": 0,
                "total": 0,
                "msg": "RAG功能已降级禁用，未安装torch/sentence_transformers依赖"
            }
        # 未指定扫描目录时，默认使用当前配置的仓库路径，支持动态配置更新
        if not root_dir:
            root_dir = get_repository_path()
        # 标准化路径格式，统一/分隔符
        root_dir = os.path.normpath(root_dir).replace("\\", "/")
        # 单文件入库大小上限（字节），来自 config.json 的 rag_max_file_size_kb，超限文件直接跳过
        max_file_size = get_max_file_size_bytes()
        # 第一步:收集所有符合条件的文件路径
        all_files = []
        for root, dirs, files in os.walk(root_dir):
            # 剪枝:排除虚拟环境/.git/打包产物等噪音目录，阻止递归进入（精确匹配，不再用"venv" in root子串误伤my_venv_tools类目录）
            file_filter_config.prune_walk_dirs(dirs)
            for file in files:
                # 文件级噪音过滤:统一复用 file_filter_config 配置中心黑名单（.pyc/.log/.tmp/.bak/.index/.min.js/.min.css 等）
                if file_filter_config.is_noise_file(file):
                    continue
                file_path = os.path.join(root, file)
                # 只处理支持的文件类型
                ext = os.path.splitext(file_path)[1].lower()
                # HTML已从RAG入库白名单移除:HTML含大量中文界面文本，可由findstr/read_file直接检索，无符号硬切碎片会稀释向量top_k
                if ext in [".py", ".md", ".js", ".java", ".cpp", ".go", ".rs", ".txt", ".json", ".yaml", ".yml"]:
                    # 超过单文件大小上限的跳过，避免超大 .min.js/大数据 .json 拖垮批量推理
                    try:
                        if os.path.getsize(file_path) > max_file_size:
                            continue
                    except:
                        continue
                    all_files.append(file_path)
        
        # 第二步：增量校验，过滤掉未修改的文件
        files_to_process = []
        for file_path in all_files:
            try:
                mtime = os.path.getmtime(file_path)
                if file_path not in LAST_UPDATE_CACHE or LAST_UPDATE_CACHE[file_path] != mtime:
                    files_to_process.append(file_path)
                    LAST_UPDATE_CACHE[file_path] = mtime
            except:
                continue
        
        if not files_to_process:
            # 无文件需要更新，直接返回
            return {
                "code": 200,
                "success": 0,
                "fail": 0,
                "total": 0,
                "msg": "所有文件均无修改，跳过全量更新"
            }
        
        # 第三步:多线程并行处理文件读取、切片、项目名提取（线程内只读+切片，不做任何索引写操作，避免并发竞态）
        def process_single_file(file_path: str):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # 提取项目名称
                repo_root = get_repository_path()
                abs_file_path = os.path.normpath(os.path.abspath(file_path)).replace("\\", "/")
                project_name = "default"
                if abs_file_path.startswith(repo_root):
                    rel_path = os.path.relpath(abs_file_path, repo_root)
                    if "/" in rel_path or os.sep in rel_path:
                        project_name = rel_path.replace("\\", "/").split("/")[0]
                # 切片（统一使用规范化的绝对正斜杠路径作为 file_name）
                slices = self._slice_code(content, abs_file_path, project_name)
                return (abs_file_path, slices)
            except:
                return (file_path, [])
        
        all_slices = []
        success_count = 0
        fail_count = 0
        success_files = []
        # max_workers=3适配4核CPU，留1个核心给模型推理和系统
        with ThreadPoolExecutor(max_workers=3) as executor:
            for file_path, slices in executor.map(process_single_file, files_to_process):
                if slices:
                    all_slices.extend(slices)
                    success_files.append(file_path)
                    success_count += 1
                else:
                    fail_count += 1
        
        # 主线程串行清理:按id一次性移除所有成功处理文件的旧切片，根除增量重编码与并发写盘竞态
        if success_files:
            norm_targets = {os.path.normpath(os.path.abspath(fp)).replace("\\", "/") for fp in success_files}
            ids_to_remove = [int(k) for k, m in self.meta.items() if os.path.normpath(os.path.abspath(m["file_name"])).replace("\\", "/") in norm_targets]
            if ids_to_remove:
                self.index.remove_ids(np.array(ids_to_remove, dtype=np.int64))
                for _id in ids_to_remove:
                    self.meta.pop(str(_id), None)
        
        if not all_slices:
            self._save_index()
            _save_update_cache()
            return {
                "code": 200,
                "success": success_count,
                "fail": fail_count,
                "total": success_count + fail_count
            }
        
        # 第四步:批量生成向量，按id一次性添加到索引
        texts = [s.get("embed_text") or s["content"] for s in all_slices]
        # 批量推理 batch_size=32 适配CPU；编码统一走 _encode（L2归一化，与IP索引配套）
        embs = self._encode(texts, batch_size=32)
        # 按id写入索引与meta，与 IndexIDMap 的 id 一一对应
        ids = list(range(self.next_id, self.next_id + len(all_slices)))
        self.next_id += len(all_slices)
        self.index.add_with_ids(np.array(embs, dtype=np.float32), np.array(ids, dtype=np.int64))
        for _id, _slice in zip(ids, all_slices):
            # embed_text 只参与编码，落盘前剔除，避免索引文件膨胀
            self.meta[str(_id)] = {k: v for k, v in _slice.items() if k != "embed_text"}
        # 仅一次写入磁盘
        self._save_index()
        # 文件更新时间缓存落盘，下次启动可继续走增量，避免全量重算
        _save_update_cache()
        
        return {
            "code": 200,
            "success": success_count,
            "fail": fail_count,
            "total": success_count + fail_count,
            "process_file_count": len(files_to_process),
            "slice_count": len(all_slices)
        }
    
    def search(self, query: str, top_k: int = TOP_K, project_name: str = None) -> List[Dict]:
        """检索相关代码片段，支持按项目过滤

        混合检索（解决"标识符查不到 + 本项目结果被挤出榜单 + score 无区分度"）:
        1) 向量通道:归一化向量 + IndexFlatIP，内积即余弦相似度，候选池放大到 top_k*20 后再按项目过滤；
        2) 词面通道:query 中的标识符/中文短语在 meta 原文做精确子串召回，补上向量通道的词面短板；
        3) RRF 融合:两路结果按排名倒数融合，量纲无关，兼顾语义与字面命中；
        4) score:统一输出 0~1 的余弦相似度，纯词面命中按 0.5 保底，便于前端设阈值。
        """
        # 降级模式:无依赖时直接返回空列表，不执行向量操作
        if not HAS_RAG_DEPENDENCIES or self.emb_model is None:
            return []
        if not self.meta:
            return []
        # 候选池放大:先大范围召回，最后才按项目过滤截断，避免本项目结果被其它项目挤掉
        pool_k = max(top_k * 20, 50)

        def _clamp(v: float) -> float:
            """余弦相似度裁剪到 0~1（方向相反的负值按 0 处理）"""
            return max(0.0, min(1.0, float(v)))

        # ---------- 通道1:向量召回（归一化向量，内积即余弦相似度，越大越相关） ----------
        query_emb = self._encode([query])
        scores, indices = self.index.search(np.array(query_emb, dtype=np.float32), pool_k)
        vec_score = {}
        for rank, idx in enumerate(indices[0]):
            if idx == -1:
                continue
            key = str(int(idx))
            if key in vec_score or key not in self.meta:
                continue
            vec_score[key] = _clamp(scores[0][rank])
        vec_ids = sorted(vec_score.keys(), key=lambda k: vec_score[k], reverse=True)

        # ---------- 通道2:词面召回（标识符/中文短语精确匹配，补词面兜底能力） ----------
        lexical_ids = []
        tokens = self._extract_query_tokens(query)
        if tokens:
            hits = {}
            for key, item in self.meta.items():
                content = item.get("content") or ""
                if not content:
                    continue
                # 大小写不敏感匹配:英文token统一小写比对，避免 upload 漏掉 UPLOAD_ROOT 这类大写常量
                content_lower = content.lower()
                matched = [t for t in tokens if t.lower() in content_lower]
                if not matched:
                    continue
                # 最长命中片段优先，其次看命中词数:长片段（如4-gram"下载任务"）比2-gram碎片（"任务"）区分度高
                hits[key] = (max(len(t) for t in matched), len(matched))
            lexical_ids = sorted(hits.keys(), key=lambda k: hits[k], reverse=True)[:pool_k]

        # ---------- RRF 融合:两路排名倒数相加，天然屏蔽两路分数量纲差异 ----------
        RRF_K = 60
        # 词面通道权重:与向量等权(1.0)。原3.0会把文档中泛词命中放大3倍，导致.md文档霸榜、
        # 语义相关的代码片被挤出榜单；等权后向量通道有机会把代码顶上来。
        LEXICAL_WEIGHT = 1.0
        fused = {}
        for rank, key in enumerate(vec_ids, start=1):
            fused[key] = fused.get(key, 0.0) + 1.0 / (RRF_K + rank)
        for rank, key in enumerate(lexical_ids, start=1):
            fused[key] = fused.get(key, 0.0) + LEXICAL_WEIGHT / (RRF_K + rank)

        results = []
        for key in sorted(fused.keys(), key=lambda k: fused[k], reverse=True):
            item = self.meta.get(key)
            if item is None:
                continue
            # 按项目过滤:先融合排序、再过滤截断，保证本项目结果不会被别项目挤空
            if project_name and item.get("project_name") != project_name:
                continue
            res = item.copy()
            # score 统一为余弦相似度（0~1）；纯词面命中的切片按 0.5 保底，与向量分数保持同一量级
            res["score"] = round(vec_score.get(key, 0.5), 4)
            results.append(res)
            if len(results) >= top_k:
                break
        return results

    @staticmethod
    def _extract_query_tokens(query: str) -> List[str]:
        """从查询语句中抽取用于词面精确匹配的关键片段（保守抽取，避免噪音词把榜单刷满）

        规则:
        1) 强英文标识符:含下划线/数字/驼峰，或长度>=6，且不在通用关键字黑名单里（add_file、KMP_DUPLICATE_LIB_OK、CodeRAGManager）；
        2) 中文连续片段:长度>=4（如"全量构建项目代码"），用于中文原文兜底召回。
        """
        import re
        text = query or ""
        # 常见标点归一为空格，避免标识符与中文粘连
        for _ch in (":", "，", "。", "、", "（", "）", "(", ")", "?", "!"):
            text = text.replace(_ch, " ")
        stop_words = {
            "return", "import", "class", "print", "while", "break", "yield", "async",
            "await", "lambda", "static", "string", "object", "number", "function",
            "python", "windows", "script", "self", "none", "true", "false"
        }
        tokens = []
        for m in re.finditer(r"[A-Za-z_][A-Za-z0-9_.]{3,}", text):
            token = m.group(0)
            if token.lower() in stop_words:
                continue
            # 只保留有区分度的标识符:带下划线/数字/驼峰，或长度>=6
            has_mark = ("_" in token) or any(c.isdigit() for c in token) or any(c.isupper() for c in token[1:])
            if has_mark or len(token) >= 6:
                tokens.append(token)
        # 中文停用词/意图词:疑问词、助词、泛化词，先剥离再切分，避免长句整串永不匹配、泛词刷榜
        zh_stop_words = (
            "哪个函数", "在哪里", "什么地方", "哪个", "哪些", "什么", "怎么", "如何",
            "在哪", "哪里", "哪儿", "是否", "这个", "那个", "这些", "那些", "一下",
            "请问", "帮我", "找到", "搜索", "查找", "检索", "负责", "实现", "处理",
            "完成", "进行", "用于", "用来", "可以", "能够", "需要", "调用", "使用",
            "定义", "位置", "地方", "函数", "方法", "代码", "文件", "功能",
            "上传", "下载", "清理", "目录", "路径", "设置", "配置", "数据", "记录",
            "信息", "系统", "任务", "状态", "列表", "管理", "保存", "读取", "写入",
            "删除", "添加", "更新", "修改", "创建", "自动"
        )
        zh_text = text
        for _w in sorted(zh_stop_words, key=len, reverse=True):
            zh_text = zh_text.replace(_w, " ")
        for m in re.finditer(r"[\u4e00-\u9fa5]{3,}", zh_text):
            seg = m.group(0)
            # 长串保留整串(兼容原行为)，并补 3~4-gram 片段兜底:最短3字，砍掉2字泛词(如"上传""清理")刷榜
            if len(seg) >= 4:
                tokens.append(seg)
            for n in (3, 4):
                for i in range(len(seg) - n + 1):
                    tokens.append(seg[i:i + n])
        # 去重保序
        seen = set()
        uniq = []
        for t in tokens:
            if t not in seen:
                seen.add(t)
                uniq.append(t)
        return uniq

# 全局单例
rag_manager = CodeRAGManager()