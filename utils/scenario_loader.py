"""
Scenario Loader for the Deadlock & Resource Management Simulator.

Loads and validates JSON scenario files with events-based model.
Provides backward compatibility with old requests format.
"""

import json
from typing import Dict, List, Any, Tuple
from pathlib import Path

from models.process import Process, ProcessState
from models.resource import Resource
from models.system_state import SystemState


class ScenarioLoadError(Exception):
    """Exception raised when scenario file cannot be loaded or is invalid."""
    pass


def load_scenario(file_path: str) -> Tuple[SystemState, Dict[int, List[Dict]]]:
    """
    Load scenario from JSON file.
    
    Args:
        file_path: Path to scenario JSON file
        
    Returns:
        Tuple of (SystemState, events_by_step)
        - SystemState: Initialized system with processes and resources
        - events_by_step: Dict mapping step number to list of events
        
    Raises:
        ScenarioLoadError: If file cannot be loaded or is invalid
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        raise ScenarioLoadError(f"Scenario file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ScenarioLoadError(f"Invalid JSON in scenario file: {e}")
    
    # Validate required fields
    if 'processes' not in data:
        raise ScenarioLoadError("Scenario missing 'processes' field")
    if 'resources' not in data:
        raise ScenarioLoadError("Scenario missing 'resources' field")
    
    # Load resources first (needed for validation)
    resources = _load_resources(data['resources'])
    num_resources = len(resources)
    
    # Load processes
    processes = []
    events_by_step = {}
    
    for proc_data in data['processes']:
        process, proc_events = _load_process(proc_data, num_resources)
        processes.append(process)
        
        # Group events by step
        for event in proc_events:
            step = event['step']
            if step not in events_by_step:
                events_by_step[step] = []
            events_by_step[step].append({**event, 'pid': process.pid})
    
    # Validate initial allocations don't exceed available resources
    _validate_initial_allocations(processes, resources)
    
    # Create system state
    system_state = SystemState(processes=processes, resources=resources)
    
    return system_state, events_by_step


def _load_resources(resource_data: List[Dict]) -> List[Resource]:
    """
    Load resource definitions from scenario data.
    
    Args:
        resource_data: List of resource dictionaries
        
    Returns:
        List of Resource objects
    """
    resources = []
    
    for res in resource_data:
        if 'type_id' not in res:
            raise ScenarioLoadError("Resource missing 'type_id' field")
        if 'total_instances' not in res:
            raise ScenarioLoadError(f"Resource {res['type_id']} missing 'total_instances'")
        
        resource = Resource(
            type_id=res['type_id'],
            total_instances=res['total_instances'],
            available_instances=res['total_instances']  # Initially all available
        )
        resources.append(resource)
    
    return sorted(resources, key=lambda r: r.type_id)


def _load_process(proc_data: Dict, num_resources: int) -> Tuple[Process, List[Dict]]:
    """
    Load a single process from scenario data.
    
    Args:
        proc_data: Process dictionary from scenario
        num_resources: Number of resource types in system
        
    Returns:
        Tuple of (Process object, list of events)
    """
    # Validate required fields
    required_fields = ['pid', 'priority', 'arrival_step', 'max_demand']
    for field in required_fields:
        if field not in proc_data:
            raise ScenarioLoadError(f"Process missing required field: {field}")
    
    # Validate max_demand matches resource count
    if len(proc_data['max_demand']) != num_resources:
        raise ScenarioLoadError(
            f"Process {proc_data['pid']}: max_demand length ({len(proc_data['max_demand'])}) "
            f"does not match resource count ({num_resources})"
        )
    
    # Get initial allocation (defaults to all zeros)
    initial_allocation = proc_data.get('initial_allocation', [0] * num_resources)
    if len(initial_allocation) != num_resources:
        raise ScenarioLoadError(
            f"Process {proc_data['pid']}: initial_allocation length mismatch"
        )
    
    # Validate initial allocation doesn't exceed max_demand
    for i, (alloc, max_d) in enumerate(zip(initial_allocation, proc_data['max_demand'])):
        if alloc > max_d:
            raise ScenarioLoadError(
                f"Process {proc_data['pid']}: initial_allocation[{i}] ({alloc}) "
                f"exceeds max_demand[{i}] ({max_d})"
            )
    
    # Create process
    process = Process(
        pid=proc_data['pid'],
        priority=proc_data['priority'],
        arrival_step=proc_data['arrival_step'],
        max_demand=proc_data['max_demand'],
        allocation=initial_allocation.copy(),
        state=ProcessState.READY
    )
    
    # Load events (or convert old requests format)
    events = _load_events(proc_data, process)
    
    return process, events


def _load_events(proc_data: Dict, process: Process) -> List[Dict]:
    """
    Load events for a process.
    Provides backward compatibility with old 'requests' format.
    
    Args:
        proc_data: Process dictionary from scenario
        process: Process object (for validation)
        
    Returns:
        List of event dictionaries
    """
    events = []
    
    # New format: events array
    if 'events' in proc_data:
        for event in proc_data['events']:
            _validate_event(event, process)
            events.append(event)
    
    # Old format: requests array (backward compatibility)
    elif 'requests' in proc_data:
        # Convert requests to request events
        for req in proc_data['requests']:
            event = {
                'step': req['step'],
                'type': 'request',
                'resource_type': req['resource_type'],
                'amount': req['amount']
            }
            _validate_event(event, process)
            events.append(event)
        
        # Add auto-finish event (when allocation == max_demand)
        # This will be checked dynamically during simulation
    
    return sorted(events, key=lambda e: e['step'])


def _validate_event(event: Dict, process: Process) -> None:
    """
    Validate an event for a process.
    
    Args:
        event: Event dictionary
        process: Process object
        
    Raises:
        ScenarioLoadError: If event is invalid
    """
    if 'step' not in event:
        raise ScenarioLoadError(f"Process {process.pid}: event missing 'step' field")
    if 'type' not in event:
        raise ScenarioLoadError(f"Process {process.pid}: event missing 'type' field")
    
    event_type = event['type']
    
    if event_type in ['request', 'release']:
        if 'resource_type' not in event:
            raise ScenarioLoadError(
                f"Process {process.pid}: {event_type} event missing 'resource_type'"
            )
        if 'amount' not in event:
            raise ScenarioLoadError(
                f"Process {process.pid}: {event_type} event missing 'amount'"
            )
        
        # Validate resource type
        if event['resource_type'] < 0 or event['resource_type'] >= len(process.max_demand):
            raise ScenarioLoadError(
                f"Process {process.pid}: invalid resource_type {event['resource_type']}"
            )
        
        # Validate amount
        if event['amount'] <= 0:
            raise ScenarioLoadError(
                f"Process {process.pid}: {event_type} amount must be positive"
            )
        
        # For requests, check it doesn't exceed max_demand
        if event_type == 'request':
            resource_type = event['resource_type']
            # We'll validate against current allocation during simulation
    
    elif event_type == 'finish':
        # Finish events don't need additional fields
        pass
    
    else:
        raise ScenarioLoadError(
            f"Process {process.pid}: unknown event type '{event_type}'"
        )


def _validate_initial_allocations(processes: List[Process], resources: List[Resource]) -> None:
    """
    Validate that initial allocations don't exceed available resources.
    Update resource available_instances accordingly.
    
    Critical validation: For each resource r, sum(allocation[:,r]) <= total[r]
    If this fails, the scenario is invalid.
    
    Args:
        processes: List of processes
        resources: List of resources
        
    Raises:
        ScenarioLoadError: If initial allocations are invalid
    """
    # Calculate total initial allocations per resource type
    total_allocated = [0] * len(resources)
    
    for process in processes:
        for i, amount in enumerate(process.allocation):
            total_allocated[i] += amount
    
    # CRITICAL CHECK: sum(allocation[:,r]) <= total[r] for all r
    for i, resource in enumerate(resources):
        if total_allocated[i] > resource.total_instances:
            raise ScenarioLoadError(
                f"VALIDATION FAILED: Resource R{i} initial allocations ({total_allocated[i]}) "
                f"exceed total instances ({resource.total_instances}).\n"
                f"Sum of process allocations for R{i} must be <= {resource.total_instances}"
            )
        
        # Update available instances
        resource.available_instances = resource.total_instances - total_allocated[i]
        
        # Verify calculation
        assert resource.available_instances >= 0, (
            f"Internal error: R{i} available_instances became negative "
            f"({resource.available_instances})"
        )


def get_scenario_description(file_path: str) -> str:
    """
    Get description from scenario file without full loading.
    
    Args:
        file_path: Path to scenario JSON file
        
    Returns:
        Description string, or empty string if not present
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('description', '')
    except:
        return ''
