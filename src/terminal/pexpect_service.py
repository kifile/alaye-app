"""
Pexpect-based terminal service implementation for Unix-like systems.
"""

from typing import Optional, Tuple

import pexpect

from .base import TerminalServiceInterface


class PexpectTerminalService(TerminalServiceInterface):
    """
    Pexpect-based terminal service implementation.

    This class uses pexpect to provide PTY functionality on Unix-like systems
    (Linux, macOS, etc.).
    """

    def __init__(self):
        self._process: Optional[pexpect.spawn] = None
        self._command: Optional[str] = None
        self._args: Optional[list] = None

    def spawn(self, command: str, *args: str, **kwargs) -> None:
        """
        Spawn a new terminal process using pexpect.

        Args:
            command: The command to execute
            *args: Additional arguments for the command
            **kwargs: Additional pexpect-specific arguments:
                - timeout: Timeout in seconds (default: 30)
                - cwd: Working directory
                - env: Environment variables
                - echo: Whether to echo input (default: False)
        """
        if self._process and self._process.isalive():
            self.terminate()

        # Extract pexpect-specific parameters
        timeout = kwargs.get("timeout", 30)
        cwd = kwargs.get("cwd")
        env = kwargs.get("env")
        echo = kwargs.get("echo", True)

        # Build command string
        if args:
            f"{command} {' '.join(args)}"

        try:
            self._process = pexpect.spawn(
                command,
                args=list(args),
                timeout=timeout,
                cwd=cwd,
                env=env,
                echo=echo,
                encoding="utf-8",
                codec_errors="replace",
            )
            self._command = command
            self._args = list(args)

        except Exception as e:
            raise RuntimeError(f"Failed to spawn process with pexpect: {e}")

    def set_size(self, rows: int, cols: int) -> None:
        """
        Set the terminal size.

        Args:
            rows: Number of rows
            cols: Number of columns
        """
        if not self._process:
            raise RuntimeError("No process is currently running")

        try:
            self._process.setwinsize(rows, cols)
        except Exception as e:
            raise RuntimeError(f"Failed to set terminal size: {e}")

    def is_alive(self) -> bool:
        """
        Check if the terminal process is still running.

        Returns:
            True if the process is alive, False otherwise
        """
        if not self._process:
            return False

        try:
            return self._process.isalive()
        except Exception:
            return False

    def write(self, data: str) -> None:
        """
        Write data to the terminal.

        Args:
            data: The data to write
        """
        if not self._process:
            raise RuntimeError("No process is currently running")

        try:
            self._process.write(data)
            self._process.flush()
        except Exception as e:
            raise RuntimeError(f"Failed to write to terminal: {e}")

    def read(self, size: int = -1) -> str:
        """
        Read data from the terminal.

        Args:
            size: Maximum number of bytes to read (-1 for all available)

        Returns:
            The data read from the terminal
        """
        if not self._process:
            raise RuntimeError("No process is currently running")

        try:
            if size == -1:
                # Read all available data using a time-based approach
                # Continue reading for up to 50ms or until no more data is available
                import time

                start_time = time.time()
                read_timeout = 0.05  # 50ms time window
                data = ""

                while time.time() - start_time < read_timeout:
                    try:
                        # Use a shorter timeout for individual reads
                        chunk = self._process.read_nonblocking(timeout=0.005)
                        if chunk:
                            data += chunk
                            # If we got data, reset the timeout to allow for more data
                            start_time = time.time()
                        else:
                            # No data available, small delay before next attempt
                            time.sleep(0.001)
                    except pexpect.exceptions.TIMEOUT:
                        # Individual read timeout, continue if we're within the time window
                        continue
                    except Exception:
                        # Other exceptions, break out
                        break

                return data
            else:
                return self._process.read_nonblocking(size=size, timeout=0.1)
        except pexpect.exceptions.TIMEOUT:
            # No data available
            return ""
        except Exception as e:
            if "EOF" in str(e):
                return ""
            raise RuntimeError(f"Failed to read from terminal: {e}")

    def terminate(self) -> None:
        """
        Terminate the terminal process.
        """
        if not self._process:
            return

        try:
            if self._process.isalive():
                self._process.terminate(force=True)
        except Exception:
            # Ignore errors during termination
            pass
        finally:
            self._process = None
            self._command = None
            self._args = None

    def wait(self) -> Optional[int]:
        """
        Wait for the terminal process to complete.

        Returns:
            Exit code of the process, or None if still running
        """
        if not self._process:
            return None

        try:
            self._process.wait()
            return self._process.exitstatus
        except Exception:
            return None

    def get_size(self) -> Tuple[int, int]:
        """
        Get the current terminal size.

        Returns:
            Tuple of (rows, cols)
        """
        if not self._process:
            raise RuntimeError("No process is currently running")

        try:
            return self._process.getwinsize()
        except Exception as e:
            raise RuntimeError(f"Failed to get terminal size: {e}")
