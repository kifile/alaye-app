"""
Cross-platform PTY (pseudo-terminal) service abstraction.

This module provides a unified interface for terminal operations across different platforms:
- Windows: Uses pywinpty
- Unix-like systems: Uses pexpect

Additionally provides event-driven PTY capabilities for real-time output monitoring.
"""

import platform

from . import events, listeners
from .base import TerminalServiceInterface
from .event_service import EventDrivenTerminalInstance
from .factory import TerminalServiceFactory

# Dynamic platform-specific imports with unified alias
system = platform.system().lower()
if system == "windows":
    from .pywinpty_service import PywinptyTerminalService as TerminalService
else:
    from .pexpect_service import PexpectTerminalService as TerminalService

__all__ = [
    # Core interfaces and factories
    "TerminalServiceInterface",
    "TerminalServiceFactory",
    "TerminalService",  # Unified alias for platform-specific implementation
    # Event-driven PTY
    "EventDrivenTerminalInstance",
    # Event system
    "events",
    "listeners",
]
