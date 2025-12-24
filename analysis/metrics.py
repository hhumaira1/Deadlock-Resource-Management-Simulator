"""
Metrics Tracking for the Deadlock & Resource Management Simulator.

Tracks performance metrics throughout simulation execution.
"""

from dataclasses import dataclass, field
from typing import List, Dict
import statistics


@dataclass
class SimulationMetrics:
    """Accumulated metrics for a single simulation run."""
    deadlock_count: int = 0
    total_steps: int = 0
    completed_processes: int = 0
    
    # Per-step samples
    utilization_samples: List[float] = field(default_factory=list)
    waiting_time_samples: List[int] = field(default_factory=list)
    
    def record_step(
        self,
        step: int,
        allocated_instances: int,
        total_instances: int,
        waiting_processes: int
    ) -> None:
        """
        Record metrics for a single simulation step.
        
        Args:
            step: Current step number
            allocated_instances: Sum of allocated instances across all resources
            total_instances: Sum of total instances across all resources
            waiting_processes: Number of processes in WAITING state
        """
        self.total_steps = step
        
        # Calculate resource utilization for this step
        if total_instances > 0:
            utilization = (allocated_instances / total_instances) * 100
            self.utilization_samples.append(utilization)
    
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
        self.waiting_time_samples.append(steps_waited)
    
    def get_avg_utilization(self) -> float:
        """Calculate average resource utilization."""
        if not self.utilization_samples:
            return 0.0
        return statistics.mean(self.utilization_samples)
    
    def get_avg_waiting_time(self) -> float:
        """Calculate average waiting time across all processes."""
        if not self.waiting_time_samples:
            return 0.0
        return statistics.mean(self.waiting_time_samples)
    
    def get_throughput(self) -> float:
        """Calculate system throughput (completed processes / total steps)."""
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
