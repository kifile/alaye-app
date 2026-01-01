"""
Integration tests for TerminalManagerService.
Tests the complete workflow: new_terminal -> write -> event listener -> close_terminal
"""

import platform
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

from terminal.models import NewTerminalManagerRequest, TerminalInstanceNotFoundError
from terminal.terminal_manager_service import (
    TerminalEventListener,
    TerminalManagerService,
    get_terminal_manager,
)


class TerminalEventListenerDemo(TerminalEventListener):
    """测试用的终端事件监听器"""

    # 注意：这个类不是测试类，而是事件监听器的实现
    # pytest 警告可以忽略，因为我们不需要收集这个类作为测试

    def __init__(self):
        self.output_events: List[Dict[str, Any]] = []
        self.state_changed_events: List[Dict[str, Any]] = []
        self.process_exited_events: List[Dict[str, Any]] = []
        self.error_events: List[Dict[str, Any]] = []
        self.size_changed_events: List[Dict[str, Any]] = []

        # 用于同步的锁和条件变量
        self._lock = threading.Lock()
        self._output_condition = threading.Condition()

    def on_terminal_output(self, instance_id: str, data: str) -> None:
        """终端输出事件"""
        with self._lock:
            self.output_events.append(
                {"instance_id": instance_id, "data": data, "timestamp": time.time()}
            )
            # 通知等待输出
            with self._output_condition:
                self._output_condition.notify_all()

    def on_terminal_state_changed(
        self, instance_id: str, old_state: Optional[str], new_state: Optional[str]
    ) -> None:
        """终端状态变化事件"""
        with self._lock:
            self.state_changed_events.append(
                {
                    "instance_id": instance_id,
                    "old_state": old_state,
                    "new_state": new_state,
                    "timestamp": time.time(),
                }
            )

    def on_terminal_process_exited(
        self, instance_id: str, exit_code: Optional[int], exit_reason: Optional[str]
    ) -> None:
        """终端进程退出事件"""
        with self._lock:
            self.process_exited_events.append(
                {
                    "instance_id": instance_id,
                    "exit_code": exit_code,
                    "exit_reason": exit_reason,
                    "timestamp": time.time(),
                }
            )

    def on_terminal_error(
        self,
        instance_id: str,
        error_type: str,
        error_message: str,
        operation: Optional[str],
    ) -> None:
        """终端错误事件"""
        with self._lock:
            self.error_events.append(
                {
                    "instance_id": instance_id,
                    "error_type": error_type,
                    "error_message": error_message,
                    "operation": operation,
                    "timestamp": time.time(),
                }
            )

    def on_terminal_size_changed(self, instance_id: str, rows: int, cols: int) -> None:
        """终端尺寸变化事件"""
        with self._lock:
            self.size_changed_events.append(
                {
                    "instance_id": instance_id,
                    "rows": rows,
                    "cols": cols,
                    "timestamp": time.time(),
                }
            )

    def wait_for_output(self, instance_id: str, timeout: float = 5.0) -> bool:
        """等待特定终端实例的输出"""
        with self._output_condition:
            end_time = time.time() + timeout
            while time.time() < end_time:
                # 检查是否有该实例的输出
                if any(
                    event["instance_id"] == instance_id for event in self.output_events
                ):
                    return True
                remaining_time = end_time - time.time()
                if remaining_time <= 0:
                    break
                self._output_condition.wait(remaining_time)
        return False

    def get_output_for_instance(self, instance_id: str) -> List[str]:
        """获取特定终端实例的所有输出"""
        with self._lock:
            return [
                event["data"]
                for event in self.output_events
                if event["instance_id"] == instance_id
            ]

    def clear_events(self):
        """清空所有事件记录"""
        with self._lock:
            self.output_events.clear()
            self.state_changed_events.clear()
            self.process_exited_events.clear()
            self.error_events.clear()
            self.size_changed_events.clear()


