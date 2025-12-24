#!/usr/bin/env python3
"""
Deadlock & Resource Management Simulator
Main entry point for the simulation system.

CSE323 - Operating Systems
Educational tool for demonstrating deadlock handling strategies.
"""

import argparse
import sys
from typing import Optional, Dict, List

from models.system_state import SystemState
from models.process import ProcessState
from utils.scenario_loader import load_scenario, ScenarioLoadError
from utils.logger import SimulatorLogger
from algorithms.avoidance import handle_request, retry_pending_requests, is_safe_state
from algorithms.detection import detect_deadlock, should_run_detection
from algorithms.recovery import recover_from_deadlock
from analysis.events import EventLog, SimulationEvent, EventType


def run_simulation(
    policy: str,
    scenario_path: str,
    detect_interval: int,
    verbose: bool
) -> EventLog:
    """
    Run the deadlock simulation with specified policy.
    
    Step Ordering (for deterministic execution):
    1. Apply releases/finishes from events (if any)
    2. Retry pending requests in PID order
    3. Apply new requests scheduled for this step (PID order)
    4. Run detection (depending on detect_interval)
    5. If deadlock and recovery enabled → recover, then retry pending once
    
    Args:
        policy: One of 'avoidance', 'detection_only', 'detection_with_recovery'
        scenario_path: Path to scenario JSON file
        detect_interval: Steps between deadlock detection
        verbose: Enable verbose logging
        
    Returns:
        EventLog containing all simulation events
    """
    logger = SimulatorLogger(verbose=verbose)
    event_log = EventLog()
    
    # Load scenario
    try:
        system_state, events_by_step = load_scenario(scenario_path)
    except ScenarioLoadError as e:
        logger.log(f"Failed to load scenario: {e}", "error")
        return event_log
    
    logger.log(f"\n{'='*60}")
    logger.log(f"SIMULATION START: {policy.upper()}")
    logger.log(f"Scenario: {scenario_path}")
    logger.log(f"{'='*60}\n")
    
    # Display initial state
    _display_initial_state(system_state, logger)
    
    # Determine maximum step from events
    max_step = max(events_by_step.keys()) if events_by_step else 10
    
    # Simulation loop
    for step in range(max_step + 5):  # Extra steps for finish/cleanup
        logger.log(f"\n{'-'*60}")
        logger.log(f"Step {step}")
        logger.log(f"{'-'*60}")
        
        # Track which processes have attempted requests this step (max 1 attempt per PID per step)
        attempted_this_step = set()
        
        # Step 1: Apply releases and finishes from scheduled events
        if step in events_by_step:
            _process_events(step, events_by_step[step], system_state, logger, event_log, policy, verbose, attempted_this_step)
        
        # Step 2: Retry pending requests (PID order) - skip processes that already attempted this step
        retry_results = retry_pending_requests(system_state, attempted_this_step, policy)
        for pid, granted, reason, resource_type, amount in retry_results:
            # Log as retry attempt
            status = "GRANTED" if granted else "DENIED"
            logger.log(f"Step {step}: P{pid} retries pending request R{resource_type}[{amount}] - {status} ({reason})")
            
            # Debug: Show available after decision
            if verbose:
                logger.log(f"  Available now: {list(system_state.available_vector)}", "debug")
            
            # CRITICAL: Track all grants in metrics
            event_type = EventType.ALLOCATION if granted else EventType.DENIAL
            event_log.add(SimulationEvent(
                step=step,
                event_type=event_type,
                process_id=pid,
                resource_type=resource_type,
                amount=amount,
                reason=reason
            ))
        
        # Step 4: Run deadlock detection (depending on detect_interval)
        if policy in ['detection_only', 'detection_with_recovery']:
            if should_run_detection(step, detect_interval):
                deadlock_exists, deadlocked_pids = detect_deadlock(system_state)
                
                if deadlock_exists:
                    logger.log(f"\n{'!'*60}")
                    logger.log(f"DEADLOCK DETECTED at Step {step}")
                    logger.log(f"Processes in deadlock: {deadlocked_pids}")
                    logger.log(f"{'!'*60}\n")
                    
                    # Log detailed deadlock info
                    for pid in deadlocked_pids:
                        process = next(p for p in system_state.processes if p.pid == pid)
                        logger.log(f"  P{pid}: allocation={process.allocation}, pending={process.current_request}")
                    
                    # Add deadlock event
                    event_log.add(SimulationEvent(
                        step=step,
                        event_type=EventType.DEADLOCK,
                        process_id=-1,  # No single process - system-wide event
                        message=f"Deadlock detected - processes: {deadlocked_pids}"
                    ))
                    
                    # For DETECTION_ONLY: halt simulation
                    if policy == 'detection_only':
                        logger.log(f"\nPolicy: DETECTION_ONLY - Halting simulation")
                        break
                    
                    # For DETECTION_WITH_RECOVERY: perform recovery
                    if policy == 'detection_with_recovery':
                        logger.log(f"\nPolicy: DETECTION_WITH_RECOVERY - Initiating recovery")
                        
                        # Recover from deadlock using termination strategy
                        success, recovery_actions = recover_from_deadlock(
                            deadlocked_pids,
                            system_state,
                            method="terminate"
                        )
                        
                        # Log recovery actions
                        for action in recovery_actions:
                            logger.log(f"  {action}")
                            
                            # Add recovery events to event log
                            if action.startswith("RECOVERY:"):
                                event_log.add(SimulationEvent(
                                    step=step,
                                    event_type=EventType.RECOVERY,
                                    process_id=-1,  # Multiple processes may be affected
                                    message=action
                                ))
                        
                        if not success:
                            logger.log(f"  Recovery failed - halting simulation", "error")
                            break
                        
                        # Verify resource conservation after recovery
                        if verbose:
                            _verify_resource_conservation(system_state, logger, step)
                            logger.log(f"  Available after recovery: {list(system_state.available_vector)}", "debug")
                            for i, p in enumerate(system_state.processes):
                                if any(system_state.request_matrix[i] > 0):
                                    logger.log(f"  P{p.pid} pending: {list(system_state.request_matrix[i])}", "debug")
                        
                        # After recovery, retry all pending requests once
                        logger.log(f"\n  Retrying pending requests after recovery...")
                        retry_results = retry_pending_requests(system_state, attempted_this_step, policy)
                        for pid, granted, reason, resource_type, amount in retry_results:
                            status = "GRANTED" if granted else "DENIED"
                            logger.log(f"  P{pid} retry R{resource_type}[{amount}] - {status} ({reason})")
                            
                            # CRITICAL: Track post-recovery grants in metrics
                            event_type = EventType.ALLOCATION if granted else EventType.DENIAL
                            event_log.add(SimulationEvent(
                                step=step,
                                event_type=event_type,
                                process_id=pid,
                                resource_type=resource_type,
                                amount=amount,
                                reason=reason
                            ))
                else:
                    if verbose:
                        logger.log(f"  Deadlock check: No deadlock detected", "debug")
        
        # Verify resource conservation invariant (debug check)
        if verbose:
            _verify_resource_conservation(system_state, logger, step)
        
        # Display current state
        if verbose:
            _display_state_snapshot(step, system_state, logger)
        
        # Check if simulation should end
        if _all_processes_finished(system_state):
            logger.log(f"\nAll processes finished at step {step}")
            break
    
    logger.log(f"\n{'='*60}")
    logger.log("SIMULATION COMPLETE")
    logger.log(f"{'='*60}\n")
    
    # Display final statistics
    _display_statistics(system_state, event_log, logger)
    
    logger.close()
    return event_log


