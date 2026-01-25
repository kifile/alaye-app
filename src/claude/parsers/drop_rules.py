"""
消息丢弃规则定义

定义哪些消息类型应该被丢弃，以及是否是预期内的丢弃
"""

from typing import Dict, Optional, Set


class DropRules:
    """消息丢弃规则配置"""

    # 预期内没有 message 字段的类型（两级模式）
    # - 第一级 key 是消息类型
    # - 如果 value 为 None，说明该类型全部丢弃
    # - 如果 value 为 set，说明只丢弃对应的 subtype
    EXPECTED_EMPTY_TYPES: Dict[str, Optional[Set[str]]] = {
        "file-history-snapshot": None,  # 全部丢弃
        "summary": None,  # 全部丢弃
        "system": {
            "turn_duration",
            "local_command",
            "api_error",
            "compact_boundary",
        },  # 只丢弃这些 subtype
    }

    # 需要跳过的特殊用户消息内容
    SKIP_USER_CONTENTS: Set[str] = {
        "Warmup",  # 系统预热请求
    }

    @classmethod
    def is_expected_empty_type(
        cls, message_type: str, subtype: Optional[str] = None
    ) -> bool:
        """
        判断是否是预期内的空消息类型

        Args:
            message_type: 消息类型
            subtype: 消息子类型（可选）

        Returns:
            bool: 是否是预期内的空消息
        """
        if message_type not in cls.EXPECTED_EMPTY_TYPES:
            return False

        allowed_subtypes = cls.EXPECTED_EMPTY_TYPES[message_type]

        # 如果 value 为 None，说明该类型全部丢弃
        if allowed_subtypes is None:
            return True

        # 如果有 subtype，检查是否在允许的 subtype 列表中
        if subtype is not None:
            return subtype in allowed_subtypes

        return False

    @classmethod
    def should_skip_content(cls, message_type: str, content: str) -> bool:
        """
        判断是否应该跳过特定内容的消息

        Args:
            message_type: 消息类型
            content: 消息内容

        Returns:
            bool: 是否应该跳过
        """
        if message_type == "user":
            return content in cls.SKIP_USER_CONTENTS
        return False


class DropRuleRegistry:
    """丢弃规则注册表，用于追踪和统计丢弃情况"""

    def __init__(self):
        self.dropped_messages: list[dict] = []

    def record_drop(
        self,
        message_data: dict,
        reason: str,
        expected: bool = False,
    ):
        """
        记录一条被丢弃的消息到统计列表

        注意：此方法只负责记录统计，不修改 message_data 的字段
          字段设置应该由调用方完成
          reason 和 expected 参数保留用于 API 清晰度和未来扩展

        Args:
            message_data: 原始消息数据（应该已包含 _drop, _drop_reason, _expected_drop 字段）
            reason: 丢弃原因（用于 API 清晰度，不从 message_data 读取）
            expected: 是否是预期内的丢弃（用于 API 清晰度，不从 message_data 读取）
        """
        # 记录到统计列表（不修改原 message_data）
        # 注意：reason 和 expected 参数主要用于 API 接口的清晰性
        # 实际值应该从 message_data 的字段中读取
        self.dropped_messages.append(message_data)

    def get_samples(
        self, max_count: int = 2, unexpected_only: bool = True
    ) -> list[dict]:
        """
        获取被丢弃消息的样本

        Args:
            max_count: 最多返回的样本数量
            unexpected_only: 是否只返回非预期丢弃的样本

        Returns:
            list[dict]: 丢弃消息的样本列表
        """
        samples = []

        for dropped_msg in self.dropped_messages:
            if unexpected_only and dropped_msg.get("_expected_drop", False):
                continue

            sample = {
                "type": dropped_msg.get("type"),
                "timestamp": dropped_msg.get("timestamp"),
                "role": dropped_msg.get("message", {}).get("role"),
                "drop_reason": dropped_msg.get("_drop_reason", "unknown"),
                "_expected_drop": dropped_msg.get("_expected_drop", False),
                "subtype": dropped_msg.get("subtype"),
            }

            content = dropped_msg.get("message", {}).get("content")
            if isinstance(content, str):
                sample["content_preview"] = content[:100]
            elif isinstance(content, list) and len(content) > 0:
                sample["content_preview"] = f"[{content[0].get('type', 'unknown')}]"

            samples.append(sample)

            if len(samples) >= max_count:
                break

        return samples

    def get_stats(self) -> dict:
        """
        获取丢弃统计信息

        Returns:
            dict: 包含 total, expected, unexpected 计数的字典
        """
        total = len(self.dropped_messages)
        expected = sum(
            1 for m in self.dropped_messages if m.get("_expected_drop", False)
        )
        unexpected = total - expected

        return {
            "total": total,
            "expected": expected,
            "unexpected": unexpected,
        }
