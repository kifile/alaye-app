"""
FastAPI 模式下的事件总线适配器
通过 WebSocket 发送事件，替代 PyWebView 模式下的 evaluate_js
"""

import json
import logging
import time
from typing import Any, Dict, Optional

from .fastapi_adapter import manager

# 配置 FastAPI 事件专用日志记录器
fastapi_event_logger = logging.getLogger("fastapi_event_bus")
fastapi_event_logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)


class FastAPIEventBus:
    """
    FastAPI 模式下的事件总线类
    负责通过 WebSocket 向前端发送事件
    """

    def __init__(self):
        """初始化 FastAPI 事件总线"""
        self.event_logger = fastapi_event_logger

    def send_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        发送事件到所有连接的 WebSocket 客户端

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        start_time = time.time()

        if not manager.active_connections:
            self.event_logger.debug(
                f"No active WebSocket connections, skipping event: {event_type}"
            )
            return

        # 记录事件开始发送
        self.event_logger.info(f"Sending event: {event_type}")
        self.event_logger.debug(f"Event data: {data}")

        # 构造事件消息
        event_message = {
            "event_type": event_type,
            "data": data,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        }

        # 转换为 JSON 字符串
        message_json = json.dumps(event_message, ensure_ascii=False)

        # 通过 WebSocket 广播事件
        try:
            import asyncio

            # 如果当前在事件循环中，创建任务
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(manager.broadcast(message_json))
            except RuntimeError:
                # 如果不在事件循环中，在新线程中运行
                import threading

                def broadcast_async():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    new_loop.run_until_complete(manager.broadcast(message_json))
                    new_loop.close()

                thread = threading.Thread(target=broadcast_async, daemon=True)
                thread.start()

            execution_time = time.time() - start_time
            self.event_logger.info(
                f"Event sent via WebSocket: {event_type} (connections={len(manager.active_connections)}, duration={execution_time:.3f}s)"
            )
        except Exception as e:
            execution_time = time.time() - start_time
            self.event_logger.error(
                f"Failed to send event via WebSocket: {event_type} (duration={execution_time:.3f}s, error={str(e)})"
            )


# 全局 FastAPI 事件总线实例
_fastapi_event_bus: Optional[FastAPIEventBus] = None


def get_fastapi_event_bus() -> FastAPIEventBus:
    """
    获取 FastAPI 事件总线实例（单例模式）

    Returns:
        FastAPIEventBus 实例
    """
    global _fastapi_event_bus
    if _fastapi_event_bus is None:
        _fastapi_event_bus = FastAPIEventBus()
    return _fastapi_event_bus
