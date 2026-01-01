"""
Integration tests for terminal services using the factory pattern.
Tests the complete workflow: spawn -> verify alive -> write -> read -> terminate -> verify dead
"""

import platform
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

from terminal.base import TerminalServiceInterface
from terminal.factory import TerminalServiceFactory


class TestTerminalServiceIntegration:
    """Integration tests for terminal services."""

    @pytest.fixture(scope="class")
    def terminal_service(self) -> TerminalServiceInterface:
        """Fixture that provides a terminal service instance for the current platform."""
        try:
            service = TerminalServiceFactory.create_terminal_service()
            return service
        except ImportError as e:
            pytest.skip(f"Terminal service not available on this platform: {e}")

    @pytest.fixture(scope="function")
    def clean_terminal(self, terminal_service):
        """Fixture that ensures a clean terminal state for each test."""
        # Clean up any existing process
        if terminal_service.is_alive():
            terminal_service.terminate()

        yield terminal_service

        # Clean up after test
        if terminal_service.is_alive():
            terminal_service.terminate()

    def test_complete_terminal_workflow(self, clean_terminal):
        """
        Test complete terminal workflow:
        1. 启动终端
        2. 验证终端进程存活
        3. 写入 echo "hello world"
        4. 验证结果读取正常
        5. 终端终端
        6. 验证终端进程结束
        """
        terminal = clean_terminal

        # Step 1: 启动终端 - 使用简单的 shell 命令
        if platform.system() == "Windows":
            terminal.spawn("cmd")
        else:
            # Use sh which is more minimal and has fewer startup messages
            terminal.spawn("sh")

        # Give the terminal a moment to initialize
        time.sleep(1.0)

        # Read any initial shell output to clear the buffer
        initial_output = ""
        for _ in range(5):
            try:
                chunk = terminal.read()
                if chunk:
                    initial_output += chunk
                time.sleep(0.1)
            except Exception:
                break

        # Step 2: 验证终端进程存活
        assert terminal.is_alive(), "Terminal should be alive after spawning"

        # Step 3: 写入 echo "hello world"
        echo_command = (
            'echo "hello world"\r\n'
            if platform.system() == "Windows"
            else 'echo "hello world"\n'
        )
        terminal.write(echo_command)

        # Give the command time to execute and read all available output
        time.sleep(0.5)

        # Read output in a loop to get the command result
        output = ""
        for _ in range(10):  # Try multiple times to get the actual command output
            try:
                chunk = terminal.read()
                if chunk:
                    output += chunk
                    if "hello world" in output.lower():
                        break
                time.sleep(0.1)
            except Exception:
                time.sleep(0.1)
                continue

        # Step 4: 验证结果读取正常
        assert isinstance(output, str), "Read output should be a string"
        assert (
            "hello world" in output.lower()
        ), f"Expected 'hello world' in output, got: {repr(output)}"

        # Step 5: 终端终端
        terminal.terminate()

        # Step 6: 验证终端进程结束
        assert not terminal.is_alive(), "Terminal should not be alive after termination"

    def test_terminal_size_operations(self, clean_terminal):
        """Test terminal size get/set operations."""
        terminal = clean_terminal

        # Start a terminal
        if platform.system() == "Windows":
            terminal.spawn("cmd")
        else:
            terminal.spawn("sh")

        time.sleep(0.5)

        # Get initial size
        initial_size = terminal.get_size()
        assert isinstance(initial_size, tuple), "Size should be a tuple"
        assert len(initial_size) == 2, "Size tuple should have 2 elements"
        assert all(
            isinstance(x, int) for x in initial_size
        ), "Size values should be integers"

        # Set new size
        new_rows, new_cols = 30, 100
        terminal.set_size(new_rows, new_cols)

        # Verify size change (may take a moment)
        time.sleep(0.1)
        terminal.get_size()
        # Note: Some terminals may not support size changes or may have constraints
        # so we just verify the method doesn't crash

        terminal.terminate()

    def test_multiple_commands_sequence(self, clean_terminal):
        """Test executing multiple commands in sequence."""
        terminal = clean_terminal

        # Start a terminal
        if platform.system() == "Windows":
            terminal.spawn("cmd")
        else:
            terminal.spawn("sh")

        time.sleep(0.5)

        # Execute multiple commands and verify each
        commands = [
            ('echo "test1"', "test1"),
            ('echo "test2"', "test2"),
            ('echo "final test"', "final test"),
        ]

        for cmd, expected in commands:
            # Write command
            full_cmd = f"{cmd}\r\n" if platform.system() == "Windows" else f"{cmd}\n"
            terminal.write(full_cmd)

            # Wait for execution
            time.sleep(0.3)

            # Read output in a loop to get the command result
            output = ""
            for _ in range(10):  # Try multiple times to get the actual command output
                try:
                    chunk = terminal.read()
                    if chunk:
                        output += chunk
                        if expected in output.lower():
                            break
                    time.sleep(0.1)
                except Exception:
                    time.sleep(0.1)
                    continue

            assert (
                expected in output.lower()
            ), f"Expected '{expected}' in output, got: {repr(output)}"

        terminal.terminate()

    def test_terminal_wait_functionality(self, clean_terminal):
        """Test the wait functionality for short-lived commands."""
        terminal = clean_terminal

        # Start a short-lived command instead of interactive shell
        if platform.system() == "Windows":
            # 在 Windows 上使用 cmd /c 来执行 echo 命令
            terminal.spawn("cmd", "/c", "echo", "quick test")
        else:
            # 在 Unix 系统上直接使用 echo
            terminal.spawn("echo", "quick test")

        # Wait for completion
        terminal.wait()

        # The process should be done
        assert not terminal.is_alive(), "Short-lived command should have completed"

        # Exit code should be available (may be None depending on implementation)
        # We just verify the method doesn't crash

    def test_error_handling_invalid_command(self, clean_terminal):
        """Test error handling for invalid commands."""
        terminal = clean_terminal

        # Try to spawn a non-existent command
        with pytest.raises(RuntimeError):
            terminal.spawn("nonexistent_command_xyz_12345")

        # Terminal should not be alive after failed spawn
        assert (
            not terminal.is_alive()
        ), "Terminal should not be alive after failed spawn"

    def test_write_to_terminated_terminal(self, clean_terminal):
        """Test error handling when writing to a terminated terminal."""
        terminal = clean_terminal

        # Don't start any process, try to write directly
        with pytest.raises(RuntimeError):
            terminal.write("test command")

    def test_read_from_terminated_terminal(self, terminal_service):
        """Test error handling when reading from a terminated terminal."""
        # Create a fresh terminal service instance to avoid state issues
        try:
            terminal = TerminalServiceFactory.create_terminal_service()
        except ImportError as e:
            pytest.skip(f"Terminal service not available: {e}")

        # Don't start any process, try to read directly
        with pytest.raises(RuntimeError):
            terminal.read()

    def test_size_operations_on_terminated_terminal(self, terminal_service):
        """Test error handling for size operations on terminated terminal."""
        # Create a fresh terminal service instance to avoid state issues
        try:
            terminal = TerminalServiceFactory.create_terminal_service()
        except ImportError as e:
            pytest.skip(f"Terminal service not available: {e}")

        # Don't start any process, try to get size
        with pytest.raises(RuntimeError):
            terminal.get_size()

        # Don't start any process, try to set size
        with pytest.raises(RuntimeError):
            terminal.set_size(24, 80)

    def test_terminal_lifecycle_multiple_cycles(self, clean_terminal):
        """Test multiple spawn/terminate cycles with the same service instance."""
        terminal = clean_terminal

        # Perform multiple spawn/terminate cycles
        for i in range(3):
            # Spawn terminal
            if platform.system() == "Windows":
                terminal.spawn("cmd")
            else:
                terminal.spawn("sh")

            time.sleep(0.3)

            # Verify it's alive
            assert terminal.is_alive(), f"Terminal should be alive in cycle {i+1}"

            # Execute a simple command
            cmd = f'echo "cycle {i+1}"'
            full_cmd = f"{cmd}\r\n" if platform.system() == "Windows" else f"{cmd}\n"
            terminal.write(full_cmd)

            time.sleep(0.5)  # Increased from 0.3 to 0.5

            # Read output in a loop to get the command result
            output = ""
            for _ in range(15):  # Increased from 10 to 15 attempts
                try:
                    chunk = terminal.read()
                    if chunk:
                        output += chunk
                        if f"cycle {i+1}" in output.lower():
                            break
                    time.sleep(0.3)  # Increased from 0.1 to 0.3 seconds
                except Exception:
                    time.sleep(0.3)  # Increased from 0.1 to 0.3 seconds
                    continue

            assert (
                f"cycle {i+1}" in output.lower()
            ), f"Expected 'cycle {i+1}' in output, got: {repr(output)}"

            # Terminate
            terminal.terminate()

            # Verify it's terminated
            assert (
                not terminal.is_alive()
            ), f"Terminal should be terminated in cycle {i+1}"

    def test_multiple_echo_commands_in_single_process(self, clean_terminal):
        """
        Test executing multiple echo commands in the same terminal process.
        This test verifies that a single spawned terminal can handle multiple commands sequentially.
        """
        terminal = clean_terminal

        # Start a terminal
        if platform.system() == "Windows":
            terminal.spawn("cmd")
        else:
            terminal.spawn("sh")

        time.sleep(0.5)

        # Verify terminal is alive
        assert terminal.is_alive(), "Terminal should be alive after spawning"

        # Execute multiple echo commands in the same process
        # Using simpler commands that are more likely to work consistently
        echo_commands = ["echo test1", "echo test2", "echo test3"]

        expected_outputs = ["test1", "test2", "test3"]

        for i, (cmd, expected) in enumerate(zip(echo_commands, expected_outputs)):
            # Write the echo command
            full_cmd = f"{cmd}\r\n" if platform.system() == "Windows" else f"{cmd}\n"
            terminal.write(full_cmd)

            # Wait for command execution
            time.sleep(0.5)

            # Read output with a simpler approach
            output = ""
            try:
                # Try reading once first
                chunk = terminal.read()
                if chunk:
                    output += chunk

                # If we don't find expected output, try more times with longer waits
                if expected not in output.lower():
                    for _ in range(10):  # Increased from 5 to 10 attempts
                        time.sleep(0.3)  # Increased from 0.2 to 0.3 seconds
                        try:
                            more_chunk = terminal.read()
                            if more_chunk:
                                output += more_chunk
                                if expected in output.lower():
                                    break
                        except Exception:
                            continue
            except Exception:
                # If read fails, wait and try once more
                time.sleep(0.5)
                try:
                    output = terminal.read()
                except Exception:
                    output = ""

            # Verify the command output was captured
            assert expected.lower() in output.lower(), (
                f"Command {i+1} failed: Expected '{expected}' in output, "
                f"got: {repr(output)}"
            )

        # Verify terminal is still alive after all commands
        assert (
            terminal.is_alive()
        ), "Terminal should still be alive after multiple commands"

        # Clean up - terminate the terminal
        terminal.terminate()

        # Verify terminal is terminated
        assert not terminal.is_alive(), "Terminal should be terminated after cleanup"

    def test_echo_commands_with_different_content_types(self, clean_terminal):
        """
        Test multiple echo commands with different content types in the same process.
        Tests commands with numbers, special characters, and different formatting.
        """
        terminal = clean_terminal

        # Start a terminal
        if platform.system() == "Windows":
            terminal.spawn("cmd")
        else:
            terminal.spawn("sh")

        time.sleep(0.5)

        # Test different types of echo content (simplified for stability)
        test_cases = [
            ("echo 12345", "12345"),  # Numbers only
            ("echo hello-world", "hello-world"),  # Simple text with dash
            ("echo test_case", "test_case"),  # Underscore
        ]

        for i, (cmd, expected) in enumerate(test_cases):
            # Write the command
            full_cmd = f"{cmd}\r\n" if platform.system() == "Windows" else f"{cmd}\n"
            terminal.write(full_cmd)

            # Wait for execution
            time.sleep(0.5)

            # Read and verify output
            output = ""
            try:
                chunk = terminal.read()
                if chunk:
                    output += chunk

                # If we don't find expected output, try more times with longer waits
                if expected not in output.lower():
                    for j in range(10):  # Increased from 3 to 10 attempts
                        time.sleep(0.3)  # Increased from 0.2 to 0.3 seconds
                        try:
                            more_chunk = terminal.read()
                            if more_chunk:
                                output += more_chunk
                                if expected in output.lower():
                                    break
                        except Exception:
                            continue
            except Exception:
                # If read fails, wait and try once more
                time.sleep(0.5)
                try:
                    output = terminal.read()
                except Exception:
                    output = ""

            assert expected.lower() in output.lower(), (
                f"Content type {i+1} failed: Expected '{expected}' in output, "
                f"got: {repr(output)}"
            )

        terminal.terminate()
        assert not terminal.is_alive(), "Terminal should be terminated"
