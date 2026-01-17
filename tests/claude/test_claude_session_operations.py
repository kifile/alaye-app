"""
Claude Session Operations 模块的单元测试
测试 Session 的扫描和读取功能，特别是消息合并逻辑
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

    # ========== 测试 _convert_summary_to_system ==========

    def test_convert_summary_to_system_success(self, session_ops):
        """测试成功转换 summary 消息"""
        message_data = {
            "type": "summary",
            "timestamp": "2024-01-01T10:00:00Z",
            "summary": "This is a summary",
        }

        result = session_ops._convert_summary_to_system(message_data)

        assert result is not None
        assert result["type"] == "system"
        assert result["message"]["role"] == "system"
        assert result["message"]["content"][0]["text"] == "This is a summary"
        assert result["_converted"] is True
        assert result["_original_type"] == "summary"

    def test_convert_summary_to_system_empty(self, session_ops):
        """测试空的 summary 消息"""
        message_data = {
            "type": "summary",
            "timestamp": "2024-01-01T10:00:00Z",
            "summary": "",
        }

        result = session_ops._convert_summary_to_system(message_data)

        assert result is None
        assert message_data["_dropped"] is True
        assert message_data["_drop_reason"] == "empty_summary"

    # ========== 测试 _merge_tool_result_to_tool_use ==========

    def test_merge_tool_result_to_tool_use_success(self, session_ops):
        """测试成功合并 tool_result 到 tool_use"""
        tool_use_map = {}
        tool_use_message = {
            "type": "assistant",
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
        }
        tool_use_map["call_123"] = tool_use_message

        tool_result = {
            "type": "tool_result",
            "tool_use_id": "call_123",
            "content": "Found 10 matches",
        }

        session_ops._merge_tool_result_to_tool_use(tool_result, tool_use_map)

        # 验证合并结果
        tool_use_item = tool_use_message["message"]["content"][0]
        assert tool_use_item["output"] == "Found 10 matches"
        assert tool_use_item["status"] == "complete"
        assert "call_123" not in tool_use_map  # 应该从 map 中移除

    def test_merge_tool_result_to_tool_use_not_found(self, session_ops, caplog):
        """测试 tool_result 找不到对应的 tool_use"""
        tool_use_map = {}
        tool_result = {
            "type": "tool_result",
            "tool_use_id": "call_unknown",
            "content": "Some result",
        }

        session_ops._merge_tool_result_to_tool_use(tool_result, tool_use_map)

        # 应该记录警告日志
        assert "not found in tool_use_map" in caplog.text

    # ========== 测试 _process_assistant_message ==========

    def test_process_assistant_message_with_tool_use(self, session_ops):
        """测试处理包含 tool_use 的 assistant 消息"""
        message_data = {
            "type": "assistant",
            "timestamp": "2024-01-01T10:00:00Z",
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
        }

        tool_use_map = {}
        result = session_ops._process_assistant_message(message_data, tool_use_map)

        assert result["type"] == "assistant"
        tool_use_item = result["message"]["content"][0]
        assert tool_use_item["status"] == "incomplete"
        assert "call_123" in tool_use_map  # 应该被添加到 map 中

    def test_process_assistant_message_with_thinking(self, session_ops):
        """测试处理包含 thinking 的 assistant 消息"""
        message_data = {
            "type": "assistant",
            "timestamp": "2024-01-01T10:00:00Z",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "Let me think..."},
                ],
            },
        }

        tool_use_map = {}
        result = session_ops._process_assistant_message(message_data, tool_use_map)

        assert result["type"] == "assistant"
        # thinking 字段应该被转换为 text 字段
        thinking_item = result["message"]["content"][0]
        assert thinking_item["type"] == "thinking"
        assert thinking_item["text"] == "Let me think..."
        assert "thinking" not in thinking_item

    def test_process_assistant_message_empty_content(self, session_ops):
        """测试处理空 content 的消息"""
        message_data = {
            "type": "assistant",
            "timestamp": "2024-01-01T10:00:00Z",
            "message": {"role": "assistant", "content": []},
        }

        tool_use_map = {}
        result = session_ops._process_assistant_message(message_data, tool_use_map)

        # 应该返回原始消息
        assert result is message_data

    # ========== 测试 _merge_tool_use_with_result ==========

    @pytest.mark.asyncio
    async def test_merge_tool_use_with_result_complete(
        self, session_ops, sample_session_data
    ):
        """测试完整的 tool_use 和 tool_result 合并流程"""
        # 提取消息部分
        messages = [m for m in sample_session_data if "message" in m]

        # 执行合并
        merged = session_ops._merge_tool_use_with_result(messages)

        # 验证合并结果
        # 应该有 3 条消息（user + assistant with merged tool_use + assistant with text）
        assert len(merged) == 3

        # 第一条是 user 消息
        assert merged[0]["type"] == "user"
        assert merged[0]["message"]["role"] == "user"

        # 第二条是 assistant 消息，包含合并后的 tool_use
        assistant_msg_1 = merged[1]
        assert assistant_msg_1["type"] == "assistant"
        assert assistant_msg_1["message"]["role"] == "assistant"
        content = assistant_msg_1["message"]["content"]
        assert len(content) == 1

        # 验证合并后的 tool_use
        tool_use = content[0]
        assert tool_use["type"] == "tool_use"
        assert tool_use["id"] == "call_abc123"
        assert tool_use["name"] == "Grep"
        assert tool_use["input"] == {
            "pattern": "@expose_api",
            "path": "/test/project/src",
        }
        assert tool_use["output"] == "Found 5 matches"
        assert tool_use["status"] == "complete"

        # 第三条是 assistant 消息，包含 text
        assistant_msg_2 = merged[2]
        assert assistant_msg_2["type"] == "assistant"
        assert assistant_msg_2["message"]["role"] == "assistant"
        text_content = assistant_msg_2["message"]["content"]
        assert len(text_content) == 1
        assert text_content[0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_merge_tool_use_without_result(self, session_ops):
        """测试没有 tool_result 的 tool_use（incomplete）"""
        messages = [
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "call_xyz789",
                            "name": "ReadFile",
                            "input": {"file_path": "/test/file.txt"},
                        }
                    ],
                },
            }
        ]

        merged = session_ops._merge_tool_use_with_result(messages)

        assert len(merged) == 1
        tool_use = merged[0]["message"]["content"][0]
        assert tool_use["type"] == "tool_use"
        assert tool_use["status"] == "incomplete"
        assert "output" not in tool_use

    @pytest.mark.asyncio
    async def test_merge_multiple_tool_uses(self, session_ops):
        """测试多个 tool_use 的合并"""
        messages = [
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "call_1",
                            "name": "Grep",
                            "input": {"pattern": "test"},
                        },
                        {
                            "type": "tool_use",
                            "id": "call_2",
                            "name": "ReadFile",
                            "input": {"file_path": "test.txt"},
                        },
                    ],
                },
            },
            {
                "type": "user",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "call_1",
                            "content": "Found 3 matches",
                        }
                    ],
                },
            },
            {
                "type": "user",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "call_2",
                            "content": "File content loaded",
                        }
                    ],
                },
            },
        ]

        merged = session_ops._merge_tool_use_with_result(messages)

        # 应该只有 1 条消息（两个 tool_use 都合并到同一 assistant 消息中）
        assert len(merged) == 1
        content = merged[0]["message"]["content"]
        assert len(content) == 2

        # 验证第一个 tool_use
        assert content[0]["type"] == "tool_use"
        assert content[0]["id"] == "call_1"
        assert content[0]["status"] == "complete"
        assert content[0]["output"] == "Found 3 matches"

        # 验证第二个 tool_use
        assert content[1]["type"] == "tool_use"
        assert content[1]["id"] == "call_2"
        assert content[1]["status"] == "complete"
        assert content[1]["output"] == "File content loaded"

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
        # 创建多个 session 文件
        sessions_to_create = [
            "session-1.jsonl",
            "session-2.jsonl",
            "agent-session-3.jsonl",
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

        assert len(sessions) == 3

        # 验证 session 信息
        session_ids = [s.session_id for s in sessions]
        assert "session-1" in session_ids
        assert "session-2" in session_ids
        assert "agent-session-3" in session_ids

        # 验证 is_agent_session 标记
        agent_session = next(s for s in sessions if s.session_id == "agent-session-3")
        assert agent_session.is_agent_session is True

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

    # ========== 测试 _load_session_data ==========

    @pytest.mark.asyncio
    async def test_load_session_data_success(self, session_ops, sample_session_jsonl):
        """测试成功加载 session 数据"""
        session, _ = session_ops._load_session_data(sample_session_jsonl)

        assert session is not None
        assert session.session_id == "test-session-123"
        assert session.session_file == str(sample_session_jsonl)
        assert session.is_agent_session is False
        # meta 消息被过滤掉了，只剩余 user 和 assistant 消息
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
        session, _ = ops._load_session_data(session_file)

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
        session, _ = ops._load_session_data(session_file)

        assert session is None

    @pytest.mark.asyncio
    async def test_load_session_data_empty_file(self, temp_session_dir):
        """测试加载空文件"""
        session_file = temp_session_dir / "empty.jsonl"
        session_file.touch()

        ops = ClaudeSessionOperations(temp_session_dir)
        session, _ = ops._load_session_data(session_file)

        # 空文件应该返回 None（没有有效消息）
        assert session is None

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
        assert len(session.messages) == 2

        # 验证合并后的 tool_use
        tool_use_msg = session.messages[1]
        content = tool_use_msg.message.get("content")
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

    # ========== 测试 quick_detect_project_path ==========

    @pytest.mark.asyncio
    async def test_quick_detect_project_path_success(self, temp_session_dir):
        """测试成功检测项目路径"""
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
        project_path = await ops.quick_detect_project_path()

        assert project_path == "/test/project"

    @pytest.mark.asyncio
    async def test_quick_detect_project_path_not_found(self, temp_session_dir):
        """测试找不到项目路径"""
        # 创建不包含 cwd 的 session 文件
        session_file = temp_session_dir / "session-1.jsonl"
        with open(session_file, "w") as f:
            f.write(json.dumps({"timestamp": "2024-01-01T10:00:00Z"}) + "\n")

        ops = ClaudeSessionOperations(temp_session_dir)
        project_path = await ops.quick_detect_project_path()

        assert project_path is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