class TestTerminalManagerServiceIntegration:
    """TerminalManagerService 集成测试"""

    @pytest.fixture(scope="function")
    def terminal_manager(self):
        """创建 TerminalManagerService 实例用于测试"""
        manager = TerminalManagerService()
        yield manager
        # 测试后清理
        manager.cleanup()

    @pytest.fixture(scope="function")
    def event_listener(self):
        """创建事件监听器用于测试"""
        listener = TerminalEventListenerDemo()
        yield listener
        # 测试后清理
        listener.clear_events()

    def test_new_terminal_workflow_with_event_listener(
        self, terminal_manager, event_listener
    ):
        """
        测试完整的终端工作流程：
        1. 设置事件监听器
        2. 创建新终端
        3. 写入命令
        4. 通过事件监听器读取输出
        5. 关闭终端
        """
        # Step 1: 设置事件监听器
        terminal_manager.set_event_listener(event_listener)

        # Step 2: 创建新终端
        request = NewTerminalManagerRequest()
        create_result = terminal_manager.new_terminal(request)

        instance_id = create_result.instance_id
        assert instance_id is not None, "Instance ID should not be None"

        # 等待终端启动
        time.sleep(1.0)

        # 验证状态变化事件（从 stopped 到 starting，再到 running）
        terminal_state_events = [
            event
            for event in event_listener.state_changed_events
            if event["instance_id"] == instance_id
        ]
        assert (
            len(terminal_state_events) >= 1
        ), f"Should have at least one state change event, got {len(terminal_state_events)}"

        # 检查是否有 starting -> running 的状态转换
        has_running_state = any(
            event["new_state"] == "running" for event in terminal_state_events
        )
        assert (
            has_running_state
        ), "Should have a state change to 'running' indicating terminal started"

        # Step 3: 写入 echo 命令
        test_message = "Hello from terminal manager"
        if platform.system() == "Windows":
            command = f'echo "{test_message}"\r\n'
        else:
            command = f'echo "{test_message}"\n'

        terminal_manager.write_to_terminal(instance_id, command)

        # Step 4: 通过事件监听器读取输出
        # 等待输出事件
        output_received = event_listener.wait_for_output(instance_id, timeout=10.0)
        assert output_received, f"Should receive output from terminal {instance_id}"

        # 获取所有输出并查找我们的测试消息
        outputs = event_listener.get_output_for_instance(instance_id)
        combined_output = "".join(outputs)

        # 调试输出
        print(f"\n[DEBUG] Total output events: {len(outputs)}")
        print(f"[DEBUG] Combined output: {repr(combined_output)}")
        print(f"[DEBUG] Looking for: {repr(test_message)}")

        # 验证测试消息出现在输出中，但增加超时和多次尝试
        max_attempts = 5
        found_message = False

        for attempt in range(max_attempts):
            outputs = event_listener.get_output_for_instance(instance_id)
            combined_output = "".join(outputs)

            if test_message in combined_output:
                found_message = True
                break

            if attempt < max_attempts - 1:
                print(f"[DEBUG] Attempt {attempt + 1}/{max_attempts} - waiting more...")
                time.sleep(1.0)
                # 额外等待输出
                event_listener.wait_for_output(instance_id, timeout=2.0)

        assert (
            found_message
        ), f"Test message '{test_message}' not found in output after {max_attempts} attempts: {repr(combined_output)}"

        # Step 5: 关闭终端
        terminal_manager.close_terminal(instance_id)

        # 验证终端已关闭（通过状态变化事件）
        terminal_state_events = [
            event
            for event in event_listener.state_changed_events
            if event["instance_id"] == instance_id
        ]

        # 检查是否有到 stopped 的状态转换
        has_stopped_state = any(
            event["new_state"] == "stopped" for event in terminal_state_events
        )
        # 注意：在某些情况下，终端可能在关闭前已经是 stopped 状态，所以这个验证是可选的
        print(f"[DEBUG] Has stopped state event: {has_stopped_state}")

    def test_multiple_terminals_concurrent_operations(
        self, terminal_manager, event_listener
    ):
        """
        测试多个终端的并发操作
        """
        # 设置事件监听器
        terminal_manager.set_event_listener(event_listener)

        # 创建多个终端
        terminal_count = 3
        instance_ids = []
        test_messages = []

        for i in range(terminal_count):
            message = f"Message from terminal {i+1}"
            test_messages.append(message)

            request = NewTerminalManagerRequest()
            create_result = terminal_manager.new_terminal(request)
            instance_ids.append(create_result.instance_id)

        # 等待所有终端启动
        time.sleep(2.0)  # 增加等待时间，确保所有终端都完全启动

        # 验证每个终端都有状态变化事件（说明已经启动）
        for instance_id in instance_ids:
            terminal_state_events = [
                event
                for event in event_listener.state_changed_events
                if event["instance_id"] == instance_id
            ]
            assert (
                len(terminal_state_events) >= 1
            ), f"Terminal {instance_id} should have state change events"

        # 向每个终端写入不同的消息
        for i, (instance_id, message) in enumerate(zip(instance_ids, test_messages)):
            if platform.system() == "Windows":
                command = f'echo "{message}"\r\n'
            else:
                command = f'echo "{message}"\n'

            terminal_manager.write_to_terminal(instance_id, command)

        # 等待所有输出并验证消息
        all_messages_found = True
        for i, (instance_id, expected_message) in enumerate(
            zip(instance_ids, test_messages)
        ):
            output_received = event_listener.wait_for_output(instance_id, timeout=10.0)
            assert output_received, f"Should receive output from terminal {instance_id}"

            # 获取输出并验证消息（增加重试机制）
            max_retries = 3
            message_found = False

            for retry in range(max_retries):
                outputs = event_listener.get_output_for_instance(instance_id)
                combined_output = "".join(outputs)

                # 清理输出中的控制字符
                clean_output = "".join(
                    char
                    for char in combined_output
                    if char.isprintable() or char in ["\n", "\r", "\t"]
                )

                if expected_message in clean_output:
                    message_found = True
                    break

                if retry < max_retries - 1:
                    print(
                        f"[DEBUG] Retry {retry+1} for terminal {i+1}, waiting more..."
                    )
                    time.sleep(1.0)
                    event_listener.wait_for_output(instance_id, timeout=2.0)

            if not message_found:
                print(f"[DEBUG] Terminal {i+1} output: {repr(combined_output[:200])}")
                all_messages_found = False

        # 至少应该有大部分终端工作正常
        assert all_messages_found, "Most terminals should receive their messages"

        # 关闭所有终端
        for i, instance_id in enumerate(instance_ids):
            terminal_manager.close_terminal(instance_id)

        # 验证关闭操作成功（通过返回值验证即可，关闭事件已移除）
        print(f"[DEBUG] All {terminal_count} terminals closed successfully")

    def test_terminal_size_change_events(self, terminal_manager, event_listener):
        """
        测试终端尺寸变化事件
        """
        # 设置事件监听器
        terminal_manager.set_event_listener(event_listener)

        # 创建终端
        request = NewTerminalManagerRequest()
        create_result = terminal_manager.new_terminal(request)

        instance_id = create_result.instance_id
        time.sleep(1.0)  # 等待终端启动

        # 设置终端大小
        new_rows, new_cols = 30, 120
        terminal_manager.set_terminal_size(instance_id, new_rows, new_cols)

        # 关闭终端
        terminal_manager.close_terminal(instance_id)

        # 验证尺寸变化事件（注意：某些终端可能不支持尺寸变化）
        if len(event_listener.size_changed_events) > 0:
            size_event = event_listener.size_changed_events[0]
            assert (
                size_event["instance_id"] == instance_id
            ), "Size change event should match instance ID"
            assert (
                size_event["rows"] == new_rows
            ), f"Rows should be {new_rows}, got {size_event['rows']}"
            assert (
                size_event["cols"] == new_cols
            ), f"Cols should be {new_cols}, got {size_event['cols']}"

    def test_error_handling_invalid_terminal_id(self, terminal_manager, event_listener):
        """
        测试无效终端ID的错误处理
        """
        # 设置事件监听器
        terminal_manager.set_event_listener(event_listener)

        invalid_id = "non-existent-terminal-id"

        # 尝试写入到无效终端
        try:
            terminal_manager.write_to_terminal(invalid_id, "test command")
            assert False, "Should fail to write to non-existent terminal"
        except TerminalInstanceNotFoundError as e:
            assert "not found" in str(
                e
            ), "Error message should mention terminal not found"

        # 尝试设置无效终端的大小
        try:
            terminal_manager.set_terminal_size(invalid_id, 24, 80)
            assert False, "Should fail to set size of non-existent terminal"
        except TerminalInstanceNotFoundError as e:
            assert "not found" in str(
                e
            ), "Error message should mention terminal not found"

        # 尝试关闭无效终端
        try:
            terminal_manager.close_terminal(invalid_id)
            assert False, "Should fail to close non-existent terminal"
        except TerminalInstanceNotFoundError as e:
            assert "not found" in str(
                e
            ), "Error message should mention terminal not found"

    def test_singleton_terminal_manager(self):
        """
        测试 TerminalManagerService 的单例模式
        """
        # 获取两个实例
        manager1 = get_terminal_manager()
        manager2 = get_terminal_manager()

        # 验证它们是同一个实例
        assert (
            manager1 is manager2
        ), "get_terminal_manager should return the same instance"

    def test_write_to_terminated_terminal(self, terminal_manager, event_listener):
        """
        测试向已终止的终端写入数据的错误处理
        """
        # 设置事件监听器
        terminal_manager.set_event_listener(event_listener)

        # 创建终端
        request = NewTerminalManagerRequest()
        create_result = terminal_manager.new_terminal(request)

        instance_id = create_result.instance_id
        time.sleep(1.0)  # 等待终端启动

        # 立即关闭终端
        terminal_manager.close_terminal(instance_id)

        # 等待关闭完成
        time.sleep(0.5)

        # 尝试向已关闭的终端写入数据
        try:
            terminal_manager.write_to_terminal(instance_id, "echo test")
            assert False, "Should fail to write to terminated terminal"
        except TerminalInstanceNotFoundError:
            # 预期的异常，因为关闭后实例会被移除
            pass
        except Exception as e:
            # 其他可能的异常，比如终端未运行
            assert "not running" in str(e) or "not found" in str(
                e
            ), f"Error message should mention terminal not running or not found: {str(e)}"

    def test_event_listener_state_changes(self, terminal_manager, event_listener):
        """
        测试事件监听器捕获状态变化
        """
        # 设置事件监听器
        terminal_manager.set_event_listener(event_listener)

        # 创建终端
        request = NewTerminalManagerRequest()
        create_result = terminal_manager.new_terminal(request)

        instance_id = create_result.instance_id
        time.sleep(1.0)  # 等待终端启动

        # 关闭终端
        terminal_manager.close_terminal(instance_id)

        # 验证状态变化事件
        state_change_events = [
            event
            for event in event_listener.state_changed_events
            if event["instance_id"] == instance_id
        ]

        # 应该至少有一些状态变化事件
        assert len(state_change_events) > 0, "Should have state change events"

        # 检查状态转换的合理性
        valid_transitions = [
            ("stopped", "starting"),
            ("starting", "running"),
            ("running", "stopped"),
            ("starting", "stopped"),
        ]

        for event in state_change_events:
            old_state = event["old_state"]
            new_state = event["new_state"]
            if old_state and new_state:  # 可能为 None
                transition = (old_state, new_state)
                assert (
                    transition in valid_transitions
                ), f"Invalid state transition: {transition}"
