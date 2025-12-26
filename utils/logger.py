"""
Logger utility for the Deadlock & Resource Management Simulator.

Provides step-by-step logging with verbosity levels.
"""

from typing import Optional
from datetime import datetime


class SimulatorLogger:
    """
    Logger for simulation events and decisions.
    
    Format: "Step X: Process PY requests RZ[n] - GRANTED/DENIED (reason)"
    """

    def __init__(self, verbose: bool = False, log_file: Optional[str] = None):
        """
        Initialize logger.
        
        Args:
            verbose: Enable verbose output
            log_file: Optional file path for logging
        """
        self.verbose = verbose
        self.log_file = log_file
        self.file_handle = None

        if self.log_file:
            self.file_handle = open(self.log_file, 'w', encoding='utf-8')
            self._write_header()

    def _write_header(self) -> None:
        """Write log file header."""
        if self.file_handle:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.file_handle.write(f"Simulation Log - {timestamp}\n")
            self.file_handle.write("="*60 + "\n\n")

    def log(self, message: str, level: str = "info") -> None:
        """
        Log a message.
        
        Args:
            message: Message to log
            level: Log level (info, debug, warning, error)
        """
        if level == "debug" and not self.verbose:
            return

        formatted = self._format_message(message, level)

        # Console output
        print(formatted)

        # File output
        if self.file_handle:
            self.file_handle.write(formatted + "\n")
            self.file_handle.flush()

    def _format_message(self, message: str, level: str) -> str:
        """Format message with level prefix."""
        if level == "error":
            return f"[ERROR] {message}"
        elif level == "warning":
            return f"[WARNING] {message}"
        elif level == "debug":
            return f"[DEBUG] {message}"
        else:
            return message

    def log_step(self, step: int, message: str) -> None:
        """Log a simulation step message."""
        self.log(f"Step {step}: {message}")

    def log_request(
        self,
        step: int,
        pid: int,
        resource_type: int,
        amount: int,
        granted: bool,
        reason: str
    ) -> None:
        """
        Log a resource request.
        
        Args:
            step: Current simulation step
            pid: Process ID
            resource_type: Resource type index
            amount: Amount requested
            granted: Whether request was granted
            reason: Reason for decision
        """
        status = "GRANTED" if granted else "DENIED"
        message = f"P{pid} requests R{resource_type}[{amount}] - {status} ({reason})"
        self.log_step(step, message)

    def log_deadlock(self, step: int, deadlocked_pids: list) -> None:
        """
        Log deadlock detection.
        
        Args:
            step: Current simulation step
            deadlocked_pids: List of PIDs in deadlock
        """
        pids_str = ", ".join(f"P{pid}" for pid in deadlocked_pids)
        message = f"DEADLOCK DETECTED - Processes in deadlock: [{pids_str}]"
        self.log_step(step, message)

    def log_recovery(
        self,
        step: int,
        victim_pid: int,
        priority: int,
        resources_held: str
    ) -> None:
        """
        Log recovery action.
        
        Args:
            step: Current simulation step
            victim_pid: PID of terminated process
            priority: Priority of victim
            resources_held: String describing resources held
        """
        message = (
            f"RECOVERY - Terminated P{victim_pid} "
            f"(priority={priority}, holding {resources_held})"
        )
        self.log_step(step, message)

    def log_system_state(self, step: int, state_str: str) -> None:
        """
        Log system state snapshot.
        
        Args:
            step: Current simulation step
            state_str: Formatted system state
        """
        if self.verbose:
            self.log_step(step, f"System State:\n{state_str}")

    def close(self) -> None:
        """Close log file if open."""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None

    def __del__(self):
        """Cleanup on destruction."""
        self.close()
