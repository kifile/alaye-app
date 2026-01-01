"""
Factory for creating platform-specific terminal service instances.
"""

import platform
from typing import Optional

from .base import TerminalServiceInterface

# Dynamic platform-specific import
system = platform.system().lower()
if system == "windows":
    from .pywinpty_service import PywinptyTerminalService as PlatformTerminalService
else:
    from .pexpect_service import PexpectTerminalService as PlatformTerminalService


class TerminalServiceFactory:
    """
    Factory class for creating appropriate terminal service instances
    based on the current platform.
    """

    @staticmethod
    def create_terminal_service() -> TerminalServiceInterface:
        """
        Create and return the appropriate terminal service for the current platform.

        Returns:
            A terminal service instance appropriate for the current platform

        Raises:
            ImportError: If required dependencies are not available
            RuntimeError: If platform is not supported
        """
        try:
            return PlatformTerminalService()
        except ImportError as e:
            system = platform.system()
            if system == "Windows":
                raise ImportError(
                    "pywinpty is required for Windows terminal support. "
                    "Install it with: pip install pywinpty"
                ) from e
            else:
                raise ImportError(
                    "pexpect is required for Unix-like terminal support. "
                    "Install it with: pip install pexpect"
                ) from e

    @staticmethod
    def is_platform_supported() -> bool:
        """
        Check if the current platform is supported.

        Returns:
            True if the platform is supported, False otherwise
        """
        try:
            PlatformTerminalService()
            return True
        except ImportError:
            return False

    @staticmethod
    def get_platform_info() -> dict:
        """
        Get information about the current platform and available terminal libraries.

        Returns:
            Dictionary containing platform and dependency information
        """
        system = platform.system()
        machine = platform.machine()
        release = platform.release()
        python_version = platform.python_version()

        info = {
            "system": system,
            "machine": machine,
            "release": release,
            "python_version": python_version,
            "preferred_backend": None,
            "available_backends": [],
        }

        if system == "Windows":
            info["preferred_backend"] = "pywinpty"
        else:
            info["preferred_backend"] = "pexpect"

        # Check if the backend is actually available
        try:
            PlatformTerminalService()
            info["available_backends"].append(info["preferred_backend"])
        except ImportError:
            pass

        return info

    @staticmethod
    def create_fallback_service() -> Optional[TerminalServiceInterface]:
        """
        Create a terminal service using available libraries, falling back gracefully
        if the preferred library is not available.

        Returns:
            A terminal service instance if any backend is available, None otherwise
        """
        try:
            return PlatformTerminalService()
        except ImportError:
            return None
