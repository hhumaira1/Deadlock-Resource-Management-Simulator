"""
Performance Analysis Library for the Deadlock & Resource Management Simulator.

Called by simulator.py --analyze to compare policies.
This is a library module, not a standalone CLI tool.
"""

from typing import List, Dict, Any
from dataclasses import dataclass
import statistics

from analysis.metrics import MetricAccumulator


@dataclass
class PolicyComparisonResult:
    """Results from comparing multiple policies."""
    policy_name: str
    deadlock_frequency: float  # Deadlocks detected / total runs
    avg_resource_utilization: float  # Average % of resources in use
    avg_waiting_time: float  # Average steps processes spend in WAITING
    system_throughput: float  # Completed processes / total simulation steps
    
    def display(self) -> str:
        """Format results for display."""
        return (
            f"\nPolicy: {self.policy_name}\n"
            f"  Deadlock Frequency: {self.deadlock_frequency:.2%}\n"
            f"  Resource Utilization: {self.avg_resource_utilization:.2f}%\n"
            f"  Avg Waiting Time: {self.avg_waiting_time:.2f} steps\n"
            f"  System Throughput: {self.system_throughput:.4f} processes/step"
        )


def analyze_policy(
    policy_name: str,
    scenario_path: str,
    num_runs: int = 100
) -> PolicyComparisonResult:
    """
    Run multiple simulations and collect metrics for a policy.
    
    Args:
        policy_name: Policy to test (avoidance, detection_only, etc.)
        scenario_path: Path to scenario JSON file
        num_runs: Number of simulation runs
        
    Returns:
        PolicyComparisonResult with aggregated metrics
    """
    # TODO: Implement multi-run simulation and metric collection
    # Run simulation num_runs times with same scenario
    # Aggregate metrics across runs
    
    return PolicyComparisonResult(
        policy_name=policy_name,
        deadlock_frequency=0.0,
        avg_resource_utilization=0.0,
        avg_waiting_time=0.0,
        system_throughput=0.0
    )


def compare_policies(
    policies: List[str],
    scenario_path: str,
    num_runs: int = 100
) -> List[PolicyComparisonResult]:
    """
    Compare multiple policies on the same scenario.
    
    Args:
        policies: List of policy names to compare
        scenario_path: Path to scenario JSON file
        num_runs: Number of runs per policy
        
    Returns:
        List of PolicyComparisonResult, one per policy
    """
    results = []
    for policy in policies:
        result = analyze_policy(policy, scenario_path, num_runs)
        results.append(result)
    return results


def generate_comparison_report(results: List[PolicyComparisonResult]) -> str:
    """
    Generate formatted comparison report.
    
    Args:
        results: List of policy comparison results
        
    Returns:
        Formatted string report
    """
    report = "\n" + "="*60 + "\n"
    report += "POLICY COMPARISON REPORT\n"
    report += "="*60 + "\n"
    
    for result in results:
        report += result.display()
        report += "\n" + "-"*60
    
    # TODO: Add expected patterns analysis
    report += "\n\nExpected Patterns:\n"
    report += "  AVOIDANCE: 0 deadlocks, possibly lower utilization (conservative)\n"
    report += "  DETECTION_ONLY: some deadlocks, higher utilization until deadlock\n"
    report += "  DETECTION_WITH_RECOVERY: deadlocks resolved, moderate throughput\n"
    
    return report
