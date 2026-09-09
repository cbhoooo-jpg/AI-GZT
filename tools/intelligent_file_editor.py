# -*- coding: utf-8 -*-
"""
生产级文件编辑工具（标准工程化集成方案）
重命名为intelligent_file_editor，规避和file_editor.html的命名冲突
功能：纯内容匹配定位+自动重试+备份+多操作类型支持，可直接作为智能体工具调用
"""
import os
import re
import shutil
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Tuple, Optional, Literal

# 导入配置
from .file_editor_config import (
    DEBUG, ENABLE_AUTO_RETRY, ENABLE_BACKUP,
    MATCH_THRESHOLD, BASE_LINE_THRESHOLD, SHORT_BASE_SCORE_THRESHOLD,
    MAX_RETRY_TIMES, RETRY_ADD_CONTEXT_LINES,
    BACKUP_DIR, SUPPORTED_FILE_TYPES, PROJECT_ROOT, REPOSITORY_PATH,
    BACKUP_RETENTION_DAYS, BACKUP_MAX_COUNT
)

class ContentMatcher:
    """纯内容匹配核心类（工业级优化版，和稳定版完全一致）"""
    def __init__(self, debug: bool = DEBUG):
        self.DEBUG = debug

    @staticmethod
    def normalize_text(text: str, for_match: bool = False) -> str:
        """
        将文本转换为统一的视觉标准格式，消除无关格式差异
        :param for_match: 是否为匹配场景使用，为True时会去除每行所有空格、过滤所有空行
        """
        if not text:
            return ""
        # 优化新增：<>符号转义预处理，统一所有形式的<>为原生半角符号
        # 替换HTML转义、代码转义的<>
        text = re.sub(r'&lt;|\\<', '<', text, flags=re.IGNORECASE)
        text = re.sub(r'&gt;|\\>', '>', text, flags=re.IGNORECASE)
        
        # 1. 制表符转4空格
        text = text.replace("\t", "    ")
        # 2. 统一换行符为\n
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        
        if for_match:
            # 匹配专用:逐行去除所有空白字符、过滤空行
            # 新增:符号容错转换，统一全角/半角、中英文标点、大小写
            def normalize_symbol(line: str) -> str:
                # 全角转半角映射（常用标点），优化新增全角<>转换
                full2half = {
                    '：': ':', '；': ';', '，': ',', '。': '.', '！': '!', '？': '?',
                    '＜': '<', '＞': '>'
                }
                for full, half in full2half.items():
                    line = line.replace(full, half)
                # 统一转为小写，消除大小写差异
                return line.lower()
            lines = [normalize_symbol(line.strip()) for line in text.split('\n')]
            lines = [line for line in lines if line]  # 过滤所有空行
            return '\n'.join(lines)
        else:
            # 普通归一化：仅压缩连续空行、去行尾空格，不改变原有格式
            text = re.sub(r'\n\s*\n', '\n\n', text)
            text = '\n'.join(line.rstrip() for line in text.split('\n'))
            return text.strip()


    def find_similar_block(self, original_content: str, target_block: str, threshold: float = MATCH_THRESHOLD) -> Tuple[int, int, float]:
        """
        在原始文件内容中查找与目标块视觉相似的内容块
        返回：(起始行索引（从0开始）, 结束行索引（从0开始）, 匹配相似度)，未找到则返回(-1, -1, 0.0)
        """
        target_original_lines = target_block.split('\n')
        target_original_len = len(target_original_lines)
        original_lines = original_content.split('\n')
        original_len = len(original_lines)
        
        if target_original_len == 0 or target_original_len > original_len:
            return (-1, -1, 0.0)
        
        # 提取目标基准行：优先第一个非空行
        target_base_line = ""
        target_base_line_idx = 0
        for idx, line in enumerate(target_original_lines):
            if line.strip():
                target_base_line = line
                target_base_line_idx = idx
                break
        if not target_base_line.strip():
            return (-1, -1, 0.0)
        
        # 短基准行自动合并优化（修复后：保留基准行范围）
        pure_base_length = len(re.sub(r'\s+', '', target_base_line.strip()))
        base_end_idx = target_base_line_idx
        if pure_base_length <=15 and target_base_line_idx + 2 < len(target_original_lines):
            merged_lines = [target_base_line]
            for i in range(1, 3):
                merged_lines.append(target_original_lines[target_base_line_idx + i])
            target_base_line = '\n'.join(merged_lines)
            base_end_idx = target_base_line_idx + 2
        
        # 固定窗口遍历
        candidate_blocks = []
        step = 1  # 全量逐行匹配，保证长锚点匹配准确率，100行以内锚点性能无影响
        
        # 归一化保留行边界，避免跨行误匹配
        def normalize_with_line_boundary(s: str) -> str:
            lines = [re.sub(r'\s+', '', line.strip()).lower() for line in s.split('\n')]
            lines = [line for line in lines if line]
            return '|||'.join(lines)
        # 新增行级匹配率计算方法，优化新增：含<>内容兼容换行差异
        def calculate_line_match_ratio(target: str, current: str) -> float:
            # 检查是否包含<>符号
            has_angle_bracket = '<' in target or '>' in target
            if has_angle_bracket:
                # 含<>内容特殊处理：去除所有换行/缩进/空白，整体计算相似度
                target_flat = re.sub(r'\s+', '', target.lower())
                current_flat = re.sub(r'\s+', '', current.lower())
                if target_flat and current_flat:
                    match_count = sum(1 for a, b in zip(target_flat, current_flat) if a == b)
                    flat_ratio = match_count / max(len(target_flat), len(current_flat))
                    # 扁平化匹配度达标直接返回高匹配率
                    if flat_ratio >= 0.8:
                        return 1.0
                    return flat_ratio
            # 原有常规逐行匹配逻辑
            target_lines = [line.strip() for line in target.split('\n') if line.strip()]
            current_lines = [line.strip() for line in current.split('\n') if line.strip()]
            if not target_lines or len(target_lines) != len(current_lines):
                return 0.0
            match_count = 0
            for t, c in zip(target_lines, current_lines):
                if re.sub(r'\s+', '', t.lower()) == re.sub(r'\s+', '', c.lower()):
                    match_count +=1
            return match_count / len(target_lines)
        pure_target = normalize_with_line_boundary(self.normalize_text(target_block, for_match=True))
        target_norm_content = self.normalize_text(target_block, for_match=True)
        
        for i in range(0, original_len - target_original_len + 1, step):
            window_lines = original_lines[i:i+target_original_len]
            current_block = '\n'.join(window_lines)
            
            # 第一层基准行过滤（修复后：合并基准行匹配对应连续多行）
            window_base_block = '\n'.join(window_lines[target_base_line_idx:base_end_idx+1]) if base_end_idx < len(window_lines) else ""
            # 短基准行归一化优化，优化新增：<>符号按普通字符计入得分
            cn_chars = re.findall(r'[\u4e00-\u9fa5]', target_base_line.strip())
            cn_count = len(cn_chars)
            # 提取所有非空白非中文的字符，包含<>
            non_cn_chars = re.findall(r'[^\u4e00-\u9fa5\s]', target_base_line.strip())
            en_count = len(non_cn_chars)
            pure_base_score = cn_count * 2 + en_count
            
            if pure_base_score <= SHORT_BASE_SCORE_THRESHOLD:
                def norm_short(s):
                    return re.sub(r'\s+', '', s.strip()).lower()
                norm_target = norm_short(target_base_line)
                norm_window = norm_short(window_base_block)
                base_similarity = 1.0 if norm_target == norm_window else SequenceMatcher(None, norm_window, norm_target).ratio()
            else:
                base_similarity = SequenceMatcher(None, window_base_block, target_base_line).ratio()
            if base_similarity < BASE_LINE_THRESHOLD:
                continue
                
            # 第二层全内容校验（修复后：保留行边界+行级匹配校验）
            norm_current = self.normalize_text(current_block, for_match=True)
            pure_current = normalize_with_line_boundary(norm_current)
            content_similarity = SequenceMatcher(None, pure_current, pure_target).ratio()
            if content_similarity >= threshold:
                # 第三层行级匹配校验，过滤错位块
                line_match_ratio = calculate_line_match_ratio(target_norm_content, norm_current)
                if line_match_ratio >= 0.6:
                    # 综合得分：内容相似度70% + 行匹配率30%
                    total_score = content_similarity * 0.7 + line_match_ratio * 0.3
                    candidate_blocks.append((i, i + target_original_len - 1, total_score))
        return sorted(candidate_blocks, key=lambda x: x[2], reverse=True)[0] if candidate_blocks else (-1, -1, 0.0)

