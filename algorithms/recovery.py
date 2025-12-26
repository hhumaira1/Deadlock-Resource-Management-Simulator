"""
Deadlock Recovery Algorithm for the Deadlock & Resource Management Simulator.

Implements process termination and resource preemption strategies.
"""

from typing import List, Tuple, Optional

from models.system_state import SystemState
from models.process import ProcessState


def select_victim(
    deadlocked_pids: List[int],
    system_state: SystemState,
    strategy: str = "priority"
) -> int:
    """
    Select victim process for termination.
    
    Strategies:
    - "priority": Lowest priority value (highest priority number)
    - "fewest_resources": Process holding fewest resources
    - "youngest": Most recently arrived process (highest arrival_step)
    
    Args:
        deadlocked_pids: List of PIDs in deadlock
        system_state: Current system state
        strategy: Selection strategy
        
    Returns:
        PID of selected victim
    """
    if not deadlocked_pids:
        return -1

    if strategy == "priority":
        # Priority: lower value = higher priority
        # Terminate process with highest priority value (lowest priority)
        def get_priority(pid):
            process = next((p for p in system_state.processes if p.pid == pid), None)
            return process.priority if process else 0

        victim_pid = max(deadlocked_pids, key=get_priority)
        return victim_pid

    elif strategy == "fewest_resources":
        # Terminate process holding fewest resources (minimize waste)
        def count_resources(pid):
            process_idx = next((i for i, p in enumerate(system_state.processes) if p.pid == pid), None)
            if process_idx is None:
                return 0
            return sum(system_state.allocation_matrix[process_idx])

        victim_pid = min(deadlocked_pids, key=count_resources)
        return victim_pid

    elif strategy == "youngest":
        # Terminate most recently arrived process
        def get_arrival_step(pid):
            process = next((p for p in system_state.processes if p.pid == pid), None)
            return process.arrival_step if process else 0

        victim_pid = max(deadlocked_pids, key=get_arrival_step)
        return victim_pid

    else:
        # Default: priority strategy
        return select_victim(deadlocked_pids, system_state, "priority")


def terminate_process(pid: int, system_state: SystemState) -> Tuple[bool, str]:
    """
    Terminate a process and release all its resources.
    
    Process termination:
    - Set state to TERMINATED
    - Release all allocated resources (update Available vector)
    - Clear allocation and request vectors
    - No snapshot needed (resources immediately available)
    
    Args:
        pid: Process ID to terminate
        system_state: Current system state
        
    Returns:
        Tuple of (success, message)
    """
    # Find process
    process = next((p for p in system_state.processes if p.pid == pid), None)
    if not process:
        return False, f"Process P{pid} not found"

    # Get process index for matrix operations
    process_idx = system_state.processes.index(process)

    # Record resource counts before clearing
    resources_held = list(system_state.allocation_matrix[process_idx])

    # Clear allocation for VICTIM ONLY
    system_state.allocation_matrix[process_idx] = [0] * system_state.num_resources
    process.allocation = [0] * len(process.max_demand)

    # Clear pending request for VICTIM ONLY
    system_state.request_matrix[process_idx] = [0] * system_state.num_resources
    process.current_request = [0] * len(process.max_demand)

    # Update process state to TERMINATED
    process.state = ProcessState.TERMINATED

    # CRITICAL: Recompute available from total - allocation (single source of truth)
    # This prevents "released but not available" bugs
    import numpy as np
    for resource_idx in range(system_state.num_resources):
        total = system_state.resources[resource_idx].total_instances
        allocated = np.sum(system_state.allocation_matrix[:, resource_idx])
        system_state.resources[resource_idx].available_instances = total - allocated

    # Refresh all matrices to reflect the changes
    system_state.refresh_matrices()

    # SANITY CHECK: Verify resource conservation after termination
    system_state.assert_resource_conservation(f"after terminating P{pid}")

    # Build message describing what resources were released
    resources_str = ", ".join([f"R{i}[{resources_held[i]}]" for i in range(
        len(resources_held)) if resources_held[i] > 0])
    message = f"Terminated P{pid} (priority={process.priority}, holding {resources_str})"

    return True, message


