"""
异步执行器 - 使用后台线程的事件循环
连接到 main.py 中创建的后台事件循环
"""

import asyncio
import threading
from functools import wraps
from typing import Any, Callable, Coroutine, Dict, TypeVar

from .api_models import ApiResponse

F = TypeVar("F", bound=Callable[..., Dict[str, Any]])


def api_async(request_model: type, return_type_check: bool = True):
    """
    异步 API 装饰器 - 在后台事件循环中执行异步方法
    只处理同步到异步的转换，不包含日志记录功能

    Args:
        request_model: Pydantic 请求模型类，用于验证输入数据
        return_type_check: 是否强制检查返回类型为 ApiResponse，默认为 True

    Usage:
        @api_async(HelloWorldRequest)
        async def hello_world(self, input_data: HelloWorldRequest) -> ApiResponse[str]:
            # 这里可以使用 await
            result = await some_async_operation()
            return ApiResponse.success_response(result)
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(self, input_data: Dict[str, Any], *args, **kwargs):
            # 验证输入数据
            validated_input = request_model.model_validate(input_data)

            # 同步执行异步方法
            result = background_thread_async_executor.run_async_sync(
                func(self, validated_input, *args, **kwargs)
            )

            # 处理返回结果
            if isinstance(result, ApiResponse):
                return result.model_dump()
            else:
                if return_type_check:
                    raise TypeError(
                        f"Method {func.__name__} must return ApiResponse instance, got {type(result).__name__} instead"
                    )
                return (
                    result
                    if isinstance(result, dict)
                    else {"data": result, "success": True}
                )

        return wrapper

    return decorator


class BackgroundThreadAsyncExecutor:
    """后台线程异步执行器 - 使用后台线程的事件循环"""

    def __init__(self):
        self.loop = None
        self._init_lock = threading.Lock()
        self._stop_event = threading.Event()

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """设置后台线程的事件循环"""
        with self._init_lock:
            self.loop = loop

    def get_loop(self):
        """获取后台线程的事件循环"""
        return self.loop

    def stop_loop(self):
        """停止后台事件循环"""
        with self._init_lock:
            if self.loop and self.loop.is_running():
                # 在事件循环的线程中调用 stop
                self.loop.call_soon_threadsafe(self.loop.stop)
        self._stop_event.set()

    def wait_for_stop(self, timeout: float = 5.0):
        """等待事件循环线程停止"""
        return self._stop_event.wait(timeout=timeout)

    def run_async_sync(self, coro: Coroutine, timeout: float = 30.0) -> Any:
        """
        同步方式运行异步协程

        Args:
            coro: 要执行的异步协程
            timeout: 超时时间（秒）

        Returns:
            协程的执行结果
        """
        if self.loop is None:
            # 如果还没有设置事件循环，尝试在当前线程创建
            try:
                self.loop = asyncio.get_running_loop()
            except RuntimeError:
                raise RuntimeError(
                    "No event loop available. Please call set_loop() first."
                )

        if self.loop.is_running():
            # 使用 run_coroutine_threadsafe 跨线程调度协程
            future = asyncio.run_coroutine_threadsafe(coro, self.loop)
            return future.result(timeout=timeout)
        else:
            raise RuntimeError("Event loop is not running")


# 全局实例
background_thread_async_executor = BackgroundThreadAsyncExecutor()
