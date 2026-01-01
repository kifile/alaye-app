#!/usr/bin/env python3
"""
测试 ProcessState 状态转换的脚本
"""

import platform
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from terminal.event_service import EventDrivenTerminalInstance
from terminal.events import EventType, ProcessState


def test_state_transitions():
    print("=== 测试 ProcessState 状态转换 ===")

    # Create terminal service
    terminal = EventDrivenTerminalInstance()

    # State tracking
    state_changes = []

    def universal_event_handler(event):
        """统一的事件处理器，根据事件类型进行不同处理"""
        if event.event_type == EventType.STATE_CHANGED:
            old_state = event.data.get("old_state", "unknown")
            new_state = event.data.get("new_state", "unknown")
            change = f"{old_state} -> {new_state}"
            state_changes.append(change)
            print(f"[状态变化] {change}")

        elif event.event_type == EventType.PROCESS_EXITED:
            exit_code = event.data.get("exit_code")
            reason = event.data.get("exit_reason")
            print(f"[进程退出] 退出码: {exit_code}, 原因: {reason}")

        elif event.event_type == EventType.OUTPUT:
            # 可以在这里处理输出事件（如果需要的话）
            pass

        elif event.event_type == EventType.ERROR:
            # 可以在这里处理错误事件（如果需要的话）
            error = event.data.get("error", "unknown")
            print(f"[错误] {error}")

    # 添加一个统一的事件监听器
    terminal.add_event_listener(universal_event_handler, "universal_handler")

    # Assert initial state
    print(f"初始状态: {terminal.state.value}")
    assert (
        terminal.state == ProcessState.STOPPED
    ), f"初始状态应该是 STOPPED，实际是: {terminal.state.value}"

    try:
        print("\n--- 启动进程 ---")
        # Spawn a process
        if platform.system() == "Windows":
            terminal.spawn("cmd")
        else:
            terminal.spawn("bash")

        # Assert state after spawn should be STARTING
        print(f"启动后状态: {terminal.state.value}")
        assert (
            terminal.state == ProcessState.STARTING
        ), f"启动后状态应该是 STARTING，实际是: {terminal.state.value}"

        # Wait for first output to transition to RUNNING
        print("等待第一个输出以转为 RUNNING 状态...")
        max_wait = 5  # Wait up to 5 seconds
        for i in range(max_wait * 10):  # Check every 0.1 second
            if terminal.state == ProcessState.RUNNING:
                break
            time.sleep(0.1)

        # Assert that we reached RUNNING state
        print(f"等待后状态: {terminal.state.value}")
        assert (
            terminal.state == ProcessState.RUNNING
        ), f"应该转为 RUNNING，实际是: {terminal.state.value}"

        # Check state transitions
        expected_transitions = ["stopped -> starting", "starting -> running"]

        print(f"\n期望的状态转换: {expected_transitions}")
        print(f"实际的状态转换: {state_changes}")

        # Assert that all expected transitions occurred
        for transition in expected_transitions:
            assert transition in state_changes, f"缺少状态转换: {transition}"

        # Test writing commands (only if running)
        print("\n--- 发送命令 ---")
        assert terminal.is_running, "进程应该处于 RUNNING 状态"
        terminal.write("echo 'State test successful'\n")
        time.sleep(1)

        print(f"发送命令后状态: {terminal.state.value}")
        assert (
            terminal.state == ProcessState.RUNNING
        ), "发送命令后状态应该仍然是 RUNNING"

        # Test termination
        print("\n--- 终止进程 ---")
        terminal.terminate()

        # Assert final state is STOPPED
        print(f"终止后状态: {terminal.state.value}")
        assert (
            terminal.state == ProcessState.STOPPED
        ), f"终止后状态应该是 STOPPED，实际是: {terminal.state.value}"

        # Check final transitions
        final_transitions = ["running -> stopping", "stopping -> stopped"]

        # Assert that all final transitions occurred
        for transition in final_transitions:
            assert transition in state_changes, f"缺少最终状态转换: {transition}"

        # Summary
        print(f"\n=== 测试总结 ===")
        print(f"初始状态正确: {terminal.state == ProcessState.STOPPED}")
        print(f"所有状态转换: {state_changes}")
        print("✅ 所有测试断言都通过了！")

    except Exception as e:
        print(f"错误: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Ensure cleanup
        if terminal.is_running:
            terminal.terminate()


def test_short_lived_process():
    print("\n=== 测试短生命周期进程状态转换 ===")

    terminal = EventDrivenTerminalInstance()

    state_changes = []

    def state_change_handler(event):
        """专注于状态变化的事件处理器"""
        if event.event_type == EventType.STATE_CHANGED:
            old_state = event.data.get("old_state", "unknown")
            new_state = event.data.get("new_state", "unknown")
            change = f"{old_state} -> {new_state}"
            state_changes.append(change)
            print(f"[状态变化] {change}")

    terminal.add_event_listener(state_change_handler, "state_handler")

    try:
        # Assert initial state
        print(f"初始状态: {terminal.state.value}")
        assert (
            terminal.state == ProcessState.STOPPED
        ), f"短生命周期进程初始状态应该是 STOPPED，实际是: {terminal.state.value}"

        # Spawn a short-lived command
        print("启动短生命周期进程 (echo test)")
        if platform.system() == "Windows":
            # 在 Windows 上使用 cmd /c 来执行 echo 命令
            terminal.spawn("cmd", "/c", "echo", "test")
        else:
            # 在 Unix 系统上直接使用 echo
            terminal.spawn("echo", "test")

        # Assert state after spawn is STARTING
        assert (
            terminal.state == ProcessState.STARTING
        ), "短生命周期进程启动后应该是 STARTING 状态"

        # Wait for process to complete
        print("等待进程完成...")
        # Wait longer for short-lived command and check if process naturally exits
        max_wait_seconds = 10
        process_exited = False
        for i in range(max_wait_seconds * 10):  # Check every 0.1 second
            if terminal.state == ProcessState.STOPPED:
                print(f"进程已在 {i/10:.1f} 秒后自然退出")
                process_exited = True
                break
            time.sleep(0.1)

        # Assert that process naturally exited
        print(f"最终状态: {terminal.state.value}")
        assert (
            terminal.state == ProcessState.STOPPED
        ), f"短生命周期进程最终状态应该是 STOPPED，实际是: {terminal.state.value}"
        assert process_exited, "短生命周期进程应该在10秒内自然退出"

        print(f"状态转换历史: {state_changes}")

        # Should have transitions: stopped -> starting -> running -> stopped
        expected_all_transitions = [
            "stopped -> starting",
            "starting -> running",
            "running -> stopping",
            "stopping -> stopped",
        ]

        # Assert complete lifecycle transitions
        for transition in expected_all_transitions:
            assert (
                transition in state_changes
            ), f"短生命周期进程缺少状态转换: {transition}"

        has_starting_transitions = (
            "stopped -> starting" in state_changes
            and "starting -> running" in state_changes
        )
        has_ending_transitions = (
            "running -> stopping" in state_changes
            and "stopping -> stopped" in state_changes
        )

        print(f"包含启动转换: {has_starting_transitions}")
        print(f"包含结束转换: {has_ending_transitions}")
        print(f"完整生命周期: {has_starting_transitions and has_ending_transitions}")
        print("✅ 短生命周期进程测试断言都通过了！")

    except Exception as e:
        print(f"错误: {e}")

    finally:
        if terminal.is_running:
            terminal.terminate()


if __name__ == "__main__":
    test_state_transitions()
    test_short_lived_process()
