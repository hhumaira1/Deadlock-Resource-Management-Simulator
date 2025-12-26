"""
Event Model for the Deadlock & Resource Management Simulator.

Defines event types for tracking simulation actions.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EventType(Enum):
    """Types of events in the simulation."""
    ALLOCATION = "allocation"
    DENIAL = "denial"
    RELEASE = "release"
    DEADLOCK = "deadlock"
    RECOVERY = "recovery"
    FINISH = "finish"


@dataclass
class SimulationEvent:
    """
    Represents a single event in the simulation.
    
    Attributes:
        step: Simulation step when event occurred
        event_type: Type of event
        process_id: PID involved in event
        resource_type: Resource type involved (if applicable)
        amount: Resource amount involved (if applicable)
        message: Human-readable description
        reason: Reason for denial/recovery action (if applicable)
    """
    step: int
    event_type: EventType
    process_id: int
    resource_type: Optional[int] = None
    amount: Optional[int] = None
    message: str = ""
    reason: str = ""

    def __str__(self) -> str:
        """Format event for logging."""
        base = f"Step {self.step}: P{self.process_id}"

        if self.event_type == EventType.ALLOCATION:
            return f"{base} requests R{self.resource_type}[{self.amount}] - GRANTED ({self.reason})"
        elif self.event_type == EventType.DENIAL:
            return f"{base} requests R{self.resource_type}[{self.amount}] - DENIED ({self.reason})"
        elif self.event_type == EventType.RELEASE:
            return f"{base} releases R{self.resource_type}[{self.amount}]"
        elif self.event_type == EventType.DEADLOCK:
            return f"{base} - DEADLOCK DETECTED ({self.message})"
        elif self.event_type == EventType.RECOVERY:
            return f"{base} - RECOVERY ({self.message})"
        elif self.event_type == EventType.FINISH:
            return f"{base} - FINISHED ({self.message})"
        else:
            return f"{base} - {self.event_type.value}: {self.message}"


@dataclass
class EventLog:
    """Collection of simulation events."""
    events: list = None

    def __post_init__(self):
        if self.events is None:
            self.events = []

    def add(self, event: SimulationEvent) -> None:
        """Add an event to the log."""
        self.events.append(event)

    def get_events_by_type(self, event_type: EventType) -> list:
        """Get all events of a specific type."""
        return [e for e in self.events if e.event_type == event_type]

    def get_events_by_step(self, step: int) -> list:
        """Get all events from a specific step."""
        return [e for e in self.events if e.step == step]

    def display(self) -> str:
        """Format all events for display."""
        return "\n".join(str(event) for event in self.events)
