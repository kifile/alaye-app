"""
Event types and data structures for event-driven PTY operations.
"""

import threading
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ProcessState(Enum):
    """Process state enumeration."""

    STOPPED = "stopped"
    RUNNING = "running"
    STARTING = "starting"
    STOPPING = "stopping"


class EventType(Enum):
    """Event type enumeration for PTY events."""

    OUTPUT = "output"  # New output from PTY
    STATE_CHANGED = "state_changed"  # Process state changed
    ERROR = "error"  # Error occurred
    PROCESS_EXITED = "process_exited"  # Process exited
    SIZE_CHANGED = "size_changed"  # Terminal size changed


@dataclass
class PTYEvent:
    """Base event data structure."""

    event_type: EventType
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class OutputEvent(PTYEvent):
    """Event for PTY output data."""

    event_type: EventType = EventType.OUTPUT
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {}
        if "text" not in self.data:
            self.data["text"] = ""


@dataclass
class StateChangedEvent(PTYEvent):
    """Event for process state changes."""

    event_type: EventType = EventType.STATE_CHANGED
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {}
        if "old_state" not in self.data:
            self.data["old_state"] = None
        if "new_state" not in self.data:
            self.data["new_state"] = None


@dataclass
class ErrorEvent(PTYEvent):
    """Event for error occurrences."""

    event_type: EventType = EventType.ERROR
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {}
        if "error" not in self.data:
            self.data["error"] = None
        if "error_type" not in self.data:
            self.data["error_type"] = None


@dataclass
class ProcessExitedEvent(PTYEvent):
    """Event for process exit."""

    event_type: EventType = EventType.PROCESS_EXITED
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {}
        if "exit_code" not in self.data:
            self.data["exit_code"] = None
        if "exit_reason" not in self.data:
            self.data["exit_reason"] = None


@dataclass
class SizeChangedEvent(PTYEvent):
    """Event for terminal size change."""

    event_type: EventType = EventType.SIZE_CHANGED
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {}
        if "rows" not in self.data:
            self.data["rows"] = None
        if "cols" not in self.data:
            self.data["cols"] = None


# Event listener type definitions
EventListener = Callable[[PTYEvent], None]
EventListenerID = str


class EventManager:
    """
    Thread-safe event manager for handling PTY events and listeners.
    All listeners receive all events regardless of type.
    """

    def __init__(self):
        self._listeners: List[EventListener] = []
        self._named_listeners: Dict[EventListenerID, EventListener] = {}
        self._lock = threading.RLock()

    def add_listener(
        self,
        listener: Optional[EventListener] = None,
        listener_id: Optional[EventListenerID] = None,
    ) -> Optional[EventListenerID]:
        """
        Add an event listener that will receive all events.

        Args:
            listener: The callback function to invoke
            listener_id: Optional ID for the listener (for removal)

        Returns:
            The listener ID if provided or auto-generated, None otherwise
        """
        # Handle different calling styles
        if listener is None:
            raise ValueError("Listener function is required")

        with self._lock:
            self._listeners.append(listener)

            if listener_id:
                self._named_listeners[listener_id] = listener
                return listener_id
            else:
                # Auto-generate an ID
                auto_id = f"listener_{id(listener)}_{threading.get_ident()}"
                self._named_listeners[auto_id] = listener
                return auto_id

    def remove_listener(self, listener: EventListener) -> bool:
        """
        Remove a specific event listener.

        Args:
            listener: The listener function to remove

        Returns:
            True if listener was found and removed, False otherwise
        """
        with self._lock:
            try:
                self._listeners.remove(listener)

                # Remove from named listeners if present
                ids_to_remove = [
                    lid for lid, l in self._named_listeners.items() if l == listener
                ]
                for lid in ids_to_remove:
                    del self._named_listeners[lid]

                return True
            except ValueError:
                return False

    def remove_listener_by_id(self, listener_id: EventListenerID) -> bool:
        """
        Remove an event listener by its ID.

        Args:
            listener_id: The ID of the listener to remove

        Returns:
            True if listener was found and removed, False otherwise
        """
        with self._lock:
            if listener_id in self._named_listeners:
                listener = self._named_listeners[listener_id]
                del self._named_listeners[listener_id]

                if listener in self._listeners:
                    self._listeners.remove(listener)

                return True
            return False

    def emit(self, event: PTYEvent) -> None:
        """
        Emit an event to all registered listeners.

        Args:
            event: The event to emit
        """
        with self._lock:
            listeners = self._listeners.copy()

        # Call listeners outside the lock to avoid deadlocks
        for listener in listeners:
            try:
                listener(event)
            except Exception as e:
                # Log error but don't let it affect other listeners
                print(f"Error in event listener: {e}")

    def clear_listeners(self) -> None:
        """
        Clear all listeners.
        """
        with self._lock:
            self._listeners.clear()
            self._named_listeners.clear()

    def get_listener_count(self) -> int:
        """
        Get the total number of listeners.

        Returns:
            Number of listeners
        """
        with self._lock:
            return len(self._listeners)

    def get_listener_ids(self) -> List[EventListenerID]:
        """
        Get all registered listener IDs.

        Returns:
            List of listener IDs
        """
        with self._lock:
            return list(self._named_listeners.keys())
