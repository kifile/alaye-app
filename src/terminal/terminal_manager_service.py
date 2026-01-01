"""
Terminal Manager Service

终端管理服务，负责维护多个终端实例，通过 EventDrivenTerminalService 处理底层逻辑。
基于参考实现适配 pywebview 架构。
"""

import logging
import os
import threading
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .event_service import EventDrivenTerminalInstance
from .models import (
    NewTerminalManagerRequest,
    TerminalDTO,
    TerminalInstanceAlreadyExistsError,
    TerminalInstanceNotFoundError,
    TerminalNotRunningError,
)


class TerminalEventListener(ABC):
    """终端事件监听器抽象基类"""

    @abstractmethod
    def on_terminal_output(self, instance_id: str, data: str) -> None:
        """处理终端输出事件"""

    @abstractmethod
    def on_terminal_state_changed(
        self, instance_id: str, old_state: str, new_state: str
    ) -> None:
        """处理终端状态变化事件"""

    @abstractmethod
    def on_terminal_process_exited(
        self, instance_id: str, exit_code: Optional[int], exit_reason: str
    ) -> None:
        """处理终端进程退出事件"""

    @abstractmethod
    def on_terminal_error(
        self,
        instance_id: str,
        error_type: str,
        error_msg: str,
        operation: Optional[str],
    ) -> None:
        """处理终端错误事件"""

    @abstractmethod
    def on_terminal_size_changed(self, instance_id: str, rows: int, cols: int) -> None:
        """处理终端尺寸变化事件"""


# 全局终端管理服务实例（单例）
_terminal_manager = None
_terminal_manager_lock = threading.Lock()


def get_terminal_manager():
    """
    获取全局终端管理服务实例（单例模式）

    Returns:
        TerminalManagerService实例
    """
    global _terminal_manager
    if _terminal_manager is None:
        with _terminal_manager_lock:
            if _terminal_manager is None:
                _terminal_manager = TerminalManagerService()
    return _terminal_manager


