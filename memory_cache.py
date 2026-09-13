"""
向量记忆库
"""
try:
    import faiss
except ImportError:
    faiss = None
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None
try:
    import numpy as np
except ImportError:
    np = None
    print("⚠️ numpy模块未加载，向量检索功能不可用，仅保留元数据记忆功能")
import json
import os
import sys
import re
import time
from typing import List, Dict

class MemoryCache:
    def __init__(self, meta_path: str = "./memory_meta.json", config_path: str = "./memory_config.json"):
        # 加载配置文件
        self.config_path = config_path
        self.load_config()
        # 加载工具配置
        self.load_tools()
        self.meta_path = meta_path
        self.index_path = "./memory_index.faiss"
        self.encoder = None
        self.index_dim = 512 # 默认维度，后续根据编码器动态覆盖
        
        # 初始化向量编码器:优先本地中文模型，加载失败自动降级，确保模块不崩溃
        if SentenceTransformer is None or np is None:
            if np is None:
                print("⚠️ numpy模块未加载，向量检索功能不可用，仅保留元数据记忆")
            else:
                print("⚠️ sentence_transformers模块未加载，向量检索功能不可用，仅保留元数据记忆")
            self.encoder = None
        else:
            try:
                # 兼容打包环境:PyInstaller打包后资源文件在sys._MEIPASS（_internal目录）下
                model_path = './gte-small-zh'
                if getattr(sys, 'frozen', False):
                    # 打包环境优先从_internal目录查找模型
                    internal_model_path = os.path.join(sys._MEIPASS, 'gte-small-zh')
                    if os.path.exists(internal_model_path):
                        model_path = internal_model_path
                        print(f"🔧 加载打包环境本地中文语义向量模型:{model_path}")
                    elif os.path.exists('./gte-small-zh'):
                        # 兼容用户手动把模型放到exe同级目录的场景
                        model_path = './gte-small-zh'
                        print(f"🔧 加载本地中文语义向量模型:{model_path}")
                    else:
                        print("⚠️ 本地gte-small-zh模型不存在，自动加载轻量多语言向量模型（首次运行会自动下载缓存）")
                        model_path = 'paraphrase-multilingual-MiniLM-L12-v2'
                else:
                    # 开发环境直接用项目根目录路径
                    if os.path.exists('./gte-small-zh'):
                        print("🔧 加载本地中文语义向量模型:./gte-small-zh")
                    else:
                        print("⚠️ 本地gte-small-zh模型不存在，自动加载轻量多语言向量模型（首次运行会自动下载缓存）")
                        model_path = 'paraphrase-multilingual-MiniLM-L12-v2'
                self.encoder = SentenceTransformer(model_path, device='cpu')
                # 动态获取向量维度，避免硬编码维度不匹配问题
                test_vec = self.encoder.encode(["测试"])
                self.index_dim = test_vec.shape[1]
                print(f"✅ 向量模型加载完成，向量维度:{self.index_dim}")
            except Exception as e:
                print(f"❌ 向量模型加载失败:{str(e)}，记忆召回功能暂时不可用，其他功能正常")
                self.encoder = None
        
        # 加载或创建FAISS索引
        if faiss is not None:
            if os.path.exists(self.index_path):
                try:
                    self.index = faiss.read_index(self.index_path)
                    # 校验索引维度和编码器维度是否匹配，不匹配则重建
                    if self.encoder is not None and self.index.d != self.index_dim:
                        print(f"⚠️ 索引维度{self.index.d}与模型维度{self.index_dim}不匹配，将自动重建索引")
                        os.remove(self.index_path)
                        self.index = faiss.IndexFlatL2(self.index_dim)
                except Exception as e:
                    print(f"❌ 加载已有索引失败:{str(e)}，将重建空索引")
                    self.index = faiss.IndexFlatL2(self.index_dim)
            else:
                self.index = faiss.IndexFlatL2(self.index_dim)
        else:
            print("⚠️ faiss模块未加载，向量检索功能不可用，仅保留元数据记忆")
            self.index = None
        
        # 加载记忆元数据，兼容旧版列表格式
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    self.meta = json.load(f)
                # 兼容旧版列表格式的meta文件，自动转换为字典结构
                if isinstance(self.meta, list):
                    new_meta = {}
                    for idx, item in enumerate(self.meta):
                        new_meta[str(idx)] = item
                    self.meta = new_meta
                    print("🔄 已自动兼容旧版记忆元数据格式，转换为字典结构")
            except Exception as e:
                print(f"❌ 加载记忆元数据失败:{str(e)}，初始化为空记忆库")
                self.meta = {}
        else:
            self.meta = {}
        
        # 修复ID空洞问题:取当前最大ID+1作为下一个ID，避免删除记忆后新ID覆盖旧记忆
        if self.meta:
            self.next_id = max(int(k) for k in self.meta.keys()) + 1
        else:
            self.next_id = 0
        
        # 编码器和索引均可用时，执行索引重建/校验逻辑
        if self.encoder is not None and self.index is not None:
            # 如果是新建索引（索引为空但有历史记忆），自动把所有历史记忆重新编码加入索引
            if self.index.ntotal == 0 and len(self.meta) > 0:
                print(f"🔄 检测到索引为空，正在重建{len(self.meta)}条历史记忆的向量索引...")
                vectors = []
                for mem in self.meta.values():
                    vec = self.encoder.encode([self._encode_text(mem["content"])])[0].astype('float32')
                    vec = vec / np.linalg.norm(vec)
                    vectors.append(vec)
                self.index.add(np.array(vectors))
                print("✅ 历史记忆索引重建完成")
        
        # 初始化完成后立即持久化，确保首次启动就生成faiss索引和meta文件
        self._save()
        print(f"✅ 记忆库初始化完成，当前共{len(self.meta)}条记忆，索引文件已持久化到{self.index_path}")

    def _compress_tool_content(self, content: str) -> str:
        """超长记忆工具内容压缩:仅截断工具调用的target_block和content字段到500字符，其他内容完全保留
        触发阈值:内容长度超过配置的tool_content_truncate_threshold值（默认1000000字符，相当于不触发截断），大小写不敏感匹配字段名，兼容中英文冒号
        """
        # 长度未超过阈值直接返回原内容，不做任何处理，阈值从配置读取，默认100万字符不截断
        truncate_threshold = self.config.get("tool_content_truncate_threshold", 1000000)
        if len(content) <= truncate_threshold:
            return content
        
        truncate_mark = "[...该工具调用内容过长已截断，仅保留前500字符，如需查看完整内容可读取对应文件获取最新版本]"
        # 字段截断处理逻辑：内容不超过500字符不处理，超过则截断加标记
        def truncate_field(match):
            field_prefix = match.group(1)  # 字段名+冒号部分
            field_content = match.group(2) # 字段内容部分
            if len(field_content) <= 500:
                return match.group(0)
            return f"{field_prefix}{field_content[:500]}{truncate_mark}"
        
        # 匹配target_block字段：大小写不敏感，兼容中文/英文冒号，非贪婪匹配到下一个参数/工具调用结束/字符串末尾
        content = re.sub(
            r'(target_block\s*[:：]\s*)(.*?)(?=\n\s*[a-zA-Z_]+[:：]|\n【工具调用结束】|\Z)',
            truncate_field,
            content,
            flags=re.IGNORECASE | re.DOTALL
        )
        # 匹配content字段：大小写不敏感，兼容中文/英文冒号，非贪婪匹配到下一个参数/工具调用结束/字符串末尾
        content = re.sub(
            r'(content\s*[:：]\s*)(.*?)(?=\n\s*[a-zA-Z_]+[:：]|\n【工具调用结束】|\Z)',
            truncate_field,
            content,
            flags=re.IGNORECASE | re.DOTALL
        )
        # 压缩完成直接返回，不做二次长度校验
        return content

    def _clean_recall_content(self, content: str) -> str:
        """清洗历史关联召回记忆:移除工具调用/执行结果/轮次标记等流水账模板，仅保留用户问题与AI自然语言回答"""
        # 1. 移除工具调用块（【工具调用开始】...【工具调用结束】）
        content = re.sub(r'【工具调用开始】.*?【工具调用结束】', '', content, flags=re.DOTALL)
        # 2. 移除工具执行结果块（兼容指令/执行结果多种格式与中英文冒号，直到遇到下一个对话标识或文本结束）
        content = re.sub(r'(🔹 指令\d+执行结果[：:]|🔹 执行结果[：:]|工具执行结果[：:]).*?(?=\n【工具调用开始】|\n用户问|\nAI回答|\nAI输出|\Z)', '', content, flags=re.DOTALL)
        # 3. 移除多轮交互标记与AI输出前缀等模板噪声
        content = re.sub(r'【第\d+轮交互】', '', content)
        content = re.sub(r'AI输出[：:]', '', content)
        # 4. 移除进度统计行（真实格式为"📊 当前进度:第x次/..."，emoji后与冒号前允许空格，兼容全/半角冒号）
        content = re.sub(r'📊\s*当前进度\s*[:\uFF1A].*', '', content)
        # 5. 移除每条记忆共有的对话骨架标签（行首"用户问:/回答:/AI回答:"），仅删标签，问题与回答正文完整保留
        content = re.sub(r'(?:^|\n)[ \t]*(?:用户问|AI回答|回答)[ \t]*[:\uFF1A][ \t]*', '\n', content)
        # 6. 清理多余的空行，保持文本紧凑
        content = re.sub(r'\n{3,}', '\n\n', content).strip()
        return content

    def _encode_text(self, content: str) -> str:
        """向量编码统一入口:入库文本先去噪（剥离工具调用/执行结果/轮次标记/进度统计等模板噪声），
        只保留用户问题+AI自然语言回答作为向量语义来源，解决流水账共性文本稀释语义、不同主题向量挤在一起的问题。
        仅用于向量编码:meta中仍保存完整原文，记忆展示/导出零信息丢失；去噪后为空（纯工具轮次）时回退原文，避免空向量。
        """
        cleaned = self._clean_recall_content(content)
        return cleaned if cleaned else content
    def add_memory(self, content: str, tags: List[str] = None, session_id: str = None) -> int:
        """新增记忆到缓存，支持绑定会话ID，自动加毫秒级时间戳"""
        # 超长记忆自动压缩工具调用冗余内容
        content = self._compress_tool_content(content)
        # 绑定会话ID到标签，方便按会话筛选
        if session_id:
            tags = tags or []
            tags.append(f"session:{session_id}")
        
        memory_id = self.next_id
        # 写入元数据，新增时间戳和会话ID字段（元数据始终保存，不受向量模型影响）
        self.meta[str(memory_id)] = {
            "content": content,
            "tags": tags or [],
            "session_id": session_id,
            "timestamp": int(time.time() * 1000),
            "call_count": 0,
            "create_time": str(os.times()[4]),
            "last_call_time": str(os.times()[4]),
            "synced_to_lora": False
        }
        self.next_id += 1
        
        # 编码器和索引均可用时才写入向量索引，不可用仅存元数据不报错
        if self.encoder is not None and self.index is not None:
            try:
                # 向量编码统一走去噪入口，生成向量并归一化，统一距离尺度到0~2范围
                vector = self.encoder.encode([self._encode_text(content)])[0].astype('float32')
                vector = vector / np.linalg.norm(vector)
                # 写入FAISS
                self.index.add(np.array([vector]))
            except Exception as e:
                print(f"⚠️ 记忆向量写入失败，仅保存元数据:{str(e)}")
        
        # 持久化
        self._save()
        return memory_id

    def get_session_history(self, session_id: str, rounds: int = 10) -> List[Dict]:
        """获取指定会话的最近N轮历史，按时间倒序排列，彻底解决时间错位问题"""
        session_memories = []
        for mem in self.meta.values():
            if mem.get("session_id") == session_id:
                session_memories.append(mem)
        # 按时间戳倒序排序，取最近N轮
        session_memories.sort(key=lambda x: x["timestamp"], reverse=True)
        return session_memories[:rounds]

    def recall_memory(self, query: str, top_k: int = None, threshold: float = None, **kwargs) -> Dict:
        """召回相关记忆：返回固定召回+向量召回两部分内容，互相独立不干扰"""
        # 优先使用传入参数，没有则用配置文件参数
        top_k = top_k if top_k is not None else self.config["recall_top_k"]
        threshold = threshold if threshold is not None else self.config["similarity_threshold"]
        context_rounds = self.config["history_context_rounds"]

        # --------------------------
        # 前置过滤：排除最近N轮（已在上下文里的）记忆，避免重复召回
        # --------------------------
        # 所有记忆按时间倒序排列，取最近N轮的最小时间戳，大于等于该时间的记忆已经在上下文中，不需要召回
        all_memories_sorted = sorted(self.meta.values(), key=lambda x: x["timestamp"], reverse=True)
        exclude_timestamp_threshold = all_memories_sorted[context_rounds-1]["timestamp"] if len(all_memories_sorted) >= context_rounds else 0
        
        # --------------------------
        # 第一步:获取固定召回内容（工具+预留位），无论向量模型是否可用都正常返回
        # --------------------------
        fixed_results = self.get_fixed_recall()
        memory_results = []
        
        # 编码器或索引不可用时直接返回固定召回，不执行向量检索，避免报错
        if self.encoder is None or self.index is None:
            print(f"[DEBUG 记忆检索] 向量模型或索引未加载，仅返回固定召回内容，条数:{len(fixed_results)}")
            return {
                "fixed_recall": fixed_results,
                "memory_recall": [],
                "context_rounds": context_rounds
            }
        
        try:
            # --------------------------
            # 前置过滤:排除最近N轮（已在上下文里的）记忆，避免重复召回
            # --------------------------
            # 所有记忆按时间倒序排列，取最近N轮的最小时间戳，大于等于该时间的记忆已经在上下文中，不需要召回
            all_memories_sorted = sorted(self.meta.values(), key=lambda x: x["timestamp"], reverse=True)
            exclude_timestamp_threshold = all_memories_sorted[context_rounds-1]["timestamp"] if len(all_memories_sorted) >= context_rounds else 0
            
            # 生成查询向量并归一化，统一距离尺度到0~2范围
            query_vector = self.encoder.encode([query])[0].astype('float32')
            query_vector = query_vector / np.linalg.norm(query_vector)
            
            # --------------------------
            # 第二步:向量召回相关记忆（带模糊query增强+精确实体加权+时间衰减+标签权重）
            # --------------------------

            # 1. 提取精确实体（文件名、路径、错误码、配置项）
            def extract_entities(text: str) -> set:
                entities = set()
                if not text:
                    return entities
                # 匹配带后缀的文件名
                entities.update(re.findall(r'\b[\w-]+\.(?:py|html|json|md|txt|js|css|yaml|yml|ini|bat|sh|exe|dll)\b', text, re.IGNORECASE))
                # 匹配Windows/Unix路径
                entities.update(re.findall(r'(?:[a-zA-Z]:\\|/)[\w\\/.-]+', text))
                # 匹配错误码/常量（大写+下划线+数字）
                entities.update(re.findall(r'\b[A-Z_]{2,}[0-9]*\b', text))
                # 匹配下划线格式配置项
                entities.update(re.findall(r'\b[a-z][a-z0-9_]{2,}_[a-z0-9_]+\b', text))
                return entities
            
            # 从query+最近上下文中提取实体
            last_user_input = kwargs.get("last_user_input", "")
            context_for_entity = f"{query} {last_user_input}"
            target_entities = extract_entities(context_for_entity)
            current_project = kwargs.get("project_name", "default")
            
            # 2. 第一次检索：原始query
            search_k = top_k * 3  # 多查3倍数据用于加权排序
            distances, indices = self.index.search(np.array([query_vector]), search_k)
            candidate_map = {}  # key: idx, value: (distance, mem) 用于去重合并两次检索结果
            
            # 阈值按余弦相似度解释:归一化向量满足 cos=1-d²/2，换算为L2距离平方硬门槛（如0.85对应d²<=0.3）
            cos_limit = 1.0 - threshold
            # 处理第一次检索结果
            for i, idx in enumerate(indices[0]):
                if str(idx) in self.meta and distances[0][i] <= cos_limit:
                    candidate_map[idx] = (distances[0][i], self.meta[str(idx)])
            
            # 3. 模糊query二次检索：如果第一次候选没有匹配到任何实体，且有上一轮用户输入，拼接上下文再搜一次
            need_second_search = True
            if target_entities:
                # 检查现有候选是否有匹配的实体
                for dist, mem in candidate_map.values():
                    mem_content = mem["content"]
                    if any(ent.lower() in mem_content.lower() for ent in target_entities):
                        need_second_search = False
                        break
            if need_second_search and last_user_input.strip():
                # 拼接上一轮用户输入生成增强query
                enhanced_query = f"{last_user_input} {query}"
                enhanced_vector = self.encoder.encode([enhanced_query])[0].astype('float32')
                enhanced_vector = enhanced_vector / np.linalg.norm(enhanced_vector)
                distances2, indices2 = self.index.search(np.array([enhanced_vector]), search_k)
                # 合并第二次检索结果，保留更小的距离
                for i, idx in enumerate(indices2[0]):
                    if str(idx) in self.meta and distances2[0][i] <= cos_limit:
                        if idx not in candidate_map or distances2[0][i] < candidate_map[idx][0]:
                            candidate_map[idx] = (distances2[0][i], self.meta[str(idx)])
            
            # 4. 对所有候选计算最终得分，执行加权
            scored_candidates = []
            now_ts = int(time.time() * 1000)
            for idx, (orig_dist, mem) in candidate_map.items():
                # 项目隔离过滤：非当前项目的记忆直接跳过
                has_project_tag = any(tag.startswith("project:") for tag in mem.get("tags", []))
                if has_project_tag and not any(tag == f"project:{current_project}" for tag in mem.get("tags", [])):
                    continue
                # 最近上下文过滤：已经在上下文里的跳过
                if mem["timestamp"] >= exclude_timestamp_threshold:
                    continue
                # 计算最终得分（距离越小越相关）
                score = orig_dist
                # ① 时间衰减权重
                age_days = (now_ts - mem["timestamp"]) / (1000 * 3600 * 24)
                if age_days > 180:
                    score += 0.2
                elif age_days > 30:
                    score += 0.1
                elif age_days > 7:
                    score += 0.05
                # ② 标签权重加成
                mem_tags = [t.lower() for t in mem.get("tags", [])]
                tag_bonus = 0
                if "bug修复" in mem_tags or "配置说明" in mem_tags or "核心规则" in mem_tags:
                    tag_bonus += 0.1
                if f"project:{current_project}" in mem_tags:
                    tag_bonus += 0.15
                score -= tag_bonus
                # ③ 精确实体匹配加分：每匹配一个实体减0.1，最多减0.3
                entity_match = 0
                mem_content_lower = mem["content"].lower()
                for ent in target_entities:
                    if ent.lower() in mem_content_lower:
                        entity_match += 1
                        if entity_match >= 3:
                            break
                score -= entity_match * 0.1
                # 余弦相似度硬门槛:加权仅用于排序，原始相似度低于阈值一律不保留
                cos_sim_raw = 1.0 - float(orig_dist) ** 2 / 2.0
                if cos_sim_raw >= threshold:
                    # 元组第4位携带原始L2距离orig_dist，供召回观测台换算余弦相似度展示
                    scored_candidates.append( (score, idx, mem, orig_dist) )
            
            # 5. 按最终得分从小到大排序（越靠前越相关），取top_k
            scored_candidates.sort(key=lambda x: x[0])
            memory_results = []
            seen_contents = set()
            show_timestamp = self.config.get("show_timestamp_in_context", True)
            # 解包4元素元组:score=加权后最终距离分, orig_dist=加权前原始L2距离
            for score, idx, mem, orig_dist in scored_candidates:
                if len(memory_results) >= top_k:
                    break
                if mem["content"] not in seen_contents:
                    seen_contents.add(mem["content"])
                    mem_copy = mem.copy()
                    # 强制转Python原生int:FAISS返回的idx是numpy.int64，直接进入JSON序列化会导致观测接口500
                    mem_copy["id"] = int(idx)
                    # 注入召回观测台所需分数字段（纯新增，不影响既有注入逻辑）
                    mem_copy["recall_score"] = round(float(score), 4)
                    # 归一化向量满足 cos=1-d²/2，clamp到[0,1]后换算为百分比相似度，仅展示用
                    cos_sim = max(0.0, min(1.0, 1.0 - float(orig_dist) ** 2 / 2.0))
                    mem_copy["similarity"] = round(cos_sim * 100, 1)
                    # 注入时间戳
                    if show_timestamp and "timestamp" in mem:
                        time_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(mem["timestamp"] / 1000))
                        mem_copy["content"] = f"[{time_str}] {mem_copy['content']}"
                    # 更新调用统计（仅保留计数，暂不用于权重计算）
                    self.meta[str(idx)]["call_count"] += 1
                    self.meta[str(idx)]["last_call_time"] = str(os.times()[4])
                    memory_results.append(mem_copy)
        
            # 优化debug日志
            print(f"[DEBUG 记忆检索] 固定召回条数:{len(fixed_results)}，向量记忆条数:{len(memory_results)}，当前阈值:{threshold}")
            print(f"[DEBUG 配置参数] 对话上下文轮数:{self.config['history_context_rounds']}，召回条数:{top_k}")
            print(f"[DEBUG 索引状态] 当前索引总记忆条数:{self.index.ntotal}")
        except Exception as e:
            print(f"❌ 向量记忆检索失败，仅返回固定召回内容:{str(e)}")
            import traceback
            traceback.print_exc()
        
        self._save()
        return {
            "fixed_recall": fixed_results,
            "memory_recall": memory_results,
            "context_rounds": context_rounds
        }

    def get_ready_for_lora(self) -> List[Dict]:
        """获取符合写入LoRA条件的记忆（调用≥3次，未同步）"""
        ready = []
        for k, v in self.meta.items():
            if v["call_count"] >=3 and not v["synced_to_lora"]:
                v["id"] = int(k)
                ready.append(v)
        return ready

    def mark_synced(self, memory_ids: List[int]) -> None:
        """标记记忆已同步到LoRA，后续不再召回"""
        for mid in memory_ids:
            if str(mid) in self.meta:
                self.meta[str(mid)]["synced_to_lora"] = True
        self._save()
    def clear_project_memory(self, project_name: str = "default") -> int:
        """清空指定项目的所有记忆，project_name传"default"清空全局主记忆库，传项目名清空对应项目记忆
        返回实际删除的记忆条数
        """
        original_count = len(self.meta)
        new_meta = {}
        # 过滤记忆
        for mem_id, mem in self.meta.items():
            tags = mem.get("tags", [])
            has_project_tag = any(tag.startswith("project:") for tag in tags)
            if project_name == "default":
                # 清空全局库：保留所有带项目标签的记忆，删除无项目标签的全局记忆
                if has_project_tag:
                    new_meta[mem_id] = mem
            else:
                # 清空指定项目库：保留不属于该项目的记忆（全局+其他项目）
                if not any(tag == f"project:{project_name}" for tag in tags):
                    new_meta[mem_id] = mem
        # 更新元数据
        self.meta = new_meta
        # 重置next_id，避免ID冲突
        self.next_id = len(self.meta)
        # 全量重建向量索引，彻底清除残留向量
        self.build_full_vector_index()
        # 持久化
        self._save()
        deleted_count = original_count - len(self.meta)
        print(f"🗑️ 已清空项目【{project_name}】的记忆，共删除{deleted_count}条，剩余{len(self.meta)}条")
        return deleted_count
    def build_full_vector_index(self):
        """全量重建记忆向量索引，和当前meta中的记忆完全对齐，清除所有残留向量，同步重置ID为连续值避免错位"""
        if self.index is None or self.encoder is None:
            print("⚠️ 向量模型或索引未加载，跳过全量重建")
            return
        print(f"🔄 开始全量重建记忆向量索引，当前记忆条数:{len(self.meta)}")
        # 清空现有索引，彻底清除残留向量
        self.index.reset()
        vectors = []
        # 先取出所有记忆值，重新映射为从0开始的连续ID，保证FAISS位置ID和meta key100%对齐
        memory_list = list(self.meta.values())
        new_meta = {}
        for idx, mem in enumerate(memory_list):
            new_meta[str(idx)] = mem
            vec = self.encoder.encode([self._encode_text(mem["content"])])[0].astype('float32')
            vec = vec / np.linalg.norm(vec)
            vectors.append(vec)
        # 更新元数据为连续ID
        self.meta = new_meta
        # 更新next_id为当前最大ID+1
        self.next_id = len(self.meta)
        if vectors:
            self.index.add(np.array(vectors))
        # 持久化新索引和元数据
        self._save()
        print("✅ 记忆向量索引全量重建完成，ID已重置为连续值，无错位问题")

    def _save(self) -> None:
        """持久化数据"""
        if self.index is not None:
            faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, 'w', encoding='utf-8') as f:
            json.dump(self.meta, f, ensure_ascii=False, indent=2)
    def load_config(self) -> None:
        """加载记忆配置"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            # 默认配置
            self.config = {
                "history_context_rounds": 5,
                "recall_top_k": 4,
                "similarity_threshold": 0.9,
                "recall_trigger_rounds": 2,
                "fixed_recall": {
                    "slot1": "AI助手工具调用规则提示词（优先级最高，必须100%严格遵守）\n🔹 核心规则（绝对不能违反）\n你不需要记忆任何JSON格式、不需要自行拼接任何工具指令结构，所有工具调用仅需要按下方固定格式输出纯文本内容即可，系统会自动生成合法可执行的指令，自行生成的任何JSON结构都会被直接拦截不执行。\n🔹 固定工具调用输出格式（完全照搬，不要修改任何结构）\n【工具调用开始】\n工具名称：[从下方白名单选择对应工具名]\n参数列表：\n[参数1名]：[参数1的实际值，原样输出即可，不需要转义任何特殊符号]\n[参数2名]：[参数2的实际值，有换行直接保留换行即可]\n【工具调用结束】\n...\n注意：不需要加任何代码块标记、不需要加任何JSON符号，仅输出以上纯文本内容即可。\n\n🔹 支持的工具白名单&必填参数清单\n工具名称\n参数列表\n功能说明\n\n工具名称：read_file\n参数列表：\nfile_name（要读取的文件相对路径）\n功能说明：读取项目指定文件的内容；\n\n工具名称：edit_file\n参数列表：\nfile_name（要操作的文件相对路径）\noperation（操作类型：replace/delete/insert_before/insert_after）\ngzt_anchor（原文中3-5行连续内容作为定位锚点，必须是整行的内容）\ngzt_newtext（要插入/替换的内容，delete操作不需要）\n功能说明：编辑修改项目指定文件的内容；\n\n工具名称：create_file\n参数列表：\npath（要创建的文件/文件夹相对路径）\nis_dir（布尔值，使用false，true为单独创建一个文件夹使用）\ngzt_newtext（要写入的文件内容，创建文件夹不需要）\n功能说明：创建新文件或文件夹；\n\n工具名称：delete_file\n参数列表：\nfile_name（要删除的文件/文件夹相对路径）\n功能说明：删除指定文件或文件夹；\n\n工具名称：exec_cmd\n参数列表：\ncmd（要执行的合法终端命令，禁止执行危险操作）\n功能说明：执行终端查询类命令；\n\n工具名称：rag_search\n参数列表：\nquery（要检索的关键词/问题）\n功能说明：检索整个项目代码库中相关的代码片段；\n\n工具名称：rename_file\n参数列表：\nold_path (字符串，原路径)\nnew_name (字符串，新名称)\n功能说明：重命名文件或文件夹\n\n工具名称：get_project_tree\n参数列表：\n功能说明：读取项目的完整文件清单。\n\n【锚点规则】\n1. 锚点优先选择包含唯一标识的3-5行连续上下文，匹配缩进空行；\n2. 禁止仅用单个符号/通用关键词作为锚点。\n\n🔹 禁止行为&兜底规则\n普通回答中如果需要举例说明工具格式，必须在示例前添加固定标识「🔹 非执行示例，仅作参考」，且不得使用【工具调用请求】标识，不会被误执行；\n输出工具调用请求前必须检查必填参数是否完整，参数值是否符合要求，遗漏参数会被自动拦截提示补充；\n工具调用请求必须独立成段，不要和普通自然语言回答混排；\n工具调用指令必须输出在正式content字段，禁止写在reasoning_content思考过程中。\n【开发项目说明】\n1. 所有的项目都位于根目录下的仓库文件夹当中，仓库文件夹当中的下级文件夹为单独的项目文件夹；\n2. 每个项目文件夹创建时都会自动生成一个项目手册，所有的文件增删改的操作信息都会实时同步更新项目手册第二和第三章节的内容；\n3. 所有信息以项目手册为准，项目手册第二章节的内容是项目文件列表，第三章节为项目文件的功能明细；\n4. 第四章节为开发计划，第五章节为风险评估与应对，开发过程中有执行新的功能开发，AI助手要先在这两个章节中更新开发规划摘要，才可以执行新的开发任务，过程中有错误发生更新第五章节给出风险点和应对方案摘要（更新内容要简洁，突出重点）；\n5. 创建，修改，读取项目根目录下的文件/文件夹：path参数直接填写名称，无需任何父级前缀；\n6. 创建，修改，读取子目录内的文件/文件夹：path参数仅补充对应的子目录相对路径（例如test_dir/sub_test.txt）；\n7. 工作台是用项目记忆隔离方式，选择不同项目操作AI助手的相关操作记忆是不互通的形式；\n8. 可以使用全路径创建，读取，修改项目外的文件，（禁止操作目录列表内的文件无法执行读取创建修改，禁止操作目录列表在工作台的配置页面中设置）。 \n\n### 🔹 编辑工具选择优先级（强制执行）\n1. **默认优先使用原生`edit_file`工具**：\n   只要待修改的锚点内容、替换内容中不包含原生工具的参数关键词（`gzt_newtext:`、`gzt_anchor:`、`operation:`、`file_name:`），一律优先使用原生编辑工具，不主动使用补充插件。\n2. **仅在原生工具存在截断风险时才启用`safe_file_editor`**：\n   只有当确认待编辑内容包含原生工具的参数关键词、会触发解析截断时，才使用安全编辑插件作为补充方案，且会提前检查内容是否包含`anchor_text:`/`replace_text:`/`edit_file_path:`/`op_type:`等安全插件自身的参数关键词，避免二次截断问题。",
                    "slot2": "【全局开发原则】（所有身份必须遵守）\n1. 配置优先原则：新增任何参数/阈值/路径时，必须优先检查是否已有统一配置中心可复用，禁止在代码中硬编码；\n2. 复用优先原则：开发新功能前，必须先检查项目中是否已有类似功能模块可复用；\n3. 统一配置入口：所有配置参数必须通过前端配置中心可编辑，禁止只在代码层面修改；\n4. 变更同步原则：修改任何配置项时，必须同步更新对应的配置文件和前端管理页面。\n4. 按钮设置原则：任何按钮的生成都不要有图标，保持设计页面的整洁。\n【强制输出规则】：\n1. 【示例输出要求】所有非执行的示例/演示/参考类内容，禁止使用任何```代码块包裹，首行必须添加固定标识「🔹 非执行示例，仅作参考」；\n2. 【拦截反馈要求】收到包含is_intercepted=true的工具返回结果时，必须立即向用户明确说明拦截原因、影响范围、操作建议，禁止无任何反馈；\n3. 【文件操作要求】\n   a. 写入文件的内容超过200行/2000字符时，绝对禁止一次性写入，必须拆分成2步：\n       第一步：调用create_file创建文件写入前半部分\n       第二步：调用edit_file插入剩余内容到文件末尾。\n4.【项目文件测试要求】项目开发完成执行测试，必须告知用户，提交用户执行相关测试，并说明测试注意事项。真实环境运行后测试出的问题才是修改项目文件的依据；必须要认真对待源码环境和真实的项目文件运行是有区别的，特别是项目经过打包安装的方式。",
                    "slot3": ""
                },
                "tools_config_path": "./toolss.json",
                "show_timestamp_in_context": True
            }
            self.save_config()

    def save_config(self) -> None:
        """保存记忆配置"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def load_tools(self) -> None:
        """加载工具列表"""
        tool_path = self.config.get("tools_config_path", "./toolss.json")
        if os.path.exists(tool_path):
            with open(tool_path, 'r', encoding='utf-8') as f:
                self.tools = json.load(f)
        else:
            self.tools = []

    def update_config(self, new_config: Dict) -> None:
        """更新配置（供前端调用）"""
        self.config.update(new_config)
        self.save_config()
        self.load_tools()

    def get_fixed_recall(self) -> List[Dict]:
        """获取固定召回内容（工具+预留位）"""
        fixed = []
        # 先加工具召回
        if self.tools:
            fixed.append({
                "type": "tools",
                "content": "【可用工具列表】\n" + "\n".join([f"{t['name']}: {t['desc']}，{t['usage']}" for t in self.tools])
            })
        # 再加预留位内容
        for slot, content in self.config["fixed_recall"].items():
            if content.strip():
                fixed.append({
                    "type": "fixed",
                    "content": content.strip()
                })
        return fixed

    def export_for_finetune(self, output_path: str = "./finetune_data.jsonl") -> None:
        """导出所有记忆为LoRA微调格式数据集"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for mem in self.meta.values():
                if not mem.get("synced_to_lora", False):
                    line = json.dumps({"text": mem["content"]}, ensure_ascii=False)
                    f.write(line + "\n")
        print(f"✅ 微调数据集已导出到：{output_path}，共{len(self.meta)}条数据")