"""
MessageParser 的单元测试
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.claude.models import StandardMessage
from src.claude.parsers.message_parser import MessageParser, ParseStats


class TestMessageParser:
    """测试 MessageParser 类"""

    @pytest.fixture
    def temp_session_dir(self):
        """创建临时 session 目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            session_path.mkdir(parents=True, exist_ok=True)
            yield session_path

    @pytest.fixture
    def parser(self):
        """创建 MessageParser 实例"""
        return MessageParser()

    # ========== 测试 ParseStats ==========

    def test_parse_stats_initialization(self):
        """测试 ParseStats 初始化"""
        stats = ParseStats()

        assert stats.raw_total == 0
        assert stats.raw_effective == 0
        assert stats.raw_meta == 0
        assert stats.raw_user == 0
        assert stats.raw_assistant == 0
        assert stats.raw_system == 0
        assert stats.raw_tool_use == 0
        assert stats.raw_tool_result == 0
        assert stats.raw_thinking == 0
        assert stats.empty_lines == 0
        assert stats.invalid_json_lines == 0

    # ========== 测试 parse_session_file_with_stats ==========

    @pytest.mark.asyncio
    async def test_parse_session_file_basic(self, temp_session_dir, parser):
        """测试基本解析功能"""
        # 创建测试文件
        session_file = temp_session_dir / "test.jsonl"
        test_data = [
            {
                "type": "user",
                "timestamp": "2024-01-01T10:00:00Z",
                "message": {"role": "user", "content": "Hello"},
            },
            {
                "type": "assistant",
                "timestamp": "2024-01-01T10:00:01Z",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Hi"}],
                },
            },
        ]

        with open(session_file, "w", encoding="utf-8") as f:
            for data in test_data:
                f.write(json.dumps(data) + "\n")

        messages, stats = await parser.parse_session_file_with_stats(
            str(session_file), collect_stats=True
        )

        assert len(messages) == 2
        assert stats.raw_total == 2
        assert stats.raw_effective == 2

    @pytest.mark.asyncio
    async def test_parse_session_file_with_stats(self, temp_session_dir, parser):
        """测试带统计的解析"""
        session_file = temp_session_dir / "test.jsonl"
        test_data = [
            {"type": "meta", "sessionId": "test", "timestamp": "2024-01-01T10:00:00Z"},
            {
                "type": "user",
                "timestamp": "2024-01-01T10:00:01Z",
                "message": {"role": "user", "content": "Test"},
            },
            {
                "type": "assistant",
                "timestamp": "2024-01-01T10:00:02Z",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "call_123",
                            "name": "Grep",
                            "input": {"pattern": "test"},
                        }
                    ],
                },
            },
        ]

        with open(session_file, "w", encoding="utf-8") as f:
            for data in test_data:
                f.write(json.dumps(data) + "\n")

        messages, stats = await parser.parse_session_file_with_stats(
            str(session_file), collect_stats=True
        )

        assert stats is not None
        assert stats.raw_total == 3
        # meta 消息会被标记为 drop，所以 raw_effective 不包含它
        # 但统计中应该有 raw_meta
        assert stats.raw_meta == 0  # meta 被 drop 了，不计入 raw_meta
        assert stats.raw_user == 1
        assert stats.raw_assistant == 1
        assert stats.raw_tool_use == 1

    @pytest.mark.asyncio
    async def test_parse_session_file_empty_lines(self, temp_session_dir, parser):
        """测试处理空行"""
        session_file = temp_session_dir / "test.jsonl"
        test_data = [
            {
                "type": "user",
                "timestamp": "2024-01-01T10:00:00Z",
                "message": {"role": "user", "content": "Test"},
            },
            "",  # 空行
            {
                "type": "assistant",
                "timestamp": "2024-01-01T10:00:01Z",
                "message": {"role": "assistant", "content": "Hi"},
            },
        ]

        with open(session_file, "w", encoding="utf-8") as f:
            for data in test_data:
                if isinstance(data, str):
                    f.write("\n")
                else:
                    f.write(json.dumps(data) + "\n")

        messages, stats = await parser.parse_session_file_with_stats(
            str(session_file), collect_stats=True
        )

        assert stats is not None
        # 空行实际上也会被计入 raw_total，所以应该是 3
        assert stats.raw_total == 3
        # 但无效的 JSON 行（空行）不会计入 empty_lines，empty_lines 统计的是其他情况
        assert stats.empty_lines == 0
        assert len(messages) == 2

    @pytest.mark.asyncio
    async def test_parse_session_file_invalid_json(self, temp_session_dir, parser):
        """测试处理无效 JSON"""
        session_file = temp_session_dir / "test.jsonl"

        with open(session_file, "w", encoding="utf-8") as f:
            f.write(
                '{"type": "user", "message": {"role": "user", "content": "Test"}}\n'
            )
            f.write("invalid json\n")
            f.write(
                '{"type": "assistant", "message": {"role": "assistant", "content": "Hi"}}\n'
            )

        messages, stats = await parser.parse_session_file_with_stats(
            str(session_file), collect_stats=True
        )

        assert stats is not None
        assert stats.invalid_json_lines == 1
        assert len(messages) == 2  # 无效行应该被跳过

    # ========== 测试 extract_session_title ==========

    @pytest.mark.asyncio
    async def test_extract_session_title_from_user_text(self, temp_session_dir, parser):
        """测试从用户消息提取标题"""
        session_file = temp_session_dir / "test.jsonl"
        test_data = [
            {"type": "meta", "sessionId": "test", "timestamp": "2024-01-01T10:00:00Z"},
            {
                "type": "user",
                "timestamp": "2024-01-01T10:00:01Z",
                "message": {"role": "user", "content": "Help me with my code"},
            },
        ]

        with open(session_file, "w", encoding="utf-8") as f:
            for data in test_data:
                f.write(json.dumps(data) + "\n")

        title, line_number = await parser.extract_session_title(str(session_file))

        assert title == "Help me with my code"
        assert line_number == 1  # meta 被过滤，user 是第一条有效消息

    @pytest.mark.asyncio
    async def test_extract_session_title_from_command(self, temp_session_dir, parser):
        """测试从 command 消息提取标题"""
        session_file = temp_session_dir / "test.jsonl"
        test_data = [
            {
                "type": "user",
                "timestamp": "2024-01-01T10:00:00Z",
                "message": {
                    "role": "user",
                    "content": "<command-message>test</command-message>\n<command-name>/test-command</command-name>",
                },
            },
        ]

        with open(session_file, "w", encoding="utf-8") as f:
            for data in test_data:
                f.write(json.dumps(data) + "\n")

        title, line_number = await parser.extract_session_title(str(session_file))

        assert title == "/test-command"
        assert line_number == 1

    @pytest.mark.asyncio
    async def test_extract_session_title_truncated(self, temp_session_dir, parser):
        """测试标题截断"""
        session_file = temp_session_dir / "test.jsonl"
        long_text = "A" * 100  # 超过默认最大长度 50

        test_data = [
            {
                "type": "user",
                "timestamp": "2024-01-01T10:00:00Z",
                "message": {"role": "user", "content": long_text},
            },
        ]

        with open(session_file, "w", encoding="utf-8") as f:
            for data in test_data:
                f.write(json.dumps(data) + "\n")

        title, line_number = await parser.extract_session_title(
            str(session_file), max_length=50
        )

        assert title is not None
        assert len(title) <= 50
        assert title.endswith("...")
        assert long_text.startswith(title[:-3])

    @pytest.mark.asyncio
    async def test_extract_session_title_no_valid_messages(
        self, temp_session_dir, parser
    ):
        """测试没有有效消息时返回 None"""
        session_file = temp_session_dir / "test.jsonl"
        test_data = [
            {"type": "meta", "sessionId": "test", "timestamp": "2024-01-01T10:00:00Z"},
        ]

        with open(session_file, "w", encoding="utf-8") as f:
            for data in test_data:
                f.write(json.dumps(data) + "\n")

        title, line_number = await parser.extract_session_title(str(session_file))

        assert title is None
        assert line_number == 0

    # ========== 测试 extract_project_path ==========

    @pytest.mark.asyncio
    async def test_extract_project_path_found(self, temp_session_dir, parser):
        """测试成功提取项目路径"""
        session_file = temp_session_dir / "test.jsonl"
        test_data = [
            {"type": "meta", "sessionId": "test"},
            {
                "type": "user",
                "cwd": "/test/project",
                "message": {"role": "user", "content": "Test"},
            },
        ]

        with open(session_file, "w", encoding="utf-8") as f:
            for data in test_data:
                f.write(json.dumps(data) + "\n")

        project_path = await parser.extract_project_path(str(session_file))

        assert project_path == "/test/project"

    @pytest.mark.asyncio
    async def test_extract_project_path_not_found(self, temp_session_dir, parser):
        """测试未找到项目路径"""
        session_file = temp_session_dir / "test.jsonl"
        test_data = [
            {"type": "user", "message": {"role": "user", "content": "Test"}},
        ]

        with open(session_file, "w", encoding="utf-8") as f:
            for data in test_data:
                f.write(json.dumps(data) + "\n")

        project_path = await parser.extract_project_path(str(session_file))

        assert project_path is None

    # ========== 测试 _truncate_title ==========

    def test_truncate_title_short_text(self, parser):
        """测试短文本不截断"""
        text = "Short text"
        result = parser._truncate_title(text, 50)

        assert result == "Short text"
        assert len(result) <= 50

    def test_truncate_title_exact_length(self, parser):
        """测试精确长度的文本"""
        text = "A" * 50
        result = parser._truncate_title(text, 50)

        assert result == text
        assert len(result) == 50

    def test_truncate_title_long_text(self, parser):
        """测试长文本截断"""
        text = "A" * 100
        result = parser._truncate_title(text, 50)

        assert len(result) == 50
        assert result.endswith("...")
        assert result[:47] == "A" * 47

    def test_truncate_title_with_whitespace(self, parser):
        """测试清理空白字符"""
        text = "  Hello   world  \n  Test  "
        result = parser._truncate_title(text, 50)

        # 应该清理多余空白
        assert "  " not in result
        assert "\n" not in result
        assert result == "Hello world Test"

    # ========== 测试 _clean_system_tags ==========

    def test_clean_system_tags_all_tags(self, parser):
        """测试清理所有系统标签"""
        text = """<local-command-caveat>Warning</local-command-caveat>
<command-name>/test</command-name>
<command-message>test</command-message>
<command-args>args</command-args>
<local-command-stdout>output</local-command-stdout>
Actual content"""

        result = parser._clean_system_tags(text)

        assert "<local-command-caveat>" not in result
        assert "<command-name>" not in result
        assert "<command-message>" not in result
        assert "<command-args>" not in result
        assert "<local-command-stdout>" not in result
        assert result == "Actual content"

    def test_clean_system_tags_partial_tags(self, parser):
        """测试部分系统标签"""
        text = """<command-name>/test</command-name>
<command-message>test</command-message>
Content"""

        result = parser._clean_system_tags(text)

        assert "<command-name>" not in result
        assert "<command-message>" not in result
        assert result == "Content"

    def test_clean_system_tags_no_tags(self, parser):
        """测试没有系统标签的文本"""
        text = "This is normal content"

        result = parser._clean_system_tags(text)

        assert result == "This is normal content"

    # ========== 测试 convert_command_message ==========

    def test_convert_command_message_success(self, parser):
        """测试成功转换 command 消息"""
        message_data = {
            "type": "user",
            "timestamp": "2024-01-01T10:00:00Z",
            "message": {
                "role": "user",
                "content": "<command-message>test</command-message>\n<command-name>/test-command</command-name>",
            },
        }

        result = parser.convert_command_message(message_data, None)

        assert result is not None
        assert isinstance(result, StandardMessage)
        assert result.type == "user"
        content = result.message.content
        assert len(content) == 1
        assert content[0]["type"] == "command"
        assert content[0]["command"] == "/test-command"
        assert content[0]["content"] == ""

    def test_convert_command_message_with_meta(self, parser):
        """测试带 isMeta 的 command 消息"""
        message_data = {
            "type": "user",
            "timestamp": "2024-01-01T10:00:00Z",
            "message": {
                "role": "user",
                "content": "<command-message>test</command-message>\n<command-name>/test</command-name>",
            },
        }

        next_message_data = {
            "type": "user",
            "isMeta": True,
            "timestamp": "2024-01-01T10:00:01Z",
            "message": {
                "role": "user",
                "content": "Command content here",
            },
        }

        result = parser.convert_command_message(message_data, next_message_data)

        assert result is not None
        content = result.message.content
        assert len(content) == 1
        assert content[0]["type"] == "command"
        assert content[0]["content"] == "Command content here"
        # 下一条消息应该被标记为跳过
        assert next_message_data.get("_skipped_next") is True
        assert next_message_data.get("_drop") is True

    def test_convert_command_message_invalid_format(self, parser):
        """测试非 command 消息"""
        message_data = {
            "type": "user",
            "timestamp": "2024-01-01T10:00:00Z",
            "message": {"role": "user", "content": "Normal message"},
        }

        result = parser.convert_command_message(message_data, None)

        assert result is None

    def test_convert_command_message_with_args(self, parser):
        """测试带参数的 command 消息"""
        message_data = {
            "type": "user",
            "timestamp": "2024-01-01T10:00:00Z",
            "message": {
                "role": "user",
                "content": "<command-message>test</command-message>\n<command-name>/test</command-name>\n<command-args>--force</command-args>",
            },
        }

        result = parser.convert_command_message(message_data, None)

        assert result is not None
        content = result.message.content
        assert content[0]["args"] == "--force"

    # ========== 测试 convert_interrupted_message ==========

    def test_convert_interrupted_message_string(self, parser):
        """测试转换字符串格式的打断消息"""
        message_data = {
            "type": "user",
            "timestamp": "2024-01-01T10:00:00Z",
            "message": {"role": "user", "content": "[Request interrupted by user]"},
        }

        result = parser.convert_interrupted_message(message_data)

        assert result is not None
        assert isinstance(result, StandardMessage)
        assert result.type == "assistant"
        content = result.message.content
        assert len(content) == 1
        assert content[0]["type"] == "interrupted"
        assert content[0]["text"] == "Request interrupted by user"

    def test_convert_interrupted_message_list(self, parser):
        """测试转换列表格式的打断消息"""
        message_data = {
            "type": "user",
            "timestamp": "2024-01-01T10:00:00Z",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "[Request interrupted by user]"}],
            },
        }

        result = parser.convert_interrupted_message(message_data)

        assert result is not None
        assert result.type == "assistant"
        content = result.message.content
        assert content[0]["type"] == "interrupted"

    def test_convert_interrupted_message_with_detail(self, parser):
        """测试带详情的打断消息"""
        message_data = {
            "type": "user",
            "timestamp": "2024-01-01T10:00:00Z",
            "message": {
                "role": "user",
                "content": "[Request interrupted by user: no response]",
            },
        }

        result = parser.convert_interrupted_message(message_data)

        assert result is not None
        content = result.message.content
        assert content[0]["type"] == "interrupted"
        assert "no response" in content[0]["text"]

    def test_convert_interrupted_message_not_interrupted(self, parser):
        """测试非打断消息"""
        message_data = {
            "type": "user",
            "timestamp": "2024-01-01T10:00:00Z",
            "message": {"role": "user", "content": "Normal message"},
        }

        result = parser.convert_interrupted_message(message_data)

        assert result is None

    # ========== 测试 _extract_title_from_content ==========

    def test_extract_title_from_command_content(self, parser):
        """测试从 command 内容提取标题"""
        content = [
            {"type": "command", "command": "/test-command", "content": "Test content"},
        ]

        title = parser._extract_title_from_content(content, 50)

        assert title == "/test-command"

    def test_extract_title_from_text_content(self, parser):
        """测试从 text 内容提取标题"""
        content = [
            {"type": "text", "text": "This is a title"},
        ]

        title = parser._extract_title_from_content(content, 50)

        assert title == "This is a title"

    def test_extract_title_from_mixed_content(self, parser):
        """测试从混合内容提取标题（优先 text）"""
        content = [
            {"type": "text", "text": "Text first"},
            {"type": "command", "command": "/command", "content": ""},
        ]

        title = parser._extract_title_from_content(content, 50)

        # 应该优先返回第一个（text）
        assert title == "Text first"

    def test_extract_title_from_empty_content(self, parser):
        """测试空内容"""
        title = parser._extract_title_from_content([], 50)

        assert title is None

    def test_extract_title_from_unknown_type(self, parser):
        """测试未知类型"""
        content = [
            {"type": "unknown", "data": "something"},
        ]

        title = parser._extract_title_from_content(content, 50)

        assert title is None

    # ========== 测试 isMeta 和 sourceToolUseID 解析 ==========

    def test_parse_single_message_with_ismeta_and_sourcetooluseid(self, parser):
        """测试解析包含 isMeta 和 sourceToolUseID 的消息"""
        message_data = {
            "type": "user",
            "uuid": "test-uuid-123",
            "timestamp": "2024-01-01T10:00:00Z",
            "isMeta": True,
            "sourceToolUseID": "call_abc123",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "Metadata text"}],
            },
        }

        result = parser._parse_single_message_internal(message_data)

        # 验证基础字段
        assert result.type == "user"
        assert result.uuid == "test-uuid-123"

        # 验证 isMeta 和 sourceToolUseID 被正确设置到 meta.extra
        assert "isMeta" in result.meta.extra
        assert result.meta.extra["isMeta"] is True
        assert "sourceToolUseID" in result.meta.extra
        assert result.meta.extra["sourceToolUseID"] == "call_abc123"

    def test_parse_single_message_with_ismeta_false(self, parser):
        """测试 isMeta 为 false 的消息"""
        message_data = {
            "type": "user",
            "uuid": "test-uuid-456",
            "timestamp": "2024-01-01T10:00:00Z",
            "isMeta": False,
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "Normal message"}],
            },
        }

        result = parser._parse_single_message_internal(message_data)

        # 验证 isMeta 被设置到 extra（即使为 false）
        assert "isMeta" in result.meta.extra
        assert result.meta.extra["isMeta"] is False

    def test_parse_single_message_without_ismeta(self, parser):
        """测试没有 isMeta 字段的消息"""
        message_data = {
            "type": "user",
            "uuid": "test-uuid-789",
            "timestamp": "2024-01-01T10:00:00Z",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "Normal message"}],
            },
        }

        result = parser._parse_single_message_internal(message_data)

        # 验证 isMeta 不在 extra 中（因为没有这个字段）
        assert "isMeta" not in result.meta.extra

    @pytest.mark.asyncio
    async def test_parse_session_file_with_ismeta_message(
        self, parser, temp_session_dir
    ):
        """测试从文件解析包含 isMeta 消息的 session"""
        # 创建临时 session 文件
        session_file = temp_session_dir / "test_session.jsonl"
        test_messages = [
            # 普通 user 消息
            {
                "type": "user",
                "uuid": "msg-1",
                "timestamp": "2024-01-01T10:00:00Z",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "Hello"}],
                },
            },
            # assistant 消息，包含 tool_use
            {
                "type": "assistant",
                "uuid": "msg-2",
                "timestamp": "2024-01-01T10:00:01Z",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "call_test123",
                            "name": "Grep",
                            "input": {"pattern": "test"},
                        }
                    ],
                },
            },
            # isMeta 消息
            {
                "type": "user",
                "uuid": "msg-3",
                "timestamp": "2024-01-01T10:00:02Z",
                "isMeta": True,
                "sourceToolUseID": "call_test123",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "Extra info"}],
                },
            },
        ]

        # 写入文件
        with open(session_file, "w", encoding="utf-8") as f:
            for msg in test_messages:
                f.write(json.dumps(msg) + "\n")

        # 解析文件
        messages, stats = await parser.parse_session_file_with_stats(
            str(session_file), collect_stats=True
        )

        # 验证解析结果
        assert len(messages) == 3

        # 验证 isMeta 消息被正确解析
        ismeta_msg = messages[2]
        assert ismeta_msg.type == "user"
        assert ismeta_msg.meta.extra.get("isMeta") is True
        assert ismeta_msg.meta.extra.get("sourceToolUseID") == "call_test123"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
