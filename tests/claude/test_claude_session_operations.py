"""
Claude Session Operations 模块的单元测试
测试 Session 的扫描和读取功能，特别是 tool_use 和 tool_result 的合并逻辑
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

    # ========== 测试 _merge_tool_use_with_result ==========

    @pytest.mark.asyncio
    async def test_merge_tool_use_with_result_complete(
        self, session_ops, sample_session_data
    ):
        """测试 tool_use 和 tool_result 的合并（完整流程）"""
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

    @pytest.mark.asyncio
    async def test_merge_thinking_messages(self, session_ops):
        """测试 thinking 消息不被合并"""
        messages = [
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "text": "Let me think..."},
                        {
                            "type": "text",
                            "text": "I'll help you with that.",
                        },
                    ],
                },
            },
        ]

        merged = session_ops._merge_tool_use_with_result(messages)

        assert len(merged) == 1
        content = merged[0]["message"]["content"]
        assert len(content) == 2
        assert content[0]["type"] == "thinking"
        assert content[1]["type"] == "text"

    @pytest.mark.asyncio
    async def test_merge_user_messages_unchanged(self, session_ops):
        """测试 user 消息不被修改"""
        messages = [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": "请帮我搜索文件",
                },
            },
        ]

        merged = session_ops._merge_tool_use_with_result(messages)

        assert len(merged) == 1
        assert merged[0]["type"] == "user"
        assert merged[0]["message"]["content"] == "请帮我搜索文件"

    # ========== 测试 _load_session_data ==========

    @pytest.mark.asyncio
    async def test_load_session_data_success(self, session_ops, sample_session_jsonl):
        """测试成功加载 session 数据"""
        session = session_ops._load_session_data(sample_session_jsonl)

        assert session is not None
        assert session.session_id == "test-session-123"
        assert session.session_file == str(sample_session_jsonl)
        assert session.is_agent_session is False
        assert session.message_count == 3  # 3 条有 message 的消息
        assert len(session.messages) == 3
        assert session.project_path == "/test/project"
        assert session.git_branch == "main"

        # 验证消息合并
        tool_use_msg = session.messages[1]
        assert tool_use_msg.message is not None
        content = tool_use_msg.message.get("content")
        assert isinstance(content, list)

        # 找到合并后的 tool_use
        tool_use = None
        for item in content:
            if isinstance(item, dict) and item.get("type") == "tool_use":
                tool_use = item
                break

        assert tool_use is not None
        assert tool_use["status"] == "complete"
        assert tool_use["output"] == "Found 5 matches"

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

        session_ops_local = ClaudeSessionOperations(temp_session_dir)
        session = session_ops_local._load_session_data(session_file)

        assert session is not None
        assert session.is_agent_session is True
        assert session.session_id == "agent-test-456"

    @pytest.mark.asyncio
    async def test_load_session_data_invalid_json(self, temp_session_dir):
        """测试加载无效的 JSON 文件"""
        session_file = temp_session_dir / "invalid.jsonl"
        with open(session_file, "w", encoding="utf-8") as f:
            f.write("invalid json content")

        session_ops_local = ClaudeSessionOperations(temp_session_dir)
        session = session_ops_local._load_session_data(session_file)

        assert session is None

    @pytest.mark.asyncio
    async def test_load_session_data_empty_file(self, temp_session_dir):
        """测试加载空文件"""
        session_file = temp_session_dir / "empty.jsonl"
        session_file.touch()

        session_ops_local = ClaudeSessionOperations(temp_session_dir)
        session = session_ops_local._load_session_data(session_file)

        # 空文件应该返回一个 session，但消息为空
        assert session is not None
        assert len(session.messages) == 0
        assert session.message_count == 0

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
    async def test_scan_sessions_sorted_by_time(self, temp_session_dir):
        """测试 session 按最后修改时间降序排序"""
        import time

        ops = ClaudeSessionOperations(temp_session_dir)

        # 创建多个 session 文件，每次创建后等待以确保文件修改时间不同
        session_names = ["session-old", "session-middle", "session-new"]
        for session_name in session_names:
            session_file = temp_session_dir / f"{session_name}.jsonl"
            with open(session_file, "w", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "type": "user",
                            "message": {
                                "role": "user",
                                "content": f"Message from {session_name}",
                            },
                        }
                    )
                    + "\n"
                )
            time.sleep(0.01)  # 确保文件修改时间不同

        sessions = await ops.scan_sessions()

        # 验证排序：最新的应该在前面
        assert len(sessions) == 3
        assert sessions[0].session_id == "session-new"
        assert sessions[1].session_id == "session-middle"
        assert sessions[2].session_id == "session-old"

    # ========== 测试 read_session_contents ==========

    @pytest.mark.asyncio
    async def test_read_session_contents_success(
        self, session_ops, sample_session_jsonl
    ):
        """测试成功读取 session 内容"""
        session = await session_ops.read_session_contents("test-session-123")

        assert session is not None
        assert session.session_id == "test-session-123"
        assert len(session.messages) == 3

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
    async def test_read_session_contents_by_filename(self, temp_session_dir):
        """测试通过文件名读取 session"""
        session_file = temp_session_dir / "my-session.jsonl"
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "type": "user",
                        "message": {"role": "user", "content": "test message"},
                    }
                )
                + "\n"
            )

        ops = ClaudeSessionOperations(temp_session_dir)
        session = await ops.read_session_contents("my-session")

        assert session is not None
        assert session.session_id == "my-session"
        assert len(session.messages) == 1

    # ========== 测试边界情况 ==========

    @pytest.mark.asyncio
    async def test_tool_use_with_complex_output(self, temp_session_dir):
        """测试 tool_use 包含复杂输出（对象/数组）"""
        session_file = temp_session_dir / "complex-output.jsonl"
        with open(session_file, "w", encoding="utf-8") as f:
            # tool_use
            f.write(
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": "call_complex",
                                    "name": "ListFiles",
                                    "input": {"path": "/test"},
                                }
                            ],
                        },
                    }
                )
                + "\n"
            )
            # tool_result with array output
            f.write(
                json.dumps(
                    {
                        "type": "user",
                        "message": {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "call_complex",
                                    "content": [
                                        {"name": "file1.txt", "size": 1024},
                                        {"name": "file2.txt", "size": 2048},
                                    ],
                                }
                            ],
                        },
                    }
                )
                + "\n"
            )

        ops = ClaudeSessionOperations(temp_session_dir)
        session = await ops.read_session_contents("complex-output")

        assert session is not None
        tool_use_msg = session.messages[0]
        content = tool_use_msg.message.get("content")
        tool_use = content[0]

        assert tool_use["output"] == [
            {"name": "file1.txt", "size": 1024},
            {"name": "file2.txt", "size": 2048},
        ]
        assert tool_use["status"] == "complete"

    @pytest.mark.asyncio
    async def test_session_with_empty_content_array(self, temp_session_dir):
        """测试包含空 content 数组的消息"""
        session_file = temp_session_dir / "empty-content.jsonl"
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {"role": "assistant", "content": []},
                    }
                )
                + "\n"
            )

        ops = ClaudeSessionOperations(temp_session_dir)
        session = await ops.read_session_contents("empty-content")

        # 应该跳过空消息
        assert session is not None
        assert len(session.messages) == 0

    @pytest.mark.asyncio
    async def test_mixed_tool_and_text_messages(self, temp_session_dir):
        """测试混合的 tool_use 和 text 消息"""
        session_file = temp_session_dir / "mixed.jsonl"
        with open(session_file, "w", encoding="utf-8") as f:
            # tool_use
            f.write(
                json.dumps(
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
                                }
                            ],
                        },
                    }
                )
                + "\n"
            )
            # text
            f.write(
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "role": "assistant",
                            "content": [{"type": "text", "text": "正在搜索..."}],
                        },
                    }
                )
                + "\n"
            )
            # tool_result
            f.write(
                json.dumps(
                    {
                        "type": "user",
                        "message": {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "call_1",
                                    "content": "Found 10 matches",
                                }
                            ],
                        },
                    }
                )
                + "\n"
            )
            # text
            f.write(
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "role": "assistant",
                            "content": [{"type": "text", "text": "找到10个匹配项"}],
                        },
                    }
                )
                + "\n"
            )

        ops = ClaudeSessionOperations(temp_session_dir)
        session = await ops.read_session_contents("mixed")

        assert session is not None
        # 应该有 3 条消息：assistant(tool_use) + assistant(text) + assistant(text)
        # tool_result 被合并到 tool_use 中
        assert len(session.messages) == 3

        # 验证第一条消息包含合并后的 tool_use
        first_msg = session.messages[0]
        tool_use = first_msg.message.get("content")[0]
        assert tool_use["type"] == "tool_use"
        assert tool_use["status"] == "complete"
        assert tool_use["output"] == "Found 10 matches"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
