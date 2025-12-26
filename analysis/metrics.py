"""
Metrics Tracking for the Deadlock & Resource Management Simulator.

Tracks performance metrics throughout simulation execution.
"""

from dataclasses import dataclass, field
from typing import List, Dict
import statistics


@dataclass
class SimulationMetrics:
    """
    Accumulated metrics for a single simulation run.
    
    Tracks four key performance metrics:
    1. Deadlock Occurrence Frequency: Count of deadlocks detected
    2. Resource Utilization %: Average (allocated/total) × 100 per step (includes initial allocations)
    3. Process Waiting Time: Average steps in WAITING state per process
    4. System Throughput: Completed processes / total simulation steps
    """
    deadlock_count: int = 0
    total_steps: int = 0
    completed_processes: int = 0
    total_processes: int = 0

    # Per-step samples
    utilization_samples: List[float] = field(default_factory=list)

    # Per-resource utilization tracking
    resource_utilization_samples: Dict[int, List[float]] = field(default_factory=dict)

    # Per-process tracking
    process_waiting_times: Dict[int, int] = field(default_factory=dict)
    process_granted_counts: Dict[int, int] = field(default_factory=dict)
    process_denied_counts: Dict[int, int] = field(default_factory=dict)
    process_final_states: Dict[int, str] = field(default_factory=dict)
    process_final_allocations: Dict[int, List[int]] = field(default_factory=dict)
    process_pending_requests: Dict[int, List[int]] = field(default_factory=dict)

    def record_step(
        self,
        step: int,
        allocated_instances: int,
        total_instances: int,
        waiting_processes: int,
        per_resource_allocated: Dict[int, int] = None,
        per_resource_total: Dict[int, int] = None
    ) -> None:
        """
        Record metrics for a single simulation step.
        
        Args:
            step: Current step number
            allocated_instances: Sum of allocated instances across all resources
            total_instances: Sum of total instances across all resources
            waiting_processes: Number of processes in WAITING state
            per_resource_allocated: Dict of allocated instances per resource type
            per_resource_total: Dict of total instances per resource type
        """
        self.total_steps = step

        # Calculate overall resource utilization for this step
        if total_instances > 0:
            utilization = (allocated_instances / total_instances) * 100
            self.utilization_samples.append(utilization)

        # Calculate per-resource utilization
        if per_resource_allocated and per_resource_total:
            for resource_id in per_resource_total.keys():
                if resource_id not in self.resource_utilization_samples:
                    self.resource_utilization_samples[resource_id] = []

                if per_resource_total[resource_id] > 0:
                    util = (per_resource_allocated[resource_id] / per_resource_total[resource_id]) * 100
                    self.resource_utilization_samples[resource_id].append(util)

    def record_deadlock(self) -> None:
        """Record a deadlock occurrence."""
        self.deadlock_count += 1

    def record_completion(self) -> None:
        """Record a process completion."""
        self.completed_processes += 1

    def record_waiting_time(self, process_id: int, steps_waited: int) -> None:
        """
        Record waiting time for a process.
        
        Args:
            process_id: Process identifier
            steps_waited: Number of steps process spent in WAITING
        """
        self.process_waiting_times[process_id] = steps_waited

    def set_total_processes(self, count: int) -> None:
        """
        Set the total number of processes in the simulation.
        
        Args:
            count: Total number of processes
        """
        self.total_processes = count

    def record_allocation(self, process_id: int) -> None:
        """
        Record a successful allocation for a process.
        
        Args:
            process_id: Process identifier
        """
        if process_id not in self.process_granted_counts:
            self.process_granted_counts[process_id] = 0
        self.process_granted_counts[process_id] += 1

    def record_denial(self, process_id: int) -> None:
        """
        Record a denied request for a process.
        
        Args:
            process_id: Process identifier
        """
        if process_id not in self.process_denied_counts:
            self.process_denied_counts[process_id] = 0
        self.process_denied_counts[process_id] += 1

    def record_process_final_state(
        self,
        process_id: int,
        state: str,
        allocation: List[int],
        pending: List[int]
    ) -> None:
        """
        Record final state of a process.
        
        Args:
            process_id: Process identifier
            state: Final process state
            allocation: Final resource allocation
            pending: Pending resource requests
        """
        self.process_final_states[process_id] = state
        # Convert numpy types to native Python int to avoid display issues
        self.process_final_allocations[process_id] = [int(x) for x in allocation]
        self.process_pending_requests[process_id] = [int(x) for x in pending]

    def get_avg_utilization(self) -> float:
        """Calculate average resource utilization (overall, includes initial allocations)."""
        if not self.utilization_samples:
            return 0.0
        return statistics.mean(self.utilization_samples)

    def get_resource_utilization(self, resource_id: int) -> float:
        """
        Calculate average utilization for a specific resource.
        
        Args:
            resource_id: Resource type identifier
            
        Returns:
            Average utilization percentage for this resource
        """
        if resource_id not in self.resource_utilization_samples:
            return 0.0
        samples = self.resource_utilization_samples[resource_id]
        if not samples:
            return 0.0
        return statistics.mean(samples)

    def get_avg_waiting_time(self) -> float:
        """
        Calculate average waiting time across all processes.
        
        Formula: Sum of all process waiting times / Number of processes
        """
        if not self.process_waiting_times:
            return 0.0
        return statistics.mean(self.process_waiting_times.values())

    def get_throughput(self) -> float:
        """
        Calculate system throughput (completed processes / total steps).
        
        Formula: Processes reaching FINISHED state / Total simulation steps
        Only counts FINISHED processes, not DEADLOCKED or TERMINATED.
        """
        if self.total_steps == 0:
            return 0.0
        return self.completed_processes / self.total_steps

    def get_deadlock_frequency(self) -> float:
        """Get deadlock frequency (deadlocks / total steps)."""
        if self.total_steps == 0:
            return 0.0
        return self.deadlock_count / self.total_steps


