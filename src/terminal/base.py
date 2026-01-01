"""
Abstract base class for terminal services with event-driven support.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple


class TerminalServiceInterface(ABC):
    """
    Abstract interface for terminal operations.

    This interface defines the contract that all terminal service implementations
    must follow, providing a consistent API regardless of the underlying platform.
    """

    @abstractmethod
    def spawn(self, command: str, *args: str, **kwargs) -> None:
        """
        Spawn a new terminal process.

        Args:
            command: The command to execute
            *args: Additional arguments for the command
            **kwargs: Additional keyword arguments (platform-specific)
        """

    @abstractmethod
    def set_size(self, rows: int, cols: int) -> None:
        """
        Set the terminal size.

        Args:
            rows: Number of rows
            cols: Number of columns
        """

    @abstractmethod
    def is_alive(self) -> bool:
        """
        Check if the terminal process is still running.

        Returns:
            True if the process is alive, False otherwise
        """

    @abstractmethod
    def write(self, data: str) -> None:
        """
        Write data to the terminal.

        Args:
            data: The data to write
        """

    @abstractmethod
    def read(self, size: int = -1) -> str:
        """
        Read data from the terminal.

        Args:
            size: Maximum number of bytes to read (-1 for all available)

        Returns:
            The data read from the terminal
        """

    @abstractmethod
    def terminate(self) -> None:
        """
        Terminate the terminal process.
        """

    @abstractmethod
    def wait(self) -> Optional[int]:
        """
        Wait for the terminal process to complete.

        Returns:
            Exit code of the process, or None if still running
        """

    @abstractmethod
    def get_size(self) -> Tuple[int, int]:
        """
        Get the current terminal size.

        Returns:
            Tuple of (rows, cols)
        """
