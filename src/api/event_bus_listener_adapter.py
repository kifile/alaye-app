"""
Event Bus Listener Adapter

事件总线监听器适配器，负责将终端事件转发到事件总线。
这个组件作为 terminal_manager 和 event_bus 之间的桥梁，实现解耦。
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from ..terminal.terminal_manager_service import TerminalEventListener


class EventBusListenerAdapter(TerminalEventListener):
    """
    事件总线监听器适配器

    负责将终端事件转发到事件总线，实现 terminal_manager 和 event_bus 的解耦。
    """

    def __init__(self, event_bus=None):
        """
        初始化事件总线监听器适配器

        Args:
            event_bus: 事件总线实例
        """
        self._event_bus = event_bus
        self._logger = logging.getLogger(__name__)

    def set_event_bus(self, event_bus):
        """
        设置事件总线

        Args:
            event_bus: 事件总线实例
        """
        self._event_bus = event_bus

    def on_terminal_output(self, instance_id: str, data: str) -> None:
        """
        处理终端输出事件

        Args:
            instance_id: 终端实例ID
            data: 输出数据
        """
        self._forward_event("output", instance_id, {"text": data})

    def on_terminal_state_changed(
        self, instance_id: str, old_state: str, new_state: str
    ) -> None:
        """
        处理终端状态变化事件

        Args:
            instance_id: 终端实例ID
            old_state: 旧状态
            new_state: 新状态
        """
        self._forward_event(
            "state_changed",
            instance_id,
            {"old_state": old_state, "new_state": new_state},
        )

    def on_terminal_process_exited(
        self, instance_id: str, exit_code: Optional[int], exit_reason: str
    ) -> None:
        """
        处理终端进程退出事件

        Args:
            instance_id: 终端实例ID
            exit_code: 退出码
            exit_reason: 退出原因
        """
        self._forward_event(
            "process_exited",
            instance_id,
            {"exit_code": exit_code, "exit_reason": exit_reason},
        )

    def on_terminal_error(
        self,
        instance_id: str,
        error_type: str,
        error_msg: str,
        operation: Optional[str] = None,
    ) -> None:
        """
        处理终端错误事件

        Args:
            instance_id: 终端实例ID
            error_type: 错误类型
            error_msg: 错误消息
            operation: 操作名称
        """
        data = {"error_type": error_type, "error": error_msg}
        if operation:
            data["operation"] = operation

        self._forward_event("error", instance_id, data)

    def on_terminal_size_changed(self, instance_id: str, rows: int, cols: int) -> None:
        """
        处理终端尺寸变化事件

        Args:
            instance_id: 终端实例ID
            rows: 行数
            cols: 列数
        """
        self._forward_event("size_changed", instance_id, {"rows": rows, "cols": cols})

    def _forward_event(
        self, event_type: str, instance_id: str, data: Dict[str, Any]
    ) -> None:
        """
        转发事件到事件总线

        Args:
            event_type: 事件类型
            instance_id: 终端实例ID
            data: 事件数据
        """
        if self._event_bus:
            event_data = {
                "type": "terminal",
                "event_type": event_type,
                "instance_id": instance_id,
                "timestamp": datetime.now().isoformat(),
                **data,
            }

            try:
                self._event_bus.send_event("terminal_event", event_data)
                self._logger.debug(
                    f"Forwarded terminal event: {event_type} from {instance_id}"
                )
            except Exception as e:
                self._logger.error(f"Failed to forward terminal event: {e}")
        else:
            self._logger.warning("Event bus not set, cannot forward terminal event")


def init_event_bus_listener_adapter(event_bus=None) -> EventBusListenerAdapter:
    """
    初始化事件总线监听器适配器，设置事件总线

    Args:
        event_bus: 事件总线实例

    Returns:
        EventBusListenerAdapter实例
    """
    return EventBusListenerAdapter(event_bus)