@dataclass
class MetricAccumulator:
    """Accumulates metrics across multiple simulation runs."""
    runs: List[SimulationMetrics] = field(default_factory=list)

    def add_run(self, metrics: SimulationMetrics) -> None:
        """Add metrics from a simulation run."""
        self.runs.append(metrics)

    def get_aggregate_deadlock_frequency(self) -> float:
        """Average deadlock frequency across all runs."""
        if not self.runs:
            return 0.0
        frequencies = [run.get_deadlock_frequency() for run in self.runs]
        return statistics.mean(frequencies)

    def get_aggregate_utilization(self) -> float:
        """Average resource utilization across all runs."""
        if not self.runs:
            return 0.0
        utilizations = [run.get_avg_utilization() for run in self.runs]
        return statistics.mean(utilizations)

    def get_aggregate_waiting_time(self) -> float:
        """Average waiting time across all runs."""
        if not self.runs:
            return 0.0
        waiting_times = [run.get_avg_waiting_time() for run in self.runs]
        return statistics.mean(waiting_times)

    def get_aggregate_throughput(self) -> float:
        """Average throughput across all runs."""
        if not self.runs:
            return 0.0
        throughputs = [run.get_throughput() for run in self.runs]
        return statistics.mean(throughputs)


def format_metrics_report(
    metrics: SimulationMetrics,
    verbose: bool = False,
    policy: str = None,
    scenario: str = None,
    stop_reason: str = None
) -> str:
    """
    Format metrics for display at end of simulation.
    
    Args:
        metrics: SimulationMetrics instance with collected data
        verbose: If True, include per-process breakdown
        policy: Policy used in simulation
        scenario: Scenario file path
        stop_reason: Reason simulation stopped
        
    Returns:
        Formatted metrics report string
    """
    lines = []
    lines.append("\n" + "="*60)
    lines.append("SIMULATION METRICS")
    lines.append("="*60)

    # Simulation info
    if policy:
        lines.append(f"Policy: {policy.upper()}")
    if scenario:
        lines.append(f"Scenario: {scenario}")
    if stop_reason:
        lines.append(f"Stop Reason: {stop_reason}")
    if policy or scenario or stop_reason:
        lines.append("")

    lines.append(f"Total Steps: {metrics.total_steps}")
    lines.append(f"Total Processes: {metrics.total_processes}")
    lines.append(f"Completed Processes: {metrics.completed_processes}")
    lines.append("")

    # Key metrics
    lines.append("KEY PERFORMANCE METRICS:")
    lines.append("-" * 60)
    lines.append(f"1. Deadlock Count: {metrics.deadlock_count}")
    lines.append(f"2. Average Resource Utilization: {metrics.get_avg_utilization():.2f}%")
    lines.append("   (Note: Includes initial allocations)")
    lines.append(f"3. Average Waiting Time: {metrics.get_avg_waiting_time():.2f} steps/process")
    lines.append(f"4. System Throughput: {metrics.get_throughput():.4f} processes/step")

    # Per-resource utilization
    if metrics.resource_utilization_samples:
        lines.append("")
        lines.append("PER-RESOURCE UTILIZATION:")
        lines.append("-" * 60)
        for resource_id in sorted(metrics.resource_utilization_samples.keys()):
            util = metrics.get_resource_utilization(resource_id)
            lines.append(f"  R{resource_id}: {util:.2f}% average")

    # Per-process summary
    if metrics.process_final_states:
        lines.append("")
        lines.append("PER-PROCESS SUMMARY:")
        lines.append("-" * 60)
        for pid in sorted(metrics.process_final_states.keys()):
            state = metrics.process_final_states[pid]
            waiting = metrics.process_waiting_times.get(pid, 0)
            granted = metrics.process_granted_counts.get(pid, 0)
            denied = metrics.process_denied_counts.get(pid, 0)
            alloc = metrics.process_final_allocations.get(pid, [])
            pending = metrics.process_pending_requests.get(pid, [])

            alloc_str = str(alloc) if alloc else "[]"
            pending_str = str(pending) if any(pending) else "none"

            lines.append(
                f"  P{pid}: {state:12} | wait={waiting:2} steps | "
                f"grant={granted:2} deny={denied:2} | alloc={alloc_str} | pending={pending_str}"
            )

    # Metric formulas (verbose mode)
    if verbose:
        lines.append("")
        lines.append("METRIC FORMULAS:")
        lines.append("-" * 60)
        lines.append("1. Deadlock Count: Number of times deadlock was detected")
        lines.append("2. Resource Utilization: Average of (SUM allocated / SUM total) x 100 per step")
        lines.append("   - Sampled at each step, includes initial allocations")
        lines.append("3. Waiting Time: Average of (SUM steps each process spent in WAITING) / # processes")
        lines.append("4. Throughput: (# processes that reached FINISHED state) / (total steps)")

    lines.append("="*60)
    return "\n".join(lines)
