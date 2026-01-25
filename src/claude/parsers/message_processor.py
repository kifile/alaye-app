"""
消息处理器

负责处理消息的合并、转换等逻辑
"""

import logging
from typing import Dict, List, Optional

from ..models import MessageMeta, StandardMessage, StandardMessageContent
from .drop_rules import DropRuleRegistry

logger = logging.getLogger("claude")


class MessageProcessor:
    """
    消息处理器

    处理消息的合并、转换等逻辑：
    1. 提取 subagent 消息到 tool_use
    2. 合并 tool_result 到 tool_use
    3. 合并 isMeta 消息到 tool_use
    4. 处理用户打断消息
    5. 合并连续的同 role 消息
    6. 规范化 thinking 消息
    """

    def __init__(self, drop_registry: Optional[DropRuleRegistry] = None):
        """
        初始化消息处理器

        Args:
            drop_registry: 丢弃规则注册表（可选）
        """
        self.drop_registry = drop_registry or DropRuleRegistry()

    def process_messages(
        self, messages: List[StandardMessage]
    ) -> List[StandardMessage]:
        """
        处理消息列表，执行完整的处理流程

        处理顺序：
        1. 合并 tool_use 和 tool_result（跳过已 drop 的消息，处理时标记 tool_result 为 drop）
        2. 根据 parentToolUseID 合并 subagent 消息（跳过已 drop 的消息，处理时标记被合并的为 drop）
        3. 将 subagent 合并到对应的 tool_use 中（跳过已 drop 的消息，处理时标记 subagent 为 drop）
        4. 过滤掉所有被标记为 drop 的消息
        5. 合并连续的同 role 消息

        Args:
            messages: 标准化的消息列表

        Returns:
            List[StandardMessage]: 处理后的消息列表
        """
        logger.debug(f"=== process_messages: Start with {len(messages)} messages ===")

        # 1. 合并 tool_use 和 tool_result（处理过程中会跳过已 drop 的消息）
        processed_messages = self._merge_tool_use_and_result(messages)
        logger.debug(
            f"After merging tool_use/result: {len(processed_messages)} messages"
        )

        # 2. 根据 parentToolUseID 合并 subagent 消息（处理过程中会跳过已 drop 的消息）
        processed_messages = self._merge_subagent_messages_inline(processed_messages)
        logger.debug(
            f"After merging subagent messages: {len(processed_messages)} messages"
        )

        # 3. 将 subagent 合并到对应的 tool_use 中（处理过程中会跳过已 drop 的消息）
        processed_messages = self._merge_subagent_to_tool_use(processed_messages)
        logger.debug(
            f"After merging subagent to tool_use: {len(processed_messages)} messages"
        )

        # 4. 合并连续的同 role 消息（内部会过滤 drop 消息）
        final_messages = self._merge_consecutive_messages(processed_messages)
        logger.debug(
            f"=== process_messages: End with {len(final_messages)} messages ==="
        )

        return final_messages

    def process_messages_with_debug(self, messages: List[StandardMessage]) -> dict:
        """
        处理消息列表，返回每个阶段的中间结果（用于调试）

        处理顺序：
        1. 合并 tool_use 和 tool_result
        2. 根据 parentToolUseID 合并 subagent 消息（直接在消息中追加）
        3. 将 subagent 合并到对应的 tool_use 中
        4. 过滤掉被标记为 drop 的消息
        5. 合并连续的同 role 消息

        Args:
            messages: 标准化的消息列表

        Returns:
            dict: 包含每个阶段结果的字典
        """
        debug_info = {}

        # 1. 合并 tool_use 和 tool_result
        processed_messages = self._merge_tool_use_and_result(messages)
        debug_info["after_merge_tool_use_result"] = {
            "message_count": len(processed_messages),
            "messages": [msg.model_dump() for msg in processed_messages],
        }

        # 2. 根据 parentToolUseID 合并 subagent 消息（直接在消息中追加）
        processed_messages = self._merge_subagent_messages_inline(processed_messages)
        debug_info["after_merge_subagent_inline"] = {
            "message_count": len(processed_messages),
            "messages": [msg.model_dump() for msg in processed_messages],
        }

        # 3. 将 subagent 合并到对应的 tool_use 中
        processed_messages = self._merge_subagent_to_tool_use(processed_messages)
        debug_info["after_merge_subagent"] = {
            "message_count": len(processed_messages),
            "messages": [msg.model_dump() for msg in processed_messages],
        }

        # 4. 合并连续的同 role 消息（内部会过滤 drop 消息）
        final_messages = self._merge_consecutive_messages(processed_messages)
        debug_info["final"] = {
            "message_count": len(final_messages),
            "messages": [msg.model_dump() for msg in final_messages],
        }

        return debug_info

    def _merge_subagent_messages_inline(
        self, messages: List[StandardMessage]
    ) -> List[StandardMessage]:
        """
        根据 parentToolUseID 合并 subagent 消息（保留 role 信息）

        处理逻辑：
        - 跳过已被标记为 drop 的消息
        - 找到每个 parentToolUseID 对应的第一条 subagent 消息
        - 将 subagent 消息简化为只包含必要字段的 StandardMessage 对象（避免循环引用）
        - 调用 _merge_consecutive_messages 合并连续的同 role 消息

        Args:
            messages: 消息列表

        Returns:
            List[StandardMessage]: 合并后的消息列表
        """
        logger.debug(
            f"=== _merge_subagent_messages_inline: Processing {len(messages)} messages ==="
        )

        # parentToolUseID -> 第一条 subagent 消息对象
        subagent_first_message: Dict[str, StandardMessage] = {}
        result_messages: List[StandardMessage] = []

        # 第一次遍历：收集并包装 subagent 消息
        for message in messages:
            # 跳过已被标记为 drop 的消息（直接物理过滤）
            if message.meta.drop:
                continue

            parent_tool_use_id = message.parentToolUseID

            # 检查是否是 subagent 消息
            if parent_tool_use_id:
                # 检查是否已经记录过该 parentToolUseID 的第一条消息
                if parent_tool_use_id not in subagent_first_message:
                    # 第一次遇到这个 parentToolUseID，创建简化的消息对象和 subagent item
                    simplified_message = StandardMessage(
                        type=message.type,
                        subtype=message.subtype,
                        uuid=message.uuid,
                        meta=message.meta,
                        message=message.message,
                        timestamp=None,
                        parentToolUseID=None,
                        uuids=[],
                        raw_message={},
                    )

                    subagent_item = {
                        "type": "subagent",
                        "parentToolUseID": parent_tool_use_id,  # 保留在 subagent_item 层面
                        "messages": [simplified_message],
                    }

                    # 创建新的 content，包含这个 subagent item
                    new_message_content = StandardMessageContent(
                        role=message.message.role if message.message else "",
                        content=[subagent_item],
                    )
                    message.message = new_message_content

                    subagent_first_message[parent_tool_use_id] = message
                    result_messages.append(message)
                    logger.debug(f"  Created subagent item for {parent_tool_use_id}")
                else:
                    # 已经有第一条消息了，将当前消息简化并添加到 subagent item 的 messages 数组中
                    first_message = subagent_first_message[parent_tool_use_id]

                    # 边界检查：确保 content 存在且至少有一个元素
                    if not first_message.message or not first_message.message.content:
                        logger.warning(
                            f"  Subagent first message has no content for {parent_tool_use_id}, skipping"
                        )
                        result_messages.append(message)
                        continue

                    if (
                        not isinstance(first_message.message.content, list)
                        or len(first_message.message.content) == 0
                    ):
                        logger.warning(
                            f"  Subagent first message content is empty or not a list for {parent_tool_use_id}, skipping"
                        )
                        result_messages.append(message)
                        continue

                    subagent_item = first_message.message.content[0]  # subagent item

                    # 验证 subagent_item 的类型和内容
                    if (
                        not isinstance(subagent_item, dict)
                        or subagent_item.get("type") != "subagent"
                    ):
                        logger.warning(
                            f"  Invalid subagent item for {parent_tool_use_id}, expected type='subagent', got: {subagent_item.get('type') if isinstance(subagent_item, dict) else 'not a dict'}, skipping"
                        )
                        result_messages.append(message)
                        continue

                    # 创建简化的消息对象
                    simplified_message = StandardMessage(
                        type=message.type,
                        subtype=message.subtype,
                        uuid=message.uuid,
                        meta=message.meta,
                        message=message.message,
                        timestamp=None,
                        parentToolUseID=None,
                        uuids=[],
                        raw_message={},
                    )

                    # 添加到 messages 数组
                    subagent_item["messages"].append(simplified_message)

                    # 不标记为 drop，因为它已经以简化形式存在于 subagent item 中
                    # 不添加到 result_messages，因为它已经被包含在第一条消息中了
                    logger.debug(f"  Added subagent message to {parent_tool_use_id}")
            else:
                # 不是 subagent 消息，直接保留
                result_messages.append(message)

        # 第二次遍历：对每个 subagent 的消息进行合并
        for parent_tool_use_id, first_message in subagent_first_message.items():
            # 验证 content 存在且有效
            if not first_message.message or not first_message.message.content:
                logger.warning(
                    f"  Skipping invalid subagent first message for {parent_tool_use_id}: no content"
                )
                continue

            if (
                not isinstance(first_message.message.content, list)
                or len(first_message.message.content) == 0
            ):
                logger.warning(
                    f"  Skipping invalid subagent first message for {parent_tool_use_id}: content is empty or not a list"
                )
                continue

            subagent_item = first_message.message.content[0]

            # 验证 subagent_item 的类型
            if (
                not isinstance(subagent_item, dict)
                or subagent_item.get("type") != "subagent"
            ):
                logger.warning(
                    f"  Skipping invalid subagent item for {parent_tool_use_id}: expected type='subagent'"
                )
                continue

            messages_list = subagent_item.get("messages", [])

            # 调用 _merge_consecutive_messages 合并连续的同 role 消息
            merged_messages = self._merge_consecutive_messages(messages_list)

            # 更新 subagent_item 的 messages（合并后的消息已经是简化版本，不需要再次转换）
            subagent_item["messages"] = merged_messages
            subagent_item["message_count"] = len(merged_messages)

            logger.debug(
                f"  Merged subagent messages for {parent_tool_use_id}: {len(messages_list)} -> {len(merged_messages)}"
            )

        logger.debug(
            f"=== After merging subagent messages inline: {len(result_messages)} messages ==="
        )
        return result_messages

    def _merge_tool_use_and_result(
        self, messages: List[StandardMessage]
    ) -> List[StandardMessage]:
        """
        合并 tool_use 和 tool_result

        处理逻辑：
        - 跳过已被标记为 drop 的消息
        - 将 tool_result 合并到对应的 tool_use 的 output 字段
        - 如果消息中只有 tool_result，标记该消息为 drop
        - 如果消息中还有其他内容，只移除 tool_result，保留其他内容

        Args:
            messages: 消息列表

        Returns:
            List[StandardMessage]: 合并后的消息列表
        """
        merged_messages: List[StandardMessage] = []
        # tool_use_id -> message 映射
        tool_use_map: Dict[str, StandardMessage] = {}

        logger.debug(
            f"=== _merge_tool_use_and_result: Processing {len(messages)} messages ==="
        )

        for idx, message in enumerate(messages):
            # 跳过已被标记为 drop 的消息（直接物理过滤）
            if message.meta.drop:
                logger.debug(f"  [{idx}] Skipping dropped message")
                continue

            msg_type = message.type
            message_content = message.message
            content = message_content.content if message_content else []

            # 处理 isMeta 消息
            is_meta = (
                message.meta.extra.get("isMeta", False) if message.meta.extra else False
            )
            source_tool_use_id = (
                message.meta.extra.get("sourceToolUseID")
                if message.meta.extra
                else None
            )

            if is_meta and source_tool_use_id:
                success = self._merge_meta_to_tool_use(message, tool_use_map)
                if success:
                    # 标记 isMeta 消息为 drop
                    message.meta.drop = True
                    message.meta.drop_reason = "merged_into_tool_use"
                    message.meta.expected_drop = True

                    # 准备包含 drop 字段的字典
                    drop_dict = message.model_dump()
                    # 确保 raw_message 中也包含 drop 相关字段
                    if drop_dict.get("raw_message"):
                        drop_dict["raw_message"]["_drop"] = True
                        drop_dict["raw_message"][
                            "_drop_reason"
                        ] = "merged_into_tool_use"
                        drop_dict["raw_message"]["_expected_drop"] = True

                    # 然后调用 record_drop（此时元数据已设置）
                    if self.drop_registry:
                        self.drop_registry.record_drop(
                            drop_dict["raw_message"],
                            reason="merged_into_tool_use",
                            expected=True,
                        )
                    logger.debug(
                        f"  [{idx}] isMeta message merged and marked as dropped"
                    )
                    merged_messages.append(message)
                    continue
                else:
                    # 合并失败，保留消息
                    logger.debug(
                        f"  [{idx}] isMeta message merge failed, keeping message"
                    )
                    merged_messages.append(message)
                    continue

            # 处理 user 和 assistant 消息中的 tool_result
            # 记录成功合并的 tool_use_id
            merged_tool_use_ids = set()

            # 单次遍历：同时处理 tool_result 合并和构建 new_content
            new_content = []
            tool_results_to_merge = []

            for item in content:
                if item.get("type") == "tool_result":
                    tool_results_to_merge.append(item)
                else:
                    new_content.append(item)

            if tool_results_to_merge:
                logger.debug(
                    f"  [{idx}] Found {len(tool_results_to_merge)} tool_results in {msg_type} message"
                )

                # 合并所有 tool_result
                for tool_result_item in tool_results_to_merge:
                    tool_use_id = tool_result_item.get("tool_use_id")
                    logger.debug(
                        f"    - Processing tool_result: tool_use_id={tool_use_id}, in_map={tool_use_id in tool_use_map}"
                    )
                    success = self._merge_tool_result_to_tool_use(
                        tool_result_item, tool_use_map
                    )
                    if success:
                        merged_tool_use_ids.add(tool_use_id)

                # 将未被合并的 tool_result 加回 new_content
                for tool_result_item in tool_results_to_merge:
                    tool_use_id = tool_result_item.get("tool_use_id")
                    if tool_use_id not in merged_tool_use_ids:
                        new_content.append(tool_result_item)

                # 检查是否还有其他内容
                has_other_content = len(new_content) > 0

                if not has_other_content:
                    # 只有 tool_result 且都成功合并，标记为 drop
                    message.meta.drop = True
                    message.meta.drop_reason = "tool_result_merged"
                    message.meta.expected_drop = True
                    logger.debug(
                        f"  [{idx}] Message only had tool_result, marked as dropped"
                    )
                else:
                    # 还有其他内容，直接更新 content
                    message_content.content = new_content
                    logger.debug(
                        f"  [{idx}] Removed merged tool_results, kept other content"
                    )

            # 处理 assistant 消息：收集 tool_use 到 map
            # 收集 tool_use 到 map
            for item in content:
                if item.get("type") in ("tool_use", "server_tool_use"):
                    tool_use_id = item.get("id")
                    if tool_use_id and tool_use_id not in tool_use_map:
                        tool_use_map[tool_use_id] = message
                        logger.debug(
                            f"      + Added tool_use to map: {tool_use_id} (total: {len(tool_use_map)})"
                        )

            merged_messages.append(message)
            logger.debug(f"  [{idx}] Assistant message processed")

        logger.debug(f"=== After merging: {len(merged_messages)} messages ===")
        return merged_messages

    def _merge_tool_result_to_tool_use(
        self, tool_result_item: dict, tool_use_map: Dict[str, StandardMessage]
    ) -> bool:
        """
        将 tool_result 合并到对应的 tool_use

        Args:
            tool_result_item: tool_result 内容项
            tool_use_map: tool_use_id -> StandardMessage 映射

        Returns:
            bool: 是否成功合并到 tool_use
        """
        tool_use_id = tool_result_item.get("tool_use_id")
        tool_result_uuid = tool_result_item.get("uuid")

        if tool_use_id and tool_use_id in tool_use_map:
            tool_use_message = tool_use_map[tool_use_id]
            tool_use_content = (
                tool_use_message.message.content if tool_use_message.message else []
            )

            # 找到对应的 tool_use 并更新
            new_content = []
            for item in tool_use_content:
                new_item = dict(item)
                if (
                    new_item.get("type") in ("tool_use", "server_tool_use")
                    and new_item.get("id") == tool_use_id
                ):
                    new_item["output"] = tool_result_item.get("content")
                    new_item["status"] = "complete"

                    # 保存 tool_result 的 uuid
                    if "result_uuids" not in new_item:
                        new_item["result_uuids"] = []
                    if tool_result_uuid:
                        new_item["result_uuids"].append(tool_result_uuid)

                    logger.debug(
                        f"      ✓ Merged tool_result to tool_use: {tool_use_id}"
                    )
                new_content.append(new_item)

            # 直接更新 tool_use_map 中消息的 content
            tool_use_message.message.content = new_content
            return True
        else:
            logger.warning(
                f"Tool_result not merged: tool_use_id={tool_use_id} not found in tool_use_map (map has {len(tool_use_map)} entries: {list(tool_use_map.keys())[:5]})"
            )
            return False

    def _merge_meta_to_tool_use(
        self, meta_message: StandardMessage, tool_use_map: Dict[str, StandardMessage]
    ) -> bool:
        """
        将 isMeta 消息合并到对应的 tool_use

        处理逻辑：
        - meta_message 是标准化的 StandardMessage，content 已被 Parser 转换为标准格式
        - 直接将 content 整个 list 设置到 tool_use item 的 extra 字段

        Args:
            meta_message: isMeta 消息 (StandardMessage)
            tool_use_map: tool_use_id -> StandardMessage 映射

        Returns:
            bool: 是否成功合并
        """
        source_tool_use_id = (
            meta_message.meta.extra.get("sourceToolUseID")
            if meta_message.meta.extra
            else None
        )

        if not (source_tool_use_id and source_tool_use_id in tool_use_map):
            logger.warning(
                f"Cannot merge isMeta: sourceToolUseID={source_tool_use_id} not found in tool_use_map"
            )
            return False

        tool_use_message = tool_use_map[source_tool_use_id]
        tool_use_content = (
            tool_use_message.message.content if tool_use_message.message else []
        )
        content = meta_message.message.content if meta_message.message else []

        if not content:
            logger.debug(
                f"No content found in isMeta message: sourceToolUseID={source_tool_use_id}"
            )
            return False

        # 找到对应的 tool_use item 并设置 extra
        for item in tool_use_content:
            if (
                isinstance(item, dict)
                and item.get("type") in ("tool_use", "server_tool_use")
                and item.get("id") == source_tool_use_id
            ):
                item["extra"] = content
                logger.debug(
                    f"  ✓ Merged isMeta to tool_use {source_tool_use_id}: {len(content)} items"
                )
                return True

        logger.warning(
            f"Cannot merge isMeta: tool_use item {source_tool_use_id} not found in content"
        )
        return False

    def _merge_subagent_to_tool_use(
        self, messages: List[StandardMessage]
    ) -> List[StandardMessage]:
        """
        将 subagent 消息合并到对应的 tool_use

        处理逻辑（单次遍历）：
        - 跳过已被标记为 drop 的消息
        - 第一次遍历：记录 tool_use_id 与消息的映射关系
        - 遍历消息的 content，当遇到 type="subagent" 的 item 时合并到对应的 tool_use
        - 清理被合并的消息，如果所有消息都被合并则标记消息为 drop

        Args:
            messages: 消息列表

        Returns:
            List[StandardMessage]: 合并后的消息列表
        """
        logger.debug(
            f"=== _merge_subagent_to_tool_use: Processing {len(messages)} messages ==="
        )

        # tool_use_id -> 包含该 tool_use 的消息
        tool_use_map: Dict[str, StandardMessage] = {}

        result_messages: List[StandardMessage] = []

        for message in messages:
            # 跳过已被标记为 drop 的消息（直接物理过滤）
            if message.meta.drop:
                continue

            message_content = message.message
            content = message_content.content if message_content else []

            if not isinstance(content, list):
                result_messages.append(message)
                continue

            # 第一次遍历 content：记录 tool_use_id 与消息的映射
            for item in content:
                if self._is_tool_use_item(item):
                    tool_use_id = item.get("id")
                    if tool_use_id and tool_use_id not in tool_use_map:
                        tool_use_map[tool_use_id] = message
                        logger.debug(f"  Recorded tool_use {tool_use_id} in message")

            # 第二次遍历 content：处理 subagent item
            new_content = []

            for item in content:
                if item.get("type") == "subagent":
                    # 找到对应的 tool_use 消息
                    parent_tool_use_id = item.get("parentToolUseID")

                    if parent_tool_use_id and parent_tool_use_id in tool_use_map:
                        # 找到对应的 tool_use 消息
                        tool_use_message = tool_use_map[parent_tool_use_id]
                        tool_use_content = (
                            tool_use_message.message.content
                            if tool_use_message.message
                            else []
                        )

                        # 在 tool_use 的 content 中找到对应的 tool_use item 并更新
                        updated_tool_use_content = []

                        for tool_use_item in tool_use_content:
                            if (
                                self._is_tool_use_item(tool_use_item)
                                and tool_use_item.get("id") == parent_tool_use_id
                            ):
                                # 直接在 tool_use_item 上修改，其他字段保持不变
                                tool_use_item["type"] = "subagent"
                                tool_use_item["agent_type"] = tool_use_item.get(
                                    "input", {}
                                ).get("subagent_type")
                                tool_use_item["session"] = {
                                    "messages": item.get("messages", []),
                                    "message_count": item.get("message_count", 0),
                                }

                                # 保存 uuid 列表
                                if "uuids" in item:
                                    tool_use_item["uuids"] = item["uuids"]

                                updated_tool_use_content.append(tool_use_item)

                                logger.debug(
                                    f"  Merged subagent to tool_use | tool_use_id: {parent_tool_use_id} | "
                                    f"message_count: {tool_use_item.get('session', {}).get('message_count', 0)}"
                                )
                            else:
                                updated_tool_use_content.append(tool_use_item)

                        # 更新 tool_use 消息的 content
                        tool_use_message.message.content = updated_tool_use_content

                        # subagent item 不需要添加到 new_content（已被合并到 tool_use 中）
                        logger.debug(
                            f"  Subagent item merged, tool_use_id: {parent_tool_use_id}"
                        )
                    else:
                        logger.warning(
                            f"  Subagent item parentToolUseID={parent_tool_use_id} not found in tool_use_map"
                        )
                        # 保留这个 subagent item（找不到对应的 tool_use）
                        new_content.append(item)
                else:
                    new_content.append(item)

            # 检查是否所有 content 都被合并了
            if len(new_content) == 0:
                # 所有消息都被合并，标记当前消息为 drop
                message.meta.drop = True
                message.meta.drop_reason = "all_content_merged_to_tool_use"
                message.meta.expected_drop = True
                logger.debug(f"  All content merged, marking message as dropped")
            elif len(new_content) < len(content):
                # 部分消息被合并，更新 content
                message_content.content = new_content
                result_messages.append(message)
                logger.debug(
                    f"  Some content merged, {len(new_content)}/{len(content)} items remaining"
                )
            else:
                # 没有消息被合并，保持原样
                result_messages.append(message)

        logger.debug(
            f"=== After merging subagent to tool_use: {len(result_messages)} messages ==="
        )
        return result_messages

    def _is_tool_use_item(self, item: dict) -> bool:
        """
        检查是否是 tool_use 类型的 item

        Args:
            item: content item

        Returns:
            bool: 是否是 tool_use 类型
        """
        return isinstance(item, dict) and item.get("type") in (
            "tool_use",
            "server_tool_use",
        )

    def _merge_consecutive_messages(
        self, messages: List[StandardMessage]
    ) -> List[StandardMessage]:
        """
        合并连续的同一 role 的消息

        Args:
            messages: 消息列表

        Returns:
            List[StandardMessage]: 合并后的消息列表
        """
        if not messages:
            return []

        merged_messages: List[StandardMessage] = []
        i = 0

        logger.debug(
            f"=== _merge_consecutive_messages: Processing {len(messages)} messages ==="
        )

        while i < len(messages):
            current_message = messages[i]

            # 跳过 drop 的消息（直接物理过滤）
            if current_message.meta.drop:
                i += 1
                continue

            current_role = (
                current_message.message.role if current_message.message else None
            )

            if not current_role:
                merged_messages.append(current_message)
                i += 1
                continue

            # system 消息不合并
            if current_role == "system":
                merged_messages.append(current_message)
                logger.debug(f"  [{i}] System message, not merged")
                i += 1
                continue

            # 收集连续的同一 role 消息
            consecutive_messages = [current_message]
            j = i + 1

            while j < len(messages):
                next_message = messages[j]

                # 跳过 drop 的消息
                if next_message.meta.drop:
                    j += 1
                    continue

                next_role = next_message.message.role if next_message.message else None

                if next_role == current_role:
                    consecutive_messages.append(next_message)
                    j += 1
                else:
                    break

            # 只有一条消息，直接添加
            if len(consecutive_messages) == 1:
                merged_messages.append(current_message)
                logger.debug(f"  [{i}-{i}] Single {current_role} message, not merged")
                i += 1
                continue

            # 合并多条消息
            logger.debug(
                f"  [{i}-{j-1}] Merging {len(consecutive_messages)} consecutive {current_role} messages"
            )
            merged_message = self._merge_message_group(consecutive_messages)
            merged_messages.append(merged_message)
            i = j

        logger.debug(
            f"=== After merging consecutive: {len(merged_messages)} messages ==="
        )
        return merged_messages

    def _merge_message_group(self, messages: List[StandardMessage]) -> StandardMessage:
        """
        合并一组连续的同 role 消息

        Args:
            messages: 连续的同 role 消息列表

        Returns:
            StandardMessage: 合并后的消息
        """
        if not messages:
            return StandardMessage(
                type="user",
                subtype=None,
                uuid=None,
                uuids=[],
                raw_message={},
                meta=MessageMeta(
                    drop=False,
                    drop_reason=None,
                    expected_drop=False,
                    has_tool_use=False,
                    has_tool_result=False,
                    has_thinking=False,
                    has_command=False,
                    uuid=None,
                ),
                message=StandardMessageContent(role="user", content=[]),
                timestamp=None,
                parentToolUseID=None,
            )

        # 收集所有 uuid
        all_uuids = []
        for msg in messages:
            if msg.uuids:
                all_uuids.extend(msg.uuids)
            elif msg.uuid:
                all_uuids.append(msg.uuid)

        # 检查 content 类型一致性
        content_types = set()
        for msg in messages:
            if msg.message and msg.message.content is not None:
                content = msg.message.content
                if isinstance(content, list):
                    content_types.add("list")
                elif isinstance(content, str):
                    content_types.add("string")
                else:
                    content_types.add("other")

        # 合并所有 content
        merged_contents = []
        for msg in messages:
            if msg.message and msg.message.content:
                content = msg.message.content
                if isinstance(content, list):
                    merged_contents.extend(content)
                else:
                    # 字符串类型的 content
                    if content_types == {"string"}:
                        merged_contents.append(content)
                    else:
                        merged_contents.append({"type": "text", "text": content})

        # 确定 role
        role = messages[0].message.role if messages[0].message else "user"

        # 确定最终的 content（确保是 List[Dict[str, Any]]）
        if content_types == {"string"} and len(merged_contents) > 1:
            # 如果全部是字符串，合并成一个字符串，然后包装成 text 类型
            final_content = [{"type": "text", "text": "\n".join(merged_contents)}]
        elif isinstance(merged_contents[0] if merged_contents else None, str):
            # 如果只有一个字符串，包装成 text 类型
            final_content = (
                [{"type": "text", "text": merged_contents[0]}]
                if merged_contents
                else []
            )
        else:
            # 已经是列表格式
            final_content = merged_contents

        # 创建新的 StandardMessage
        return StandardMessage(
            type=messages[0].type,
            subtype=messages[0].subtype,
            uuid=all_uuids[0] if all_uuids else messages[0].uuid,
            uuids=all_uuids,
            raw_message=messages[0].raw_message,
            meta=messages[0].meta,
            message=StandardMessageContent(role=role, content=final_content),
            timestamp=messages[0].timestamp,
            parentToolUseID=messages[0].parentToolUseID,
        )
