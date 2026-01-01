"""
Event-driven PTY instance that provides real-time output monitoring and state management.
"""

import queue
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .base import TerminalServiceInterface
from .events import (
    ErrorEvent,
    EventListenerID,
    EventManager,
    OutputEvent,
    ProcessExitedEvent,
    ProcessState,
    PTYEvent,
    SizeChangedEvent,
    StateChangedEvent,
)
from .factory import TerminalServiceFactory


class EventDrivenTerminalInstance:
    """
    Event-driven terminal service that spawns processes and monitors their output
    in real-time using background threads.
    """

    def __init__(
        self,
        instance_id: Optional[str] = None,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        terminal_service: Optional[TerminalServiceInterface] = None,
    ):
        """
        Initialize the event-driven terminal instance.

        Args:
            instance_id: Unique identifier for this terminal instance
            command: Command to be executed
            args: Arguments for the command
            metadata: Additional metadata for the instance
            terminal_service: Optional terminal service to use, creates one if None
        """
        # Instance identification and metadata
        self.id = instance_id or str(uuid.uuid4())
        self.command = command
        self.args = args or []
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.last_activity = datetime.now()

        self._terminal_service = (
            terminal_service or TerminalServiceFactory.create_terminal_service()
        )
        self._event_manager = EventManager()
        self._state = ProcessState.STOPPED
        self._state_lock = threading.RLock()

        # Thread management
        self._read_thread: Optional[threading.Thread] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._output_queue = queue.Queue()

        # Process information
        self._current_command: Optional[str] = None
        self._current_args: Optional[list] = None
        self._exit_code: Optional[int] = None
        self._exit_reason: Optional[str] = None

        # Event listener reference for cleanup
        self._event_listener = None

        # Read configuration
        self._read_interval = (
            0.05  # 50ms between read attempts (faster for better responsiveness)
        )
        self._monitor_interval = 0.5  # 500ms between process state checks
        self._max_read_attempts = 3

    @property
    def state(self) -> ProcessState:
        """Get the current process state."""
        with self._state_lock:
            return self._state

    @property
    def is_running(self) -> bool:
        """Check if the process is currently running."""
        return self.state == ProcessState.RUNNING

    @property
    def terminal_service(self) -> TerminalServiceInterface:
        """Get the underlying terminal service."""
        return self._terminal_service

    @property
    def status(self) -> ProcessState:
        """Get the current process status - alias for state property."""
        return self._state

    def to_dict(self) -> Dict[str, Any]:
        """Convert instance to dictionary format."""
        return {
            "id": self.id,
            "command": self.command,
            "args": self.args,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "metadata": self.metadata,
            "process_info": self.get_process_info(),
        }

    def add_event_listener(
        self,
        listener: Callable[[PTYEvent], None],
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
        return self._event_manager.add_listener(
            listener=listener, listener_id=listener_id
        )

    def remove_event_listener(self, listener: Callable[[PTYEvent], None]) -> bool:
        """
        Remove an event listener.

        Args:
            listener: The listener function to remove

        Returns:
            True if listener was found and removed, False otherwise
        """
        return self._event_manager.remove_listener(listener)

    def remove_event_listener_by_id(self, listener_id: EventListenerID) -> bool:
        """
        Remove an event listener by its ID.

        Args:
            listener_id: The ID of the listener to remove

        Returns:
            True if listener was found and removed, False otherwise
        """
        return self._event_manager.remove_listener_by_id(listener_id)

    def spawn(self, command: str, *args: str, **kwargs) -> None:
        """
        Spawn a new terminal process and start monitoring it.

        Args:
            command: The command to execute
            *args: Additional arguments for the command
            **kwargs: Additional keyword arguments (passed to terminal service)
        """
        with self._state_lock:
            if self._state != ProcessState.STOPPED:
                raise RuntimeError(
                    f"Cannot spawn process in state {self._state}. Process must be stopped first."
                )

            # Update state
            old_state = self._state
            self._state = ProcessState.STARTING
            self._current_command = command
            self._current_args = list(args)

            # Update instance properties
            self.command = command
            self.args = list(args)
            self.last_activity = datetime.now()

        # Clear stop event and reset exit information
        self._stop_event.clear()
        self._exit_code = None
        self._exit_reason = None
        self._output_queue.queue.clear()

        try:
            # Emit starting state change event first
            self._emit_state_changed(old_state, ProcessState.STARTING)

            # Spawn the process
            self._terminal_service.spawn(command, *args, **kwargs)

            # Verify the process is actually alive, but stay in STARTING state
            if not self._terminal_service.is_alive():
                # Process died immediately after spawn
                with self._state_lock:
                    self._state = ProcessState.STOPPED
                    self._exit_reason = "process_died_immediately"

                # Emit state change event
                self._emit_state_changed(ProcessState.STARTING, ProcessState.STOPPED)

                raise RuntimeError(
                    f"Process died immediately after spawning: {command}"
                )

            # Start monitoring threads - will transition to RUNNING when first output is received
            self._start_monitoring_threads()

        except Exception as e:
            # Update state to stopped on error
            with self._state_lock:
                self._state = ProcessState.STOPPED

            # Emit error event
            error_event = ErrorEvent(
                timestamp=datetime.now(),
                data={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "command": command,
                    "args": list(args),
                },
            )
            self._event_manager.emit(error_event)

            # Emit state change event (from current state which should be STARTING)
            self._emit_state_changed(ProcessState.STARTING, ProcessState.STOPPED)

            raise

    def write(self, data: str) -> None:
        """
        Write data to the terminal.

        Args:
            data: The data to write
        """
        if not self.is_running:
            raise RuntimeError("Cannot write to terminal: process is not running")

        try:
            self._terminal_service.write(data)
            self.last_activity = datetime.now()
        except Exception as e:
            error_event = ErrorEvent(
                timestamp=datetime.now(),
                data={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "operation": "write",
                },
            )
            self._event_manager.emit(error_event)
            raise

    def set_size(self, rows: int, cols: int) -> None:
        """
        Set the terminal size.

        Args:
            rows: Number of rows
            cols: Number of columns
        """
        if not self.is_running:
            raise RuntimeError("Cannot set terminal size: process is not running")

        try:
            self._terminal_service.set_size(rows, cols)

            # 发送尺寸变化事件
            size_event = SizeChangedEvent(
                timestamp=datetime.now(),
                data={
                    "rows": rows,
                    "cols": cols,
                },
            )
            self._event_manager.emit(size_event)

        except Exception as e:
            error_event = ErrorEvent(
                timestamp=datetime.now(),
                data={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "operation": "set_size",
                    "rows": rows,
                    "cols": cols,
                },
            )
            self._event_manager.emit(error_event)
            raise

    def get_size(self) -> tuple:
        """
        Get the current terminal size.

        Returns:
            Tuple of (rows, cols)
        """
        if not self.is_running:
            raise RuntimeError("Cannot get terminal size: process is not running")

        try:
            return self._terminal_service.get_size()
        except Exception as e:
            error_event = ErrorEvent(
                timestamp=datetime.now(),
                data={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "operation": "get_size",
                },
            )
            self._event_manager.emit(error_event)
            raise

    def terminate(self) -> None:
        """
        Terminate the terminal process and stop monitoring.
        """
        with self._state_lock:
            if self._state in [ProcessState.STOPPED, ProcessState.STOPPING]:
                return

            old_state = self._state
            self._state = ProcessState.STOPPING

        # Emit state change event
        self._emit_state_changed(old_state, ProcessState.STOPPING)

        # Signal threads to stop
        self._stop_event.set()

        try:
            # Terminate the terminal process
            if self._terminal_service.is_alive():
                self._terminal_service.terminate()

            # Wait for threads to finish
            if self._read_thread and self._read_thread.is_alive():
                self._read_thread.join(timeout=1.0)

            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=1.0)

            # Update state to stopped
            with self._state_lock:
                self._state = ProcessState.STOPPED
                self._exit_reason = "terminated_by_user"

            # Emit process exited event
            exit_event = ProcessExitedEvent(
                timestamp=datetime.now(),
                data={
                    "exit_code": self._exit_code,
                    "exit_reason": self._exit_reason,
                    "command": self._current_command,
                    "args": self._current_args,
                },
            )
            self._event_manager.emit(exit_event)

            # Emit final state change event
            self._emit_state_changed(ProcessState.STOPPING, ProcessState.STOPPED)

        except Exception as e:
            # Even if there's an error, set state to stopped
            with self._state_lock:
                self._state = ProcessState.STOPPED

            error_event = ErrorEvent(
                timestamp=datetime.now(),
                data={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "operation": "terminate",
                },
            )
            self._event_manager.emit(error_event)

            self._emit_state_changed(ProcessState.STOPPING, ProcessState.STOPPED)

    def wait(self) -> Optional[int]:
        """
        Wait for the process to complete and return exit code.

        Returns:
            Exit code of the process, or None if still running
        """
        if self.is_running:
            return self._terminal_service.wait()
        return self._exit_code

    def _start_monitoring_threads(self) -> None:
        """Start the background monitoring threads."""
        # Start read thread
        self._read_thread = threading.Thread(
            target=self._read_worker, name="PTYReadWorker", daemon=True
        )
        self._read_thread.start()

        # Start monitor thread
        self._monitor_thread = threading.Thread(
            target=self._monitor_worker, name="PTYMonitorWorker", daemon=True
        )
        self._monitor_thread.start()

    def _read_worker(self) -> None:
        """Background thread worker for reading PTY output."""
        while not self._stop_event.is_set():
            try:
                # Check if process is still alive
                if not self._terminal_service.is_alive():
                    break

                # Try to read data
                data = None
                for attempt in range(self._max_read_attempts):
                    try:
                        data = self._terminal_service.read()
                        if data:
                            break
                    except Exception:
                        time.sleep(0.05)  # Brief delay before retry
                        continue

                # If we got data, handle state transition and emit output event
                if data:
                    # Update last activity
                    self.last_activity = datetime.now()

                    # Check if we need to transition from STARTING to RUNNING
                    should_transition_to_running = False
                    with self._state_lock:
                        if self._state == ProcessState.STARTING:
                            should_transition_to_running = True
                            self._state = ProcessState.RUNNING

                    # Emit state change event if transitioning
                    if should_transition_to_running:
                        self._emit_state_changed(
                            ProcessState.STARTING, ProcessState.RUNNING
                        )

                    # Emit output event
                    output_event = OutputEvent(
                        timestamp=datetime.now(), data={"text": data}
                    )
                    self._event_manager.emit(output_event)

                # Brief sleep before next read attempt
                time.sleep(self._read_interval)

            except Exception:
                # Don't emit error events for normal read failures
                # (they happen frequently when no data is available)
                time.sleep(self._read_interval)
                continue

    def _monitor_worker(self) -> None:
        """Background thread worker for monitoring process state."""
        while not self._stop_event.is_set():
            try:
                # Check if process is still alive
                if not self._terminal_service.is_alive():
                    self._handle_process_exit()
                    break

                # Sleep before next check
                time.sleep(self._monitor_interval)

            except Exception as e:
                error_event = ErrorEvent(
                    timestamp=datetime.now(),
                    data={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "operation": "process_monitoring",
                    },
                )
                self._event_manager.emit(error_event)

                time.sleep(self._monitor_interval)

    def _handle_process_exit(self) -> None:
        """Handle the process exiting naturally."""
        with self._state_lock:
            if self._state != ProcessState.RUNNING:
                return

            old_state = self._state
            # First transition to STOPPING
            self._state = ProcessState.STOPPING

        # Emit state change to STOPPING
        self._emit_state_changed(old_state, ProcessState.STOPPING)

        # Get exit information
        try:
            self._exit_code = self._terminal_service.wait()
            self._exit_reason = "natural_exit"
        except Exception:
            self._exit_code = None
            self._exit_reason = "unknown"

        # Stop the monitoring threads
        self._stop_event.set()

        # Emit process exited event
        exit_event = ProcessExitedEvent(
            timestamp=datetime.now(),
            data={
                "exit_code": self._exit_code,
                "exit_reason": self._exit_reason,
                "command": self._current_command,
                "args": self._current_args,
            },
        )
        self._event_manager.emit(exit_event)

        # Final transition to STOPPED
        with self._state_lock:
            self._state = ProcessState.STOPPED

        # Emit final state change event
        self._emit_state_changed(ProcessState.STOPPING, ProcessState.STOPPED)

    def _emit_state_changed(
        self, old_state: ProcessState, new_state: ProcessState
    ) -> None:
        """Emit a state change event."""
        state_event = StateChangedEvent(
            timestamp=datetime.now(),
            data={
                "old_state": old_state.value,
                "new_state": new_state.value,
                "command": self._current_command,
                "args": self._current_args,
            },
        )
        self._event_manager.emit(state_event)

    def get_process_info(self) -> Dict[str, Any]:
        """
        Get information about the current process.

        Returns:
            Dictionary containing process information
        """
        with self._state_lock:
            return {
                "state": self._state.value,
                "command": self._current_command,
                "args": self._current_args,
                "exit_code": self._exit_code,
                "exit_reason": self._exit_reason,
                "is_alive": (
                    self._terminal_service.is_alive()
                    if self._terminal_service
                    else False
                ),
                "listener_count": self._event_manager.get_listener_count(),
            }
