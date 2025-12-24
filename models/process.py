"""
Process model for the Deadlock & Resource Management Simulator.

Represents a process in the system with its resource demands and state.
"""

from dataclasses import dataclass, field
from typing import List
from enum import Enum


class ProcessState(Enum):
    """Process states in the simulation."""
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    FINISHED = "FINISHED"
    DEADLOCKED = "DEADLOCKED"
    TERMINATED = "TERMINATED"


@dataclass
class Process:
    """
    Represents a process in the operating system simulation.
    
    Attributes:
        pid: Process identifier (unique)
        priority: Priority level (lower value = higher priority for victim selection)
        arrival_step: Simulation step when process entered the system
        max_demand: Maximum resource demand declared by process [R]
        allocation: Current resource allocation [R]
        state: Current process state
        current_request: Pending resource request [R] (what process is blocked on)
    """
    pid: int
    priority: int
    arrival_step: int
    max_demand: List[int]
    allocation: List[int] = field(default_factory=list)
    state: ProcessState = ProcessState.READY
    current_request: List[int] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize allocation and request vectors if not provided."""
        if not self.allocation:
            self.allocation = [0] * len(self.max_demand)
        if not self.current_request:
            self.current_request = [0] * len(self.max_demand)
    
    def can_request(self, resource_type: int, amount: int) -> bool:
        """
        Check if process can request specified resources.
        
        Args:
            resource_type: Index of resource type
            amount: Number of instances requested
            
        Returns:
            True if request is valid (doesn't exceed max_demand)
        """
        # Validate resource type
        if resource_type < 0 or resource_type >= len(self.max_demand):
            return False
        
        # Request must not exceed max_demand
        if self.allocation[resource_type] + amount > self.max_demand[resource_type]:
            return False
        
        # Amount must be positive
        if amount <= 0:
            return False
        
        return True
    
    def allocate_resource(self, resource_type: int, amount: int) -> None:
        """
        Allocate resources to this process.
        
        Implements Hold and Wait condition: Process keeps current allocation
        while requesting more resources.
        
        Args:
            resource_type: Index of resource type
            amount: Number of instances to allocate
            
        Raises:
            ValueError: If allocation would exceed max_demand
        """
        if not self.can_request(resource_type, amount):
            raise ValueError(
                f"P{self.pid}: Cannot allocate R{resource_type}[{amount}] - "
                f"would exceed max_demand ({self.max_demand[resource_type]})"
            )
        
        self.allocation[resource_type] += amount
        
        # Clear pending request for this resource if it matches
        if self.current_request[resource_type] == amount:
            self.current_request[resource_type] = 0
    
    def release_resource(self, resource_type: int, amount: int) -> None:
        """
        Release resources from this process.
        
        Implements No Preemption condition: Resources are released voluntarily
        by the process (or forcibly by recovery mechanism).
        
        Args:
            resource_type: Index of resource type
            amount: Number of instances to release
            
        Raises:
            ValueError: If trying to release more than currently allocated
        """
        if resource_type < 0 or resource_type >= len(self.allocation):
            raise ValueError(f"P{self.pid}: Invalid resource type {resource_type}")
        
        if amount <= 0:
            raise ValueError(f"P{self.pid}: Release amount must be positive")
        
        if self.allocation[resource_type] < amount:
            raise ValueError(
                f"P{self.pid}: Cannot release R{resource_type}[{amount}] - "
                f"only holding {self.allocation[resource_type]}"
            )
        
        self.allocation[resource_type] -= amount
    
    def is_finished(self) -> bool:
        """
        Check if process has completed execution.
        
        Returns:
            True if process state is FINISHED or TERMINATED
        """
        return self.state in [ProcessState.FINISHED, ProcessState.TERMINATED]
    
    def has_reached_max_demand(self) -> bool:
        """
        Check if process has received all its max_demand resources.
        This is separate from finishing - a process can finish before reaching max.
        
        Returns:
            True if allocation == max_demand
        """
        return self.allocation == self.max_demand
    
    def release_all_resources(self) -> List[int]:
        """
        Release all allocated resources (called when process finishes).
        
        Returns:
            List of released amounts by resource type
        """
        released = self.allocation.copy()
        self.allocation = [0] * len(self.allocation)
        self.current_request = [0] * len(self.current_request)
        return released
    
    def finish(self) -> List[int]:
        """
        Mark process as finished and release all resources.
        Called when a 'finish' event occurs or when process completes naturally.
        
        Returns:
            List of released resource amounts
        """
        self.state = ProcessState.FINISHED
        return self.release_all_resources()
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"Process(pid={self.pid}, priority={self.priority}, "
            f"state={self.state.value}, alloc={self.allocation}, "
            f"max={self.max_demand})"
        )
