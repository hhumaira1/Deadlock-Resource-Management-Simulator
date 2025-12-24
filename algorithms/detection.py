"""
Deadlock Detection Algorithm for the Deadlock & Resource Management Simulator.

Implements matrix-based deadlock detection (Work/Finish algorithm) for
multi-instance resource systems.
"""

import numpy as np
from typing import List, Tuple

from models.system_state import SystemState
from models.process import ProcessState


def detect_deadlock(system_state: SystemState) -> Tuple[bool, List[int]]:
    """
    Detect deadlock using matrix-based Work/Finish algorithm.
    
    Algorithm (Multi-Instance Resources):
    1. Initialize Work = Available.copy(), Finish = [False] * num_processes
    2. Set Finish[i] = True for processes already FINISHED or TERMINATED
    3. Find process i where Finish[i] == False and Request[i] <= Work (element-wise)
    4. If found: Finish[i] = True, Work += Allocation[i], repeat step 3
    5. If no such process: deadlock exists if any Finish[i] == False
    
    CRITICAL: Uses Request[i] (current pending request), NOT Need[i] (max future request)
    
    Time Complexity: O(P²×R) where P = processes, R = resource types
    
    Four Deadlock Conditions Manifested:
    - Mutual Exclusion: Resource allocation (only one process per instance)
    - Hold and Wait: Process keeps allocation while having pending requests in Request Matrix
    - No Preemption: Resources released only voluntarily or by recovery
    - Circular Wait: Unsatisfiable pending requests; detection identifies the cycle
    
    Args:
        system_state: Current global system state
        
    Returns:
        Tuple of (deadlock_exists, list of deadlocked process PIDs)
        
    References:
        Silberschatz, A., Galvin, P. B., & Gagne, G. (2018).
        Operating System Concepts (10th ed.). Chapter 7: Deadlocks.
    """
    num_processes = system_state.num_processes
    num_resources = system_state.num_resources
    
    # Step 1: Initialize Work and Finish vectors
    work = system_state.available_vector.copy()
    finish = np.array([False] * num_processes)
    
    # Step 2: Mark already completed/terminated processes
    # SANITY CHECK: TERMINATED processes are treated as finished in detection
    for i, process in enumerate(system_state.processes):
        if process.state in [ProcessState.FINISHED, ProcessState.TERMINATED]:
            finish[i] = True
    
    # Step 3-4: Iteratively find processes that can complete
    # CRITICAL: Use Request[i] (current pending request), NOT Need[i] (max future request)
    found_progress = True
    while found_progress:
        found_progress = False
        
        for i, process in enumerate(system_state.processes):
            # Skip if already finished
            if finish[i]:
                continue
            
            # Check if Request[i] <= Work (element-wise)
            # A process can complete if its current pending request can be satisfied
            request = system_state.request_matrix[i]
            can_complete = np.all(request <= work)
            
            if can_complete:
                # Process can complete - add its allocation back to work
                work += system_state.allocation_matrix[i]
                finish[i] = True
                found_progress = True
                # Restart search from beginning for deterministic behavior
                break
    
    # Step 5: Identify deadlocked processes
    # All processes with finish[i] == False are deadlocked
    deadlocked_pids = []
    
    for i, is_finished in enumerate(finish):
        if not is_finished:
            process = system_state.processes[i]
            deadlocked_pids.append(process.pid)
            # Mark process as deadlocked
            process.state = ProcessState.DEADLOCKED
    
    deadlock_exists = len(deadlocked_pids) > 0
    
    return deadlock_exists, deadlocked_pids


def should_run_detection(current_step: int, detect_interval: int) -> bool:
    """
    Determine if detection should run at current simulation step.
    
    Args:
        current_step: Current simulation step number
        detect_interval: Steps between detection checks
        
    Returns:
        True if detection should run
    """
    return current_step % detect_interval == 0
