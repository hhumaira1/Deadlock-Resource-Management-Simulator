"""
System State model for the Deadlock & Resource Management Simulator.

Maintains global state including all matrices and vectors required for
deadlock detection and avoidance algorithms.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from models.process import Process, ProcessState
from models.resource import Resource


@dataclass
class SystemState:
    """
    Global system state for deadlock simulation.
    
    Maintains all matrices and vectors required for Banker's Algorithm
    and matrix-based deadlock detection.
    
    Attributes:
        processes: List of all processes in the system
        resources: List of all resource types
        allocation_matrix: [P][R] Current resources held by each process
        max_demand_matrix: [P][R] Maximum resource need declared by each process
        available_vector: [R] Free resource instances by type
        request_matrix: [P][R] Current pending resource requests
        need_matrix: [P][R] Computed as Max - Allocation (for Banker's safety check)
        work_vector: [R] Temporary vector for detection algorithm
        finish_vector: [P] Boolean array for detection algorithm
    """
    processes: List[Process] = field(default_factory=list)
    resources: List[Resource] = field(default_factory=list)
    
    # Matrices and vectors (initialized as None, computed on first access)
    _allocation_matrix: Optional[np.ndarray] = None
    _max_demand_matrix: Optional[np.ndarray] = None
    _available_vector: Optional[np.ndarray] = None
    _request_matrix: Optional[np.ndarray] = None
    _need_matrix: Optional[np.ndarray] = None
    _work_vector: Optional[np.ndarray] = None
    _finish_vector: Optional[np.ndarray] = None
    
    @property
    def num_processes(self) -> int:
        """Number of processes in the system."""
        return len(self.processes)
    
    @property
    def num_resources(self) -> int:
        """Number of resource types in the system."""
        return len(self.resources)
    
    @property
    def allocation_matrix(self) -> np.ndarray:
        """Get allocation matrix [P][R]."""
        if self._allocation_matrix is None:
            self._build_allocation_matrix()
        return self._allocation_matrix
    
    @property
    def max_demand_matrix(self) -> np.ndarray:
        """Get max demand matrix [P][R]."""
        if self._max_demand_matrix is None:
            self._build_max_demand_matrix()
        return self._max_demand_matrix
    
    @property
    def available_vector(self) -> np.ndarray:
        """Get available resources vector [R]."""
        if self._available_vector is None:
            self._build_available_vector()
        return self._available_vector
    
    @property
    def request_matrix(self) -> np.ndarray:
        """Get pending request matrix [P][R]."""
        if self._request_matrix is None:
            self._build_request_matrix()
        return self._request_matrix
    
    @property
    def need_matrix(self) -> np.ndarray:
        """
        Get need matrix [P][R].
        Computed as: Need = Max - Allocation
        Used for Banker's Algorithm safety check.
        """
        if self._need_matrix is None:
            self._need_matrix = self.max_demand_matrix - self.allocation_matrix
        return self._need_matrix
    
    def _build_allocation_matrix(self) -> None:
        """Build allocation matrix from process states."""
        self._allocation_matrix = np.zeros((self.num_processes, self.num_resources), dtype=int)
        for i, process in enumerate(self.processes):
            for j in range(self.num_resources):
                self._allocation_matrix[i][j] = process.allocation[j]
    
    def _build_max_demand_matrix(self) -> None:
        """Build max demand matrix from process declarations."""
        self._max_demand_matrix = np.zeros((self.num_processes, self.num_resources), dtype=int)
        for i, process in enumerate(self.processes):
            for j in range(self.num_resources):
                self._max_demand_matrix[i][j] = process.max_demand[j]
    
    def _build_available_vector(self) -> None:
        """Build available resources vector."""
        self._available_vector = np.zeros(self.num_resources, dtype=int)
        for i, resource in enumerate(self.resources):
            self._available_vector[i] = resource.available_instances
    
    def _build_request_matrix(self) -> None:
        """Build pending request matrix from process states."""
        self._request_matrix = np.zeros((self.num_processes, self.num_resources), dtype=int)
        for i, process in enumerate(self.processes):
            for j in range(self.num_resources):
                self._request_matrix[i][j] = process.current_request[j]
    
    def refresh_matrices(self) -> None:
        """Refresh all matrices and vectors from current process/resource state."""
        self._allocation_matrix = None
        self._max_demand_matrix = None
        self._available_vector = None
        self._request_matrix = None
        self._need_matrix = None
        self._work_vector = None
        self._finish_vector = None
    
    def snapshot(self) -> Dict:
        """
        Create snapshot of current system state for rollback.
        Only required for resource preemption, not for process termination.
        
        Returns:
            Dictionary containing serializable state
        """
        return {
            'allocation_matrix': self.allocation_matrix.copy(),
            'available_vector': self.available_vector.copy(),
            'request_matrix': self.request_matrix.copy(),
            'need_matrix': self.need_matrix.copy(),
            'process_states': [(p.pid, p.state, p.allocation.copy(), p.current_request.copy()) 
                               for p in self.processes]
        }
    
    def restore(self, snapshot: Dict) -> None:
        """
        Restore system state from snapshot.
        Used for rolling back preempted processes.
        
        Args:
            snapshot: State dictionary from previous snapshot()
        """
        # Restore matrices
        self._allocation_matrix = snapshot['allocation_matrix'].copy()
        self._available_vector = snapshot['available_vector'].copy()
        self._request_matrix = snapshot['request_matrix'].copy()
        self._need_matrix = snapshot['need_matrix'].copy()
        
        # Restore process states
        for pid, state, allocation, current_request in snapshot['process_states']:
            process = next(p for p in self.processes if p.pid == pid)
            process.state = state
            process.allocation = allocation.copy()
            process.current_request = current_request.copy()
    
    def display(self) -> str:
        """
        Generate readable string representation of system state.
        
        Returns:
            Formatted string showing all matrices and vectors
        """
        output = []
        output.append("\n" + "="*60)
        output.append("SYSTEM STATE")
        output.append("="*60)
        
        # Process states
        output.append("\nProcess States:")
        for i, process in enumerate(self.processes):
            output.append(
                f"  P{process.pid}: {process.state.value:12} "
                f"(priority={process.priority}, arrival={process.arrival_step})"
            )
        
        # Available resources
        output.append("\nAvailable Resources:")
        avail_str = "  ["
        for i in range(self.num_resources):
            avail_str += f"R{i}:{self.available_vector[i]:2}"
            if i < self.num_resources - 1:
                avail_str += ", "
        avail_str += "]"
        output.append(avail_str)
        
        # Allocation Matrix
        output.append("\nAllocation Matrix:")
        output.append("     " + " ".join([f"R{i:2}" for i in range(self.num_resources)]))
        for i, process in enumerate(self.processes):
            row = f"  P{process.pid}: "
            row += " ".join([f"{self.allocation_matrix[i][j]:3}" for j in range(self.num_resources)])
            output.append(row)
        
        # Max Demand Matrix
        output.append("\nMax Demand Matrix:")
        output.append("     " + " ".join([f"R{i:2}" for i in range(self.num_resources)]))
        for i, process in enumerate(self.processes):
            row = f"  P{process.pid}: "
            row += " ".join([f"{self.max_demand_matrix[i][j]:3}" for j in range(self.num_resources)])
            output.append(row)
        
        # Need Matrix
        output.append("\nNeed Matrix (Max - Allocation):")
        output.append("     " + " ".join([f"R{i:2}" for i in range(self.num_resources)]))
        for i, process in enumerate(self.processes):
            row = f"  P{process.pid}: "
            row += " ".join([f"{self.need_matrix[i][j]:3}" for j in range(self.num_resources)])
            output.append(row)
        
        # Request Matrix (pending requests)
        output.append("\nRequest Matrix (Pending):")
        output.append("     " + " ".join([f"R{i:2}" for i in range(self.num_resources)]))
        for i, process in enumerate(self.processes):
            row = f"  P{process.pid}: "
            row += " ".join([f"{self.request_matrix[i][j]:3}" for j in range(self.num_resources)])
            output.append(row)
        
        output.append("\n" + "="*60)
        return "\n".join(output)
    
    def assert_resource_conservation(self, context=""):
        """Verify resource conservation: allocated + available = total for all resources.
        
        Args:
            context: Description of when this check is being run (for error messages)
        
        Raises:
            AssertionError: If resource conservation is violated
        """
        allocation_matrix = self.allocation_matrix
        total_instances = np.array([r.total_instances for r in self.resources])
        
        for r_idx, resource in enumerate(self.resources):
            allocated = allocation_matrix[:, r_idx].sum()
            available = self.available_vector[r_idx]
            total = total_instances[r_idx]
            
            # Check conservation: allocated + available = total
            assert allocated + available == total, (
                f"Resource conservation violated for R{r_idx} {context}\n"
                f"  Allocated: {allocated}, Available: {available}, Total: {total}\n"
                f"  Allocated + Available = {allocated + available} != {total}"
            )
            
            # Check non-negative available
            assert available >= 0, (
                f"Negative available resources for R{r_idx} {context}\n"
                f"  Available: {available}"
            )