def preempt_resources(
    pid: int,
    resource_type: int,
    amount: int,
    system_state: SystemState
) -> Tuple[bool, str, Optional[dict]]:
    """
    Preempt resources from a process.
    
    Resource preemption:
    - Create state snapshot for rollback
    - Forcibly take resources from process
    - Update Available vector
    - Process may need to be rolled back later
    
    Args:
        pid: Process ID to preempt from
        resource_type: Index of resource type
        amount: Number of instances to preempt
        system_state: Current system state
        
    Returns:
        Tuple of (success, message, snapshot if created else None)
    """
    # Find process
    process = next((p for p in system_state.processes if p.pid == pid), None)
    if not process:
        return False, f"Process P{pid} not found", None

    # Get process index for matrix operations
    process_idx = system_state.processes.index(process)

    # Check if process has enough resources to preempt
    allocated = system_state.allocation_matrix[process_idx][resource_type]
    if allocated < amount:
        return False, f"P{pid} only has {allocated} of R{resource_type}, cannot preempt {amount}", None

    # Create snapshot before preemption
    snapshot = system_state.snapshot()

    # Preempt resources
    system_state.allocation_matrix[process_idx][resource_type] -= amount
    process.allocation[resource_type] -= amount

    # Return resources to available pool
    system_state.available_vector[resource_type] += amount

    # Update need matrix
    system_state.need_matrix[process_idx][resource_type] += amount

    # Mark process as needing rollback (keep in WAITING state if already waiting)
    if process.state == ProcessState.RUNNING or process.state == ProcessState.READY:
        process.state = ProcessState.WAITING

    message = f"Preempted R{resource_type}[{amount}] from P{pid} (now holding {process.allocation[resource_type]})"

    return True, message, snapshot


def recover_from_deadlock(
    deadlocked_pids: List[int],
    system_state: SystemState,
    method: str = "terminate"
) -> Tuple[bool, List[str]]:
    """
    Recover from deadlock by terminating victims or preempting resources.
    
    Methods:
    - "terminate": Kill victim processes until deadlock broken
    - "preempt": Preempt resources from victims (requires rollback support)
    
    Args:
        deadlocked_pids: List of PIDs in deadlock
        system_state: Current system state
        method: Recovery method
        
    Returns:
        Tuple of (success, list of action messages)
    """
    from algorithms.detection import detect_deadlock

    actions = []

    if not deadlocked_pids:
        return False, ["No deadlocked processes to recover"]

    if method == "terminate":
        # Terminate victims one by one until deadlock broken
        remaining_deadlocked = deadlocked_pids.copy()

        while remaining_deadlocked:
            # Select victim using priority strategy (lowest priority = highest priority number)
            victim_pid = select_victim(remaining_deadlocked, system_state, strategy="priority")

            # Terminate the victim
            success, message = terminate_process(victim_pid, system_state)

            if not success:
                actions.append(f"FAILED: {message}")
                return False, actions

            actions.append(f"RECOVERY: {message}")

            # Re-run deadlock detection to see if deadlock is broken
            deadlock_exists, new_deadlocked = detect_deadlock(system_state)

            if not deadlock_exists:
                # Deadlock resolved - reset states for non-terminated processes
                for process in system_state.processes:
                    if process.state == ProcessState.DEADLOCKED:
                        # Reset to WAITING if they have pending requests, otherwise READY
                        if any(process.current_request):
                            process.state = ProcessState.WAITING
                        else:
                            process.state = ProcessState.READY

                actions.append("Deadlock resolved - system restored to safe state")
                return True, actions

            # Update remaining deadlocked processes
            remaining_deadlocked = new_deadlocked

        # If we get here, all deadlocked processes were terminated
        actions.append("All deadlocked processes terminated")
        return True, actions

    elif method == "preempt":
        # Preemption strategy (optional advanced feature)
        # This is more complex and requires careful rollback management
        actions.append("Preemption strategy not fully implemented")

        # Placeholder: would need to identify which resources to preempt
        # and from which processes, then manage snapshots for rollback

        return False, actions

    else:
        return False, [f"Unknown recovery method: {method}"]
