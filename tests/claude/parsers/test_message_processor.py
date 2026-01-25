"""
MessageProcessor 的单元测试
"""

import pytest

from src.claude.models import MessageMeta, StandardMessage, StandardMessageContent
from src.claude.parsers.drop_rules import DropRuleRegistry
from src.claude.parsers.message_processor import MessageProcessor


class TestMessageProcessor:
    """测试 MessageProcessor 类"""

    @pytest.fixture
    def processor(self):
        """创建 MessageProcessor 实例"""
        return MessageProcessor()

    @pytest.fixture
    def drop_registry(self):
        """创建 DropRuleRegistry 实例"""
        return DropRuleRegistry()

    # ========== 测试 process_messages ==========

    def test_process_messages_empty(self, processor):
        """测试处理空消息列表"""
        result = processor.process_messages([])

        assert result == []

    def test_process_messages_basic(self, processor):
        """测试基本消息处理"""
        messages = [
            StandardMessage(
                type="user",
                subtype=None,
                uuid=None,
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="user", content=[{"type": "text", "text": "Hello"}]
                ),
                timestamp="2024-01-01T10:00:00Z",
                parentToolUseID=None,
            ),
            StandardMessage(
                type="assistant",
                subtype=None,
                uuid=None,
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="assistant",
                    content=[{"type": "text", "text": "Hi"}],
                ),
                timestamp="2024-01-01T10:00:01Z",
                parentToolUseID=None,
            ),
        ]

        result = processor.process_messages(messages)

        assert len(result) == 2

    def test_process_messages_filter_dropped(self, processor):
        """测试过滤已标记为 drop 的消息"""
        messages = [
            StandardMessage(
                type="user",
                subtype=None,
                uuid=None,
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="user", content=[{"type": "text", "text": "Hello"}]
                ),
                timestamp="2024-01-01T10:00:00Z",
                parentToolUseID=None,
            ),
            StandardMessage(
                type="meta",
                subtype=None,
                uuid=None,
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=True, drop_reason="expected_empty:meta"),
                message=StandardMessageContent(role="system", content=[]),
                timestamp="2024-01-01T10:00:01Z",
                parentToolUseID=None,
            ),
        ]

        result = processor.process_messages(messages)

        # drop 的消息应该被过滤掉
        assert len(result) == 1
        assert result[0].type == "user"

    # ========== 测试 _merge_tool_use_and_result ==========

    def test_merge_tool_use_and_result_success(self, processor):
        """测试成功合并 tool_use 和 tool_result"""
        messages = [
            # Assistant 消息，包含 tool_use
            StandardMessage(
                type="assistant",
                subtype=None,
                uuid="uuid-1",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="assistant",
                    content=[
                        {
                            "type": "tool_use",
                            "id": "call_123",
                            "name": "Grep",
                            "input": {"pattern": "test"},
                        }
                    ],
                ),
                timestamp="2024-01-01T10:00:00Z",
                parentToolUseID=None,
            ),
            # User 消息，包含 tool_result
            StandardMessage(
                type="user",
                subtype=None,
                uuid="uuid-2",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="user",
                    content=[
                        {
                            "type": "tool_result",
                            "tool_use_id": "call_123",
                            "content": "Found 10 matches",
                        }
                    ],
                ),
                timestamp="2024-01-01T10:00:01Z",
                parentToolUseID=None,
            ),
        ]

        result = processor._merge_tool_use_and_result(messages)

        # 应该有 2 条消息（tool_result 已合并）
        assert len(result) == 2

        # 验证 tool_use 已被更新
        assistant_msg = result[0]
        tool_use_item = assistant_msg.message.content[0]
        assert tool_use_item["id"] == "call_123"
        assert tool_use_item["output"] == "Found 10 matches"
        assert tool_use_item["status"] == "complete"

        # 验证 tool_result 消息已被标记为 drop
        assert result[1].meta.drop is True
        assert result[1].meta.drop_reason == "tool_result_merged"

    def test_merge_tool_use_and_result_not_found(self, processor):
        """测试 tool_result 找不到对应的 tool_use"""
        messages = [
            StandardMessage(
                type="user",
                subtype=None,
                uuid="uuid-1",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="user",
                    content=[
                        {
                            "type": "tool_result",
                            "tool_use_id": "call_unknown",
                            "content": "Some result",
                        }
                    ],
                ),
                timestamp="2024-01-01T10:00:00Z",
                parentToolUseID=None,
            ),
        ]

        result = processor._merge_tool_use_and_result(messages)

        # 消息应该保留（因为没有成功合并）
        assert len(result) == 1
        assert result[0].meta.drop is False

    def test_merge_tool_use_and_result_multiple_results(self, processor):
        """测试多个 tool_result 合并到同一个 tool_use"""
        messages = [
            # Assistant 消息，包含一个 tool_use
            StandardMessage(
                type="assistant",
                subtype=None,
                uuid="uuid-1",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="assistant",
                    content=[
                        {
                            "type": "tool_use",
                            "id": "call_123",
                            "name": "Grep",
                            "input": {"pattern": "test"},
                        }
                    ],
                ),
                timestamp="2024-01-01T10:00:00Z",
                parentToolUseID=None,
            ),
            # User 消息，包含多个 tool_result
            StandardMessage(
                type="user",
                subtype=None,
                uuid="uuid-2",
                uuids=["result-uuid-1", "result-uuid-2"],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="user",
                    content=[
                        {
                            "type": "tool_result",
                            "tool_use_id": "call_123",
                            "content": "Result 1",
                            "uuid": "result-uuid-1",
                        },
                        {
                            "type": "tool_result",
                            "tool_use_id": "call_123",
                            "content": "Result 2",
                            "uuid": "result-uuid-2",
                        },
                    ],
                ),
                timestamp="2024-01-01T10:00:01Z",
                parentToolUseID=None,
            ),
        ]

        result = processor._merge_tool_use_and_result(messages)

        # 应该有 2 条消息
        assert len(result) == 2

        # 验证 tool_use 只保留最后一个 output
        assistant_msg = result[0]
        tool_use_item = assistant_msg.message.content[0]
        # 最后一个 tool_result 的内容应该被使用
        assert tool_use_item["output"] == "Result 2"

        # 验证 result_uuids 保存了两个 uuid
        assert "result_uuids" in tool_use_item
        assert len(tool_use_item["result_uuids"]) == 2

    # ========== 测试 _merge_meta_to_tool_use ==========

    def test_merge_meta_to_tool_use_success_with_text_content(self, processor):
        """测试成功合并 isMeta 消息到 tool_use（text content）"""
        tool_use_map = {}

        # 创建 tool_use 消息
        tool_use_message = StandardMessage(
            type="assistant",
            subtype=None,
            uuid="uuid-1",
            uuids=[],
            raw_message={},
            meta=MessageMeta(drop=False, extra={"isMeta": False}),
            message=StandardMessageContent(
                role="assistant",
                content=[
                    {
                        "type": "tool_use",
                        "id": "call_123",
                        "name": "Grep",
                        "input": {"pattern": "test"},
                    }
                ],
            ),
            timestamp="2024-01-01T10:00:00Z",
            parentToolUseID=None,
        )
        tool_use_map["call_123"] = tool_use_message

        # 创建 isMeta 消息（content 是列表格式）
        meta_message = StandardMessage(
            type="user",
            subtype=None,
            uuid="uuid-2",
            uuids=[],
            raw_message={},
            meta=MessageMeta(
                drop=False, extra={"isMeta": True, "sourceToolUseID": "call_123"}
            ),
            message=StandardMessageContent(
                role="user",
                content=[{"type": "text", "text": "This is the metadata text"}],
            ),
            timestamp="2024-01-01T10:00:01Z",
            parentToolUseID=None,
        )

        result = processor._merge_meta_to_tool_use(meta_message, tool_use_map)

        # 验证返回值为 True
        assert result is True

        # 验证 extra 字段被设置为整个 content list
        tool_use_item = tool_use_message.message.content[0]
        assert "extra" in tool_use_item
        assert isinstance(tool_use_item["extra"], list)
        assert len(tool_use_item["extra"]) == 1
        assert tool_use_item["extra"][0]["type"] == "text"
        assert tool_use_item["extra"][0]["text"] == "This is the metadata text"

    def test_merge_meta_to_tool_use_success_with_multiple_content_items(
        self, processor
    ):
        """测试成功合并 isMeta 消息（多个 content items）"""
        tool_use_map = {}

        tool_use_message = StandardMessage(
            type="assistant",
            subtype=None,
            uuid="uuid-1",
            uuids=[],
            raw_message={},
            meta=MessageMeta(drop=False),
            message=StandardMessageContent(
                role="assistant",
                content=[
                    {
                        "type": "tool_use",
                        "id": "call_456",
                        "name": "Read",
                        "input": {"file_path": "/path/to/file"},
                    }
                ],
            ),
            timestamp="2024-01-01T10:00:00Z",
            parentToolUseID=None,
        )
        tool_use_map["call_456"] = tool_use_message

        # isMeta 消息包含多个 content items
        meta_message = StandardMessage(
            type="user",
            subtype=None,
            uuid="uuid-2",
            uuids=[],
            raw_message={},
            meta=MessageMeta(
                drop=False, extra={"isMeta": True, "sourceToolUseID": "call_456"}
            ),
            message=StandardMessageContent(
                role="user",
                content=[
                    {"type": "text", "text": "First line"},
                    {"type": "text", "text": "Second line"},
                ],
            ),
            timestamp="2024-01-01T10:00:01Z",
            parentToolUseID=None,
        )

        result = processor._merge_meta_to_tool_use(meta_message, tool_use_map)

        assert result is True
        tool_use_item = tool_use_message.message.content[0]
        assert "extra" in tool_use_item
        assert isinstance(tool_use_item["extra"], list)
        assert len(tool_use_item["extra"]) == 2
        assert tool_use_item["extra"][0]["text"] == "First line"
        assert tool_use_item["extra"][1]["text"] == "Second line"

    def test_merge_meta_to_tool_use_source_tool_use_id_not_found(self, processor):
        """测试 isMeta 消息找不到对应的 tool_use_id"""
        tool_use_map = {}

        meta_message = StandardMessage(
            type="user",
            subtype=None,
            uuid="uuid-1",
            uuids=[],
            raw_message={},
            meta=MessageMeta(
                drop=False, extra={"isMeta": True, "sourceToolUseID": "call_unknown"}
            ),
            message=StandardMessageContent(
                role="user", content=[{"type": "text", "text": "Meta text"}]
            ),
            timestamp="2024-01-01T10:00:00Z",
            parentToolUseID=None,
        )

        result = processor._merge_meta_to_tool_use(meta_message, tool_use_map)

        # 应该返回 False
        assert result is False

    def test_merge_meta_to_tool_use_no_source_tool_use_id(self, processor):
        """测试 isMeta 消息没有 sourceToolUseID"""
        tool_use_map = {}
        tool_use_map["call_123"] = StandardMessage(
            type="assistant",
            subtype=None,
            uuid="uuid-1",
            uuids=[],
            raw_message={},
            meta=MessageMeta(drop=False),
            message=StandardMessageContent(
                role="assistant",
                content=[{"type": "tool_use", "id": "call_123", "name": "Test"}],
            ),
            timestamp="2024-01-01T10:00:00Z",
            parentToolUseID=None,
        )

        # isMeta 消息但没有 sourceToolUseID
        meta_message = StandardMessage(
            type="user",
            subtype=None,
            uuid="uuid-2",
            uuids=[],
            raw_message={},
            meta=MessageMeta(drop=False, extra={"isMeta": True}),
            message=StandardMessageContent(
                role="user", content=[{"type": "text", "text": "Meta text"}]
            ),
            timestamp="2024-01-01T10:00:01Z",
            parentToolUseID=None,
        )

        result = processor._merge_meta_to_tool_use(meta_message, tool_use_map)

        assert result is False

    def test_merge_meta_to_tool_use_empty_content(self, processor):
        """测试 isMeta 消息 content 为空"""
        tool_use_map = {}

        tool_use_message = StandardMessage(
            type="assistant",
            subtype=None,
            uuid="uuid-1",
            uuids=[],
            raw_message={},
            meta=MessageMeta(drop=False),
            message=StandardMessageContent(
                role="assistant",
                content=[{"type": "tool_use", "id": "call_789", "name": "Test"}],
            ),
            timestamp="2024-01-01T10:00:00Z",
            parentToolUseID=None,
        )
        tool_use_map["call_789"] = tool_use_message

        # isMeta 消息 content 为空列表
        meta_message = StandardMessage(
            type="user",
            subtype=None,
            uuid="uuid-2",
            uuids=[],
            raw_message={},
            meta=MessageMeta(
                drop=False, extra={"isMeta": True, "sourceToolUseID": "call_789"}
            ),
            message=StandardMessageContent(role="user", content=[]),
            timestamp="2024-01-01T10:00:01Z",
            parentToolUseID=None,
        )

        result = processor._merge_meta_to_tool_use(meta_message, tool_use_map)

        assert result is False

    def test_merge_meta_to_tool_use_tool_use_item_not_found_in_content(self, processor):
        """测试 tool_use_id 在 map 中存在，但对应的消息 content 中找不到对应的 item"""
        tool_use_map = {}

        # 创建一个没有 tool_use item 的消息
        tool_use_message = StandardMessage(
            type="assistant",
            subtype=None,
            uuid="uuid-1",
            uuids=[],
            raw_message={},
            meta=MessageMeta(drop=False),
            message=StandardMessageContent(
                role="assistant",
                content=[{"type": "text", "text": "Just text, no tool_use"}],
            ),
            timestamp="2024-01-01T10:00:00Z",
            parentToolUseID=None,
        )
        tool_use_map["call_999"] = tool_use_message

        meta_message = StandardMessage(
            type="user",
            subtype=None,
            uuid="uuid-2",
            uuids=[],
            raw_message={},
            meta=MessageMeta(
                drop=False, extra={"isMeta": True, "sourceToolUseID": "call_999"}
            ),
            message=StandardMessageContent(
                role="user", content=[{"type": "text", "text": "Meta text"}]
            ),
            timestamp="2024-01-01T10:00:01Z",
            parentToolUseID=None,
        )

        result = processor._merge_meta_to_tool_use(meta_message, tool_use_map)

        # 应该返回 False（找不到对应的 tool_use item）
        assert result is False

    def test_merge_tool_use_and_result_with_ismeta_success(self, processor):
        """测试在 _merge_tool_use_and_result 中成功合并 isMeta 消息"""
        messages = [
            # Assistant 消息，包含 tool_use
            StandardMessage(
                type="assistant",
                subtype=None,
                uuid="uuid-1",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="assistant",
                    content=[
                        {
                            "type": "tool_use",
                            "id": "call_123",
                            "name": "Grep",
                            "input": {"pattern": "test"},
                        }
                    ],
                ),
                timestamp="2024-01-01T10:00:00Z",
                parentToolUseID=None,
            ),
            # isMeta 消息
            StandardMessage(
                type="user",
                subtype=None,
                uuid="uuid-2",
                uuids=[],
                raw_message={},
                meta=MessageMeta(
                    drop=False, extra={"isMeta": True, "sourceToolUseID": "call_123"}
                ),
                message=StandardMessageContent(
                    role="user",
                    content=[{"type": "text", "text": "Extra information from isMeta"}],
                ),
                timestamp="2024-01-01T10:00:01Z",
                parentToolUseID=None,
            ),
        ]

        result = processor._merge_tool_use_and_result(messages)

        # 应该有 2 条消息（isMeta 被标记为 drop 但仍在列表中）
        assert len(result) == 2

        # 验证 tool_use 的 extra 字段被设置
        assistant_msg = result[0]
        tool_use_item = assistant_msg.message.content[0]
        assert "extra" in tool_use_item
        assert isinstance(tool_use_item["extra"], list)
        assert tool_use_item["extra"][0]["text"] == "Extra information from isMeta"

        # 验证 isMeta 消息被标记为 drop
        assert result[1].meta.drop is True
        assert result[1].meta.drop_reason == "merged_into_tool_use"
        assert result[1].meta.expected_drop is True

    def test_merge_tool_use_and_result_with_ismeta_not_found(self, processor):
        """测试在 _merge_tool_use_and_result 中 isMeta 找不到对应的 tool_use"""
        messages = [
            # isMeta 消息，sourceToolUseID 不存在
            StandardMessage(
                type="user",
                subtype=None,
                uuid="uuid-1",
                uuids=[],
                raw_message={},
                meta=MessageMeta(
                    drop=False,
                    extra={"isMeta": True, "sourceToolUseID": "call_unknown"},
                ),
                message=StandardMessageContent(
                    role="user",
                    content=[{"type": "text", "text": "This should not be merged"}],
                ),
                timestamp="2024-01-01T10:00:00Z",
                parentToolUseID=None,
            ),
        ]

        result = processor._merge_tool_use_and_result(messages)

        # 消息应该保留（因为没有成功合并）
        assert len(result) == 1
        assert result[0].meta.drop is False
        # 验证消息未被修改
        assert result[0].message.content[0]["text"] == "This should not be merged"

    def test_merge_tool_use_and_result_with_ismeta_no_source_id(self, processor):
        """测试在 _merge_tool_use_and_result 中 isMeta 没有 sourceToolUseID"""
        messages = [
            # isMeta 消息但没有 sourceToolUseID
            StandardMessage(
                type="user",
                subtype=None,
                uuid="uuid-1",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False, extra={"isMeta": True}),
                message=StandardMessageContent(
                    role="user",
                    content=[{"type": "text", "text": "Meta without source"}],
                ),
                timestamp="2024-01-01T10:00:00Z",
                parentToolUseID=None,
            ),
        ]

        result = processor._merge_tool_use_and_result(messages)

        # 消息应该保留
        assert len(result) == 1
        assert result[0].meta.drop is False

    # ========== 测试 _merge_subagent_messages_inline ==========

    def test_merge_subagent_messages_inline(self, processor):
        """测试合并 subagent 消息"""
        messages = [
            # 第一条 subagent 消息
            StandardMessage(
                type="user",
                subtype=None,
                uuid="msg-1",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="user", content=[{"type": "text", "text": "Subagent task 1"}]
                ),
                timestamp="2024-01-01T10:00:00Z",
                parentToolUseID="call_123",
            ),
            # 第二条 subagent 消息（同一个 parentToolUseID）
            StandardMessage(
                type="assistant",
                subtype=None,
                uuid="msg-2",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="assistant",
                    content=[{"type": "text", "text": "Subagent response 1"}],
                ),
                timestamp="2024-01-01T10:00:01Z",
                parentToolUseID="call_123",
            ),
            # 第三条 subagent 消息（同一个 parentToolUseID）
            StandardMessage(
                type="user",
                subtype=None,
                uuid="msg-3",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="user", content=[{"type": "text", "text": "Subagent task 2"}]
                ),
                timestamp="2024-01-01T10:00:02Z",
                parentToolUseID="call_123",
            ),
            # 普通消息
            StandardMessage(
                type="assistant",
                subtype=None,
                uuid="msg-4",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="assistant",
                    content=[{"type": "text", "text": "Normal response"}],
                ),
                timestamp="2024-01-01T10:00:03Z",
                parentToolUseID=None,
            ),
        ]

        result = processor._merge_subagent_messages_inline(messages)

        # 应该有 2 条消息（subagent 消息合并成 1 条 + 1 条普通消息）
        assert len(result) == 2

        # 验证第一条消息包含 subagent item
        first_msg = result[0]
        assert len(first_msg.message.content) == 1
        subagent_item = first_msg.message.content[0]
        assert subagent_item["type"] == "subagent"
        assert "messages" in subagent_item
        # 3 条消息（user, assistant, user），不同 role 不会合并
        assert subagent_item["message_count"] == 3

    def test_merge_subagent_messages_inline_dropped_filtered(self, processor):
        """测试 subagent 消息合并时过滤已 drop 的消息"""
        messages = [
            # 第一条 subagent 消息
            StandardMessage(
                type="user",
                subtype=None,
                uuid="msg-1",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="user", content=[{"type": "text", "text": "Subagent task"}]
                ),
                timestamp="2024-01-01T10:00:00Z",
                parentToolUseID="call_123",
            ),
            # 被标记为 drop 的 subagent 消息
            StandardMessage(
                type="assistant",
                subtype=None,
                uuid="msg-2",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=True, drop_reason="test"),
                message=StandardMessageContent(
                    role="assistant",
                    content=[{"type": "text", "text": "Should be filtered"}],
                ),
                timestamp="2024-01-01T10:00:01Z",
                parentToolUseID="call_123",
            ),
        ]

        result = processor._merge_subagent_messages_inline(messages)

        # drop 的消息应该被过滤，只保留 1 条
        assert len(result) == 1
        subagent_item = result[0].message.content[0]
        assert len(subagent_item["messages"]) == 1

    # ========== 测试 _merge_subagent_to_tool_use ==========

    def test_merge_subagent_to_tool_use(self, processor):
        """测试将 subagent 合并到 tool_use"""
        messages = [
            # Assistant 消息，包含 tool_use
            StandardMessage(
                type="assistant",
                subtype=None,
                uuid="uuid-1",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="assistant",
                    content=[
                        {
                            "type": "tool_use",
                            "id": "call_123",
                            "name": "Task",
                            "input": {
                                "subagent_type": "test_agent",
                                "description": "Test task",
                            },
                        }
                    ],
                ),
                timestamp="2024-01-01T10:00:00Z",
                parentToolUseID=None,
            ),
            # 包含 subagent item 的消息
            StandardMessage(
                type="assistant",
                subtype=None,
                uuid="uuid-2",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="assistant",
                    content=[
                        {
                            "type": "subagent",
                            "parentToolUseID": "call_123",
                            "messages": [
                                {
                                    "type": "user",
                                    "message": {
                                        "role": "user",
                                        "content": "Subagent task",
                                    },
                                }
                            ],
                            "message_count": 1,
                        }
                    ],
                ),
                timestamp="2024-01-01T10:00:01Z",
                parentToolUseID=None,
            ),
        ]

        result = processor._merge_subagent_to_tool_use(messages)

        # subagent 应该被合并到 tool_use，原消息被标记为 drop
        assert len(result) == 1

        # 验证 tool_use 已被转换为 subagent 类型
        tool_use_msg = result[0]
        tool_use_item = tool_use_msg.message.content[0]
        assert tool_use_item["type"] == "subagent"
        assert tool_use_item["agent_type"] == "test_agent"
        assert "session" in tool_use_item
        assert tool_use_item["session"]["message_count"] == 1

    # ========== 测试 _merge_consecutive_messages ==========

    def test_merge_consecutive_messages_same_role(self, processor):
        """测试合并连续的同 role 消息"""
        messages = [
            StandardMessage(
                type="user",
                subtype=None,
                uuid="uuid-1",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="user", content=[{"type": "text", "text": "First"}]
                ),
                timestamp="2024-01-01T10:00:00Z",
                parentToolUseID=None,
            ),
            StandardMessage(
                type="user",
                subtype=None,
                uuid="uuid-2",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="user", content=[{"type": "text", "text": "Second"}]
                ),
                timestamp="2024-01-01T10:00:01Z",
                parentToolUseID=None,
            ),
            StandardMessage(
                type="user",
                subtype=None,
                uuid="uuid-3",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="user", content=[{"type": "text", "text": "Third"}]
                ),
                timestamp="2024-01-01T10:00:02Z",
                parentToolUseID=None,
            ),
        ]

        result = processor._merge_consecutive_messages(messages)

        # 应该合并成 1 条消息
        assert len(result) == 1

        # 验证内容合并
        merged_msg = result[0]
        assert len(merged_msg.message.content) == 3
        assert merged_msg.message.content[0]["text"] == "First"
        assert merged_msg.message.content[1]["text"] == "Second"
        assert merged_msg.message.content[2]["text"] == "Third"

    def test_merge_consecutive_messages_different_roles(self, processor):
        """测试不同 role 的消息不合并"""
        messages = [
            StandardMessage(
                type="user",
                subtype=None,
                uuid="uuid-1",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="user", content=[{"type": "text", "text": "User message"}]
                ),
                timestamp="2024-01-01T10:00:00Z",
                parentToolUseID=None,
            ),
            StandardMessage(
                type="assistant",
                subtype=None,
                uuid="uuid-2",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="assistant",
                    content=[{"type": "text", "text": "Assistant message"}],
                ),
                timestamp="2024-01-01T10:00:01Z",
                parentToolUseID=None,
            ),
        ]

        result = processor._merge_consecutive_messages(messages)

        # 不应该合并
        assert len(result) == 2

    def test_merge_consecutive_messages_system_not_merged(self, processor):
        """测试 system 消息不合并"""
        messages = [
            StandardMessage(
                type="system",
                subtype=None,
                uuid="uuid-1",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="system", content=[{"type": "text", "text": "System 1"}]
                ),
                timestamp="2024-01-01T10:00:00Z",
                parentToolUseID=None,
            ),
            StandardMessage(
                type="system",
                subtype=None,
                uuid="uuid-2",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="system", content=[{"type": "text", "text": "System 2"}]
                ),
                timestamp="2024-01-01T10:00:01Z",
                parentToolUseID=None,
            ),
        ]

        result = processor._merge_consecutive_messages(messages)

        # system 消息不应该合并
        assert len(result) == 2

    def test_merge_consecutive_messages_with_dropped(self, processor):
        """测试合并时过滤已 drop 的消息"""
        messages = [
            StandardMessage(
                type="user",
                subtype=None,
                uuid="uuid-1",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="user", content=[{"type": "text", "text": "First"}]
                ),
                timestamp="2024-01-01T10:00:00Z",
                parentToolUseID=None,
            ),
            StandardMessage(
                type="user",
                subtype=None,
                uuid="uuid-2",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=True, drop_reason="test"),
                message=StandardMessageContent(
                    role="user", content=[{"type": "text", "text": "Dropped"}]
                ),
                timestamp="2024-01-01T10:00:01Z",
                parentToolUseID=None,
            ),
            StandardMessage(
                type="user",
                subtype=None,
                uuid="uuid-3",
                uuids=[],
                raw_message={},
                meta=MessageMeta(drop=False),
                message=StandardMessageContent(
                    role="user", content=[{"type": "text", "text": "Third"}]
                ),
                timestamp="2024-01-01T10:00:02Z",
                parentToolUseID=None,
            ),
        ]

        result = processor._merge_consecutive_messages(messages)

        # drop 的消息应该被过滤，但前后两条应该合并
        assert len(result) == 1
        assert len(result[0].message.content) == 2

    # ========== 测试 _is_tool_use_item ==========

    def test_is_tool_use_item_tool_use(self, processor):
        """测试识别 tool_use"""
        assert (
            processor._is_tool_use_item({"type": "tool_use", "id": "call_123"}) is True
        )

    def test_is_tool_use_item_server_tool_use(self, processor):
        """测试识别 server_tool_use"""
        assert (
            processor._is_tool_use_item({"type": "server_tool_use", "id": "call_123"})
            is True
        )

    def test_is_tool_use_item_text(self, processor):
        """测试非 tool_use 类型"""
        assert processor._is_tool_use_item({"type": "text", "text": "Hello"}) is False

    def test_is_tool_use_item_empty(self, processor):
        """测试空 dict"""
        assert processor._is_tool_use_item({}) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
