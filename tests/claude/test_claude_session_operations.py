"""
Claude Session Operations 模块的单元测试
测试 Session 的扫描和读取功能
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.claude.claude_session_operations import ClaudeSessionOperations


class TestClaudeSessionOperations:
    """测试 ClaudeSessionOperations 类"""

    @pytest.fixture
    def temp_session_dir(self):
        """创建临时 session 目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            session_path.mkdir(parents=True, exist_ok=True)
            yield session_path

    @pytest.fixture
    def session_ops(self, temp_session_dir):
        """创建 ClaudeSessionOperations 实例"""
        return ClaudeSessionOperations(temp_session_dir)

    @pytest.fixture
    def sample_session_data(self):
        """创建示例 session 数据"""
        return [
            # Meta 消息
            {
                "type": "meta",
                "sessionId": "test-session-123",
                "timestamp": "2026-01-12T10:00:00.000Z",
            },
            # User 消息
            {
                "type": "user",
                "userType": "external",
                "sessionId": "test-session-123",
                "timestamp": "2026-01-12T10:00:01.000Z",
                "cwd": "/test/project",
                "gitBranch": "main",
                "message": {
                    "role": "user",
                    "content": "请帮我搜索文件中的 @expose_api 定义",
                },
            },
            # Assistant 消息 - tool_use
            {
                "type": "assistant",
                "userType": "external",
                "sessionId": "test-session-123",
                "timestamp": "2026-01-12T10:00:02.000Z",
                "cwd": "/test/project",
                "gitBranch": "main",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "call_abc123",
                            "name": "Grep",
                            "input": {
                                "pattern": "@expose_api",
                                "path": "/test/project/src",
                            },
                        }
                    ],
                },
            },
            # User 消息 - tool_result
            {
                "type": "user",
                "userType": "external",
                "sessionId": "test-session-123",
                "timestamp": "2026-01-12T10:00:03.000Z",
                "cwd": "/test/project",
                "gitBranch": "main",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "call_abc123",
                            "content": "Found 5 matches",
                        }
                    ],
                },
            },
            # Assistant 消息 - text
            {
                "type": "assistant",
                "userType": "external",
                "sessionId": "test-session-123",
                "timestamp": "2026-01-12T10:00:04.000Z",
                "cwd": "/test/project",
                "gitBranch": "main",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "我找到了5个匹配项",
                        }
                    ],
                },
            },
        ]

    @pytest.fixture
    def sample_session_jsonl(self, temp_session_dir, sample_session_data):
        """创建示例 session JSONL 文件"""
        session_file = temp_session_dir / "test-session-123.jsonl"
        with open(session_file, "w", encoding="utf-8") as f:
            for message_data in sample_session_data:
                f.write(json.dumps(message_data) + "\n")
        return session_file

    # ========== 测试 scan_sessions ==========

    @pytest.mark.asyncio
    async def test_scan_sessions_empty(self, session_ops):
        """测试扫描空的 session 目录"""
        sessions = await session_ops.scan_sessions()

        assert sessions == []
        assert isinstance(sessions, list)

    @pytest.mark.asyncio
    async def test_scan_sessions_success(self, temp_session_dir, session_ops):
        """测试成功扫描 session 列表"""
        # 创建多个 session 文件（agent session 会被跳过）
        sessions_to_create = [
            "session-1.jsonl",
            "session-2.jsonl",
            "agent-session-3.jsonl",  # 这个会被跳过
        ]

        for session_name in sessions_to_create:
            session_file = temp_session_dir / session_name
            with open(session_file, "w", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "type": "user",
                            "message": {"role": "user", "content": "test"},
                        }
                    )
                    + "\n"
                )

        sessions = await session_ops.scan_sessions()

        # agent session 会被跳过，所以只返回2个
        assert len(sessions) == 2

        # 验证 session 信息
        session_ids = [s.session_id for s in sessions]
        assert "session-1" in session_ids
        assert "session-2" in session_ids
        assert "agent-session-3" not in session_ids  # agent session 被跳过

        # 验证 is_agent_session 标记
        normal_session = next(s for s in sessions if s.session_id == "session-1")
        assert normal_session.is_agent_session is False

    @pytest.mark.asyncio
    async def test_scan_sessions_nonexistent_directory(self):
        """测试扫描不存在的目录"""
        nonexistent_path = Path("/tmp/this-directory-does-not-exist-12345")
        ops = ClaudeSessionOperations(nonexistent_path)

        sessions = await ops.scan_sessions()

        # 不存在的目录应该返回空列表
        assert sessions == []

    @pytest.mark.asyncio
    async def test_scan_sessions_incremental(self, temp_session_dir, session_ops):
        """测试增量扫描（使用现有 title）"""
        # 创建一个 session 文件
        session_file = temp_session_dir / "session-1.jsonl"
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "type": "user",
                        "message": {"role": "user", "content": "Test message"},
                    }
                )
                + "\n"
            )

        # 第一次扫描（需要读取文件）
        sessions_first = await session_ops.scan_sessions()
        assert len(sessions_first) == 1
        assert sessions_first[0].title is not None

        # 第二次扫描（传入现有 title，应该跳过读取）
        existing_titles = {s.session_id: s.title for s in sessions_first}
        sessions_second = await session_ops.scan_sessions(existing_titles)
        assert len(sessions_second) == 1
        assert sessions_second[0].title == sessions_first[0].title

    @pytest.mark.asyncio
    async def test_scan_sessions_filter_without_title(
        self, temp_session_dir, session_ops
    ):
        """测试过滤没有标题的 session"""
        # 创建多个 session 文件
        sessions_to_create = [
            ("session-with-title.jsonl", "This session has a title"),
            ("session-without-title.jsonl", None),  # 会创建空文件或只有 meta 消息的文件
            ("agent-session.jsonl", "Agent session title"),  # agent session 会被跳过
        ]

        for session_name, content in sessions_to_create:
            session_file = temp_session_dir / session_name
            with open(session_file, "w", encoding="utf-8") as f:
                if content:
                    # 写入有内容的用户消息
                    f.write(
                        json.dumps(
                            {
                                "type": "user",
                                "message": {"role": "user", "content": content},
                            }
                        )
                        + "\n"
                    )
                else:
                    # 只写入 meta 消息（不会被提取为标题）
                    f.write(
                        json.dumps(
                            {
                                "type": "meta",
                                "sessionId": "test-session",
                                "timestamp": "2026-01-12T10:00:00.000Z",
                            }
                        )
                        + "\n"
                    )

        sessions = await session_ops.scan_sessions()

        # agent session 被跳过，没有标题的 session 也被过滤，只返回1个
        assert len(sessions) == 1
        session_ids = [s.session_id for s in sessions]
        assert "session-with-title" in session_ids
        assert "agent-session" not in session_ids  # agent session 被跳过
        assert "session-without-title" not in session_ids

    @pytest.mark.asyncio
    async def test_scan_sessions_filter_empty_content(
        self, temp_session_dir, session_ops
    ):
        """测试过滤只有 Warmup 消息的 session"""
        # 创建一个只有 Warmup 消息的 session
        session_file = temp_session_dir / "session-warmup-only.jsonl"
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "type": "user",
                        "message": {"role": "user", "content": "Warmup"},
                    }
                )
                + "\n"
            )

        # 创建一个正常的 session
        normal_session = temp_session_dir / "session-normal.jsonl"
        with open(normal_session, "w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "type": "user",
                        "message": {"role": "user", "content": "Normal message"},
                    }
                )
                + "\n"
            )

        sessions = await session_ops.scan_sessions()

        # Warmup-only session 应该被过滤掉
        assert len(sessions) == 1
        assert sessions[0].session_id == "session-normal"

    @pytest.mark.asyncio
    async def test_scan_sessions_with_existing_titles_filtering(
        self, temp_session_dir, session_ops
    ):
        """测试使用 existing_titles 时的过滤逻辑"""
        # 创建一个有标题的 session
        session_file = temp_session_dir / "session-1.jsonl"
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "type": "user",
                        "message": {"role": "user", "content": "Test message"},
                    }
                )
                + "\n"
            )

        # 传入包含 None title 的 existing_titles
        existing_titles = {
            "session-1": "Existing Title",
            "session-2": None,  # 没有 title 的应该被过滤
        }

        sessions = await session_ops.scan_sessions(existing_titles)

        # 即使传入了 None title，也只会返回实际存在且有标题的 session
        assert len(sessions) == 1
        assert sessions[0].session_id == "session-1"
        assert sessions[0].title == "Existing Title"

    # ========== 测试 _load_session_data ==========

    @pytest.mark.asyncio
    async def test_load_session_data_success(self, session_ops, sample_session_jsonl):
        """测试成功加载 session 数据"""
        session, _ = await session_ops._load_session_data(sample_session_jsonl)

        assert session is not None
        assert session.session_id == "test-session-123"
        assert session.session_file == str(sample_session_jsonl)
        assert session.is_agent_session is False
        # meta 消息被过滤掉了，只剩余 user 和 assistant 消息
        # 但由于 tool_result 已合并，应该有 2 条消息
        assert session.message_count == 2

    @pytest.mark.asyncio
    async def test_load_session_data_agent_session(self, temp_session_dir):
        """测试加载 agent session"""
        session_file = temp_session_dir / "agent-test-456.jsonl"
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "type": "user",
                        "message": {"role": "user", "content": "test"},
                    }
                )
                + "\n"
            )

        ops = ClaudeSessionOperations(temp_session_dir)
        session, _ = await ops._load_session_data(session_file)

        assert session is not None
        assert session.is_agent_session is True
        assert session.session_id == "agent-test-456"

    @pytest.mark.asyncio
    async def test_load_session_data_invalid_json(self, temp_session_dir):
        """测试加载无效的 JSON 文件"""
        session_file = temp_session_dir / "invalid.jsonl"
        with open(session_file, "w", encoding="utf-8") as f:
            f.write("invalid json content")

        ops = ClaudeSessionOperations(temp_session_dir)
        session, _ = await ops._load_session_data(session_file)

        assert session is None

    @pytest.mark.asyncio
    async def test_load_session_data_empty_file(self, temp_session_dir):
        """测试加载空文件"""
        session_file = temp_session_dir / "empty.jsonl"
        session_file.touch()

        ops = ClaudeSessionOperations(temp_session_dir)
        session, _ = await ops._load_session_data(session_file)

        # 空文件应该返回 None（没有有效消息）
        assert session is None

    @pytest.mark.asyncio
    async def test_load_session_data_with_debug(
        self, session_ops, sample_session_jsonl
    ):
        """测试加载 session 数据并收集调试信息"""
        session, debug_info = await session_ops._load_session_data(
            sample_session_jsonl, debug=True
        )

        assert session is not None
        assert "error" in debug_info
        assert debug_info["error"] is None

        # 验证调试信息包含基本统计
        assert "raw_total" in debug_info
        assert "raw_effective" in debug_info
        assert "merged_total" in debug_info

    # ========== 测试 read_session_contents ==========

    @pytest.mark.asyncio
    async def test_read_session_contents_success(
        self, session_ops, sample_session_jsonl
    ):
        """测试成功读取 session 内容"""
        session = await session_ops.read_session_contents("test-session-123")

        assert session is not None
        assert session.session_id == "test-session-123"
        # meta 消息被过滤掉了，只剩余 user 和 assistant 消息
        # tool_result 已合并到 tool_use
        assert len(session.messages) == 2

        # 验证合并后的 tool_use
        # 第二条消息包含 tool_use 和 text，在同一个 content 数组中
        tool_use_msg = session.messages[1]
        # message 是 dict 类型
        content = (
            tool_use_msg.message.get("content", []) if tool_use_msg.message else []
        )
        tool_use = next(
            (
                item
                for item in content
                if isinstance(item, dict) and item.get("type") == "tool_use"
            ),
            None,
        )
        assert tool_use is not None
        assert tool_use["status"] == "complete"
        assert tool_use["output"] == "Found 5 matches"

    @pytest.mark.asyncio
    async def test_read_session_contents_not_found(self, session_ops):
        """测试读取不存在的 session"""
        session = await session_ops.read_session_contents("nonexistent-session")

        assert session is None

    @pytest.mark.asyncio
    async def test_read_session_contents_invalid_id(self, session_ops):
        """测试使用无效的 session_id（路径遍历攻击）"""
        with pytest.raises(ValueError, match="Invalid session_id"):
            await session_ops.read_session_contents("../etc/passwd")

    # ========== 测试 _read_session_title ==========

    @pytest.mark.asyncio
    async def test_read_session_title_with_command(self, temp_session_dir):
        """测试从 command 消息中提取标题"""
        session_file = temp_session_dir / "session-command.jsonl"
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "type": "user",
                        "timestamp": "2024-01-01T10:00:00Z",
                        "message": {
                            "role": "user",
                            "content": "<command-message>code-review:code-review</command-message>\n<command-name>/code-review:code-review</command-name>",
                        },
                    }
                )
                + "\n"
            )

        ops = ClaudeSessionOperations(temp_session_dir)
        title, line_number = await ops._read_session_title(session_file)

        assert title == "/code-review:code-review"
        assert line_number == 1

    @pytest.mark.asyncio
    async def test_read_session_title_command_truncated(self, temp_session_dir):
        """测试 command 名称被截断"""
        session_file = temp_session_dir / "session-command-long.jsonl"
        long_command_name = (
            "/very:long:command:name:that:exceeds:default:max:length:limit"
        )
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "type": "user",
                        "timestamp": "2024-01-01T10:00:00Z",
                        "message": {
                            "role": "user",
                            "content": f"<command-message>test</command-message>\n<command-name>{long_command_name}</command-name>",
                        },
                    }
                )
                + "\n"
            )

        ops = ClaudeSessionOperations(temp_session_dir)
        title, line_number = await ops._read_session_title(session_file)

        # 默认最大长度是 50，所以应该被截断
        assert title is not None
        assert len(title) <= 50
        assert title.endswith("...")
        assert long_command_name.startswith(title[:-3])

    @pytest.mark.asyncio
    async def test_read_session_title_normal_message_after_command(
        self, temp_session_dir
    ):
        """测试 command 消息优先于普通消息被用作标题"""
        session_file = temp_session_dir / "session-mixed.jsonl"
        with open(session_file, "w", encoding="utf-8") as f:
            # 写入一条 command 消息
            f.write(
                json.dumps(
                    {
                        "type": "user",
                        "timestamp": "2024-01-01T10:00:00Z",
                        "message": {
                            "role": "user",
                            "content": "<command-message>test</command-message>\n<command-name>/test</command-name>",
                        },
                    }
                )
                + "\n"
            )
            # 写入一条普通消息
            f.write(
                json.dumps(
                    {
                        "type": "user",
                        "timestamp": "2024-01-01T10:00:01Z",
                        "message": {"role": "user", "content": "Normal message"},
                    }
                )
                + "\n"
            )

        ops = ClaudeSessionOperations(temp_session_dir)
        title, line_number = await ops._read_session_title(session_file)

        # 应该使用 command 名称作为标题
        assert title == "/test"
        assert line_number == 1

    # ========== 测试 detect_project_info ==========

    @pytest.mark.asyncio
    async def test_detect_project_info_success(self, temp_session_dir):
        """测试成功检测项目路径和时间"""
        # 创建包含 cwd 的 session 文件
        session_file = temp_session_dir / "session-1.jsonl"
        with open(session_file, "w") as f:
            f.write(
                json.dumps(
                    {"timestamp": "2024-01-01T10:00:00Z", "cwd": "/test/project"}
                )
                + "\n"
            )

        ops = ClaudeSessionOperations(temp_session_dir)
        project_path, last_active = await ops.detect_project_info()

        assert project_path == "/test/project"
        assert last_active is not None

    @pytest.mark.asyncio
    async def test_detect_project_info_not_found(self, temp_session_dir):
        """测试找不到项目路径"""
        # 创建不包含 cwd 的 session 文件
        session_file = temp_session_dir / "session-1.jsonl"
        with open(session_file, "w") as f:
            f.write(json.dumps({"timestamp": "2024-01-01T10:00:00Z"}) + "\n")

        ops = ClaudeSessionOperations(temp_session_dir)
        project_path, last_active = await ops.detect_project_info()

        assert project_path is None
        assert last_active is None

    # ========== 测试 _validate_session_id ==========

    def test_validate_session_id_valid(self, session_ops):
        """测试有效的 session_id"""
        # 不应该抛出异常
        session_ops._validate_session_id("valid-session-id")

    def test_validate_session_id_empty(self, session_ops):
        """测试空的 session_id"""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            session_ops._validate_session_id("")

    def test_validate_session_id_none(self, session_ops):
        """测试 None 的 session_id"""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            session_ops._validate_session_id(None)

    def test_validate_session_id_path_traversal(self, session_ops):
        """测试包含路径遍历字符的 session_id"""
        with pytest.raises(ValueError, match="path traversal"):
            session_ops._validate_session_id("../etc/passwd")

    def test_validate_session_id_absolute_path(self, session_ops):
        """测试绝对路径的 session_id"""
        with pytest.raises(ValueError, match="path traversal"):
            session_ops._validate_session_id("/etc/passwd")

    # ========== 测试 _create_parser 和 _create_processor ==========

    def test_create_parser(self, session_ops):
        """测试创建 parser"""
        parser = session_ops._create_parser()
        assert parser is not None
        # 应该有 drop_registry
        assert parser.drop_registry is not None

    def test_create_processor(self, session_ops):
        """测试创建 processor"""
        drop_registry = session_ops._create_parser().drop_registry
        processor = session_ops._create_processor(drop_registry)
        assert processor is not None
        # 应该有 drop_registry
        assert processor.drop_registry is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
