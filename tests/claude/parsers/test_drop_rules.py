"""
DropRules 和 DropRuleRegistry 的单元测试
"""

import pytest

from src.claude.parsers.drop_rules import DropRuleRegistry, DropRules


class TestDropRules:
    """测试 DropRules 类"""

    def test_is_expected_empty_type_full_drop(self):
        """测试需要全部丢弃的消息类型"""
        # file-history-snapshot 应该全部丢弃
        assert DropRules.is_expected_empty_type("file-history-snapshot") is True
        assert DropRules.is_expected_empty_type("file-history-snapshot", None) is True
        assert (
            DropRules.is_expected_empty_type("file-history-snapshot", "any_subtype")
            is True
        )

        # summary 应该全部丢弃
        assert DropRules.is_expected_empty_type("summary") is True

    def test_is_expected_empty_type_subtype_specific(self):
        """测试需要根据 subtype 决定的消息类型"""
        # system 消息需要根据 subtype 判断
        assert DropRules.is_expected_empty_type("system", "turn_duration") is True
        assert DropRules.is_expected_empty_type("system", "local_command") is True
        assert DropRules.is_expected_empty_type("system", "api_error") is True
        assert DropRules.is_expected_empty_type("system", "compact_boundary") is True

        # system 消息的其他 subtype 不应该被丢弃
        assert DropRules.is_expected_empty_type("system", "other_subtype") is False
        assert DropRules.is_expected_empty_type("system", None) is False

    def test_is_expected_empty_type_unknown_type(self):
        """测试未知的消息类型"""
        assert DropRules.is_expected_empty_type("unknown_type") is False
        assert DropRules.is_expected_empty_type("user") is False
        assert DropRules.is_expected_empty_type("assistant") is False

    def test_should_skip_content_user_warmup(self):
        """测试跳过用户消息的 Warmup 内容"""
        assert DropRules.should_skip_content("user", "Warmup") is True

    def test_should_skip_content_user_normal(self):
        """测试不跳过用户消息的普通内容"""
        assert DropRules.should_skip_content("user", "Normal message") is False

    def test_should_skip_content_other_types(self):
        """测试其他消息类型的内容"""
        assert DropRules.should_skip_content("assistant", "Some content") is False
        assert DropRules.should_skip_content("system", "Some content") is False