def _process_events(
    step: int,
    events: List[Dict],
    system_state: SystemState,
    logger: SimulatorLogger,
    event_log: EventLog,
    policy: str,
    verbose: bool,
    attempted_this_step: set
) -> None:
    """
    Process scheduled events for current step.
    
    Args:
        step: Current simulation step
        events: List of events scheduled for this step
        system_state: Current system state
        logger: Logger instance
        event_log: Event log
        policy: Current policy
        verbose: Enable verbose output
        attempted_this_step: Set of PIDs that have attempted requests this step
    """
    # Sort by PID for deterministic execution
    sorted_events = sorted(events, key=lambda e: e['pid'])
    
    for event in sorted_events:
        pid = event['pid']
        event_type = event['type']
        
        # Find process
        process = next((p for p in system_state.processes if p.pid == pid), None)
        if not process:
            logger.log(f"Process P{pid} not found", "error")
            continue
        
        if event_type == 'request':
            resource_type = event['resource_type']
            amount = event['amount']
            
            # Mark that this process attempted a request this step
            attempted_this_step.add(pid)
            
            # Handle request based on policy
            if policy == 'avoidance':
                granted, reason = handle_request(process, resource_type, amount, system_state)
            else:  # detection_only or detection_with_recovery
                # Grant if available, no safety check
                granted, reason = _simple_allocation(process, resource_type, amount, system_state)
            
            logger.log_request(step, pid, resource_type, amount, granted, reason)
            
            # Debug: Show available and allocation after decision
            if verbose:
                logger.log(f"  Available now: {list(system_state.available_vector)}", "debug")
                logger.log(f"  P{pid} allocation: {process.allocation}", "debug")
            
            evt_type = EventType.ALLOCATION if granted else EventType.DENIAL
            event_log.add(SimulationEvent(
                step=step,
                event_type=evt_type,
                process_id=pid,
                resource_type=resource_type,
                amount=amount,
                reason=reason
            ))
        
        elif event_type == 'release':
            resource_type = event['resource_type']
            amount = event['amount']
            
            # Validate release
            if process.allocation[resource_type] < amount:
                logger.log(f"P{pid} cannot release R{resource_type}[{amount}] - only holds [{process.allocation[resource_type]}]", "error")
                continue
            
            # Release resources
            process.allocation[resource_type] -= amount
            system_state.resources[resource_type].available_instances += amount
            system_state.refresh_matrices()
            
            logger.log(f"Step {step}: P{pid} releases R{resource_type}[{amount}]")
            event_log.add(SimulationEvent(
                step=step,
                event_type=EventType.RELEASE,
                process_id=pid,
                resource_type=resource_type,
                amount=amount
            ))
        
        elif event_type == 'finish':
            # Process explicitly finishes - release all resources
            _finish_process(process, system_state, logger, step)
            event_log.add(SimulationEvent(
                step=step,
                event_type=EventType.FINISH,
                process_id=pid,
                message="Process completed execution"
            ))


