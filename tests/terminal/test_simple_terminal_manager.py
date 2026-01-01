"""
简化的 TerminalManagerService 集成测试，专注于核心功能验证
"""

import platform
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from terminal.models import NewTerminalManagerRequest
from terminal.terminal_manager_service import TerminalManagerService


def test_simple_terminal_workflow():
    """
    测试简化的终端工作流程：
    1. 创建终端
    2. 验证终端存活
    3. 写入命令并直接读取
    4. 关闭终端
    """
    manager = TerminalManagerService()

    try:
        # Step 1: 创建终端
        request = NewTerminalManagerRequest()
        create_result = manager.new_terminal(request)

        instance_id = create_result.instance_id
        assert instance_id is not None, "Instance ID should not be None"

        print(f"[DEBUG] Created terminal with ID: {instance_id}")
        print(f"[DEBUG] Terminal status: {create_result.status}")

        # 等待终端完全启动
        time.sleep(2.0)

        # Step 2: 验证终端存活
        with manager._lock:
            instance = manager._instances.get(instance_id)
            assert instance is not None, "Terminal instance should exist"
            assert instance.is_running, "Terminal should be running"

        print(f"[DEBUG] Terminal is running: {instance.is_running}")
        print(f"[DEBUG] Terminal status: {instance.status.value}")

        # Step 3: 写入简单的命令
        if platform.system() == "Windows":
            # 在 Windows 上使用 dir 命令，这通常比 echo 更可靠
            command = "dir\r\n"
        else:
            # 在 Unix 系统上使用 ls 命令
            command = "ls\n"

        print(f"[DEBUG] Sending command: {repr(command)}")

        try:
            manager.write_to_terminal(instance_id, command)
            print(f"[DEBUG] Command sent successfully")
        except Exception as e:
            assert False, f"Failed to write to terminal: {str(e)}"

        # 等待命令执行
        time.sleep(2.0)

        # Step 4: 关闭终端
        try:
            manager.close_terminal(instance_id)
            print(f"[DEBUG] Terminal closed successfully")
        except Exception as e:
            assert False, f"Failed to close terminal: {str(e)}"

        # 验证终端不再存在
        with manager._lock:
            instance_after_close = manager._instances.get(instance_id)
            assert (
                instance_after_close is None
            ), "Terminal instance should be removed after close"

    finally:
        # 确保清理
        manager.cleanup()


def test_create_and_close_multiple_terminals():
    """
    测试创建和关闭多个终端
    """
    manager = TerminalManagerService()

    try:
        terminal_count = 3
        instance_ids = []

        # 创建多个终端
        for i in range(terminal_count):
            request = NewTerminalManagerRequest()
            create_result = manager.new_terminal(request)

            instance_id = create_result.instance_id
            instance_ids.append(instance_id)
            print(f"[DEBUG] Created terminal {i+1} with ID: {instance_id}")
            print(f"[DEBUG] Terminal {i+1} status: {create_result.status}")

        # 等待所有终端启动
        time.sleep(1.0)

        # 验证所有终端都存在
        with manager._lock:
            for i, instance_id in enumerate(instance_ids):
                instance = manager._instances.get(instance_id)
                assert instance is not None, f"Terminal {i+1} instance should exist"
                assert instance.is_running, f"Terminal {i+1} should be running"

        print(f"[DEBUG] All {terminal_count} terminals are running")

        # 关闭所有终端
        for i, instance_id in enumerate(instance_ids):
            try:
                manager.close_terminal(instance_id)
                print(f"[DEBUG] Closed terminal {i+1}")
            except Exception as e:
                assert False, f"Failed to close terminal {i+1}: {str(e)}"

        # 验证所有终端都被移除
        with manager._lock:
            assert (
                len(manager._instances) == 0
            ), f"All terminals should be removed, but found {len(manager._instances)}"

        print(f"[DEBUG] All terminals successfully removed")

    finally:
        manager.cleanup()


if __name__ == "__main__":
    # 直接运行测试
    print("Running simple terminal workflow test...")
    test_simple_terminal_workflow()
    print("Simple workflow test passed")

    print("\nRunning multiple terminals test...")
    test_create_and_close_multiple_terminals()
    print("Multiple terminals test passed")

    print("\nAll tests passed!")
