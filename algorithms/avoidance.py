"""
Deadlock Avoidance Algorithm (Banker's Algorithm) for the Simulator.

Implements Banker's Algorithm to prevent system from entering unsafe states.
"""

import numpy as np
from typing import List, Optional, Tuple

from models.system_state import SystemState
from models.process import Process, ProcessState


def is_safe_state(system_state: SystemState) -> Tuple[bool, Optional[List[int]]]:
    """
    Check if system is in a safe state using Banker's Algorithm.
    
    Algorithm:
    1. Initialize Work = Available, Finish = [False] * num_processes
    2. Find process i where Finish[i] == False and Need[i] <= Work
    3. If found: Finish[i] = True, Work += Allocation[i], add PID to sequence
    4. Repeat step 2 until all processes finish (SAFE) or stuck (UNSAFE)
    
    Time Complexity: O(P²×R)
    
    Args:
        system_state: Current system state
        
    Returns:
        Tuple of (is_safe, safe_sequence if exists else None)
        
    References:
        Silberschatz, A., Galvin, P. B., & Gagne, G. (2018).
        Operating System Concepts (10th ed.). Chapter 7.5: Deadlock Avoidance.
    """
    # Step 1: Initialize Work and Finish vectors
    # Work = copy of Available (prevents modification of original)
    work = system_state.available_vector.copy()
    finish = np.zeros(system_state.num_processes, dtype=bool)
    safe_sequence = []

    # Only consider processes that are not FINISHED or TERMINATED
    active_processes = [
        i for i, p in enumerate(system_state.processes)
        if p.state not in [ProcessState.FINISHED, ProcessState.TERMINATED]
    ]

    # Step 2-4: Find processes that can finish with available resources
    # Loop until no more processes can be added to safe sequence
    made_progress = True
    while made_progress:
        made_progress = False

        for i in active_processes:
            # Skip if already marked as finished
            if finish[i]:
                continue

            process = system_state.processes[i]

            # Check if Need[i] <= Work for all resource types
            # Need[i][j] = Max[i][j] - Allocation[i][j]
            need = system_state.need_matrix[i]

            # Check if all resource needs can be satisfied
            if np.all(need <= work):
                # Process can finish: add its allocation back to work
                work += system_state.allocation_matrix[i]
                finish[i] = True
                safe_sequence.append(process.pid)
                made_progress = True
                break  # Restart search from beginning for determinism

    # Check if all active processes could finish
    all_finished = all(finish[i] for i in active_processes)

    if all_finished:
        return True, safe_sequence
    else:
        return False, None


