"""
Claude Session 操作模块
处理 Session 的扫描和读取操作
"""

import copy
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import aiofiles

from src.utils.time_utils import parse_iso_timestamp

from .models import ClaudeMessage, ClaudeSession, ClaudeSessionInfo

# Configure logger
logger = logging.getLogger("claude")

# Constants
VALID_MESSAGE_TYPES: Set[str] = {"user", "assistant", "system"}
META_MESSAGE_TYPES: Set[str] = {"file-history-snapshot", "summary"}
DEFAULT_TITLE_MAX_LENGTH = 50


class ClaudeSessionOperations:
    """Claude Session 操作类"""

    def __init__(self, claude_session_path: Path):
        """
        初始化 Session 操作管理器

        Args:
            claude_session_path: 项目的 session 存储目录路径
        """
        self.session_path = claude_session_path

    @staticmethod
    def _validate_session_id(session_id: str) -> None:
        """
        验证 session_id 是否有效，防止路径遍历攻击

        Args:
            session_id: 要验证的 session ID

        Raises:
            ValueError: 如果 session_id 无效
        """
        if not session_id or not isinstance(session_id, str):
            raise ValueError("session_id must be a non-empty string")

        # 防止路径遍历攻击
        if ".." in session_id or "/" in session_id or "\\" in session_id:
            raise ValueError(
                f"Invalid session_id (contains path traversal characters): {session_id}"
            )

        # 防止绝对路径
        if session_id.startswith(("/", "\\")):
            raise ValueError(
                f"Invalid session_id (looks like absolute path): {session_id}"
            )

    def _convert_interrupted_to_assistant(self, message_data: dict) -> Optional[dict]:
        """
        将打断消息转换为 assistant 消息，并标记为 interrupted 类型

        打断消息通常是用户打断了 assistant 的响应过程，因此应该归类为 assistant 消息
        同时将 content 的 type 标记为 "interrupted"，以便前端识别和特殊渲染

        Args:
            message_data: 原始消息数据

        Returns:
            转换后的消息数据，如果不是打断消息则返回 None
        """
        message = message_data.get("message", {})
        content = message.get("content", "")

        # 正则匹配打断消息：[Request interrupted by user...]
        # 使用更精确的模式，避免匹配过多的内容
        interrupted_pattern = re.compile(r"^\[Request interrupted by user[^\]]*\]$")

        # 提取文本内容进行检测
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

        # 使用正则检测是否是打断消息
        if not text_to_check or not interrupted_pattern.match(text_to_check):
            return None

        # 去除前后中括号，提取实际的消息文本
        # 例如：[Request interrupted by user] -> Request interrupted by user
        display_text = (
            text_to_check[1:-1] if text_to_check.startswith("[") else text_to_check
        )

        # 将打断消息转换为 assistant 类型消息
        # content 的 type 使用 "interrupted" 以便前端识别
        message_data["type"] = "assistant"
        message_data["message"] = {
            "role": "assistant",
            "content": [{"type": "interrupted", "text": display_text}],
        }
        # 标记该消息已被转换（用于统计）
        message_data["_converted"] = True
        message_data["_original_type"] = "interrupted"

        logger.debug(
            f"Converted interrupted message to assistant message | "
            f"timestamp: {message_data.get('timestamp')} | "
            f"text: {display_text}"
        )
        return message_data

    def _convert_command_message(
        self, message_data: dict, next_message_data: Optional[dict]
    ) -> Optional[dict]:
        """
        将 command 消息转换为用户消息，并标记为 command 类型

        Command 消息的格式（严格匹配）：
        1. 第一条消息的 content 必须完全是：
           - <command-message>...</command-message>\n<command-name>...</command-name>
           - 或：<command-message>...</command-message>\n<command-name>...</command-name>\n<command-args>...</command-args>
        2. 第二条消息（可选）是 isMeta=true，包含 command 的具体内容

        Args:
            message_data: 当前消息数据
            next_message_data: 下一条消息数据（用于查找 isMeta 消息）

        Returns:
            转换后的消息数据，如果不是 command 消息则返回 None
        """
        message = message_data.get("message", {})
        content = message.get("content", "")

        # 检查是否是 command 标签
        if not isinstance(content, str):
            return None

        # 严格匹配：整个 content 必须是标准的 command 消息格式
        # 格式 1：<command-message>xxx</command-message> <换行> <command-name>xxx</command-name>
        # 格式 2：<command-message>xxx</command-message> <换行> <command-name>xxx</command-name> <换行> <command-args>xxx</command-args>
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

        # 提取 command 内容（从下一条 isMeta 消息中）
        command_content = None
        if next_message_data and next_message_data.get("isMeta"):
            next_message = next_message_data.get("message", {})
            next_content = next_message.get("content", "")

            # 提取文本内容
            if isinstance(next_content, str):
                command_content = next_content
            elif isinstance(next_content, list) and len(next_content) > 0:
                # 从数组中提取 text 内容
                for item in next_content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        command_content = item.get("text", "")
                        break

            # 在原始的 next_message_data 上添加标记，使其在后续处理中被过滤
            next_message_data["_skipped_next"] = True

        # 创建新消息对象（不修改原始 message_data）
        converted_message = copy.copy(message_data)
        # 将 command 消息转换为用户消息
        converted_message["type"] = "user"
        converted_message["message"] = {
            "role": "user",
            "content": [
                {
                    "type": "command",
                    "command": command_name,
                    "content": command_content or "",
                    "args": command_args or "",
                }
            ],
        }
        # 标记该消息已被转换（用于统计）
        converted_message["_converted"] = True
        converted_message["_original_type"] = "command"

        logger.debug(
            f"Converted command message | "
            f"timestamp: {message_data.get('timestamp')} | "
            f"command: {command_name} | "
            f"has_content: {command_content is not None} | "
            f"has_args: {command_args is not None}"
        )
        return converted_message

    def _merge_tool_result_to_tool_use(
        self, tool_result_item: dict, tool_use_map: Dict[str, dict]
    ) -> None:
        """
        将 tool_result 合并到对应的 tool_use 中

        Args:
            tool_result_item: tool_result 内容项
            tool_use_map: tool_use_id -> message_data 映射（会被修改）
        """
        tool_use_id = tool_result_item.get("tool_use_id")
        if tool_use_id and tool_use_id in tool_use_map:
            # 找到对应的 tool_use 消息
            tool_use_message_data = tool_use_map[tool_use_id]
            tool_use_content = tool_use_message_data.get("message", {}).get(
                "content", []
            )

            # 在 tool_use_content 中找到对应的 tool_use 或 server_tool_use 并添加 output
            for tool_use_item in tool_use_content:
                if (
                    isinstance(tool_use_item, dict)
                    and tool_use_item.get("type") in ("tool_use", "server_tool_use")
                    and tool_use_item.get("id") == tool_use_id
                ):
                    tool_use_item["output"] = tool_result_item.get("content")
                    tool_use_item["status"] = "complete"
                    break

            # 从 map 中移除已处理的 tool_use（避免重复处理）
            del tool_use_map[tool_use_id]
        else:
            # 找不到对应的 tool_use，记录被丢弃的 tool_result
            logger.warning(
                f"Dropping tool_result: tool_use_id={tool_use_id} not found in tool_use_map | "
                f"full tool_result_item: {tool_result_item}"
            )

    def _process_assistant_message(
        self, message_data: dict, tool_use_map: Dict[str, dict]
    ) -> dict:
        """
        处理 assistant 消息，规范化 tool_use 和 thinking

        Args:
            message_data: 原始消息数据
            tool_use_map: tool_use_id -> message_data 映射（会被修改）

        Returns:
            处理后的消息数据
        """
        message = message_data.get("message", {})
        content = message.get("content", [])

        if not isinstance(content, list) or len(content) == 0:
            return message_data

        # 检查是否包含 tool_use 或 server_tool_use
        has_tool_use = any(
            isinstance(item, dict)
            and item.get("type") in ("tool_use", "server_tool_use")
            for item in content
        )

        if has_tool_use:
            # 为 tool_use 添加 incomplete status（如果没有 output）
            # 使用浅拷贝以提高性能
            message_data_copy = copy.copy(message_data)
            # 深拷贝 message 部分，因为需要修改 content
            message_data_copy["message"] = copy.deepcopy(
                message_data.get("message", {})
            )
            content_copy = message_data_copy["message"].get("content", [])

            for item in content_copy:
                if isinstance(item, dict) and item.get("type") in (
                    "tool_use",
                    "server_tool_use",
                ):
                    tool_use_id = item.get("id")
                    if tool_use_id:
                        # 检测重复的 tool_use_id
                        if tool_use_id in tool_use_map:
                            logger.warning(
                                f"Duplicate tool_use_id detected: {tool_use_id} | "
                                f"timestamp: {message_data.get('timestamp')} | "
                                f"previous entry will be overwritten"
                            )
                        # 记录到 map 中，供后续 tool_result 查找
                        tool_use_map[tool_use_id] = message_data_copy

                    # 如果没有 output，标记为 incomplete
                    if "output" not in item and "status" not in item:
                        item["status"] = "incomplete"

            return message_data_copy
        else:
            # 普通 assistant 消息（text、thinking 等），需要规范化处理
            # 使用浅拷贝以提高性能
            message_data_copy = copy.copy(message_data)
            # 深拷贝 message 部分，因为需要修改 content
            message_data_copy["message"] = copy.deepcopy(
                message_data.get("message", {})
            )
            content_copy = message_data_copy["message"].get("content", [])

            # 规范化 thinking 类型：将 thinking 字段转换为 text 字段
            for item in content_copy:
                if isinstance(item, dict) and item.get("type") == "thinking":
                    # 如果存在 thinking 字段但没有 text 字段，则进行转换
                    if "thinking" in item and "text" not in item:
                        item["text"] = item.pop("thinking")

            return message_data_copy

    def _merge_tool_use_with_result(self, raw_messages: List[dict]) -> List[dict]:
        """
        合并 tool_use 和 tool_result 消息

        当遇到 tool_result 时，根据 tool_use_id 找到对应的 tool_use 消息，
        将两者合并成一条包含完整信息的消息。

        Args:
            raw_messages: 原始消息列表

        Returns:
            List[dict]: 合并后的消息列表
        """
        merged_messages = []
        # tool_use_id -> message_data 映射
        tool_use_map: Dict[str, dict] = {}

        for i, message_data in enumerate(raw_messages):
            message_type = message_data.get("type")

            # 获取下一条消息（用于 command 消息处理）
            next_message_data = (
                raw_messages[i + 1] if i + 1 < len(raw_messages) else None
            )

            # 检查是否已经被之前的 command 消息合并（通过 _skipped_next 标记）
            if message_data.get("_skipped_next"):
                # 标记为丢弃（已被合并）
                message_data["_dropped"] = True
                message_data["_drop_reason"] = "merged_into_command"
                message_data["_expected_drop"] = True
                continue

            # 处理 command 消息
            # 需要在处理打断消息之前进行，因为 command 消息包含特殊标签
            converted_command = self._convert_command_message(
                message_data, next_message_data
            )
            if converted_command:
                merged_messages.append(converted_command)
                continue

            message = message_data.get("message", {})
            content = message.get("content", [])

            # 处理打断消息 - 转换为 assistant role 的消息
            # 需要在处理空消息之前进行，因为打断消息有 content
            converted_interrupted = self._convert_interrupted_to_assistant(message_data)
            if converted_interrupted:
                merged_messages.append(converted_interrupted)
                continue

            # 跳过空消息
            if not message:
                message_type = message_data.get("type")
                subtype = message_data.get("subtype", "")

                # 对于已知的特殊类型（不含 message 字段的元数据），使用 debug 级别
                if message_type in META_MESSAGE_TYPES:
                    logger.debug(
                        f"Dropping known metadata type: {message_type} | "
                        f"timestamp: {message_data.get('timestamp')}"
                    )
                    # 标记为丢弃（预期内）
                    message_data["_dropped"] = True
                    message_data["_drop_reason"] = f"metadata_type:{message_type}"
                    message_data["_expected_drop"] = True
                    continue

                # 对于某些特殊类型的空消息，也是预期内的
                # 1. type=system, subtype=turn_duration
                # 2. type=system, subtype=local_command
                # 3. type=process (MCP 执行过程)
                # 4. type=progress (执行进度)
                is_expected_empty = (
                    message_type == "system"
                    and subtype in ("turn_duration", "local_command")
                    or message_type in ("process", "progress")
                )

                if is_expected_empty:
                    logger.debug(
                        f"Dropping expected empty message: type={message_type}, subtype={subtype} | "
                        f"timestamp: {message_data.get('timestamp')}"
                    )
                    # 标记为丢弃（预期内）
                    message_data["_dropped"] = True
                    message_data["_drop_reason"] = (
                        f"expected_empty:{message_type}:{subtype}"
                        if subtype
                        else f"expected_empty:{message_type}"
                    )
                    message_data["_expected_drop"] = True
                    continue

                # 对于其他类型（包括 VALID_MESSAGE_TYPES 中的类型），如果没有 message 字段，则视为异常
                logger.warning(
                    f"Dropping message with empty message field: type={message_type}, subtype={subtype} | "
                    f"timestamp: {message_data.get('timestamp')} | "
                    f"full message_data: {message_data}"
                )
                # 标记为丢弃（非预期）
                message_data["_dropped"] = True
                message_data["_drop_reason"] = "empty_message_field"
                message_data["_expected_drop"] = False
                continue

            # 跳过 Warmup 消息（系统预热请求）
            if message_data.get("type") == "user" and content == "Warmup":
                logger.debug(
                    f"Dropping Warmup message | "
                    f"timestamp: {message_data.get('timestamp')}"
                )
                # 标记为丢弃（预期内）
                message_data["_dropped"] = True
                message_data["_drop_reason"] = "warmup_message"
                message_data["_expected_drop"] = True
                continue

            # 处理空 content
            if not content or (isinstance(content, list) and len(content) == 0):
                logger.warning(
                    f"Dropping message with empty content: {message_data.get('type')} | "
                    f"timestamp: {message_data.get('timestamp')} | "
                    f"full message_data: {message_data}"
                )
                # 标记为丢弃（非预期）
                message_data["_dropped"] = True
                message_data["_drop_reason"] = "empty_content"
                message_data["_expected_drop"] = False
                continue

            # 处理 user 消息和 assistant 消息中的 tool_result
            # 注意：tool_result 消息可能是 type="user" 或 type="assistant"
            if message_data.get("type") in ("user", "assistant") and isinstance(
                content, list
            ):
                # 检查是否包含 tool_result
                tool_results = [
                    item
                    for item in content
                    if isinstance(item, dict) and item.get("type") == "tool_result"
                ]

                if tool_results:
                    # 遍历所有 tool_result，找到对应的 tool_use 并合并
                    for tool_result_item in tool_results:
                        self._merge_tool_result_to_tool_use(
                            tool_result_item, tool_use_map
                        )
                    # 不单独添加 tool_result 消息（已经合并到 tool_use 中）
                    continue

            # 处理 assistant 消息
            if isinstance(content, list) and len(content) > 0:
                processed_message = self._process_assistant_message(
                    message_data, tool_use_map
                )
                merged_messages.append(processed_message)
            else:
                # 字符串类型的 content（user 消息），直接添加
                merged_messages.append(message_data)

        return merged_messages

    def _merge_consecutive_messages(self, messages: List[dict]) -> List[dict]:
        """
        合并连续的同一 role 的消息

        将连续的同一 role（user 或 assistant）的多条消息合并成一条，
        合并后的 message 的 content 是一个数组，包含所有原始消息的 content。

        Args:
            messages: 已合并 tool_use 的消息列表

        Returns:
            List[dict]: 进一步合并后的消息列表
        """
        if not messages:
            return []

        merged_messages = []
        i = 0

        while i < len(messages):
            current_message = messages[i]
            current_role = current_message.get("message", {}).get("role")

            # 如果当前消息没有 role，直接添加
            if not current_role:
                merged_messages.append(current_message)
                i += 1
                continue

            # 收集连续的同一 role 的消息
            consecutive_messages = [current_message]
            j = i + 1

            # system 消息不合并，保持独立
            if current_role == "system":
                merged_messages.append(current_message)
                i += 1
                continue

            while j < len(messages):
                next_message = messages[j]
                next_role = next_message.get("message", {}).get("role")

                if next_role == current_role:
                    consecutive_messages.append(next_message)
                    j += 1
                else:
                    break

            # 如果只有一条消息，直接添加
            if len(consecutive_messages) == 1:
                merged_messages.append(current_message)
                i += 1
                continue

            # 合并多条消息
            if len(consecutive_messages) > 1:
                # 检查 content 类型的一致性
                content_types = set()
                for msg in consecutive_messages:
                    content = msg.get("message", {}).get("content")
                    if content is None:
                        continue
                    if isinstance(content, list):
                        content_types.add("list")
                    elif isinstance(content, str):
                        content_types.add("string")
                    else:
                        content_types.add("other")

                # 创建合并后的消息
                merged_message = copy.copy(current_message)
                merged_message["message"] = copy.deepcopy(
                    current_message.get("message", {})
                )

                # 合并所有 content
                merged_contents = []
                for msg in consecutive_messages:
                    content = msg.get("message", {}).get("content")
                    if content:
                        if isinstance(content, list):
                            merged_contents.extend(content)
                        else:
                            # 字符串类型的 content
                            # 如果所有消息都是字符串，保持为字符串（用分隔符连接）
                            if content_types == {"string"}:
                                merged_contents.append(content)
                            else:
                                # 混合类型，转换为统一格式
                                merged_contents.append(
                                    {"type": "text", "text": content}
                                )

                # 更新合并后的消息
                if merged_message.get("message"):
                    # 如果所有消息都是字符串，合并为单个字符串
                    if content_types == {"string"} and len(merged_contents) > 1:
                        merged_message["message"]["content"] = "\n".join(
                            merged_contents
                        )
                    else:
                        merged_message["message"]["content"] = merged_contents

                merged_messages.append(merged_message)
                i = j
            else:
                merged_messages.append(current_message)
                i += 1

        return merged_messages

    async def scan_sessions(
        self, existing_titles: Optional[dict[str, str]] = None
    ) -> List[ClaudeSessionInfo]:
        """
        扫描 session 列表（只返回基本信息，选择性读取文件内容）

        Args:
            existing_titles: 已存在的 session 标题映射 {session_id: title}，
                           如果提供了 title，则跳过读取文件

        Returns:
            List[ClaudeSessionInfo]: session 简要信息列表
        """
        if not self.session_path.exists():
            logger.warning(f"Session directory does not exist: {self.session_path}")
            return []

        session_infos = []
        existing_titles = existing_titles or {}

        # 扫描该目录下的所有 session 文件
        for session_file in self.session_path.glob("*.jsonl"):
            session_id = session_file.stem
            is_agent_session = session_file.name.startswith("agent-")

            # 获取文件最后修改时间并转换为 datetime
            try:
                file_stat = session_file.stat()
                file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
                file_size = file_stat.st_size
            except Exception as e:
                logger.warning(f"Failed to get file stat for {session_file}: {e}")
                file_mtime = None
                file_size = None

            # 如果已有 title，直接使用；否则读取文件获取
            title = None
            if session_id in existing_titles and existing_titles[session_id]:
                title = existing_titles[session_id]
                logger.debug(f"Using existing title for session: {session_id}")
            else:
                # 只在需要时读取文件获取 title
                title, _ = await self._read_session_title(session_file)

            session_info = ClaudeSessionInfo(
                session_id=session_id,
                session_file=str(session_file),
                title=title,
                file_mtime=file_mtime,
                file_size=file_size,
                is_agent_session=is_agent_session,
            )
            session_infos.append(session_info)

        # 按文件修改时间降序排序（最新的在前面）
        session_infos.sort(key=lambda x: (x.file_mtime or datetime.min), reverse=True)

        return session_infos

    async def _read_session_title(
        self, session_file: Path, max_length: int = DEFAULT_TITLE_MAX_LENGTH
    ) -> tuple[Optional[str], int]:
        """
        从 session 文件中读取标题

        优先级：
        1. 第一条用户消息的内容
        2. 第一条 assistant 消息的 text 内容（用于 agent session）

        跳过特殊行（不增加行号计数）：
        - type='file-history-snapshot'
        - type='summary'
        - 用户消息内容为 'Warmup'

        Args:
            session_file: session 文件路径
            max_length: 标题最大长度（超过则截取并添加省略号）

        Returns:
            tuple[Optional[str], int]: (session 标题, 提取标题的行号)，
                                       如果未找到则返回 (None, 0)
        """
        try:
            line_number = 0
            async with aiofiles.open(session_file, "r", encoding="utf-8") as f:
                async for raw_line in f:
                    line = raw_line.strip()
                    if not line:
                        continue

                    try:
                        message_data = json.loads(line)
                        msg_type = message_data.get("type", "")

                        # 跳过 file-history-snapshot 和 summary（不增加行号）
                        if msg_type in ("file-history-snapshot", "summary"):
                            logger.debug(f"Skipping {msg_type} in {session_file.name}")
                            continue

                        # 只在有效行增加行号计数
                        line_number += 1

                        # 检查消息内容
                        message = message_data.get("message", {})
                        if isinstance(message, dict):
                            role = message.get("role", "")
                            content = message.get("content", "")

                            # 如果是用户消息
                            if role == "user":
                                # 跳过 Warmup 消息（系统预热请求）
                                if content == "Warmup":
                                    logger.debug(
                                        f"Skipping Warmup message in {session_file.name}"
                                    )
                                    # 回退行号计数（因为这不是有效的内容行）
                                    line_number -= 1
                                    continue

                                # 优先检查是否是 command 消息，如果是则提取 command 名称
                                command_name = self._extract_command_name(content)
                                if command_name:
                                    title = self._truncate_title(
                                        command_name, max_length
                                    )
                                    if title:
                                        logger.debug(
                                            f"Extracted command title from user message in {session_file.name} at line {line_number}: {title}"
                                        )
                                        return title, line_number

                                # 使用用户消息内容作为标题
                                if content:
                                    title = self._truncate_title(
                                        str(content), max_length
                                    )
                                    if title:
                                        logger.debug(
                                            f"Extracted title from user message in {session_file.name} at line {line_number}: {title}"
                                        )
                                        return title, line_number

                            # 如果是 assistant 消息（用于 agent session）
                            elif role == "assistant":
                                # 尝试从 content 中提取 text
                                text = self._extract_text_from_content(content)
                                if text:
                                    title = self._truncate_title(text, max_length)
                                    if title:
                                        logger.debug(
                                            f"Extracted title from assistant message in {session_file.name} at line {line_number}: {title}"
                                        )
                                        return title, line_number

                    except json.JSONDecodeError:
                        # 跳过无法解析的行，继续尝试下一行
                        continue
        except (IOError, UnicodeDecodeError, OSError) as e:
            logger.warning(f"Failed to read title from {session_file}: {e}")
        return None, 0

    def _extract_command_name(self, content: str) -> Optional[str]:
        """
        从 content 中提取 command 名称

        严格匹配：content 必须完全是标准的 command 消息格式
        格式 1：<command-message>...</command-message>\n<command-name>...</command-name>
        格式 2：<command-message>...</command-message>\n<command-name>...</command-name>\n<command-args>...</command-args>

        Args:
            content: 消息的 content 字段

        Returns:
            Optional[str]: 提取的 command 名称，如果未找到或格式不匹配则返回 None
        """
        if not isinstance(content, str):
            return None

        # 严格匹配整个 content 必须是 command 消息格式
        # 格式 1：<command-message>xxx</command-message> <换行> <command-name>xxx</command-name>
        # 格式 2：<command-message>xxx</command-message> <换行> <command-name>xxx</command-name> <换行> <command-args>xxx</command-args>
        # 前后不能有其他字符
        command_pattern = re.compile(
            r"^<command-message>.*?</command-message>\s*<command-name>(.*?)</command-name>(?:\s*<command-args>.*?)?$"
        )
        match = command_pattern.match(content.strip())

        if match:
            return match.group(1)

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

    def _extract_text_from_content(self, content) -> Optional[str]:
        """
        从 content 中提取 text 内容

        Args:
            content: message 的 content 字段

        Returns:
            Optional[str]: 提取的文本，如果未找到则返回 None
        """
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text = item.get("text", "")
                        if text:
                            return text
        return None

    async def _extract_project_path_from_session(
        self, session_file: Path
    ) -> Optional[str]:
        """
        从 session 文件中提取项目路径（遍历所有行直到找到 cwd）

        Args:
            session_file: session 文件路径

        Returns:
            Optional[str]: 项目路径，如果未找到则返回 None
        """
        try:
            async with aiofiles.open(session_file, "r", encoding="utf-8") as f:
                async for line in f:
                    line = line.strip()
                    if line:
                        try:
                            message_data = json.loads(line)
                            # 尝试从 cwd 字段获取项目路径
                            if "cwd" in message_data and message_data["cwd"]:
                                return message_data["cwd"]
                        except json.JSONDecodeError:
                            # 跳过无法解析的行，继续尝试下一行
                            continue
        except (IOError, UnicodeDecodeError, OSError) as e:
            logger.warning(f"Failed to read project path from {session_file}: {e}")
        return None

    async def detect_project_info(self) -> tuple[Optional[str], Optional[datetime]]:
        """
        检测项目路径和最后活跃时间，从最近修改的 session 文件中提取信息

        Returns:
            tuple[Optional[str], Optional[datetime]]: (项目路径, 最后活跃时间)，
                如果未找到则返回 (None, None)
        """
        if not self.session_path.exists():
            return None, None

        # 获取所有 session 文件并按修改时间排序（最新的在前）
        session_files = list(self.session_path.glob("*.jsonl"))
        if not session_files:
            return None, None

        # 按文件修改时间逆序排序（最新的在前）
        try:
            session_files.sort(
                key=lambda f: f.stat().st_mtime if f.exists() else 0, reverse=True
            )
        except OSError as e:
            logger.warning(f"Failed to sort session files by mtime: {e}")
            # 排序失败，继续使用未排序的列表

        # 从最近的 session 文件开始查找项目路径
        for session_file in session_files:
            try:
                project_path = await self._extract_project_path_from_session(
                    session_file
                )
                if project_path:
                    # 获取文件修改时间作为最后活跃时间
                    file_mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
                    logger.debug(
                        f"Found project path: {project_path} from {session_file.name} "
                        f"(mtime: {file_mtime})"
                    )
                    return project_path, file_mtime
            except OSError as e:
                logger.warning(f"Failed to stat {session_file}: {e}")
                continue

        return None, None

    async def _load_session_data(
        self, session_file: Path, debug: bool = False
    ) -> tuple[Optional[ClaudeSession], dict]:
        """
        完整加载 session 数据（包含所有 messages）

        Args:
            session_file: session 文件路径
            debug: 是否收集详细的调试信息（默认为 False）

        Returns:
            tuple[Optional[ClaudeSession], dict]: (完整的 session 数据, 调试信息字典)
                - session: 完整的 session 数据，如果失败则返回 None
                - debug_info: 当 debug=True 时包含详细统计信息，否则只包含基本错误信息
                    - raw_total: 原始总行数
                    - raw_effective: 有效消息数量
                    - raw_meta: meta 消息数量（包括 summary）
                    - raw_user: user 消息数量
                    - raw_assistant: assistant 消息数量
                    - raw_system: system 消息数量
                    - raw_tool_use: 原始 tool_use 数量
                    - raw_tool_result: 原始 tool_result 数量
                    - raw_thinking: 原始 thinking 数量
                    - merged_total: 合并后消息总数
                    - merged_tool_use: 合并后 tool_use 数量
                    - merged_tool_use_complete: 完成的 tool_use 数量
                    - merged_tool_use_incomplete: 未完成的 tool_use 数量
                    - merged_text: 合并后 text 数量
                    - merged_thinking: 合并后 thinking 数量
                    - dropped_messages: 丢弃的消息总数
                    - dropped_expected: 预期内的丢弃数量（如 file-history-snapshot、summary）
                    - dropped_unexpected: 非预期的丢弃数量（需要警告）
                    - dropped_samples: 最多 2 条被丢弃消息的示例
                    - error: 错误信息（如果有）
        """
        session_id = session_file.stem
        is_agent_session = session_file.name.startswith("agent-")

        # 初始化调试信息（只初始化基本字段，详细字段按需初始化）
        debug_info: Dict[str, Any] = {
            "error": None,
        }

        # 只在 debug 模式下初始化详细统计字段
        if debug:
            debug_info.update(
                {
                    "raw_total": 0,
                    "raw_effective": 0,
                    "raw_meta": 0,
                    "raw_user": 0,
                    "raw_assistant": 0,
                    "raw_system": 0,
                    "raw_tool_use": 0,
                    "raw_tool_result": 0,
                    "raw_thinking": 0,
                    "merged_total": 0,
                    "merged_tool_use": 0,
                    "merged_tool_use_complete": 0,
                    "merged_tool_use_incomplete": 0,
                    "merged_text": 0,
                    "merged_thinking": 0,
                    "dropped_messages": 0,
                    "dropped_samples": [],  # 返回所有丢弃消息的样本，不在这里过滤
                }
            )

        try:
            # 获取文件统计信息
            file_stat = session_file.stat()
            file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
            file_size = file_stat.st_size

            # 读取会话标题
            title, _ = await self._read_session_title(session_file)

            # 读取整个文件
            with open(session_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 解析所有行并同时统计原始消息
            raw_messages = []
            first_active_at = None
            last_active_at = None
            total_lines = 0
            empty_lines = 0
            invalid_json_lines = 0

            # 在 debug 模式下的统计变量
            raw_meta = raw_user = raw_assistant = raw_system = 0
            raw_tool_use = raw_tool_result = raw_thinking = 0

            for line in content.splitlines():
                total_lines += 1
                line = line.strip()
                if not line:
                    empty_lines += 1
                    continue

                try:
                    message_data = json.loads(line)
                    raw_messages.append(message_data)

                    # 提取时间信息
                    if "timestamp" in message_data:
                        timestamp_str = message_data["timestamp"]
                        timestamp = parse_iso_timestamp(timestamp_str)

                        if timestamp:
                            if first_active_at is None:
                                first_active_at = timestamp
                            last_active_at = max(last_active_at or timestamp, timestamp)

                    # 在 debug 模式下同时统计原始消息
                    if debug:
                        msg_type = message_data.get("type", "")
                        message = message_data.get("message", {})

                        if msg_type == "meta" or msg_type == "summary":
                            raw_meta += 1
                        elif msg_type == "user":
                            raw_user += 1
                            # 统计 user 消息中的 tool_result
                            content = message.get("content", [])
                            if isinstance(content, list):
                                for item in content:
                                    if (
                                        isinstance(item, dict)
                                        and item.get("type") == "tool_result"
                                    ):
                                        raw_tool_result += 1
                        elif msg_type == "assistant":
                            raw_assistant += 1
                            # 统计 assistant 消息中的 content 类型
                            content = message.get("content", [])
                            if isinstance(content, list):
                                for item in content:
                                    if isinstance(item, dict):
                                        if item.get("type") in (
                                            "tool_use",
                                            "server_tool_use",
                                        ):
                                            raw_tool_use += 1
                                        elif item.get("type") == "thinking":
                                            raw_thinking += 1
                            elif isinstance(content, str) and content:
                                raw_thinking += 1
                        elif msg_type == "system":
                            raw_system += 1

                except json.JSONDecodeError:
                    invalid_json_lines += 1
                    continue

            # 在 debug 模式下保存原始消息统计
            if debug:
                debug_info["raw_total"] = total_lines
                debug_info["raw_effective"] = len(raw_messages)
                debug_info["raw_meta"] = raw_meta
                debug_info["raw_user"] = raw_user
                debug_info["raw_assistant"] = raw_assistant
                debug_info["raw_system"] = raw_system
                debug_info["raw_tool_use"] = raw_tool_use
                debug_info["raw_tool_result"] = raw_tool_result
                debug_info["raw_thinking"] = raw_thinking

            # 如果没有找到有效数据，返回 None
            if not raw_messages:
                logger.debug(
                    f"No valid messages found in {session_file} | "
                    f"total_lines: {total_lines} | "
                    f"empty_lines: {empty_lines} | "
                    f"invalid_json_lines: {invalid_json_lines}"
                )
                return None, debug_info

            # 合并 tool_use 和 tool_result
            merged_messages = self._merge_tool_use_with_result(raw_messages)

            # 合并连续的同一 role 的消息
            merged_messages = self._merge_consecutive_messages(merged_messages)

            # 只在 debug 模式下收集被丢弃的消息和统计信息
            if debug:
                # 收集被丢弃的消息（用于调试）
                # 通过检查 _dropped 标记来判断，而不是通过 id 比较
                dropped = [m for m in raw_messages if m.get("_dropped", False)]
                debug_info["dropped_messages"] = len(dropped)

                # 保存最多 2 条被丢弃的消息样本（所有丢弃消息）
                for dropped_msg in dropped[:2]:
                    sample = {
                        "type": dropped_msg.get("type"),
                        "timestamp": dropped_msg.get("timestamp"),
                        "role": dropped_msg.get("message", {}).get("role"),
                        "drop_reason": dropped_msg.get("_drop_reason", "unknown"),
                        "_expected_drop": dropped_msg.get("_expected_drop", False),
                        "subtype": dropped_msg.get("subtype"),
                    }
                    # 提取内容的前 100 个字符作为示例
                    content = dropped_msg.get("message", {}).get("content")
                    if isinstance(content, str):
                        sample["content_preview"] = content[:100]
                    elif isinstance(content, list) and len(content) > 0:
                        sample["content_preview"] = (
                            f"[{content[0].get('type', 'unknown')}]"
                        )
                    # 对于 summary 类型，尝试从 summary 字段获取内容
                    elif dropped_msg.get("type") == "summary":
                        summary_text = dropped_msg.get("summary", "")
                        sample["content_preview"] = str(summary_text)[:100]
                    debug_info["dropped_samples"].append(sample)

            # 创建 ClaudeMessage 对象
            messages = []
            for message_data in merged_messages:
                # 清理内部标记字段（以 _ 开头的字段）
                clean_data = {
                    k: v for k, v in message_data.items() if not k.startswith("_")
                }

                message = ClaudeMessage.model_validate(
                    {
                        "timestamp": clean_data.get("timestamp", ""),
                        "message": clean_data.get("message"),
                        "cwd": clean_data.get("cwd"),
                        "gitBranch": clean_data.get("gitBranch"),
                        "raw_data": clean_data,
                    }
                )
                messages.append(message)

            message_count = len(messages)

            # 如果合并后消息条数为 0，返回 None（所有消息都被过滤掉了）
            if message_count == 0:
                logger.warning(
                    f"All messages were filtered out after merging in {session_file.name} | "
                    f"total_lines: {total_lines} | "
                    f"raw_messages count: {len(raw_messages)} | "
                    f"empty_lines: {empty_lines} | "
                    f"invalid_json_lines: {invalid_json_lines} | "
                    f"merged_messages count: {len(merged_messages)}"
                )
                return None, debug_info

            # 只在 debug 模式下统计合并后的消息
            if debug:
                debug_info["merged_total"] = message_count
                for message_data in merged_messages:
                    message = message_data.get("message", {})
                    content = message.get("content", [])
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict):
                                if item.get("type") in ("tool_use", "server_tool_use"):
                                    debug_info["merged_tool_use"] += 1
                                    if item.get("status") == "complete":
                                        debug_info["merged_tool_use_complete"] += 1
                                    elif item.get("status") == "incomplete":
                                        debug_info["merged_tool_use_incomplete"] += 1
                                elif item.get("type") == "text":
                                    debug_info["merged_text"] += 1
                                elif item.get("type") == "thinking":
                                    debug_info["merged_thinking"] += 1
                    elif isinstance(content, str):
                        debug_info["merged_text"] += 1

            session = ClaudeSession(
                session_id=session_id,
                session_file=str(session_file),
                title=title,
                session_file_md5=None,
                file_mtime=file_mtime,
                file_size=file_size,
                is_agent_session=is_agent_session,
                messages=messages,
                first_active_at=first_active_at,
                last_active_at=last_active_at,
                project_path=None,  # 不再提取
                git_branch=None,  # 不再提取
                message_count=message_count,
            )

            return session, debug_info

        except (IOError, UnicodeDecodeError, OSError) as e:
            debug_info["error"] = f"Failed to read file: {e}"
            logger.error(f"Failed to read file {session_file}: {e}")
            return None, debug_info
        except Exception as e:
            debug_info["error"] = f"Unexpected error: {e}"
            logger.error(f"Unexpected error loading {session_file}: {e}")
            return None, debug_info

    async def read_session_contents(self, session_id: str) -> Optional[ClaudeSession]:
        """
        读取指定 session 的完整内容（包含所有 messages）

        Args:
            session_id: session ID

        Returns:
            Optional[ClaudeSession]: session 完整数据，包含 messages
                                    如果找不到则返回 None

        Raises:
            ValueError: 如果 session_id 无效（包含路径遍历字符等）
        """
        # 验证 session_id，防止路径遍历攻击
        self._validate_session_id(session_id)

        if not self.session_path.exists():
            logger.warning(f"Session directory does not exist: {self.session_path}")
            return None

        # 查找匹配的 session 文件
        session_files = [
            f
            for f in self.session_path.glob("*.jsonl")
            if f.stem == session_id or f.name == f"{session_id}.jsonl"
        ]

        for session_file in session_files:
            session, _ = await self._load_session_data(session_file)
            if session:
                return session

        logger.warning(f"Session not found: {session_id}")
        return None
