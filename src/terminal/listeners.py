"""
Convenience event listener implementations and utilities for event-driven PTY operations.
"""

import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .events import (
    ErrorEvent,
    OutputEvent,
    ProcessExitedEvent,
    ProcessState,
    PTYEvent,
    StateChangedEvent,
)


class BasePTYListener:
    """Base class for PTY event listeners."""

    def on_output(self, event: OutputEvent) -> None:
        """Called when new output is received from the PTY."""

    def on_state_changed(self, event: StateChangedEvent) -> None:
        """Called when the process state changes."""

    def on_error(self, event: ErrorEvent) -> None:
        """Called when an error occurs."""

    def on_process_exited(self, event: ProcessExitedEvent) -> None:
        """Called when the process exits."""

    def __call__(self, event: PTYEvent) -> None:
        """Main event dispatcher - routes events to appropriate handlers."""
        if isinstance(event, OutputEvent):
            self.on_output(event)
        elif isinstance(event, StateChangedEvent):
            self.on_state_changed(event)
        elif isinstance(event, ErrorEvent):
            self.on_error(event)
        elif isinstance(event, ProcessExitedEvent):
            self.on_process_exited(event)


class OutputCollector(BasePTYListener):
    """Listener that collects all PTY output into a list or string."""

    def __init__(self, keep_as_list: bool = True, max_size: Optional[int] = None):
        """
        Initialize the output collector.

        Args:
            keep_as_list: If True, keep output as list of chunks. If False, concatenate to string.
            max_size: Maximum number of items to keep (None for unlimited)
        """
        self.keep_as_list = keep_as_list
        self.max_size = max_size
        self._output: List[str] = []
        self._full_output: str = ""
        self._lock = threading.Lock()

    def on_output(self, event: OutputEvent) -> None:
        """Collect output from the PTY."""
        with self._lock:
            text = event.data.get("text", "")
            if text:
                self._output.append(text)
                self._full_output += text

                # Trim if max_size is specified
                if self.max_size and len(self._output) > self.max_size:
                    self._output = self._output[-self.max_size :]

    def get_output(self) -> Any:
        """Get the collected output."""
        with self._lock:
            return self._output if self.keep_as_list else self._full_output

    def get_latest(self, count: int = 1) -> List[str]:
        """Get the latest N output chunks."""
        with self._lock:
            return self._output[-count:] if count > 0 else []

    def clear(self) -> None:
        """Clear all collected output."""
        with self._lock:
            self._output.clear()
            self._full_output = ""

    def size(self) -> int:
        """Get the number of output chunks collected."""
        with self._lock:
            return len(self._output)


class StateMonitor(BasePTYListener):
    """Listener that monitors and tracks process state changes."""

    def __init__(self):
        self._state_history: List[Dict[str, Any]] = []
        self._current_state: Optional[ProcessState] = None
        self._lock = threading.Lock()

    def on_state_changed(self, event: StateChangedEvent) -> None:
        """Track state changes."""
        with self._lock:
            old_state = ProcessState(event.data.get("old_state"))
            new_state = ProcessState(event.data.get("new_state"))

            self._current_state = new_state
            self._state_history.append(
                {
                    "timestamp": event.timestamp,
                    "old_state": old_state,
                    "new_state": new_state,
                    "command": event.data.get("command"),
                    "args": event.data.get("args"),
                }
            )

    def get_current_state(self) -> Optional[ProcessState]:
        """Get the current process state."""
        with self._lock:
            return self._current_state

    def get_state_history(self) -> List[Dict[str, Any]]:
        """Get the complete state change history."""
        with self._lock:
            return self._state_history.copy()

    def is_running(self) -> bool:
        """Check if the process is currently running."""
        return self.get_current_state() == ProcessState.RUNNING

    def is_stopped(self) -> bool:
        """Check if the process is currently stopped."""
        return self.get_current_state() == ProcessState.STOPPED

    def clear_history(self) -> None:
        """Clear the state change history."""
        with self._lock:
            self._state_history.clear()


class OutputToFile(BasePTYListener):
    """Listener that writes PTY output to a file."""

    def __init__(self, filename: str, append: bool = True, encoding: str = "utf-8"):
        """
        Initialize the file output listener.

        Args:
            filename: Path to the output file
            append: If True, append to existing file. If False, overwrite.
            encoding: File encoding
        """
        self.filename = filename
        self.append = append
        self.encoding = encoding
        self._lock = threading.Lock()

        # Create/open the file
        mode = "a" if append else "w"
        with open(filename, mode, encoding=encoding) as f:
            if not append or f.tell() == 0:
                # Write header if file is empty
                f.write(f"# PTY Output Log - Started at {datetime.now()}\n")

    def on_output(self, event: OutputEvent) -> None:
        """Write output to file."""
        text = event.data.get("text", "")
        if text:
            with self._lock:
                try:
                    with open(self.filename, "a", encoding=self.encoding) as f:
                        f.write(text)
                        f.flush()  # Ensure data is written immediately
                except Exception as e:
                    print(f"Error writing to file {self.filename}: {e}")