def handle_request(
    process: Process,
    resource_type: int,
    amount: int,
    system_state: SystemState,
    current_step: int = 0
) -> Tuple[bool, str]:
    """
    Handle resource request using Banker's Algorithm.
    
    Steps:
    1. Validate: request <= need (otherwise error)
    2. Check: request <= available (if not, process enters WAITING)
    3. Tentatively allocate resources
    4. Run safety algorithm on new state
    5. If safe: commit allocation, clear pending request
       If unsafe: rollback, process enters WAITING, request stays pending
    
    Args:
        process: Process making the request
        resource_type: Index of resource type
        amount: Number of instances requested
        system_state: Current system state
        current_step: Current simulation step (for waiting time tracking)
        
    Returns:
        Tuple of (granted, reason_string)
    """
    # Step 1: Validate request doesn't exceed need
    # Need = Max - Allocation
    need = process.max_demand[resource_type] - process.allocation[resource_type]

    if amount > need:
        return False, f"Request exceeds need (requested: {amount}, need: {need})"

    if amount <= 0:
        return False, f"Invalid request amount: {amount}"

    # Step 2: Check if resources are available
    available = system_state.resources[resource_type].available_instances

    if amount > available:
        # Process must wait - insufficient resources currently available
        # Set pending request
        process.current_request[resource_type] = amount
        process.enter_waiting(current_step)
        return False, f"Insufficient resources (requested: {amount}, available: {available}) - Process enters WAITING"

    # Step 3: Tentatively allocate resources
    # Save original state for rollback
    original_allocation = process.allocation[resource_type]
    original_available = system_state.resources[resource_type].available_instances

    # Make tentative allocation
    process.allocation[resource_type] += amount
    system_state.resources[resource_type].available_instances -= amount

    # Refresh matrices to reflect tentative allocation
    system_state.refresh_matrices()

    # Step 4: Run safety algorithm
    is_safe, safe_seq = is_safe_state(system_state)

    # Step 5: Decide whether to commit or rollback
    if is_safe:
        # SAFE: Commit allocation, clear pending request
        process.current_request[resource_type] = 0
        if process.state == ProcessState.WAITING:
            process.exit_waiting(current_step)
            process.state = ProcessState.READY

        # SANITY CHECK: Verify resource conservation after grant
        system_state.assert_resource_conservation(f"after granting R{resource_type}[{amount}] to P{process.pid}")

        seq_str = " -> ".join([f"P{pid}" for pid in safe_seq])
        return True, f"GRANTED (Safe state maintained, sequence: {seq_str})"
    else:
        # UNSAFE: Rollback allocation
        process.allocation[resource_type] = original_allocation
        system_state.resources[resource_type].available_instances = original_available

        # Set pending request and enter WAITING state
        process.current_request[resource_type] = amount
        process.enter_waiting(current_step)

        # Refresh matrices after rollback
        system_state.refresh_matrices()

        return False, "DENIED (Unsafe state detected) - Process enters WAITING, request remains pending"


def retry_pending_requests(
    system_state: SystemState,
    attempted_this_step: set = None,
    policy: str = 'avoidance',
    current_step: int = 0
) -> List[Tuple[int, bool, str, int, int]]:
    """
    Retry all pending requests in the Request Matrix.
    
    Called each simulation step to re-attempt blocked requests.
    Processes in PID order for deterministic execution.
    
    Args:
        system_state: Current system state
        attempted_this_step: Set of PIDs that already attempted requests this step (skip these)
        policy: Allocation policy ('avoidance' or 'detection')
        current_step: Current simulation step (for waiting time tracking)
        
    Returns:
        List of (pid, granted, reason, resource_type, amount) tuples for each retry
    """
    results = []

    if attempted_this_step is None:
        attempted_this_step = set()

    # Process requests in PID order for deterministic behavior
    sorted_processes = sorted(system_state.processes, key=lambda p: p.pid)

    for process in sorted_processes:
        # Skip processes that already attempted a request this step
        if process.pid in attempted_this_step:
            continue

        # SANITY CHECK: Skip FINISHED or TERMINATED processes
        # TERMINATED processes MUST NOT retry pending requests
        if process.state in [ProcessState.FINISHED, ProcessState.TERMINATED]:
            continue

        # Check if process has any pending requests in Request Matrix
        process_idx = system_state.processes.index(process)
        has_pending = any(system_state.request_matrix[process_idx] > 0)

        if not has_pending:
            continue

        # Try to grant each pending request
        for resource_type in range(system_state.num_resources):
            # Use request_matrix as single source of truth
            amount = system_state.request_matrix[process_idx][resource_type]

            if amount == 0:
                continue

            # Only retry ONE pending request per step
            # (First non-zero request in resource type order)

            # Attempt to grant the request using appropriate policy
            if policy == 'avoidance':
                granted, reason = handle_request(
                    process,
                    resource_type,
                    amount,
                    system_state,
                    current_step
                )
            else:  # detection policies - use simple allocation
                # Import here to avoid circular dependency
                from simulator import _simple_allocation
                granted, reason = _simple_allocation(
                    process,
                    resource_type,
                    amount,
                    system_state,
                    current_step
                )

            results.append((process.pid, granted, reason, resource_type, amount))
            break  # Only retry first pending request per step
            # If not granted, request remains pending (already set by handle_request)
            # If granted, handle_request clears the pending request

    return results
