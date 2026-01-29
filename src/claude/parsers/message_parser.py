"""
消息解析器

负责将原始 JSON 数据解析为标准化的消息格式
"""

import copy
import heapq
import json
import logging
import re
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import aiofiles
import orjson

from ..models import StandardMessage
from .drop_rules import DropRuleRegistry, DropRules

logger = logging.getLogger("claude")


class ParseStats:
    """解析统计数据"""

    def __init__(self):
        self.raw_total = 0
        self.raw_effective = 0
        self.raw_meta = 0
        self.raw_user = 0
        self.raw_assistant = 0
        self.raw_system = 0
        self.raw_tool_use = 0
        self.raw_tool_result = 0
        self.raw_thinking = 0
        self.empty_lines = 0
        self.invalid_json_lines = 0


# 工具函数
def _json_loads(s: str) -> dict:
    """使用 orjson 加载 JSON，提升性能"""
    return orjson.loads(s)


class MessageParser:
    """
    消息解析器

    将原始 JSON 数据解析为标准化的消息格式：
    1. 统一 messages、message、normalizedMessages 为标准格式
    2. 提取并标记需要丢弃的消息
    3. 应用丢弃规则
    """

    def __init__(self, drop_registry: Optional[DropRuleRegistry] = None):
        """
        初始化消息解析器

        Args:
            drop_registry: 丢弃规则注册表（可选）
        """
        self.drop_registry = drop_registry or DropRuleRegistry()

    class _FileReader:
        """
        文件读取器：用于多文件归并排序
        """

        def __init__(self, file_path: Path, file_idx: int, priority: int):
            self.file_path = file_path
            self.file_idx = file_idx
            self.priority = priority
            self.file_handle: Optional[Any] = None
            self.line_number = 0

        async def open(self) -> bool:
            try:
                self.file_handle = await aiofiles.open(
                    self.file_path, "r", encoding="utf-8"
                )
                return True
            except Exception as e:
                logger.warning(f"Failed to open file {self.file_path}: {e}")
                return False

        async def read_next(self) -> Optional[Tuple]:
            """读取下一条有效消息，返回 (timestamp, priority, file_idx, message_data, line_number)"""
            if not self.file_handle:
                return None

            while True:
                try:
                    line = await self.file_handle.__anext__()
                    self.line_number += 1
                    line = line.strip()

                    if not line:
                        continue

                    try:
                        message_data = _json_loads(line)
                        timestamp = message_data.get("timestamp")
                        if timestamp is not None:
                            return (
                                timestamp,
                                self.priority,
                                self.file_idx,
                                message_data,
                                self.line_number,
                            )
                        else:
                            # 记录跳过没有 timestamp 的消息
                            logger.debug(
                                f"Skipping message without timestamp in {self.file_path.name} at line {self.line_number}"
                            )
                    except (json.JSONDecodeError, KeyError, TypeError):
                        pass
                except StopAsyncIteration:
                    return None

        async def close(self):
            if self.file_handle:
                await self.file_handle.close()

    async def _read_json_lines(
        self,
        session_path: Path,
        session_id: str,
        read_subagents: bool = False,
    ) -> AsyncGenerator[Tuple[int, Optional[dict]], None]:
        """
        异步生成器：逐行读取 JSON 文件并解析

        支持两种模式：
        1. 单文件模式（read_subagents=False）：只读取主文件 {session_id}.jsonl
        2. 多文件归并模式（read_subagents=True）：读取主文件和 subagent 文件，按 timestamp 归并

        Args:
            session_path: session 目录路径
            session_id: session ID
            read_subagents: 是否读取并归并 subagent 文件

        Yields:
            Tuple[int, Optional[dict]]: (行号, 解析后的消息数据)
                                       如果解析失败则为 (行号, None)
        """
        # 单文件模式：只读取主文件
        if not read_subagents:
            main_file = session_path / f"{session_id}.jsonl"
            line_number = 0
            async with aiofiles.open(main_file, "r", encoding="utf-8") as f:
                async for line in f:
                    line_number += 1
                    line = line.strip()
                    if not line:
                        yield (line_number, None)
                        continue

                    try:
                        message_data = _json_loads(line)
                        yield (line_number, message_data)
                    except (json.JSONDecodeError, KeyError, TypeError):
                        yield (line_number, None)
            return

        # 多文件归并模式
        main_file = session_path / f"{session_id}.jsonl"
        subagent_dir = session_path / session_id / "subagents"

        files_to_merge = []
        file_priorities = {}  # 主文件优先级 0，subagent 文件优先级按顺序

        # 添加主文件（优先级 0）
        if main_file.exists():
            files_to_merge.append(main_file)
            file_priorities[str(main_file)] = 0
            logger.debug(f"Found main session file: {main_file}")
        else:
            logger.warning(f"Main session file not found: {main_file}")

        # 添加 subagent 文件（优先级按文件名排序）
        if subagent_dir.exists() and subagent_dir.is_dir():
            subagent_files = sorted(subagent_dir.glob("agent-*.jsonl"))
            for idx, subagent_file in enumerate(subagent_files, start=1):
                files_to_merge.append(subagent_file)
                file_priorities[str(subagent_file)] = idx
                logger.debug(f"Found subagent file: {subagent_file}")

        if not files_to_merge:
            logger.warning(f"No files found for session: {session_id}")
            return

        # 归并排序多个文件
        async for line_number, message_data in self._merge_json_files(
            files_to_merge, file_priorities
        ):
            yield (line_number, message_data)

    async def _merge_json_files(
        self,
        file_paths: List[Path],
        file_priorities: Dict[str, int],
    ) -> AsyncGenerator[Tuple[int, Optional[dict]], None]:
        """
        归并排序多个 JSONL 文件（简化版）

        按 timestamp 归并，如果 timestamp 相同则按文件优先级排序
        使用堆（heapq）优化性能，避免每次循环都排序

        Args:
            file_paths: 要合并的文件路径列表
            file_priorities: 每个文件的优先级字典

        Yields:
            Tuple[int, Optional[dict]]: (全局行号, 解析后的消息数据)
        """
        # 打开所有文件
        readers: List[MessageParser._FileReader] = []
        for idx, file_path in enumerate(file_paths):
            reader = self._FileReader(
                file_path, idx, file_priorities.get(str(file_path), 999)
            )
            if await reader.open():
                readers.append(reader)

        if not readers:
            return

        try:
            # 初始化堆：(timestamp, priority, file_idx, message_data, line_number)
            heap: List[Tuple] = []
            for reader in readers:
                result = await reader.read_next()
                if result:
                    heapq.heappush(heap, result)

            # 归并排序：每次从堆中取出最小的消息
            while heap:
                _, priority, file_idx, message_data, line_number = heapq.heappop(heap)
                yield (line_number, message_data)

                # 从同一文件读取下一条消息
                result = await readers[file_idx].read_next()
                if result:
                    heapq.heappush(heap, result)

        finally:
            # 关闭所有文件
            for reader in readers:
                await reader.close()

    async def parse_session_file_with_stats(
        self, file_path: str, collect_stats: bool = False
    ) -> Tuple[List[StandardMessage], Optional["ParseStats"]]:
        """
        解析 session 文件（包括主文件和 subagent 文件），返回标准化的消息列表和统计数据

        使用归并排序合并主文件和所有 subagent 文件的消息

        Args:
            file_path: session 文件路径
            collect_stats: 是否收集统计信息

        Returns:
            Tuple: 标准化的消息列表和统计数据（如果 collect_stats=True）
        """
        # 从文件路径提取 session_path 和 session_id
        path_obj = Path(file_path)
        session_path = path_obj.parent
        session_id = path_obj.stem

        # 检查是否有 subagent 文件
        subagent_dir = session_path / session_id / "subagents"
        has_subagents = (
            subagent_dir.exists()
            and subagent_dir.is_dir()
            and len(list(subagent_dir.glob("agent-*.jsonl"))) > 0
        )

        # 创建已处理 uuid 集合（用于去重）
        processed_uuids = set()

        stats = ParseStats() if collect_stats else None
        standard_messages = []

        # 根据是否有 subagent 决定读取模式
        async for line_number, message_data in self._read_json_lines(
            session_path, session_id, read_subagents=has_subagents
        ):
            # 更新基本统计
            if stats:
                stats.raw_total = line_number
                if message_data is None:
                    stats.invalid_json_lines += 1
                    continue

            # 提前过滤无效消息：快速检查基本结构
            if message_data is None or not self._is_valid_message_structure(
                message_data
            ):
                if stats:
                    stats.invalid_json_lines += 1
                continue

            # 解析当前消息（此时 message_data 不为 None）
            parsed_msg = self._parse_single_message_internal(
                message_data, processed_uuids=processed_uuids
            )
            # 统一处理 raw_message
            if collect_stats:
                parsed_msg.raw_message = message_data  # type: ignore[arg-type]
            standard_messages.append(parsed_msg)
            if stats and not parsed_msg.meta.drop:
                stats.raw_effective += 1
                self._collect_message_stats(parsed_msg, stats)

        return standard_messages, stats

    def _parse_single_message_internal(
        self,
        message_data: dict,
        processed_uuids: Optional[set] = None,
    ) -> StandardMessage:
        """
        内部方法：解析单条消息

        不丢弃任何消息，只进行标准化和打标记

        Args:
            message_data: 原始消息数据
            processed_uuids: 已处理的 uuid 集合（用于去重），如果为 None 则创建新的

        Returns:
            StandardMessage: 标准化后的消息对象
        """
        # 如果没有提供 processed_uuids，创建一个新的（用于单条消息解析）
        if processed_uuids is None:
            processed_uuids = set()

        # 1. 先尝试转换特殊消息类型
        converted_msg = self._convert_special_message(message_data)
        if converted_msg:
            # 应用丢弃规则
            self._mark_drop_if_needed(converted_msg)
            return converted_msg

        # 2. 标准化转换
        standard_msg = self._normalize_message(message_data, processed_uuids)

        # 3. 检查是否有 _should_drop 标记（例如系统标签清理后为空）
        if message_data.get("_should_drop"):
            drop_reason = message_data.get("_drop_reason", "unknown")
            expected_drop = message_data.get("_expected_drop", False)
            self._mark_message_dropped(standard_msg, drop_reason, expected_drop)
            return standard_msg

        # 4. 应用丢弃规则（不返回 None，而是添加标记位）
        self._mark_drop_if_needed(standard_msg)

        return standard_msg

    async def extract_project_path(self, file_path: str) -> Optional[str]:
        """
        从 session 文件中提取项目路径（遍历所有行直到找到 cwd）

        Args:
            file_path: session 文件路径

        Returns:
            Optional[str]: 项目路径，如果未找到则返回 None
        """
        try:
            # 从文件路径提取 session_path 和 session_id
            path_obj = Path(file_path)
            session_path = path_obj.parent
            session_id = path_obj.stem

            async for _, message_data in self._read_json_lines(
                session_path, session_id, read_subagents=False
            ):
                if message_data and "cwd" in message_data and message_data["cwd"]:
                    return message_data["cwd"]
        except (IOError, UnicodeDecodeError, OSError) as e:
            logger.warning(f"Failed to read project path from {file_path}: {e}")

        return None

    async def extract_session_title(
        self, file_path: str, max_length: int = 50
    ) -> tuple[Optional[str], int]:
        """
        从 session 文件中读取标题

        优先级：
        1. 第一条用户消息的内容
        2. 第一条 assistant 消息的 text 内容（用于 agent session）

        使用统一的解析流程，通过 meta.drop 标记过滤消息
        只统计未被 drop 的消息的行号

        Args:
            file_path: session 文件路径
            max_length: 标题最大长度（超过则截取并添加省略号）

        Returns:
            tuple[Optional[str], int]: (session 标题, 提取标题的行号)，
                                       如果未找到则返回 (None, 0)
        """
        try:
            # 从文件路径提取 session_path 和 session_id
            path_obj = Path(file_path)
            session_path = path_obj.parent
            session_id = path_obj.stem

            line_number = 0

            async for _, message_data in self._read_json_lines(
                session_path, session_id, read_subagents=False
            ):
                if not message_data:
                    continue

                # 使用统一的解析方法
                parsed_msg = self._parse_single_message_internal(message_data)

                # 如果消息被标记为丢弃，跳过（不增加行号）
                if parsed_msg.meta.drop:
                    continue

                # 只对未被 drop 的消息增加行号计数
                line_number += 1

                # 从解析后的消息中提取标题
                role = parsed_msg.message.role
                content = parsed_msg.message.content

                # 对 user 和 assistant 消息使用相同的提取逻辑
                # parser 已经处理了特殊消息类型转换（command、interrupted）
                title = self._extract_title_from_content(content, max_length)
                if title:
                    logger.debug(
                        f"Extracted title from {role} message in {file_path} at line {line_number}: {title}"
                    )
                    return title, line_number

        except (IOError, UnicodeDecodeError, OSError) as e:
            logger.warning(f"Failed to read title from {file_path}: {e}")

        return None, 0

    def _extract_title_from_content(
        self, content: List[Dict[str, Any]], max_length: int
    ) -> Optional[str]:
        """
        从 content 中提取标题

        支持多种 content 格式：
        - command 类型的列表：提取 command 名称
        - 其他列表类型：提取 text 内容

        Args:
            content: 消息的 content 字段
            max_length: 最大长度

        Returns:
            Optional[str]: 提取的标题，如果无法提取则返回 None
        """
        if not content:
            return None

        for item in content:
            if not isinstance(item, dict):
                continue

            item_type = item.get("type", "")

            # command 类型：提取 command 名称作为标题
            if item_type == "command":
                command_name = item.get("command", "")
                if command_name:
                    return self._truncate_title(command_name, max_length)

            # text 类型：提取文本内容
            elif item_type == "text":
                text = item.get("text", "")
                if text:
                    return self._truncate_title(text, max_length)

        return None

    def _truncate_title(self, text: str, max_length: int) -> str:
        """
        截断标题到指定长度，如果超过则添加省略号

        Args:
            text: 原始文本
            max_length: 最大长度

        Returns:
            str: 截断后的标题（如果超过长度则添加 "..."）
        """
        # 清理文本：移除换行和多余空格
        cleaned_text = " ".join(text.split())

        # 如果超过长度限制，截取并添加省略号
        if len(cleaned_text) > max_length:
            return cleaned_text[: max_length - 3] + "..."
        return cleaned_text[:max_length]

    def _collect_message_stats(
        self, message: StandardMessage, stats: "ParseStats"
    ) -> None:
        """
        收集单条消息的统计信息

        Args:
            message: 标准消息对象
            stats: 统计数据对象
        """
        msg_type = message.type
        content = message.message.content

        if msg_type == "meta" or msg_type == "summary":
            stats.raw_meta += 1
        elif msg_type == "user":
            stats.raw_user += 1
            # 统计 user 消息中的 tool_result
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_result":
                        stats.raw_tool_result += 1
        elif msg_type == "assistant":
            stats.raw_assistant += 1
            # 统计 assistant 消息中的 content 类型
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") in ("tool_use", "server_tool_use"):
                            stats.raw_tool_use += 1
                        elif item.get("type") == "thinking":
                            stats.raw_thinking += 1
            elif isinstance(content, str) and content:
                stats.raw_thinking += 1
        elif msg_type == "system":
            stats.raw_system += 1

    def _convert_special_message(self, message_data: dict) -> Optional[StandardMessage]:
        """
        尝试转换特殊消息类型（command、interrupted、suggestion、compact）

        Args:
            message_data: 当前消息数据

        Returns:
            Optional[StandardMessage]: 转换后的消息，如果不是特殊类型则返回 None
        """
        # 尝试转换 command 消息
        converted_command = self.convert_command_message(message_data)
        if converted_command:
            return converted_command

        # 尝试转换 interrupted 消息
        converted_interrupted = self.convert_interrupted_message(message_data)
        if converted_interrupted:
            return converted_interrupted

        # 尝试转换 suggestion 消息
        converted_suggestion = self.convert_suggestion_message(message_data)
        if converted_suggestion:
            return converted_suggestion

        # 尝试转换 compact 消息
        converted_compact = self.convert_compact_message(message_data)
        if converted_compact:
            return converted_compact

        # 不是特殊消息类型
        return None

    def _process_normalized_messages(
        self, message_data: dict, normalized_messages: List[dict], processed_uuids: set
    ) -> Optional[StandardMessage]:
        """
        处理 normalizedMessages，将嵌套消息列表合并到一条消息的 content 数组中

        Args:
            message_data: 原始消息数据
            normalized_messages: normalizedMessages 列表
            processed_uuids: 已处理的 uuid 集合（用于去重）

        Returns:
            Optional[StandardMessage]: 转换后的消息，如果无法转换则返回 None
        """
        # 转换所有 normalizedMessages 并合并到一条消息的 content 数组中
        # 使用 uuid 去重，避免 normalizedMessages 中的重复消息
        content_items = []

        for msg in normalized_messages:
            # 检查是否有 uuid，用于去重
            msg_uuid = msg.get("uuid") if isinstance(msg, dict) else None

            # 如果有 uuid 且已处理过，跳过
            if msg_uuid and msg_uuid in processed_uuids:
                continue

            # 标记为已处理
            if msg_uuid:
                processed_uuids.add(msg_uuid)

            # 提取 content item，保留 timestamp 和 uuid
            if isinstance(msg, dict) and "message" in msg:
                content_item = self._extract_content_item_from_message(msg)
                if content_item:
                    # 保留 timestamp 和 uuid
                    if "timestamp" in msg:
                        content_item["timestamp"] = msg["timestamp"]
                    if msg_uuid:
                        content_item["uuid"] = msg_uuid
                    content_items.append(content_item)
            elif isinstance(msg, str):
                content_items.append({"type": "text", "text": msg})
            elif isinstance(msg, dict):
                # 其他 dict 类型，尝试转换为 text
                content_items.append({"type": "text", "text": str(msg)})

        if not content_items:
            return None

        # 复用 message_data，只修改 message 字段
        message_data["type"] = normalized_messages[0].get("type", "user")
        message_data["message"] = {
            "role": normalized_messages[0].get("message", {}).get("role", "user"),
            "content": content_items,
        }
        # 保留消息的 uuid 列表（用于追踪消息来源）
        message_uuids = []
        for item in content_items:
            if "uuid" in item:
                message_uuids.append(item["uuid"])
        if message_uuids:
            message_data["uuid"] = message_uuids[0]  # 第一条 uuid 作为消息的主 uuid
            message_data["uuids"] = message_uuids  # 完整的 uuid 列表

        return StandardMessage.from_dict(message_data)

    def _normalize_message(
        self, message_data: dict, processed_uuids: set
    ) -> StandardMessage:
        """
        将原始消息标准化为统一格式

        只负责将消息转换成标准的 message + content 格式

        Args:
            message_data: 原始消息数据
            processed_uuids: 已处理的 uuid 集合（用于去重）

        Returns:
            StandardMessage: 标准化后的消息对象
        """
        # 1. 尝试从 data.normalizedMessages 提取（嵌套消息列表）
        data = message_data.get("data", {})
        if data:
            normalized_messages = data.get("normalizedMessages", [])
            if normalized_messages and isinstance(normalized_messages, list):
                result = self._process_normalized_messages(
                    message_data, normalized_messages, processed_uuids
                )
                if result:
                    return result

            # 2. 检查 data.message，如果有则提升到顶层（统一处理）
            message_obj = data.get("message")
            if message_obj and isinstance(message_obj, dict):
                # 检查是否是嵌套消息结构（message.message 存在）
                nested_message = message_obj.get("message")
                if nested_message and isinstance(nested_message, dict):
                    # 检查嵌套消息的 content 是否有内容
                    nested_content = nested_message.get("content")
                    nested_has_content = (
                        isinstance(nested_content, list) and len(nested_content) > 0
                    ) or (isinstance(nested_content, str) and nested_content.strip())

                    # 检查顶层 message 的 content 是否有内容
                    top_content = message_data.get("message", {}).get("content")
                    top_has_content = (
                        isinstance(top_content, list) and len(top_content) > 0
                    ) or (isinstance(top_content, str) and top_content.strip())

                    # 如果嵌套消息有内容，且顶层没有内容或没有 message 字段，使用嵌套消息
                    if nested_has_content and (
                        not top_has_content or "message" not in message_data
                    ):
                        message_data["message"] = nested_message
                        # 如果嵌套消息有 type，也同步更新
                        if "type" in nested_message and not message_data.get("type"):
                            message_data["type"] = nested_message["type"]
                    elif "message" not in message_data:
                        # 没有嵌套内容或顶层已有内容，使用外层消息
                        message_data["message"] = message_obj
                        if "type" in message_obj and not message_data.get("type"):
                            message_data["type"] = message_obj["type"]
                elif "message" not in message_data:
                    # 不是嵌套结构，直接使用外层消息
                    message_data["message"] = message_obj
                    if "type" in message_obj and not message_data.get("type"):
                        message_data["type"] = message_obj["type"]

        # 3. 处理普通消息（统一使用 _normalize_standard_message）
        normalized_dict = self._normalize_standard_message(message_data)
        return StandardMessage.from_dict(normalized_dict)

    def _convert_content_items_to_standard(self, content_items: List) -> List[dict]:
        """
        将 content 项转换为标准格式

        Args:
            content_items: content 项列表

        Returns:
            List[dict]: 转换后的标准 content 项列表
        """
        converted = []
        for item in content_items:
            # 字符串直接转换
            if isinstance(item, str):
                converted.append({"type": "text", "text": item})
            # dict 类型
            elif isinstance(item, dict):
                # 检查是否是完整消息结构（有 message/role/timestamp 这些顶层消息字段）
                if any(key in item for key in ["message", "role", "timestamp"]):
                    # 完整消息结构，提取 content
                    content_item = self._extract_content_item_from_message(item)
                    if content_item:
                        converted.append(content_item)
                elif "type" in item:
                    # 已经是 content item 格式（有 type 且没有顶层消息字段）
                    converted.append(item)
                else:
                    # 其他 dict，尝试转换为 text
                    converted.append({"type": "text", "text": str(item)})
            # 其他类型忽略
        return converted

    def _extract_content_item_from_message(self, message_obj: dict) -> Optional[dict]:
        """
        从完整消息结构中提取第一个 content item

        Args:
            message_obj: 完整的消息对象 {type, message: {content: [...]}}

        Returns:
            Optional[dict]: 提取的 content item，如果无法提取则返回 None
        """
        msg_type = message_obj.get("type")
        if msg_type not in ("user", "assistant", "system"):
            return None

        message = message_obj.get("message", {})
        if not message:
            return None

        content = message.get("content", [])
        if not content:
            return None

        # 确保 content 是列表
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        elif not isinstance(content, list):
            content = [content]

        # 转换并返回第一个 content item
        normalized_content = self._convert_content_items_to_standard(content)
        return normalized_content[0] if normalized_content else None

    def _is_fully_wrapped_by_system_tags(self, text: str) -> bool:
        """
        检测文本是否被系统标签完全包裹

        使用栈来检测标签嵌套层级，确保外层标签完全包裹整个文本。

        Args:
            text: 要检测的文本

        Returns:
            bool: 如果文本被系统标签完全包裹则返回 True
        """
        if not text or not isinstance(text, str):
            return False

        text = text.strip()
        if not text:
            return False

        # 系统标签列表（与 _clean_system_tags 中的标签一致）
        system_tags = [
            "local-command-caveat",
            "command-message",
            "command-name",
            "command-args",
            "local-command-stdout",
            "local-command-stderr",
        ]

        # 检查是否以某个系统标签开头并以对应的闭合标签结尾
        for tag in system_tags:
            opening_tag = f"<{tag}>"
            closing_tag = f"</{tag}>"

            # 检查是否以该标签开头和结尾
            if not text.startswith(opening_tag) or not text.endswith(closing_tag):
                continue

            # 使用栈检测标签嵌套是否正确
            stack = []
            i = 0
            while i < len(text):
                # 查找下一个开标签或闭标签
                next_open = text.find(opening_tag, i)
                next_close = text.find(closing_tag, i)

                # 如果没有找到任何标签，结束循环
                if next_open == -1 and next_close == -1:
                    break

                # 确定哪个标签更近
                if next_open != -1 and (next_close == -1 or next_open < next_close):
                    # 找到开标签
                    stack.append(tag)
                    i = next_open + len(opening_tag)
                elif next_close != -1:
                    # 找到闭标签
                    if not stack:
                        # 闭标签多于开标签，不匹配
                        return False
                    stack.pop()
                    i = next_close + len(closing_tag)

            # 如果栈为空，说明标签正确配对，且完全包裹
            return len(stack) == 0

        return False

    def _normalize_standard_message(self, message_data: dict) -> dict:
        """
        标准化普通消息

        确保 message 字段存在，并统一 content 格式
        只做标准化，不做 drop 判断

        Args:
            message_data: 原始消息数据

        Returns:
            dict: 标准化后的消息
        """
        # 保留原始消息的 uuid
        original_uuid = message_data.get("uuid")

        # 确保 message 字段存在
        if "message" not in message_data:
            message_data["message"] = {}

        # 确保消息有 type 字段
        if "type" not in message_data:
            message_data["type"] = "user"

        # 规范化 content 格式
        message = message_data.get("message", {})
        if isinstance(message, dict):
            content = message.get("content")
            if content is None:
                message_data["message"]["content"] = []
            elif isinstance(content, str):
                # 检查是否被系统标签完全包裹
                text_content = content
                if self._is_fully_wrapped_by_system_tags(content):
                    text_content = self._clean_system_tags(content)
                    # 如果清理后为空，设置标记
                    if not text_content:
                        message_data["_should_drop"] = True
                        message_data["_drop_reason"] = "empty_after_clean_system_tags"
                        message_data["_expected_drop"] = True

                message_data["message"]["content"] = [
                    {"type": "text", "text": text_content, "uuid": original_uuid}
                ]
            elif isinstance(content, dict):
                # dict 类型 content
                if "type" in content:
                    # 已经是 content item 格式
                    # 如果 content item 没有 uuid 但原始消息有，添加 uuid
                    if "uuid" not in content:
                        content["uuid"] = original_uuid

                    # 如果是 text 类型且被系统标签完全包裹，清理系统标签
                    if content.get("type") == "text" and "text" in content:
                        original_text = content["text"]
                        if self._is_fully_wrapped_by_system_tags(original_text):
                            cleaned_text = self._clean_system_tags(original_text)
                            if not cleaned_text:
                                # 清理后为空，设置标记
                                message_data["_should_drop"] = True
                                message_data["_drop_reason"] = (
                                    "empty_after_clean_system_tags"
                                )
                                message_data["_expected_drop"] = True
                                content["text"] = ""
                            else:
                                content["text"] = cleaned_text

                    message_data["message"]["content"] = [content]
                else:
                    # 其他 dict 类型，转换为 text
                    text_value = str(content)
                    if self._is_fully_wrapped_by_system_tags(text_value):
                        text_value = self._clean_system_tags(text_value)
                        if not text_value:
                            message_data["_should_drop"] = True
                            message_data["_drop_reason"] = (
                                "empty_after_clean_system_tags"
                            )
                            message_data["_expected_drop"] = True

                    message_data["message"]["content"] = [
                        {"type": "text", "text": text_value, "uuid": original_uuid}
                    ]
            elif isinstance(content, list):
                # list 类型，为每个 content item 添加 uuid
                converted_content = self._convert_content_items_to_standard(content)

                # 清理所有被系统标签完全包裹的 text 类型内容
                has_valid_content = False
                for item in converted_content:
                    if isinstance(item, dict):
                        item_type = item.get("type")
                        # 如果是 text 类型且被系统标签完全包裹，清理它
                        if item_type == "text" and "text" in item:
                            original_text = item["text"]
                            if self._is_fully_wrapped_by_system_tags(original_text):
                                cleaned_text = self._clean_system_tags(original_text)
                                item["text"] = cleaned_text
                            # 检查清理后是否有内容
                            if item.get("text", "").strip():
                                has_valid_content = True
                        # 其他类型（tool_use, tool_result, thinking 等）算作有效内容
                        elif item_type in (
                            "tool_use",
                            "server_tool_use",
                            "tool_result",
                            "thinking",
                        ):
                            has_valid_content = True

                # 如果列表为空或清理后没有有效内容，设置标记
                if not has_valid_content:
                    message_data["_should_drop"] = True
                    message_data["_drop_reason"] = "empty_after_clean_system_tags"
                    message_data["_expected_drop"] = True

                # 如果原始消息有 uuid，为每个没有 uuid 的 content item 添加
                if original_uuid:
                    for item in converted_content:
                        if isinstance(item, dict) and "uuid" not in item:
                            item["uuid"] = original_uuid
                message_data["message"]["content"] = converted_content
            else:
                # 其他类型，转换为 text
                text_value = str(content)
                if self._is_fully_wrapped_by_system_tags(text_value):
                    text_value = self._clean_system_tags(text_value)
                    if not text_value:
                        message_data["_should_drop"] = True
                        message_data["_drop_reason"] = "empty_after_clean_system_tags"
                        message_data["_expected_drop"] = True

                message_data["message"]["content"] = [
                    {"type": "text", "text": text_value, "uuid": original_uuid}
                ]

        return message_data

    def _mark_message_dropped(
        self, message: StandardMessage, reason: str, expected: bool
    ) -> None:
        """
        标记消息为已丢弃

        Args:
            message: 标准化后的消息对象
            reason: 丢弃原因
            expected: 是否预期内的丢弃
        """
        self.drop_registry.record_drop(
            message.raw_message,
            reason=reason,
            expected=expected,
        )
        message.meta.drop = True
        message.meta.expected_drop = expected
        message.meta.drop_reason = reason

    def _mark_drop_if_needed(self, message: StandardMessage) -> None:
        """
        判断消息是否应该被丢弃，并添加标记位

        不返回 bool，而是直接在 message.meta 上添加标记位

        Args:
            message: 标准化后的消息对象
        """
        # 如果已经有丢弃标记，跳过（避免重复记录）
        if message.meta.drop:
            return

        msg_type = message.type
        subtype = message.subtype
        content = message.message.content

        # 检查 content 是否为空
        if not content or len(content) == 0:
            if DropRules.is_expected_empty_type(msg_type, subtype):
                reason = (
                    f"expected_empty:{msg_type}:{subtype}"
                    if subtype
                    else f"expected_empty:{msg_type}"
                )
                self._mark_message_dropped(message, reason, expected=True)
            else:
                # 空内容但不是预期内的类型
                self._mark_message_dropped(message, "empty_content", expected=False)
            return

        # 过滤掉需要跳过的 text 内容
        filtered_content = []
        has_skip = False
        for item in content:
            if item.get("type") == "text":
                text_content = item.get("text", "")
                if DropRules.should_skip_content(msg_type, text_content):
                    has_skip = True
                    continue  # 跳过这个内容项
            filtered_content.append(item)

        # 如果有跳过的内容，更新 content
        if has_skip:
            if filtered_content:
                # 过滤后还有内容，更新 message.content
                message.message.content = filtered_content
            else:
                # 过滤后没有内容了，标记整条消息为 drop
                self._mark_message_dropped(message, "skip_content", expected=True)

    def convert_interrupted_message(
        self, message_data: dict
    ) -> Optional[StandardMessage]:
        """
        将打断消息转换为 assistant 消息

        Args:
            message_data: 原始消息数据

        Returns:
            Optional[StandardMessage]: 转换后的消息，如果不是打断消息则返回 None
        """
        message = message_data.get("message", {})
        content = message.get("content", "")

        # 正则匹配打断消息
        interrupted_pattern = re.compile(r"^\[Request interrupted by user[^\]]*\]$")

        # 提取文本内容
        text_to_check = ""
        if isinstance(content, str):
            text_to_check = content
        elif (
            isinstance(content, list)
            and len(content) > 0
            and isinstance(content[0], dict)
            and content[0].get("type") == "text"
        ):
            text_to_check = content[0].get("text", "")

        if not text_to_check or not interrupted_pattern.match(text_to_check):
            return None

        # 去除中括号
        display_text = (
            text_to_check[1:-1] if text_to_check.startswith("[") else text_to_check
        )

        # 提取 uuid（如果存在）
        message_uuid = message_data.get("uuid") or message_data.get("messageId")

        # 转换为 assistant 消息
        message_data = copy.copy(message_data)
        message_data["type"] = "assistant"
        message_data["message"] = {
            "role": "assistant",
            "content": [
                {"type": "interrupted", "text": display_text, "uuid": message_uuid}
            ],
        }

        logger.debug(
            f"Converted interrupted message | "
            f"timestamp: {message_data.get('timestamp')} | "
            f"text: {display_text}"
        )

        return StandardMessage.from_dict(message_data)

    def convert_suggestion_message(
        self, message_data: dict
    ) -> Optional[StandardMessage]:
        """
        将 suggestion 消息转换为 assistant 消息

        Args:
            message_data: 原始消息数据

        Returns:
            Optional[StandardMessage]: 转换后的消息，如果不是 suggestion 消息则返回 None
        """
        message = message_data.get("message", {})
        content = message.get("content", "")

        # Suggestion 消息前缀
        suggestion_prefix = "[SUGGESTION MODE: Suggest what the user might naturally type next into Claude Code.]"

        # 提取文本内容
        text_to_check = ""
        if isinstance(content, str):
            text_to_check = content
        elif (
            isinstance(content, list)
            and len(content) > 0
            and isinstance(content[0], dict)
            and content[0].get("type") == "text"
        ):
            text_to_check = content[0].get("text", "")

        # 检查是否是 suggestion 消息
        if not text_to_check or not text_to_check.startswith(suggestion_prefix):
            return None

        # 提取前缀后的内容
        suggestion_text = text_to_check[len(suggestion_prefix) :].strip()

        # 提取 uuid（如果存在）
        message_uuid = message_data.get("uuid") or message_data.get("messageId")

        # 转换为 assistant 消息
        message_data = copy.copy(message_data)
        message_data["type"] = "assistant"
        message_data["message"] = {
            "role": "assistant",
            "content": [
                {"type": "suggestion", "text": suggestion_text, "uuid": message_uuid}
            ],
        }

        logger.debug(
            f"Converted suggestion message | "
            f"timestamp: {message_data.get('timestamp')} | "
            f"text: {suggestion_text[:100] if suggestion_text else ''}"
        )

        return StandardMessage.from_dict(message_data)

    def convert_compact_message(self, message_data: dict) -> Optional[StandardMessage]:
        """
        将 compact 消息转换为 assistant 消息

        支持两种 compact 模式：
        1. "This session is being continued from a previous conversation" - 提取第二行及以后的内容
        2. "Your task is to create a detailed summary of the conversation so far" - 整个内容作为 compact text

        Args:
            message_data: 原始消息数据

        Returns:
            Optional[StandardMessage]: 转换后的消息，如果不是 compact 消息则返回 None
        """
        message = message_data.get("message", {})
        content = message.get("content", "")

        # Compact 消息前缀（两种模式）
        compact_prefix_1 = (
            "This session is being continued from a previous conversation"
        )
        compact_prefix_2 = (
            "Your task is to create a detailed summary of the conversation so far"
        )

        # 提取文本内容
        text_to_check = ""
        if isinstance(content, str):
            text_to_check = content
        elif (
            isinstance(content, list)
            and len(content) > 0
            and isinstance(content[0], dict)
            and content[0].get("type") == "text"
        ):
            text_to_check = content[0].get("text", "")

        if not text_to_check:
            return None

        compact_text = ""
        # 检查是否是第一种 compact 模式
        if text_to_check.startswith(compact_prefix_1):
            # 提取第二行及以后的内容
            lines = text_to_check.split("\n", 1)
            compact_text = lines[1] if len(lines) > 1 else ""
        # 检查是否是第二种 compact 模式
        elif text_to_check.startswith(compact_prefix_2):
            # 整个内容作为 compact text
            compact_text = text_to_check
        else:
            return None

        # 提取 uuid（如果存在）
        message_uuid = message_data.get("uuid") or message_data.get("messageId")

        # 转换为 assistant 消息
        message_data = copy.copy(message_data)
        message_data["type"] = "assistant"
        message_data["message"] = {
            "role": "assistant",
            "content": [
                {"type": "compact", "text": compact_text, "uuid": message_uuid}
            ],
        }

        logger.debug(
            f"Converted compact message | "
            f"timestamp: {message_data.get('timestamp')}"
        )

        return StandardMessage.from_dict(message_data)

    def convert_command_message(self, message_data: dict) -> Optional[StandardMessage]:
        """
        将 command 消息转换为用户消息

        Args:
            message_data: 当前消息数据

        Returns:
            Optional[StandardMessage]: 转换后的消息，如果不是 command 消息则返回 None
        """
        message = message_data.get("message", {})
        content = message.get("content", "")

        if not isinstance(content, str):
            return None

        # 严格匹配 command 格式
        command_pattern = re.compile(
            r"^<command-message>.*?</command-message>\s*<command-name>(.*?)</command-name>(?:\s*<command-args>(.*?)</command-args>)?$"
        )
        match = command_pattern.match(content.strip())

        if not match:
            return None

        # 提取 command 名称和参数
        command_name = match.group(1)
        command_args = (
            match.group(2) if len(match.groups()) > 1 and match.group(2) else None
        )

        # 提取 uuid（如果存在）
        message_uuid = message_data.get("uuid") or message_data.get("messageId")

        # 创建新消息对象
        converted_message = copy.copy(message_data)
        converted_message["type"] = "user"
        converted_message["message"] = {
            "role": "user",
            "content": [
                {
                    "type": "command",
                    "command": command_name,
                    "content": "",  # content 由下一条消息提供，但不再在这里处理
                    "args": command_args or "",
                    "uuid": message_uuid,
                }
            ],
        }

        logger.debug(
            f"Converted command message | "
            f"timestamp: {message_data.get('timestamp')} | "
            f"command: {command_name}"
        )

        return StandardMessage.from_dict(converted_message)

    def _clean_system_tags(self, text: str) -> str:
        """
        清理用户消息中的系统标签

        Args:
            text: 原始文本

        Returns:
            str: 清理后的文本
        """
        system_tag_patterns = [
            r"<local-command-caveat>.*?</local-command-caveat>\s*",
            r"<command-name>.*?</command-name>\s*",
            r"<command-message>.*?</command-message>\s*",
            r"<command-args>.*?</command-args>\s*",
            r"<local-command-stdout>.*?</local-command-stdout>\s*",
            r"<local-command-stderr>.*?</local-command-stderr>\s*",
        ]

        cleaned_text = text
        for pattern in system_tag_patterns:
            cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.DOTALL)

        return cleaned_text.strip()

    def _is_valid_message_structure(self, message_data: dict) -> bool:
        """
        快速验证消息的基本结构，提前过滤无效消息

        性能优化：在完整解析之前检查消息是否具有基本的有效结构
        避免对明显无效的消息进行复杂的解析处理

        Args:
            message_data: 原始消息数据

        Returns:
            bool: 如果消息具有基本有效结构则返回 True
        """
        # 必须是字典类型
        if not isinstance(message_data, dict):
            return False

        # 必须有 type 或 message 字段
        if "type" not in message_data and "message" not in message_data:
            return False

        # 如果有 message 字段，必须是字典类型
        if "message" in message_data:
            message = message_data["message"]
            if message is not None and not isinstance(message, dict):
                return False

        # 如果有 data 字段，必须是字典类型
        if "data" in message_data:
            data = message_data["data"]
            if data is not None and not isinstance(data, dict):
                return False

        return True