def _simple_allocation(process, resource_type: int, amount: int, system_state: SystemState) -> tuple:
    """
    Simple allocation without safety check (for detection policies).
    Grant if request <= available.
    
    Args:
        process: Process making request
        resource_type: Resource type index
        amount: Amount requested
        system_state: System state
        
    Returns:
        Tuple of (granted, reason)
    """
    # Check if request exceeds need
    need = process.max_demand[resource_type] - process.allocation[resource_type]
    if amount > need:
        return False, f"Request exceeds need (requested: {amount}, need: {need})"
    
    # Check availability
    available = system_state.resources[resource_type].available_instances
    if amount > available:
        process.current_request[resource_type] = amount
        process.state = ProcessState.WAITING
        system_state.refresh_matrices()  # Update Request Matrix
        return False, f"Insufficient resources (requested: {amount}, available: {available}) - Process enters WAITING"
    
    # Grant allocation
    process.allocation[resource_type] += amount
    system_state.resources[resource_type].available_instances -= amount
    process.current_request[resource_type] = 0
    if process.state == ProcessState.WAITING:
        process.state = ProcessState.READY
    
    system_state.refresh_matrices()
    
    # SANITY CHECK: Verify resource conservation after grant
    system_state.assert_resource_conservation(f"after granting R{resource_type}[{amount}] to P{process.pid}")
    
    return True, "GRANTED (Resources available)"


def _finish_process(process, system_state: SystemState, logger: SimulatorLogger, step: int) -> None:
    """
    Finish a process and release all its resources.
    
    Args:
        process: Process to finish
        system_state: System state
        logger: Logger instance
        step: Current step
    """
    resources_str = []
    for i, amount in enumerate(process.allocation):
        if amount > 0:
            resources_str.append(f"R{i}[{amount}]")
            system_state.resources[i].available_instances += amount
            process.allocation[i] = 0
    
    process.state = ProcessState.FINISHED
    system_state.refresh_matrices()
    
    # SANITY CHECK: Verify resource conservation after finish
    system_state.assert_resource_conservation(f"after P{process.pid} finished")
    
    resources_released = ", ".join(resources_str) if resources_str else "none"
    logger.log(f"Step {step}: P{process.pid} - FINISHED (released: {resources_released})")


def _find_pending_resource(system_state: SystemState, pid: int) -> Optional[int]:
    """Find first resource type with pending request for process."""
    process = next((p for p in system_state.processes if p.pid == pid), None)
    if not process:
        return None
    for i, amount in enumerate(process.current_request):
        if amount > 0:
            return i
    return None