class TerminalManagerService:
    """终端管理服务

    负责维护终端实例对象，在响应调用时通过 event_service.py 完成逻辑处理。
    不直接依赖 event_bus，通过事件监听器模式实现解耦。
    """

    def __init__(self):
        """
        初始化终端管理服务
        """
        self._instances: Dict[str, EventDrivenTerminalInstance] = {}
        self._lock = threading.RLock()
        self._event_listener: Optional[TerminalEventListener] = (
            None  # 事件监听器的默认值
        )

        # 日志配置
        self._logger = logging.getLogger(__name__)

        self._logger.info("TerminalManagerService initialized")

    def _get_default_shell(self) -> str:
        """获取系统默认 shell"""
        import platform

        if platform.system() == "Windows":
            # Windows 系统的常见 shell，按优先级排序
            candidates = ["powershell", "pwsh", "cmd"]
            import shutil

            for candidate in candidates:
                if shutil.which(candidate):
                    return candidate
            return "cmd"
        else:
            # Unix-like 系统的常见 shell
            candidates = ["bash", "zsh", "sh"]
            import shutil

            for candidate in candidates:
                if shutil.which(candidate):
                    return candidate
            return "sh"

    def _create_terminal_service(
        self,
        instance_id: str,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EventDrivenTerminalInstance:
        """创建新的终端实例"""
        return EventDrivenTerminalInstance(
            instance_id=instance_id,
            command=command,
            args=args,
            metadata=metadata,
        )

    def new_terminal(self, request: NewTerminalManagerRequest) -> TerminalDTO:
        """
        创建新的终端实例

        Args:
            request: 经过验证的新建终端请求模型

        Returns:
            终端数据传输对象，包含实例ID和状态信息

        Raises:
            TerminalInstanceAlreadyExistsError: 当指定的终端ID已存在时
            TerminalOperationError: 当终端创建过程中出现错误时
        """
        # 生成或使用指定的实例ID
        if request.terminal_id:
            instance_id = request.terminal_id
            with self._lock:
                if instance_id in self._instances:
                    raise TerminalInstanceAlreadyExistsError(instance_id)
        else:
            instance_id = str(uuid.uuid4())

        # 使用默认命令如果没有指定
        command = request.command
        args = request.args
        if not command:
            command = self._get_default_shell()
            args = []
            self._logger.info(f"Using default shell: {command}")

        # 创建终端实例
        instance = self._create_terminal_service(
            instance_id=instance_id,
            command=command,
            args=args,
            metadata=request.metadata,
        )

        # 设置事件监听器
        self._setup_event_listeners(instance)

        # 保存实例
        with self._lock:
            self._instances[instance_id] = instance

        # 启动终端进程
        spawn_kwargs = {}
        if request.work_dir:
            spawn_kwargs["cwd"] = request.work_dir
        if request.env:
            spawn_kwargs["env"] = {**os.environ, **request.env}

        instance.spawn(command, *args, **spawn_kwargs)

        # 设置终端大小（如果指定）
        if request.size:
            try:
                instance.set_size(request.size.rows, request.size.cols)
            except Exception as e:
                self._logger.warning(f"Failed to set terminal size: {e}")

        self._logger.info(f"Created new terminal instance: {instance_id}")

        return TerminalDTO(
            instance_id=instance_id,
            status=instance.status.value,
        )

    def set_event_listener(self, event_listener: TerminalEventListener) -> None:
        """
        设置全局事件监听器

        Args:
            event_listener: 终端事件监听器实例
        """
        self._event_listener = event_listener

    def _setup_event_listeners(self, instance: EventDrivenTerminalInstance) -> None:
        """为终端实例设置事件监听器"""

        def on_terminal_event(event):
            """统一的终端事件处理器 - 转发底层PTY事件到外部监听器"""
            from .events import EventType

            # EventDrivenTerminalInstance 内部已经处理了底层PTY事件，
            # 这里将事件转发到外部事件监听器，由监听器决定如何处理
            # 处理输出事件
            if event.event_type == EventType.OUTPUT:
                if self._event_listener:
                    self._event_listener.on_terminal_output(
                        instance.id, event.data.get("text", "")
                    )

            # 处理状态变化事件
            elif event.event_type == EventType.STATE_CHANGED:
                old_state = event.data.get("old_state")
                new_state = event.data.get("new_state")

                # 发送状态变化事件
                if self._event_listener:
                    self._event_listener.on_terminal_state_changed(
                        instance.id, old_state, new_state
                    )

            # 处理进程退出事件
            elif event.event_type == EventType.PROCESS_EXITED:
                exit_code = event.data.get("exit_code")
                exit_reason = event.data.get("exit_reason")

                if self._event_listener:
                    self._event_listener.on_terminal_process_exited(
                        instance.id, exit_code, exit_reason
                    )

            # 处理错误事件
            elif event.event_type == EventType.ERROR:
                error_msg = event.data.get("error", "Unknown error")

                if self._event_listener:
                    self._event_listener.on_terminal_error(
                        instance.id,
                        event.data.get("error_type", "unknown"),
                        error_msg,
                        event.data.get("operation"),
                    )

            # 处理尺寸变化事件
            elif event.event_type == EventType.SIZE_CHANGED:
                rows = event.data.get("rows")
                cols = event.data.get("cols")

                if self._event_listener:
                    self._event_listener.on_terminal_size_changed(
                        instance.id, rows, cols
                    )

        # 添加统一的事件监听器并保存引用
        instance.add_event_listener(on_terminal_event)
        instance._event_listener = on_terminal_event

    def close_terminal(self, instance_id: str) -> None:
        """
        关闭终端实例

        Args:
            instance_id: 终端实例ID

        Raises:
            TerminalInstanceNotFoundError: 当终端实例不存在时
        """
        with self._lock:
            instance = self._instances.get(instance_id)
            if not instance:
                raise TerminalInstanceNotFoundError(instance_id)

        # 移除事件监听器防止内存泄漏
        if instance._event_listener:
            try:
                instance.remove_event_listener(instance._event_listener)
            except Exception as e:
                self._logger.warning(
                    f"Failed to remove event listener for terminal '{instance_id}': {e}"
                )

        # 终止终端进程
        if instance.is_running:
            instance.terminate()

        # 从实例列表中移除
        with self._lock:
            if instance_id in self._instances:
                del self._instances[instance_id]

        self._logger.info(f"Closed terminal instance: {instance_id}")

    def write_to_terminal(self, instance_id: str, data: str) -> None:
        """
        向终端写入数据

        Args:
            instance_id: 终端实例ID
            data: 要写入的数据

        Raises:
            TerminalInstanceNotFoundError: 当终端实例不存在时
            TerminalNotRunningError: 当终端未运行时
        """
        with self._lock:
            instance = self._instances.get(instance_id)
            if not instance:
                raise TerminalInstanceNotFoundError(instance_id)

        # 检查终端是否在运行
        if not instance.is_running:
            raise TerminalNotRunningError(instance_id)

        # 写入数据
        instance.write(data)

    def set_terminal_size(self, instance_id: str, rows: int, cols: int) -> None:
        """
        设置终端大小

        Args:
            instance_id: 终端实例ID
            rows: 行数
            cols: 列数

        Raises:
            TerminalInstanceNotFoundError: 当终端实例不存在时
            TerminalNotRunningError: 当终端未运行时
        """
        with self._lock:
            instance = self._instances.get(instance_id)
            if not instance:
                raise TerminalInstanceNotFoundError(instance_id)

        # 检查终端是否在运行
        if not instance.is_running:
            raise TerminalNotRunningError(instance_id)

        # 设置大小 - EventDrivenTerminalInstance 内部会发送 size_changed 事件
        instance.set_size(rows, cols)

    def cleanup(self) -> None:
        """清理所有终端实例"""
        self._logger.info("Cleaning up all terminal instances...")

        with self._lock:
            instance_ids = list(self._instances.keys())

        for instance_id in instance_ids:
            try:
                self.close_terminal(instance_id)
            except Exception as e:
                self._logger.error(
                    f"Failed to close terminal '{instance_id}' during cleanup: {e}"
                )

        self._logger.info("TerminalManagerService cleanup completed")
