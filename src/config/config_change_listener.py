"""
配置变化监听器
处理配置变化的事件监听和处理逻辑
"""

import asyncio
from abc import ABC
from datetime import datetime
from typing import Any, Dict, List, Optional


class ConfigInitializeEvent:
    """配置初始化事件"""

    def __init__(self, results: Dict[str, Any], timestamp: Optional[datetime] = None):
        self.results = results or {}
        self.timestamp = timestamp or datetime.now()

    def __repr__(self):
        return f"ConfigInitializeEvent(count={len(self.results)}, timestamp={self.timestamp})"


class ConfigKeyUpdateEvent:
    """配置键更新事件"""

    def __init__(
        self,
        key: str,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.key = key
        self.old_value = old_value
        self.new_value = new_value
        self.timestamp = timestamp or datetime.now()

    def __repr__(self):
        return f"ConfigKeyUpdateEvent(key={self.key}, old={self.old_value}, new={self.new_value}, timestamp={self.timestamp})"


class ConfigListenerResult:
    """监听器结果"""

    def __init__(self, success: bool = True, error_message: str = ""):
        self.success = success
        self.error_message = error_message


class ConfigChangeListener(ABC):
    """配置变化监听器基类"""

    async def onInitialize(self, event: ConfigInitializeEvent) -> None:
        """
        配置初始化事件处理方法

        Args:
            event: 配置初始化事件
        """

    async def beforeKeyUpdate(
        self, event: ConfigKeyUpdateEvent
    ) -> ConfigListenerResult:
        """
        配置键更新前校验方法

        Args:
            event: 配置键更新事件（包含key和value）

        Returns:
            ConfigListenerResult: 校验结果，success为True表示允许更新，False表示拒绝更新
        """
        return ConfigListenerResult(True)

    async def onKeyUpdated(self, event: ConfigKeyUpdateEvent) -> None:
        """
        配置键更新事件处理方法

        Args:
            event: 配置键更新事件
        """


class ConfigChangeManager:
    """配置变化管理器"""

    def __init__(self):
        self._listeners: List[ConfigChangeListener] = []
        self._enabled = True

    def add_listener(self, listener: ConfigChangeListener) -> None:
        """
        添加监听器

        Args:
            listener: 监听器实例
        """
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: ConfigChangeListener) -> None:
        """
        移除监听器

        Args:
            listener: 监听器实例
        """
        if listener in self._listeners:
            self._listeners.remove(listener)

    def clear_listeners(self) -> None:
        """清空所有监听器"""
        self._listeners.clear()

    def enable(self) -> None:
        """启用事件通知"""
        self._enabled = True

    def disable(self) -> None:
        """禁用事件通知"""
        self._enabled = False

    async def notify_initialize(self, event: ConfigInitializeEvent) -> None:
        """
        通知所有监听器配置初始化事件

        Args:
            event: 配置初始化事件
        """
        if not self._enabled:
            return

        # 并行通知所有监听器
        tasks = []
        for listener in self._listeners:
            try:
                task = asyncio.create_task(listener.onInitialize(event))
                tasks.append(task)
            except Exception as e:
                print(f"Error creating task for listener {listener}: {e}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def before_key_update(
        self, event: ConfigKeyUpdateEvent
    ) -> ConfigListenerResult:
        """
        通知所有监听器进行配置键更新前校验

        Args:
            event: 配置键更新事件

        Returns:
            ConfigListenerResult: 如果任何监听器拒绝更新，返回失败结果
        """
        if not self._enabled:
            return ConfigListenerResult(True)

        # 并行通知所有监听器进行校验
        tasks = []
        for listener in self._listeners:
            try:
                task = asyncio.create_task(listener.beforeKeyUpdate(event))
                tasks.append(task)
            except Exception as e:
                print(
                    f"Error creating beforeKeyUpdate task for listener {listener}: {e}"
                )

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 检查所有结果，如果有任何一个拒绝，就返回失败
            for result in results:
                if isinstance(result, Exception):
                    print(f"Error in beforeKeyUpdate listener: {result}")
                    return ConfigListenerResult(False, str(result))

                if not result.success:
                    return result

        return ConfigListenerResult(True)

    async def notify_key_updated(self, event: ConfigKeyUpdateEvent) -> None:
        """
        通知所有监听器配置键更新事件

        Args:
            event: 配置键更新事件
        """
        if not self._enabled:
            return

        # 并行通知所有监听器
        tasks = []
        for listener in self._listeners:
            try:
                task = asyncio.create_task(listener.onKeyUpdated(event))
                tasks.append(task)
            except Exception as e:
                print(f"Error creating task for listener {listener}: {e}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


# 全局配置变化管理器实例
config_change_manager = ConfigChangeManager()
