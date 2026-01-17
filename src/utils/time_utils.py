"""
时间处理工具模块
提供时间解析、转换和格式化的统一接口
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def parse_iso_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    解析 ISO 8601 格式的时间戳字符串，统一转换为 UTC 时间（无时区信息）

    此函数处理多种 ISO 8601 格式，包括：
    - 2024-01-12T10:00:00.000Z（UTC 时间，Z 后缀）
    - 2024-01-12T10:00:00.000+00:00（UTC 时间，时区偏移）
    - 2024-01-12T10:00:00.000+08:00（其他时区）

    所有时间都会被转换为 UTC 并移除时区信息，确保一致性。

    Args:
        timestamp_str: ISO 8601 格式的时间戳字符串

    Returns:
        Optional[datetime]: 解析后的 datetime 对象（无时区信息，值为 UTC 时间），
                          如果失败则返回 None

    Examples:
        >>> parse_iso_timestamp("2024-01-12T10:00:00.000Z")
        datetime.datetime(2024, 1, 12, 10, 0, 0)

        >>> parse_iso_timestamp("2024-01-12T18:00:00.000+08:00")
        datetime.datetime(2024, 1, 12, 10, 0, 0)  # 转换为 UTC
    """
    if not timestamp_str or not isinstance(timestamp_str, str):
        logger.warning(f"Invalid timestamp input: {timestamp_str}")
        return None

    try:
        # 处理 Z 后缀（UTC 时间）
        normalized_str = timestamp_str
        if timestamp_str.endswith("Z"):
            normalized_str = timestamp_str.replace("Z", "+00:00")

        # 解析时间戳
        timestamp = datetime.fromisoformat(normalized_str)

        # 转换为 UTC 并移除时区信息
        if timestamp.tzinfo is not None:
            timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)

        return timestamp

    except (ValueError, AttributeError) as e:
        logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
        return None


def format_timestamp(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化 datetime 对象为字符串

    Args:
        dt: datetime 对象
        format_str: 格式化字符串，默认为 "%Y-%m-%d %H:%M:%S"

    Returns:
        str: 格式化后的时间字符串

    Examples:
        >>> format_timestamp(datetime(2024, 1, 12, 10, 0, 0))
        "2024-01-12 10:00:00"
    """
    if dt is None:
        return ""
    return dt.strftime(format_str)


def get_current_utc_time() -> datetime:
    """
    获取当前 UTC 时间（无时区信息）

    Returns:
        datetime: 当前 UTC 时间，无时区信息
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def datetime_to_timestamp(dt: datetime) -> int:
    """
    将 datetime 对象转换为 Unix 时间戳（秒）

    Args:
        dt: datetime 对象

    Returns:
        int: Unix 时间戳（秒）
    """
    if dt is None:
        return 0
    return int(dt.timestamp())


def timestamp_to_datetime(timestamp: int) -> Optional[datetime]:
    """
    将 Unix 时间戳转换为 datetime 对象（UTC）

    Args:
        timestamp: Unix 时间戳（秒）

    Returns:
        Optional[datetime]: datetime 对象（UTC，无时区信息）
    """
    if timestamp is None or timestamp == 0:
        return None

    try:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(tzinfo=None)
    except (ValueError, OSError) as e:
        logger.warning(f"Failed to convert timestamp {timestamp} to datetime: {e}")
        return None
