"""
Claude Session 操作模块
处理 Session 的扫描和读取操作
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .models import ClaudeMessage, ClaudeSession, ClaudeSessionInfo, StandardMessage
from .parsers import DropRuleRegistry, MessageParser, MessageProcessor

# Configure logger
logger = logging.getLogger("claude")

# Constants
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

    def _create_parser(self) -> MessageParser:
        """创建消息解析器"""
        return MessageParser()

    def _create_processor(self, drop_registry: DropRuleRegistry) -> MessageProcessor:
        """创建消息处理器"""
        return MessageProcessor(drop_registry)

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

    async def _process_session_messages_from_file(
        self, session_file: Path, debug: bool = False
    ) -> tuple[List[StandardMessage], List[ClaudeMessage], DropRuleRegistry, dict]:
        """
        从文件处理 session 消息的完整流程（带调试信息的版本）

        Args:
            session_file: session 文件路径
            debug: 是否启用调试模式

        Returns:
            tuple:
                - 处理后的消息字典列表
                - ClaudeMessage 对象列表
                - DropRuleRegistry（包含丢弃统计）
                - debug_info: 调试信息（仅在 debug=True 时有数据）
        """
        # 创建丢弃规则注册表（用于统计和调试）
        drop_registry = DropRuleRegistry()

        # 初始化 debug_info
        debug_info: dict = {}
        if debug:
            debug_info["raw_total"] = 0
            debug_info["raw_effective"] = 0
            debug_info["raw_meta"] = 0
            debug_info["raw_user"] = 0
            debug_info["raw_assistant"] = 0
            debug_info["raw_system"] = 0
            debug_info["raw_tool_use"] = 0
            debug_info["raw_tool_result"] = 0
            debug_info["raw_thinking"] = 0
            debug_info["empty_lines"] = 0
            debug_info["invalid_json_lines"] = 0
            debug_info["merged_total"] = 0
            debug_info["merged_tool_use"] = 0
            debug_info["merged_tool_use_complete"] = 0
            debug_info["merged_tool_use_incomplete"] = 0
            debug_info["merged_text"] = 0
            debug_info["merged_thinking"] = 0
            debug_info["dropped_messages"] = 0
            debug_info["dropped_samples"] = []

        # 使用 parser 从文件读取并解析消息（同时收集统计）
        parser = self._create_parser()
        parsed_messages, parse_stats = await parser.parse_session_file_with_stats(
            str(session_file), collect_stats=debug
        )

        if debug and parse_stats:
            debug_info["raw_total"] = parse_stats.raw_total
            debug_info["raw_effective"] = parse_stats.raw_effective
            debug_info["raw_meta"] = parse_stats.raw_meta
            debug_info["raw_user"] = parse_stats.raw_user
            debug_info["raw_assistant"] = parse_stats.raw_assistant
            debug_info["raw_system"] = parse_stats.raw_system
            debug_info["raw_tool_use"] = parse_stats.raw_tool_use
            debug_info["raw_tool_result"] = parse_stats.raw_tool_result
            debug_info["raw_thinking"] = parse_stats.raw_thinking
            debug_info["empty_lines"] = parse_stats.empty_lines
            debug_info["invalid_json_lines"] = parse_stats.invalid_json_lines

        # 2. 创建处理器并处理消息
        processor = self._create_processor(drop_registry)
        processed_messages = processor.process_messages(parsed_messages)

        # 3. 创建 ClaudeMessage 对象列表
        claude_messages = []
        for message_data in processed_messages:
            # message_data 现在是 StandardMessage 对象
            # 使用 model_dump() 转换为字典
            message_dict = (
                message_data.model_dump() if hasattr(message_data, "model_dump") else {}
            )

            # timestamp 可能为 None，需要转换为空字符串
            timestamp_value = message_dict.get("timestamp") or ""

            claude_message = ClaudeMessage.model_validate(
                {
                    "timestamp": timestamp_value,
                    "message": message_dict.get("message"),
                    "cwd": message_dict.get("cwd"),
                    "gitBranch": message_dict.get("gitBranch"),
                }
            )
            claude_messages.append(claude_message)

        return processed_messages, claude_messages, drop_registry, debug_info

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

            # 跳过 agent session 文件（这些是 subagent 的执行记录）
            if is_agent_session:
                logger.debug(f"Skipping agent session file: {session_file.name}")
                continue

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

            # 如果没有标题，说明可能没有产生真实会话，过滤掉该 session
            if not title:
                logger.debug(
                    f"Skipping session without title: {session_id} | "
                    f"file: {session_file.name}"
                )
                continue

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

        Args:
            session_file: session 文件路径
            max_length: 标题最大长度（超过则截取并添加省略号）

        Returns:
            tuple[Optional[str], int]: (session 标题, 提取标题的行号)，
                                       如果未找到则返回 (None, 0)
        """
        parser = self._create_parser()
        return await parser.extract_session_title(str(session_file), max_length)

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
        parser = self._create_parser()
        return await parser.extract_project_path(str(session_file))

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
        """
        session_id = session_file.stem
        is_agent_session = session_file.name.startswith("agent-")

        # 初始化调试信息（只初始化基本字段，详细字段按需初始化）
        debug_info: dict = {
            "error": None,
        }

        try:
            # 获取文件统计信息
            file_stat = session_file.stat()
            file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
            file_size = file_stat.st_size

            # 读取会话标题
            title, _ = await self._read_session_title(session_file)

            # 使用新的流程：直接从文件读取并处理消息
            merged_messages, messages, drop_registry, parse_debug_info = (
                await self._process_session_messages_from_file(session_file, debug)
            )

            # 合并 debug 信息
            if debug and parse_debug_info:
                debug_info.update(parse_debug_info)

            message_count = len(messages)

            # 如果合并后消息条数为 0，返回 None（所有消息都被过滤掉了）
            if message_count == 0:
                logger.warning(
                    f"All messages were filtered out after merging in {session_file.name}"
                )
                return None, debug_info

            # 只在 debug 模式下统计丢弃和合并后的消息
            if debug:
                # 获取丢弃统计
                drop_stats = drop_registry.get_stats()
                debug_info["dropped_messages"] = drop_stats["total"]
                debug_info["dropped_samples"] = drop_registry.get_samples(
                    max_count=2, unexpected_only=True
                )

                # 统计合并后的消息
                debug_info["merged_total"] = message_count
                for message_data in merged_messages:
                    # message_data 现在是 StandardMessage 对象
                    if not message_data.message:
                        continue

                    content = message_data.message.content
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict):
                                item_type = item.get("type")

                                if item_type in ("tool_use", "server_tool_use"):
                                    debug_info["merged_tool_use"] += 1
                                    if item.get("status") == "complete":
                                        debug_info["merged_tool_use_complete"] += 1
                                    elif item.get("status") == "incomplete":
                                        debug_info["merged_tool_use_incomplete"] += 1
                                elif item_type == "subagent":
                                    # 统计 subagent 内部的 tool_use
                                    # subagent 结构: {"type": "subagent", "messages": [...]}
                                    subagent_messages = item.get("messages", [])
                                    if isinstance(subagent_messages, list):
                                        for sub_msg in subagent_messages:
                                            # sub_msg 可能是 StandardMessage 对象或 dict
                                            if hasattr(sub_msg, "message") and hasattr(
                                                sub_msg.message, "content"
                                            ):
                                                # StandardMessage 对象
                                                sub_msg_content = (
                                                    sub_msg.message.content
                                                )
                                            elif isinstance(sub_msg, dict):
                                                # dict 格式
                                                sub_msg_data = sub_msg.get(
                                                    "message", {}
                                                )
                                                if isinstance(sub_msg_data, dict):
                                                    sub_msg_content = sub_msg_data.get(
                                                        "content", []
                                                    )
                                                else:
                                                    continue
                                            else:
                                                continue

                                            if not isinstance(sub_msg_content, list):
                                                continue

                                            for sub_item in sub_msg_content:
                                                if not isinstance(sub_item, dict):
                                                    continue
                                                sub_item_type = sub_item.get("type")
                                                if sub_item_type in (
                                                    "tool_use",
                                                    "server_tool_use",
                                                ):
                                                    debug_info["merged_tool_use"] += 1
                                                    if (
                                                        sub_item.get("status")
                                                        == "complete"
                                                    ):
                                                        debug_info[
                                                            "merged_tool_use_complete"
                                                        ] += 1
                                                    elif (
                                                        sub_item.get("status")
                                                        == "incomplete"
                                                    ):
                                                        debug_info[
                                                            "merged_tool_use_incomplete"
                                                        ] += 1
                                                elif sub_item_type == "text":
                                                    debug_info["merged_text"] += 1
                                                elif sub_item_type == "thinking":
                                                    debug_info["merged_thinking"] += 1
                                elif item_type == "text":
                                    debug_info["merged_text"] += 1
                                elif item_type == "thinking":
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
