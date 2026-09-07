# -*- coding: utf-8 -*-
"""
添加文件到RAG库，自动提取项目归属标签
"""
import os
import json
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict

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
# 嵌入模型路径改为基于程序目录的绝对路径
EMB_MODEL_NAME = os.path.join(_BASE_DIR, "gte-small-zh")
MAX_SLICE_LENGTH = 512  # 每个代码片段最大长度
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
            print(f"⚠️ RAG模块读取仓库路径配置失败，使用默认路径:{str(e)}")
    # 配置不存在时自动创建默认目录
    os.makedirs(default_repo, exist_ok=True)
    return default_repo
class CodeRAGManager:
    def __init__(self):
        # 自动创建RAG目录
        os.makedirs(RAG_DIR, exist_ok=True)
        
        # 降级模式:无外部依赖时不初始化模型，直接返回空壳
        if not HAS_RAG_DEPENDENCIES:
            print("⚠️ [RAG] 未检测到torch/sentence_transformers依赖，代码RAG知识库功能已降级禁用")
            self.emb_model = None
            self.emb_dim = 0
            self.index = None
            self.meta = []
            return
        
        try:
            # 加载embedding模型，默认用CPU，要GPU的话去掉device参数
            self.emb_model = SentenceTransformer(EMB_MODEL_NAME, device="cpu")
            # 限制PyTorch CPU线程数，留1个核心给系统，避免CPU跑满卡顿
            torch.set_num_threads(max(1, torch.get_num_threads() - 1))
            # 动态获取模型实际输出维度，适配所有模型
            if hasattr(self.emb_model, 'get_sentence_embedding_dimension'):
                self.emb_dim = self.emb_model.get_sentence_embedding_dimension()
            else:
                self.emb_dim = self.emb_model.get_embedding_dimension()

            # 加载/初始化索引，新增损坏自动重建容错
            try:
                if os.path.exists(INDEX_PATH) and os.path.exists(META_PATH):
                    self.index = faiss.read_index(INDEX_PATH)
                    with open(META_PATH, "r", encoding="utf-8") as f:
                        self.meta = json.load(f)
                else:
                    raise Exception("索引文件不存在，自动重建")
            except Exception as e:
                # 索引不存在/损坏/读取失败时自动重建
                self.index = faiss.IndexFlatL2(self.emb_dim)
                self.meta = []
                self._save_index()
        except Exception as e:
            # 模型加载失败时降级为空壳，避免启动崩溃
            print(f"⚠️ [RAG] 模型加载失败，代码RAG知识库功能已降级禁用:{str(e)}")
            self.emb_model = None
            self.emb_dim = 0
            self.index = None
            self.meta = []
    
    def _save_index(self):
        """保存索引和元数据到本地"""
        faiss.write_index(self.index, INDEX_PATH)
        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump(self.meta, f, ensure_ascii=False, indent=2)
    
    def _slice_code(self, content: str, file_name: str, project_name: str = "default") -> List[Dict]:
        """代码切片：按函数/类拆分，每个片段不超过MAX_SLICE_LENGTH，新增项目归属标签"""
        slices = []
        # 简单切片规则：按def/class拆分，也可以后续换成tree-sitter做精准解析
        raw_slices = content.split("\ndef ") + content.split("\nclass ")
        for i, s in enumerate(raw_slices):
            if not s.strip():
                continue
            # 补全拆分丢失的前缀
            if i > 0 and raw_slices[i-1].strip():
                if s.startswith("def "):
                    s = "def " + s
                elif s.startswith("class "):
                    s = "class " + s
            # 超过最大长度的截断
            if len(s) > MAX_SLICE_LENGTH:
                s = s[:MAX_SLICE_LENGTH] + "..."
            slices.append({
                "content": s,
                "file_name": file_name,
                "project_name": project_name,
                "slice_idx": i
            })
        return slices
    
    def add_file(self, file_path: str):
        """添加单个文件到RAG库，自动提取项目归属标签"""
        # 降级模式:无依赖时直接返回False，不执行向量操作
        if not HAS_RAG_DEPENDENCIES or self.emb_model is None:
            return False
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return False
        # 只处理代码文件和文档文件
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in [".py", ".md", ".js", ".html", ".css", ".java", ".cpp", ".go", ".rs", ".txt", ".json", ".yaml", ".yml"]:
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

        # 删除该文件旧的索引
        self.delete_file(file_path)
        # 切片并添加新索引
        slices = self._slice_code(content, file_path, project_name)
        if not slices:
            return False
        # 生成embedding
        texts = [s["content"] for s in slices]
        embs = self.emb_model.encode(texts)
        # 添加到索引
        self.index.add(np.array(embs))
        self.meta.extend(slices)
        self._save_index()
        return True
    
    def delete_file(self, file_path: str):
        """删除单个文件的索引"""
        # 降级模式:无依赖时直接返回，不执行向量操作
        if not HAS_RAG_DEPENDENCIES or self.emb_model is None:
            return
        if not self.meta:
            return
        # 找到所有该文件的片段索引
        indices_to_keep = [i for i, m in enumerate(self.meta) if m["file_name"] != file_path]
        if len(indices_to_keep) == len(self.meta):
            return
        # 重建索引（faiss不支持删除，数据量小直接重建成本很低）
        new_meta = [self.meta[i] for i in indices_to_keep]
        embs = self.emb_model.encode([m["content"] for m in new_meta])
        self.index = faiss.IndexFlatL2(self.emb_dim)
        if embs.size > 0:
            self.index.add(embs)
        self.meta = new_meta
        self._save_index()

    def delete_project(self, project_name: str):
        """删除指定项目的所有RAG索引"""
        # 降级模式:无依赖时直接返回，不执行向量操作
        if not HAS_RAG_DEPENDENCIES or self.emb_model is None:
            return
        if not self.meta:
            return
        # 过滤掉所有属于该项目的片段
        indices_to_keep = [i for i, m in enumerate(self.meta) if m.get("project_name", "default") != project_name]
        if len(indices_to_keep) == len(self.meta):
            # 没有该项目的索引，直接返回
            return
        # 重建索引
        new_meta = [self.meta[i] for i in indices_to_keep]
        embs = self.emb_model.encode([m["content"] for m in new_meta])
        self.index = faiss.IndexFlatL2(self.emb_dim)
        if embs.size > 0:
            self.index.add(embs)
        self.meta = new_meta
        self._save_index()

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
        # 第一步:收集所有符合条件的文件路径
        all_files = []
        for root, dirs, files in os.walk(root_dir):
            # 跳过不需要扫描的目录
            if any(skip in root for skip in [".git", "__pycache__", "venv", "node_modules", "code_rag", "logs"]):
                continue
            for file in files:
                file_path = os.path.join(root, file)
                # 只处理支持的文件类型
                ext = os.path.splitext(file_path)[1].lower()
                if ext in [".py", ".md", ".js", ".html", ".css", ".java", ".cpp", ".go", ".rs", ".txt", ".json", ".yaml", ".yml"]:
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
        
        # 第三步：多线程并行处理文件读取、切片、项目名提取
        def process_single_file(file_path: str) -> List[Dict]:
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
                # 切片
                slices = self._slice_code(content, file_path, project_name)
                # 先删除该文件旧索引
                self.delete_file(file_path)
                return slices
            except:
                return []
        
        all_slices = []
        success_count = 0
        fail_count = 0
        # max_workers=3适配4核CPU，留1个核心给模型推理和系统
        with ThreadPoolExecutor(max_workers=3) as executor:
            for slices in executor.map(process_single_file, files_to_process):
                if slices:
                    all_slices.extend(slices)
                    success_count += 1
                else:
                    fail_count += 1
        
        if not all_slices:
            self._save_index()
            return {
                "code": 200,
                "success": success_count,
                "fail": fail_count,
                "total": success_count + fail_count
            }
        
        # 第四步：批量生成向量，一次性添加到索引
        texts = [s["content"] for s in all_slices]
        # 批量推理，batch_size=32适配CPU，效率最高
        embs = self.emb_model.encode(texts, batch_size=32)
        self.index.add(np.array(embs))
        self.meta.extend(all_slices)
        # 仅一次写入磁盘
        self._save_index()
        
        return {
            "code": 200,
            "success": success_count,
            "fail": fail_count,
            "total": success_count + fail_count,
            "process_file_count": len(files_to_process),
            "slice_count": len(all_slices)
        }
    
    def search(self, query: str, top_k: int = TOP_K, project_name: str = None) -> List[Dict]:
        """检索相关代码片段，支持按项目过滤"""
        # 降级模式:无依赖时直接返回空列表，不执行向量操作
        if not HAS_RAG_DEPENDENCIES or self.emb_model is None:
            return []
        if not self.meta:
            return []
        query_emb = self.emb_model.encode([query])
        distances, indices = self.index.search(query_emb, top_k*2)  # 多查一倍结果方便过滤
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.meta):
                res = self.meta[idx].copy()
                # 按项目过滤
                if project_name and res.get("project_name") != project_name:
                    continue
                res["score"] = float(1 - distances[0][i]/10)  # 转换为0-1的相似度得分
                results.append(res)
                if len(results) >= top_k:
                    break
        return results

# 全局单例
rag_manager = CodeRAGManager()