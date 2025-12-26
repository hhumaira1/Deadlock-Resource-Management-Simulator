"""
Resource model for the Deadlock & Resource Management Simulator.

Represents a resource type with multiple instances in the system.
"""

from dataclasses import dataclass


@dataclass
class Resource:
    """
    Represents a resource type in the operating system simulation.
    
    Attributes:
        type_id: Resource type identifier
        total_instances: Total number of instances available
        available_instances: Current number of available (unallocated) instances
        
    Invariant:
        0 <= available_instances <= total_instances
    """
    type_id: int
    total_instances: int
    available_instances: int

    def __post_init__(self):
        """Validate resource state."""
        if self.available_instances < 0:
            raise ValueError(f"Resource {self.type_id}: available_instances cannot be negative")
        if self.available_instances > self.total_instances:
            raise ValueError(
                f"Resource {self.type_id}: available ({self.available_instances}) "
                f"exceeds total ({self.total_instances})"
            )

    def allocate(self, amount: int) -> bool:
        """
        Allocate resource instances if available.
        
        Implements Mutual Exclusion condition: Only one process can hold an instance.
        
        Args:
            amount: Number of instances to allocate
            
        Returns:
            True if allocation successful, False if insufficient resources
        """
        if amount > self.available_instances:
            return False
        self.available_instances -= amount
        return True

    def deallocate(self, amount: int) -> None:
        """
        Deallocate (release) resource instances.
        
        Implements No Preemption condition: Resources released voluntarily
        or by recovery mechanism only.
        
        Args:
            amount: Number of instances to release
            
        Raises:
            ValueError: If deallocation would exceed total instances
        """
        if self.available_instances + amount > self.total_instances:
            raise ValueError(
                f"Resource {self.type_id}: deallocation of {amount} would exceed "
                f"total instances ({self.total_instances})"
            )
        self.available_instances += amount