def _verify_resource_conservation(system_state: SystemState, logger: SimulatorLogger, step: int) -> None:
    """Verify resource conservation invariant: sum(allocation[:,r]) + available[r] == total[r]."""
    for r_idx, resource in enumerate(system_state.resources):
        total_allocated = sum(p.allocation[r_idx] for p in system_state.processes)
        available = resource.available_instances
        total = resource.total_instances
        
        if total_allocated + available != total:
            error_msg = (
                f"INVARIANT VIOLATION at step {step}: "
                f"R{r_idx} allocated={total_allocated} + available={available} = {total_allocated + available} != total={total}"
            )
            logger.log(error_msg, "error")
            raise RuntimeError(error_msg)
        else:
            logger.log(f"  R{r_idx} conservation check: {total_allocated} + {available} = {total} [OK]", "debug")


def _all_processes_finished(system_state: SystemState) -> bool:
    """Check if all processes are finished or terminated."""
    return all(
        p.state in [ProcessState.FINISHED, ProcessState.TERMINATED]
        for p in system_state.processes
    )


def _display_initial_state(system_state: SystemState, logger: SimulatorLogger) -> None:
    """Display initial system state."""
    logger.log("Initial System State:")
    logger.log("\nProcesses:")
    for p in system_state.processes:
        logger.log(f"  P{p.pid}: priority={p.priority}, max_demand={p.max_demand}, allocation={p.allocation}")
    
    logger.log("\nResources:")
    for r in system_state.resources:
        logger.log(f"  R{r.type_id}: total={r.total_instances}, available={r.available_instances}")


def _display_state_snapshot(step: int, system_state: SystemState, logger: SimulatorLogger) -> None:
    """Display current state snapshot."""
    logger.log("\n[State Snapshot]")
    logger.log(f"Available: {list(system_state.available_vector)}")
    
    for i, p in enumerate(system_state.processes):
        alloc = list(system_state.allocation_matrix[i])
        need = list(system_state.need_matrix[i])
        req = list(system_state.request_matrix[i])
        logger.log(f"P{p.pid}: state={p.state.value}, alloc={alloc}, need={need}, pending={req}")


def _display_statistics(system_state: SystemState, event_log: EventLog, logger: SimulatorLogger) -> None:
    """Display final simulation statistics."""
    logger.log("\nSimulation Statistics:")
    
    total_processes = len(system_state.processes)
    finished = sum(1 for p in system_state.processes if p.state == ProcessState.FINISHED)
    terminated = sum(1 for p in system_state.processes if p.state == ProcessState.TERMINATED)
    
    logger.log(f"  Total Processes: {total_processes}")
    logger.log(f"  Finished: {finished}")
    logger.log(f"  Terminated: {terminated}")
    
    allocations = len(event_log.get_events_by_type(EventType.ALLOCATION))
    denials = len(event_log.get_events_by_type(EventType.DENIAL))
    deadlocks = len(event_log.get_events_by_type(EventType.DEADLOCK))
    
    logger.log(f"\n  Successful Allocations: {allocations}")
    logger.log(f"  Denials: {denials}")
    logger.log(f"  Deadlocks Detected: {deadlocks}")


def main():
    """Main entry point for the simulator."""
    parser = argparse.ArgumentParser(
        description='Deadlock & Resource Management Simulator'
    )
    parser.add_argument(
        '--policy',
        choices=['avoidance', 'detection_only', 'detection_with_recovery'],
        required=True,
        help='Deadlock handling policy to use'
    )
    parser.add_argument(
        '--scenario',
        type=str,
        required=True,
        help='Path to scenario JSON file'
    )
    parser.add_argument(
        '--detect-interval',
        type=int,
        default=1,
        help='Steps between deadlock detection checks (default: 1)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--analyze',
        action='store_true',
        help='Run performance analysis mode'
    )
    parser.add_argument(
        '--compare-policies',
        action='store_true',
        help='Compare all policies (requires --analyze)'
    )
    parser.add_argument(
        '--runs',
        type=int,
        default=1,
        help='Number of simulation runs for analysis (default: 1)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.compare_policies and not args.analyze:
        parser.error('--compare-policies requires --analyze')
    
    # Run simulation
    if args.analyze:
        print("[Analysis mode not yet implemented]")
        return 1
    else:
        run_simulation(args.policy, args.scenario, args.detect_interval, args.verbose)
        return 0


if __name__ == '__main__':
    sys.exit(main())
