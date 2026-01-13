"""
Claude Session 操作模块
处理 Session 的扫描和读取操作
"""

import copy
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .models import ClaudeMessage, ClaudeSession, ClaudeSessionInfo

# Configure logger
logger = logging.getLogger("claude")


class ClaudeSessionOperations:
    """Claude Session 操作类"""

    def __init__(self, claude_session_path: Path):
        """
        初始化 Session 操作管理器

        Args:
            claude_session_path: 项目的 session 存储目录路径
        """
        self.session_path = claude_session_path

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

        for message_data in raw_messages:
            message = message_data.get("message", {})
            content = message.get("content", [])

            # 跳过空消息
            if not message:
                # 保留非消息类型（如 meta、file-history-snapshot）
                if message_data.get("type") not in ["user", "assistant"]:
                    continue
                merged_messages.append(message_data)
                continue

            # 处理空 content
            if not content or (isinstance(content, list) and len(content) == 0):
                continue

            # 处理 user 消息中的 tool_result
            # 注意：tool_result 消息的 type="user" 但 message.role="assistant"
            if message_data.get("type") == "user" and isinstance(content, list):
                # 检查是否包含 tool_result
                tool_results = [
                    item
                    for item in content
                    if isinstance(item, dict) and item.get("type") == "tool_result"
                ]

                if tool_results:
                    # 遍历所有 tool_result，找到对应的 tool_use 并合并
                    for tool_result_item in tool_results:
                        tool_use_id = tool_result_item.get("tool_use_id")
                        if tool_use_id and tool_use_id in tool_use_map:
                            # 找到对应的 tool_use 消息
                            tool_use_message_data = tool_use_map[tool_use_id]
                            tool_use_content = tool_use_message_data.get(
                                "message", {}
                            ).get("content", [])

                            # 在 tool_use_content 中找到对应的 tool_use 并添加 output
                            for tool_use_item in tool_use_content:
                                if (
                                    isinstance(tool_use_item, dict)
                                    and tool_use_item.get("type") == "tool_use"
                                    and tool_use_item.get("id") == tool_use_id
                                ):
                                    tool_use_item["output"] = tool_result_item.get(
                                        "content"
                                    )
                                    tool_use_item["status"] = "complete"
                                    break

                            # 从 map 中移除已处理的 tool_use（避免重复处理）
                            del tool_use_map[tool_use_id]
                    # 不单独添加 tool_result 消息（已经合并到 tool_use 中）
                    continue

            # 处理 assistant 消息
            if isinstance(content, list) and len(content) > 0:
                # 检查是否包含 tool_use
                has_tool_use = any(
                    isinstance(item, dict) and item.get("type") == "tool_use"
                    for item in content
                )

                if has_tool_use:
                    # 为 tool_use 添加 incomplete status（如果没有 output）
                    message_data_copy = copy.deepcopy(message_data)
                    content_copy = message_data_copy.get("message", {}).get(
                        "content", []
                    )

                    for item in content_copy:
                        if isinstance(item, dict) and item.get("type") == "tool_use":
                            tool_use_id = item.get("id")
                            if tool_use_id:
                                # 记录到 map 中，供后续 tool_result 查找
                                tool_use_map[tool_use_id] = message_data_copy

                            # 如果没有 output，标记为 incomplete
                            if "output" not in item and "status" not in item:
                                item["status"] = "incomplete"

                    merged_messages.append(message_data_copy)
                else:
                    # 普通 assistant 消息（text、thinking 等），需要规范化处理
                    message_data_copy = copy.deepcopy(message_data)
                    content_copy = message_data_copy.get("message", {}).get(
                        "content", []
                    )

                    # 规范化 thinking 类型：将 thinking 字段转换为 text 字段
                    for item in content_copy:
                        if isinstance(item, dict) and item.get("type") == "thinking":
                            # 如果存在 thinking 字段但没有 text 字段，则进行转换
                            if "thinking" in item and "text" not in item:
                                item["text"] = item.pop("thinking")

                    merged_messages.append(message_data_copy)
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
                # 创建合并后的消息
                merged_message = copy.deepcopy(current_message)

                # 合并所有 content
                merged_contents = []
                for msg in consecutive_messages:
                    content = msg.get("message", {}).get("content")
                    if content:
                        if isinstance(content, list):
                            merged_contents.extend(content)
                        else:
                            # 字符串类型的 content，转换为数组形式
                            merged_contents.append({"type": "text", "text": content})

                # 更新合并后的消息
                if merged_message.get("message"):
                    merged_message["message"]["content"] = merged_contents

                merged_messages.append(merged_message)
                i = j
            else:
                merged_messages.append(current_message)
                i += 1

        return merged_messages

    def _load_session_data(self, session_file: Path) -> Optional[ClaudeSession]:
        """
        从 JSONL 文件加载 session 数据

        Args:
            session_file: session 文件路径

        Returns:
            Optional[ClaudeSession]: 加载的 session 数据，如果失败则返回 None
        """
        session_id = session_file.stem
        is_agent_session = session_file.name.startswith("agent-")

        try:
            with open(session_file, "rb") as f:
                # Read entire file content for MD5 calculation
                content_bytes = f.read()
                file_hash = hashlib.md5()
                file_hash.update(content_bytes)
                file_md5 = file_hash.hexdigest()

                # Decode content for JSON parsing
                content = content_bytes.decode("utf-8")

                # 第一遍：收集所有原始消息
                raw_messages = []
                for line in content.splitlines():
                    line = line.strip()
                    if line:
                        message_data = json.loads(line)
                        raw_messages.append(message_data)

                # 第二遍：合并 tool_use 和 tool_result
                merged_messages = self._merge_tool_use_with_result(raw_messages)

                # 第三遍：合并连续的同一 role 的消息
                merged_messages = self._merge_consecutive_messages(merged_messages)

                # 第四遍：创建 ClaudeMessage 对象
                messages = []
                first_active_at = None
                last_active_at = None
                project_path = None
                git_branch = None

                for message_data in merged_messages:
                    # Create ClaudeMessage object using model_validate
                    message = ClaudeMessage.model_validate(
                        {
                            "timestamp": message_data.get("timestamp", ""),
                            "message": message_data.get("message"),
                            "cwd": message_data.get("cwd"),
                            "gitBranch": message_data.get("gitBranch"),
                            "raw_data": message_data,
                        }
                    )
                    messages.append(message)

                    # Extract metadata from messages
                    if "timestamp" in message_data:
                        timestamp_str = message_data["timestamp"]
                        if timestamp_str.endswith("Z"):
                            timestamp_str = timestamp_str.replace("Z", "+00:00")
                        timestamp = datetime.fromisoformat(timestamp_str)

                        # Convert to naive datetime for consistent comparison
                        if timestamp.tzinfo is not None:
                            timestamp = timestamp.replace(tzinfo=None)

                        if first_active_at is None:
                            first_active_at = timestamp
                        last_active_at = max(last_active_at or timestamp, timestamp)

                    if "cwd" in message_data and not project_path:
                        project_path = message_data["cwd"]

                    if "gitBranch" in message_data and not git_branch:
                        git_branch = message_data["gitBranch"]

                # 计算 message_count：统计所有 content 项的总数
                message_count = 0
                for msg in messages:
                    if msg.message is not None:
                        content = msg.message.get("content")
                        if isinstance(content, list):
                            message_count += len(content)
                        elif content:
                            message_count += 1

                # Create and return updated session with loaded data
                return ClaudeSession(
                    session_id=session_id,
                    session_file=str(session_file),
                    session_file_md5=file_md5,
                    is_agent_session=is_agent_session,
                    messages=messages,
                    first_active_at=first_active_at,
                    last_active_at=last_active_at,
                    project_path=project_path,
                    git_branch=git_branch,
                    message_count=message_count,
                )

        except (IOError, UnicodeDecodeError) as e:
            logger.error(f"Failed to read file {session_file}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse {session_file}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading {session_file}: {e}")
            return None

    async def scan_sessions(self) -> List[ClaudeSessionInfo]:
        """
        扫描 session 列表（只返回基本信息，不读取文件内容）

        Returns:
            List[ClaudeSessionInfo]: session 简要信息列表
        """
        if not self.session_path.exists():
            logger.warning(f"Session directory does not exist: {self.session_path}")
            return []

        session_infos = []

        # 扫描该目录下的所有 session 文件
        for session_file in self.session_path.glob("*.jsonl"):
            session_id = session_file.stem
            is_agent_session = session_file.name.startswith("agent-")

            # 获取文件最后修改时间并转换为 datetime
            try:
                mtime = session_file.stat().st_mtime
                last_modified = datetime.fromtimestamp(mtime)
            except Exception as e:
                logger.warning(f"Failed to get mtime for {session_file}: {e}")
                last_modified = None

            session_info = ClaudeSessionInfo(
                session_id=session_id,
                session_file=str(session_file),
                last_modified=last_modified,
                is_agent_session=is_agent_session,
            )
            session_infos.append(session_info)

        # 按最后修改时间降序排序（最新的在前面）
        session_infos.sort(
            key=lambda x: (x.last_modified or datetime.min), reverse=True
        )

        return session_infos

    async def read_session_contents(self, session_id: str) -> Optional[ClaudeSession]:
        """
        读取指定 session 的完整内容（包含 messages）

        Args:
            session_id: session ID

        Returns:
            Optional[ClaudeSession]: session 完整数据，包含 messages
                                    如果找不到则返回 None
        """
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
            session = self._load_session_data(session_file)
            if session:
                return session

        logger.warning(f"Session not found: {session_id}")
        return None
