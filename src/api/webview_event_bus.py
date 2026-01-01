"""
事件总线模块 - 用于后端向前端发送自定义事件
"""

import json
import logging
import time
from typing import Any, Dict, Optional

# 配置事件日志记录器
event_logger = logging.getLogger("event_bus")
event_logger.setLevel(logging.INFO)


class EventBus:
    """事件总线类 - 负责向前端发送自定义事件"""

    def __init__(self):
        """初始化事件总线"""
        self._webview_window = (
            None  # pywebview窗口实例 (私有属性，避免被JavaScript桥接器访问)
        )
        self.event_logger = event_logger

    def set_webview_window(self, window):
        """
        设置pywebview窗口实例

        Args:
            window: pywebview窗口实例
        """
        self._webview_window = window
        self.event_logger.info("EventBus: WebView window instance set")

    def _create_event_data(
        self, event_type: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建事件数据结构

        Args:
            event_type: 事件类型
            data: 事件数据（可选）

        Returns:
            事件数据字典
        """
        return {
            "event_type": event_type,
            "data": data or {},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        }

    def _create_event_script(self, event_data: Dict[str, Any]) -> str:
        """
        创建触发前端事件的JavaScript代码

        Args:
            event_data: 事件数据

        Returns:
            JavaScript代码字符串
        """
        # 将事件数据转换为JSON字符串
        event_json = json.dumps(event_data)
        event_type = event_data.get("event_type", "unknown_event")

        # 创建触发自定义事件的JavaScript代码
        event_script = f"""
        (function() {{
            try {{
                const eventData = {event_json};
                const event = new CustomEvent('{event_type}', {{ detail: eventData }});
                window.dispatchEvent(event);
                console.log('Backend event sent:', eventData);
            }} catch (error) {{
                console.error('Failed to send backend event:', error);
            }}
        }})();
        """

        return event_script

    def send_event(
        self, event_type: str, data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送自定义事件到前端

        Args:
            event_type: 事件类型
            data: 事件数据（可选）

        Returns:
            发送是否成功
        """
        if not self._webview_window:
            self.event_logger.error(
                "EventBus: WebView window not set, cannot send event"
            )
            return False

        try:
            # 创建事件数据
            event_data = self._create_event_data(event_type, data)

            # 创建JavaScript代码
            event_script = self._create_event_script(event_data)

            # 使用evaluate_js执行JavaScript代码
            self._webview_window.evaluate_js(event_script)

            # 记录日志
            self.event_logger.info(f"EventBus: Event sent - {event_type}: {data or {}}")

            return True

        except Exception as e:
            # 记录错误日志
            self.event_logger.error(f"EventBus: Failed to send event - {str(e)}")
            return False


# 创建全局事件总线实例
event_bus = EventBus()


def get_event_bus() -> EventBus:
    """
    获取全局事件总线实例

    Returns:
        EventBus实例
    """
    return event_bus


def init_event_bus(window):
    """
    初始化事件总线，设置pywebview窗口实例

    Args:
        window: pywebview窗口实例
    """
    event_bus.set_webview_window(window)