class PatternMatcher(BasePTYListener):
    """Listener that triggers callbacks when specific patterns are found in output."""

    def __init__(self):
        self._patterns: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def add_pattern(
        self,
        pattern: str,
        callback: Callable[[str, OutputEvent], None],
        case_sensitive: bool = False,
        name: Optional[str] = None,
    ) -> str:
        """
        Add a pattern to match.

        Args:
            pattern: The pattern to search for in output
            callback: Function to call when pattern is found
            case_sensitive: Whether the match should be case sensitive
            name: Optional name for the pattern

        Returns:
            Pattern ID for later removal
        """
        pattern_id = name or f"pattern_{len(self._patterns)}"
        pattern_config = {
            "id": pattern_id,
            "pattern": pattern,
            "callback": callback,
            "case_sensitive": case_sensitive,
            "match_count": 0,
        }

        with self._lock:
            self._patterns.append(pattern_config)

        return pattern_id

    def remove_pattern(self, pattern_id: str) -> bool:
        """
        Remove a pattern by ID.

        Args:
            pattern_id: The pattern ID to remove

        Returns:
            True if pattern was found and removed
        """
        with self._lock:
            for i, pattern in enumerate(self._patterns):
                if pattern["id"] == pattern_id:
                    del self._patterns[i]
                    return True
            return False

    def on_output(self, event: OutputEvent) -> None:
        """Check output for matching patterns."""
        text = event.data.get("text", "")
        if not text:
            return

        patterns_to_check = []
        with self._lock:
            patterns_to_check = self._patterns.copy()

        # Check each pattern (outside the lock to avoid deadlocks)
        for pattern_config in patterns_to_check:
            pattern = pattern_config["pattern"]
            case_sensitive = pattern_config["case_sensitive"]

            # Perform case-sensitive or insensitive matching
            search_text = text if case_sensitive else text.lower()
            search_pattern = pattern if case_sensitive else pattern.lower()

            if search_pattern in search_text:
                # Pattern matched, call callback
                try:
                    pattern_config["callback"](text, event)
                    pattern_config["match_count"] += 1
                except Exception as e:
                    print(f"Error in pattern callback for '{pattern}': {e}")

    def get_pattern_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all patterns."""
        with self._lock:
            return [
                {
                    "id": p["id"],
                    "pattern": p["pattern"],
                    "match_count": p["match_count"],
                    "case_sensitive": p["case_sensitive"],
                }
                for p in self._patterns
            ]

    def clear_patterns(self) -> None:
        """Clear all patterns."""
        with self._lock:
            self._patterns.clear()


class ConditionalListener(BasePTYListener):
    """Listener that only processes events when a condition is met."""

    def __init__(self, condition: Callable[[], bool], target_listener: BasePTYListener):
        """
        Initialize the conditional listener.

        Args:
            condition: Function that returns True if events should be processed
            target_listener: The listener to forward events to when condition is met
        """
        self.condition = condition
        self.target_listener = target_listener

    def __call__(self, event: PTYEvent) -> None:
        """Only forward events if condition is met."""
        try:
            if self.condition():
                self.target_listener(event)
        except Exception:
            # If condition fails, don't forward the event
            pass

    def on_output(self, event: OutputEvent) -> None:
        """Forward output event if condition is met."""
        if self.condition():
            self.target_listener.on_output(event)

    def on_state_changed(self, event: StateChangedEvent) -> None:
        """Forward state change event if condition is met."""
        if self.condition():
            self.target_listener.on_state_changed(event)

    def on_error(self, event: ErrorEvent) -> None:
        """Forward error event if condition is met."""
        if self.condition():
            self.target_listener.on_error(event)

    def on_process_exited(self, event: ProcessExitedEvent) -> None:
        """Forward process exited event if condition is met."""
        if self.condition():
            self.target_listener.on_process_exited(event)


class ChainedListener(BasePTYListener):
    """Listener that chains multiple listeners together."""

    def __init__(self, listeners: List[BasePTYListener]):
        """
        Initialize the chained listener.

        Args:
            listeners: List of listeners to chain together
        """
        self.listeners = listeners

    def __call__(self, event: PTYEvent) -> None:
        """Forward event to all listeners in order."""
        for listener in self.listeners:
            try:
                listener(event)
            except Exception as e:
                print(f"Error in chained listener: {e}")

    def on_output(self, event: OutputEvent) -> None:
        """Forward output event to all listeners."""
        for listener in self.listeners:
            try:
                listener.on_output(event)
            except Exception as e:
                print(f"Error in chained listener output: {e}")

    def on_state_changed(self, event: StateChangedEvent) -> None:
        """Forward state change event to all listeners."""
        for listener in self.listeners:
            try:
                listener.on_state_changed(event)
            except Exception as e:
                print(f"Error in chained listener state change: {e}")

    def on_error(self, event: ErrorEvent) -> None:
        """Forward error event to all listeners."""
        for listener in self.listeners:
            try:
                listener.on_error(event)
            except Exception as e:
                print(f"Error in chained listener error: {e}")

    def on_process_exited(self, event: ProcessExitedEvent) -> None:
        """Forward process exited event to all listeners."""
        for listener in self.listeners:
            try:
                listener.on_process_exited(event)
            except Exception as e:
                print(f"Error in chained listener process exit: {e}")

    def add_listener(self, listener: BasePTYListener) -> None:
        """Add a listener to the chain."""
        self.listeners.append(listener)

    def remove_listener(self, listener: BasePTYListener) -> bool:
        """Remove a listener from the chain."""
        try:
            self.listeners.remove(listener)
            return True
        except ValueError:
            return False

    def clear_listeners(self) -> None:
        """Clear all listeners from the chain."""
        self.listeners.clear()