class TestDropRuleRegistry:
    """测试 DropRuleRegistry 类"""

    def test_record_drop(self):
        """测试记录丢弃消息"""
        registry = DropRuleRegistry()

        message_data = {
            "type": "user",
            "timestamp": "2024-01-01T10:00:00Z",
            "_drop": True,
            "_drop_reason": "test_reason",
            "_expected_drop": True,
            "message": {"role": "user", "content": "Test"},
        }

        registry.record_drop(message_data, reason="test_reason", expected=True)

        assert len(registry.dropped_messages) == 1
        assert registry.dropped_messages[0] == message_data

    def test_record_drop_multiple(self):
        """测试记录多条丢弃消息"""
        registry = DropRuleRegistry()

        for i in range(5):
            message_data = {
                "type": "user",
                "timestamp": f"2024-01-01T10:00:0{i}Z",
                "_drop": True,
                "_drop_reason": f"reason_{i}",
                "_expected_drop": i % 2 == 0,  # 偶数个是预期内的
                "message": {"role": "user", "content": f"Message {i}"},
            }
            registry.record_drop(
                message_data, reason=f"reason_{i}", expected=i % 2 == 0
            )

        assert len(registry.dropped_messages) == 5

    def test_get_stats_empty(self):
        """测试空统计"""
        registry = DropRuleRegistry()
        stats = registry.get_stats()

        assert stats["total"] == 0
        assert stats["expected"] == 0
        assert stats["unexpected"] == 0

    def test_get_stats_mixed(self):
        """测试混合统计"""
        registry = DropRuleRegistry()

        # 添加 3 条预期内的和 2 条非预期的
        for i in range(5):
            message_data = {
                "type": "user",
                "_drop": True,
                "_drop_reason": f"reason_{i}",
                "_expected_drop": i < 3,  # 前 3 条是预期内的
                "message": {"role": "user", "content": f"Message {i}"},
            }
            registry.record_drop(message_data, reason=f"reason_{i}", expected=i < 3)

        stats = registry.get_stats()

        assert stats["total"] == 5
        assert stats["expected"] == 3
        assert stats["unexpected"] == 2

    def test_get_samples_empty(self):
        """测试空样本列表"""
        registry = DropRuleRegistry()
        samples = registry.get_samples()

        assert samples == []

    def test_get_samples_unexpected_only(self):
        """测试只获取非预期丢弃的样本"""
        registry = DropRuleRegistry()

        # 添加多条消息
        for i in range(5):
            message_data = {
                "type": "user",
                "timestamp": f"2024-01-01T10:00:0{i}Z",
                "_drop": True,
                "_drop_reason": f"reason_{i}",
                "_expected_drop": i < 3,  # 前 3 条是预期内的，后 2 条是非预期的
                "message": {"role": "user", "content": f"Message {i}"},
            }
            registry.record_drop(message_data, reason=f"reason_{i}", expected=i < 3)

        # 只获取非预期的
        samples = registry.get_samples(max_count=10, unexpected_only=True)

        # 应该有 2 条是非预期的（i=3 和 i=4）
        assert len(samples) == 2
        assert all(s["_expected_drop"] is False for s in samples)

    def test_get_samples_max_count(self):
        """测试最大样本数量限制"""
        registry = DropRuleRegistry()

        # 添加 10 条消息
        for i in range(10):
            message_data = {
                "type": "user",
                "timestamp": f"2024-01-01T10:00:0{i}Z",
                "_drop": True,
                "_drop_reason": "test",
                "_expected_drop": False,
                "message": {"role": "user", "content": f"Message {i}"},
            }
            registry.record_drop(message_data, reason="test", expected=False)

        # 只获取前 3 条
        samples = registry.get_samples(max_count=3, unexpected_only=True)

        assert len(samples) == 3

    def test_get_samples_content_preview_string(self):
        """测试字符串内容的预览"""
        registry = DropRuleRegistry()

        message_data = {
            "type": "user",
            "timestamp": "2024-01-01T10:00:00Z",
            "_drop": True,
            "_drop_reason": "test",
            "_expected_drop": False,
            "message": {"role": "user", "content": "A" * 200},  # 超长内容
        }
        registry.record_drop(message_data, reason="test", expected=False)

        samples = registry.get_samples(max_count=1, unexpected_only=True)

        assert len(samples) == 1
        assert "content_preview" in samples[0]
        assert len(samples[0]["content_preview"]) <= 100

    def test_get_samples_content_preview_list(self):
        """测试列表内容的预览"""
        registry = DropRuleRegistry()

        message_data = {
            "type": "user",
            "timestamp": "2024-01-01T10:00:00Z",
            "_drop": True,
            "_drop_reason": "test",
            "_expected_drop": False,
            "message": {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Hello"},
                    {"type": "tool_use", "name": "Grep"},
                ],
            },
        }
        registry.record_drop(message_data, reason="test", expected=False)

        samples = registry.get_samples(max_count=1, unexpected_only=True)

        assert len(samples) == 1
        assert "content_preview" in samples[0]
        assert samples[0]["content_preview"] == "[text]"

    def test_get_samples_all_including_expected(self):
        """测试获取所有样本（包括预期内的）"""
        registry = DropRuleRegistry()

        # 添加混合消息
        for i in range(5):
            message_data = {
                "type": "user",
                "timestamp": f"2024-01-01T10:00:0{i}Z",
                "_drop": True,
                "_drop_reason": "test",
                "_expected_drop": i % 2 == 0,  # 偶数是预期内的
                "message": {"role": "user", "content": f"Message {i}"},
            }
            registry.record_drop(message_data, reason="test", expected=i % 2 == 0)

        # 获取所有样本
        samples = registry.get_samples(max_count=10, unexpected_only=False)

        assert len(samples) == 5

    def test_get_samples_with_subtype(self):
        """测试包含 subtype 的样本"""
        registry = DropRuleRegistry()

        message_data = {
            "type": "system",
            "subtype": "turn_duration",
            "timestamp": "2024-01-01T10:00:00Z",
            "_drop": True,
            "_drop_reason": "expected_empty:system:turn_duration",
            "_expected_drop": True,
            "message": {"role": "system", "content": []},
        }
        registry.record_drop(
            message_data, reason="expected_empty:system:turn_duration", expected=True
        )

        samples = registry.get_samples(max_count=1, unexpected_only=False)

        assert len(samples) == 1
        assert samples[0]["subtype"] == "turn_duration"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