class IntelligentFileEditor:
    """生产级文件编辑器，可直接作为智能体工具调用"""
    def __init__(self):
        self.matcher = ContentMatcher()
        # 会话级备份缓存，存储已备份的(会话ID, 文件绝对路径)元组
        self.session_backup_cache = set()
        # 自动创建备份目录
        if ENABLE_BACKUP and not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR, exist_ok=True)

    def _resolve_file_path(self, file_path: str) -> str:
        """自动解析文件路径：支持相对项目根路径/绝对路径"""
        if os.path.isabs(file_path):
            return file_path
        return os.path.join(PROJECT_ROOT, file_path)

    def _backup_file(self, file_path: str) -> bool:
        """修改前自动备份原文件"""
        if not ENABLE_BACKUP:
            return True
        try:
            file_name = os.path.basename(file_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 标准化路径，自动判断文件归属，生成统一格式的相对路径
            norm_file_path = os.path.normpath(file_path).replace("\\", "/")
            norm_repo = os.path.normpath(REPOSITORY_PATH).replace("\\", "/")
            if norm_file_path.startswith(norm_repo + "/") or norm_file_path == norm_repo:
                # 仓库内文件:生成「仓库文件夹/xxx/yyy.py」格式路径，匹配前端分组规则
                rel_in_repo = norm_file_path[len(norm_repo)+1:]
                rel_path = os.path.join("仓库文件夹", rel_in_repo).replace("\\", "/")
            else:
                # 程序自身文件:生成相对于PROJECT_ROOT的路径
                rel_path = os.path.relpath(norm_file_path, PROJECT_ROOT).replace("\\", "/")
            # 编码原文件相对路径，解决同名文件路径冲突问题
            encoded_path = rel_path.replace('/', '@').replace('.', '-')
            backup_path = os.path.join(BACKUP_DIR, f"{timestamp}_{encoded_path}#{file_name}")
            shutil.copy2(file_path, backup_path)
            if DEBUG:
                print(f"【文件备份】已备份到:{backup_path}")
            return True
        except Exception as e:
            if DEBUG:
                print(f"【备份失败】{str(e)}")
            return False

    def backup_single_file(self, file_path: str) -> Tuple[bool, str]:
        """公开方法:备份单个文件，供外部全量备份等接口调用"""
        if not ENABLE_BACKUP:
            return False, "备份功能未开启"
        if not os.path.exists(file_path):
            return False, f"文件不存在:{file_path}"
        if not os.path.isfile(file_path):
            return False, f"路径不是文件:{file_path}"
        try:
            backup_success = self._backup_file(file_path)
            if backup_success:
                return True, f"文件备份成功:{os.path.basename(file_path)}"
            else:
                return False, f"文件备份失败:{os.path.basename(file_path)}"
        except Exception as e:
            return False, f"备份异常:{str(e)}"

    def get_backup_list(self) -> Tuple[bool, list]:
        """获取所有备份文件列表"""
        try:
            if not ENABLE_BACKUP or not os.path.exists(BACKUP_DIR):
                return True, []
            backup_list = []
            for filename in os.listdir(BACKUP_DIR):
                file_path = os.path.join(BACKUP_DIR, filename)
                if not os.path.isfile(file_path):
                    continue
                # 解析文件名: 时间戳(固定15位格式YYYYMMDD_HHMMSS)_编码路径_原文件名
                if len(filename) >= 15 and filename[8] == '_':
                    # 新格式（时间戳固定前15位）
                    try:
                        timestamp_str = filename[:15]
                        backup_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
                        # 剩余部分分割为编码路径和原文件名
                        remaining_part = filename[16:]
                        # 兼容新旧格式:新格式用#分隔，旧格式用_分隔
                        if '#' in remaining_part:
                            encoded_path, original_name = remaining_part.split('#', 1)
                        elif '_' in remaining_part:
                            encoded_path, original_name = remaining_part.split('_', 1)
                        else:
                            raise ValueError("无效文件名格式")
                        # 解码原路径（统一使用/作为分隔符，跨平台兼容）
                        # 目录段只做@→/还原（目录名原生减号保留，不做-→.还原）
                        decoded_parts = encoded_path.replace('@', '/').split('/')
                        # 文件名一律采用#（旧格式_）后保存的原始文件名，避免原生减号被误还原为点
                        if decoded_parts:
                            decoded_parts[-1] = original_name
                        original_path = '/'.join(decoded_parts)
                        norm_repo = os.path.normpath(REPOSITORY_PATH).replace("\\", "/")
                        # 对齐restore_backup恢复方法的路径解析逻辑:先判断路径前缀再选择根目录拼接
                        if original_path.startswith("仓库文件夹/"):
                            # 仓库内文件:去掉前缀后拼接仓库根目录，路径100%准确
                            rel_in_repo = original_path[len("仓库文件夹/"):]
                            original_abs_path = os.path.normpath(os.path.join(REPOSITORY_PATH, rel_in_repo)).replace("\\", "/")
                            display_path = original_path
                        else:
                            # 系统/旧版本备份:拼接AI程序根目录，自动处理../相对路径
                            original_abs_path = os.path.normpath(os.path.join(PROJECT_ROOT, original_path)).replace("\\", "/")
                            display_path = os.path.relpath(original_abs_path, PROJECT_ROOT).replace("\\", "/")
                        # 可恢复判定:路径能成功解析即视为可恢复（文件被误删时也可通过备份重建，不再依赖文件当前是否存在）
                        restorable = True
                        original_path = display_path
                        file_stat = os.stat(file_path)
                        backup_list.append({
                            "backup_file": filename,
                            "backup_time": backup_time,
                            "original_path": original_path,
                            "file_size": f"{round(file_stat.st_size / 1024, 2)}KB",
                            "restorable": restorable
                        })
                        continue
                    except:
                        # 解析失败走旧格式逻辑
                        pass
                # 历史旧格式备份文件
                file_stat = os.stat(file_path)
                backup_time = datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                backup_list.append({
                    "backup_file": filename,
                    "backup_time": backup_time,
                    "original_path": "未知路径（旧版本备份）",
                    "file_size": f"{round(file_stat.st_size / 1024, 2)}KB",
                    "restorable": False
                })
            # 按时间倒序排列
            return True, sorted(backup_list, key=lambda x: x["backup_time"], reverse=True)
        except Exception as e:
            return False, []

    def restore_backup(self, backup_file_name: str) -> Tuple[bool, str]:
        """恢复指定备份文件"""
        backup_path = os.path.join(BACKUP_DIR, backup_file_name)
        if not os.path.exists(backup_path):
            return False, "备份文件不存在"
        # 解析原路径，和get_backup_list逻辑完全对齐
        if len(backup_file_name) >= 15 and backup_file_name[8] == '_':
            try:
                # 新格式（时间戳固定前15位）
                remaining_part = backup_file_name[16:]
                # 兼容新旧格式:新格式用#分隔，旧格式用_分隔
                if '#' in remaining_part:
                    encoded_path, original_name = remaining_part.split('#', 1)
                elif '_' in remaining_part:
                    encoded_path, original_name = remaining_part.split('_', 1)
                else:
                    raise ValueError("无效文件名格式")
                # 解码原路径:目录段只做@→/还原（目录名原生减号保留），文件名一律采用#/_后保存的原始文件名
                decoded_parts = encoded_path.replace('@', '/').split('/')
                if decoded_parts:
                    decoded_parts[-1] = original_name
                original_path = '/'.join(decoded_parts)
                # 正确解析路径:仓库文件夹前缀的文件拼接REPOSITORY_PATH，其他文件拼接PROJECT_ROOT
                norm_original = original_path.replace("\\", "/")
                if norm_original.startswith("仓库文件夹/"):
                    rel_in_repo = norm_original[len("仓库文件夹/"):]
                    original_abs_path = os.path.normpath(os.path.join(REPOSITORY_PATH, rel_in_repo)).replace("\\", "/")
                else:
                    original_abs_path = os.path.normpath(os.path.join(PROJECT_ROOT, original_path)).replace("\\", "/")
            except:
                return False, "旧版本备份文件无法自动恢复，请手动恢复"
        else:
            return False, "旧版本备份文件无法自动恢复，请手动恢复"
        try:
            # 父目录不存在时自动重建（支持文件/父目录被误删后的恢复）
            parent_dir = os.path.dirname(original_abs_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
            if os.path.exists(original_abs_path):
                # 文件仍存在:恢复前先备份当前最新版本，双重保险
                self._backup_file(original_abs_path)
                # 覆盖原文件
                shutil.copy2(backup_path, original_abs_path)
                return True, f"恢复成功，已自动备份恢复前的最新版本"
            else:
                # 文件已被误删:直接从备份重建，无需备份当前版本
                shutil.copy2(backup_path, original_abs_path)
                return True, f"原文件已删除，已从备份重建成功"
        except Exception as e:
            return False, f"恢复失败:{str(e)}"

    def delete_backup(self, backup_file_name: str) -> Tuple[bool, str]:
        """删除指定备份文件"""
        backup_path = os.path.join(BACKUP_DIR, backup_file_name)
        if not os.path.exists(backup_path):
            return False, "备份文件不存在"
        try:
            os.remove(backup_path)
            return True, "备份删除成功"
        except Exception as e:
            return False, f"删除失败:{str(e)}"

    def clean_expired_backup(self, retention_days: int = None, max_count: int = None) -> Tuple[bool, str, int]:
        """清理过期备份文件，返回删除数量"""
        if not os.path.exists(BACKUP_DIR):
            return True, "备份目录不存在", 0
        # 未传参数则使用默认配置
        retention_days = retention_days if retention_days is not None else BACKUP_RETENTION_DAYS
        max_count = max_count if max_count is not None else BACKUP_MAX_COUNT
        success, backup_list = self.get_backup_list()
        if not success:
            return False, "获取备份列表失败", 0
        delete_count = 0
        # 先按保留天数过滤
        if retention_days > 0:
            expire_time = datetime.now() - timedelta(days=retention_days)
            for item in backup_list:
                try:
                    backup_time = datetime.strptime(item["backup_time"], "%Y-%m-%d %H:%M:%S")
                    if backup_time < expire_time:
                        success, _ = self.delete_backup(item["backup_file"])
                        if success:
                            delete_count += 1
                except:
                    continue
        # 再按最大数量过滤，保留最新的max_count个
        success, backup_list = self.get_backup_list()
        if not success:
            return False, "获取备份列表失败", delete_count
        if len(backup_list) > max_count > 0:
            to_delete = backup_list[max_count:]
            for item in to_delete:
                success, _ = self.delete_backup(item["backup_file"])
                if success:
                    delete_count += 1
        return True, f"清理完成，共删除{delete_count}个过期备份", delete_count

    def _extend_target_block(self, original_content: str, target_block: str, add_lines: int = 1) -> str:
        """匹配失败时自动扩展锚点，增加前后上下文行"""
        original_lines = original_content.split('\n')
        target_lines = target_block.split('\n')
        if not target_lines:
            return target_block
        
        # 先匹配原锚点的位置，找到后扩展前后行
        start, _, _ = self.matcher.find_similar_block(original_content, target_block, threshold=0.7)
        if start == -1:
            return target_block
        
        new_start = max(0, start - add_lines)
        new_end = min(len(original_lines), start + len(target_lines) + add_lines)
        return '\n'.join(original_lines[new_start:new_end])

    def edit_file(
        self,
        file_path: str,
        operation: Literal["replace", "insert_before", "insert_after", "delete", "insert_start", "insert_end"],
        target_block: str = "",
        content: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        编辑文件主入口，支持4种操作类型
        :param file_path: 要编辑的文件路径，支持相对项目根路径/绝对路径
        :param operation: 操作类型：replace/insert_before/insert_after/delete
        :param target_block: 定位锚点内容
        :param content: 要插入/替换的内容，delete操作不需要传
        :return: (是否成功, 结果信息)
        """
        # 解析文件路径
        abs_file_path = self._resolve_file_path(file_path)
        # 前置校验
        if not os.path.exists(abs_file_path):
            return False, f"文件不存在：{file_path}（解析后路径：{abs_file_path}）"
        if not os.path.isfile(abs_file_path):
            return False, f"路径不是文件:{file_path}"
        # 已放开文件类型白名单限制:任意扩展名/无扩展名的文本文件均可编辑
        # 二进制文件（图片/压缩包/可执行文件/PDF/Office等）会在下方UTF-8读取阶段被安全拦截，不会损坏文件、不会产生垃圾备份
        if operation != "delete" and content is None:
            return False, "非删除操作必须传入content参数"
        
        # 读取原文件内容
        try:
            with open(abs_file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except UnicodeDecodeError:
            return False, "该文件为二进制格式或非UTF-8编码，文本编辑器无法修改（图片/压缩包/可执行文件/PDF/Office等请使用专用工具）"
        except PermissionError:
            return False, "没有文件读写权限"
        except Exception as e:
            return False, f"读取文件失败：{str(e)}"
        
        # 备份文件（同会话同文件仅第一次修改备份）
        if ENABLE_BACKUP:
            if session_id is None:
                # 无会话ID时兼容旧逻辑，每次修改都备份
                if not self._backup_file(abs_file_path):
                    return False, "文件备份失败，终止编辑"
            else:
                cache_key = (session_id, abs_file_path)
                if cache_key not in self.session_backup_cache:
                    if not self._backup_file(abs_file_path):
                        return False, "文件备份失败，终止编辑"
                    self.session_backup_cache.add(cache_key)
                else:
                    if DEBUG:
                        print(f"【会话内已备份】跳过重复备份:{abs_file_path} 会话ID:{session_id}")
        
        # 匹配定位（支持自动重试）
        start_line = end_line = -1
        score = 0.0
        current_target = target_block
        retry_times = 0

        while retry_times <= (MAX_RETRY_TIMES if ENABLE_AUTO_RETRY else 0):
            start_line, end_line, score = self.matcher.find_similar_block(original_content, current_target)
            if start_line != -1:
                break
            retry_times += 1
            current_target = self._extend_target_block(original_content, target_block, add_lines=retry_times)
            if DEBUG:
                print(f"【重试第{retry_times}次】扩展后锚点：\n{current_target}")
        
        if start_line == -1:
            return False, f"匹配失败，无法定位锚点位置，请扩展锚点内容确定锚点唯一性。"
        
        if DEBUG:
            print(f"【匹配成功】行范围[{start_line}, {end_line}]，相似度：{score:.2f}")
        
        # 执行操作
        original_lines = original_content.split('\n')
        try:
            if operation == "replace":
                # 替换定位块内容
                original_lines[start_line:end_line+1] = content.split('\n')
            elif operation == "insert_before":
                # 在定位块之前插入内容
                original_lines[start_line:start_line] = content.split('\n')
            elif operation == "insert_after":
                # 在定位块之后插入内容
                original_lines[end_line+1:end_line+1] = content.split('\n')
            elif operation == "delete":
                # 删除定位块内容
                del original_lines[start_line:end_line+1]
            else:
                return False, f"不支持的操作类型：{operation}"
        except Exception as e:
            return False, f"执行操作失败：{str(e)}"
        
        # 写入新内容
        new_content = '\n'.join(original_lines)
        try:
            with open(abs_file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        except Exception as e:
            # 写入失败自动回滚
            if ENABLE_BACKUP:
                self._backup_file(abs_file_path)
                with open(abs_file_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
            return False, f"写入文件失败，已回滚：{str(e)}"
        
        return True, f"编辑成功，匹配相似度：{score:.2f}，已自动备份原文件"

# 全局单例，直接导入调用即可
intelligent_file_editor = IntelligentFileEditor()

# 快速调用示例
if __name__ == "__main__":
    # 示例：替换文件内容
    success, msg = intelligent_file_editor.edit_file(
        file_path="test.py",
        operation="replace",
        target_block="def hello():\n    print('hello')",
        content="def hello():\n    print('hello world')\n    return 'ok'"
    )
    print(msg)