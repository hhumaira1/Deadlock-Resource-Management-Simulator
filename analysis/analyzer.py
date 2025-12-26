"""
Performance Analysis Library for the Deadlock & Resource Management Simulator.

Called by simulator.py --analyze to compare policies.
This is a library module, not a standalone CLI tool.
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass
import statistics


@dataclass
class RunResult:
    """Results from a single simulation run."""
    policy: str
    run_number: int
    stop_reason: str
    total_steps: int
    completed_processes: int
    total_processes: int
    deadlock_count: int
    avg_utilization: float
    avg_waiting_time: float
    throughput: float

    def is_successful(self) -> bool:
        """Check if run completed successfully (all processes finished)."""
        return self.completed_processes == self.total_processes or "All processes finished" in self.stop_reason

    def had_deadlock(self) -> bool:
        """Check if run encountered a deadlock."""
        return self.deadlock_count > 0


@dataclass
class PolicyComparisonResult:
    """Results from comparing multiple policies."""
    policy_name: str
    deadlock_frequency: float  # Deadlocks detected / total runs
    avg_resource_utilization: float  # Average % of resources in use
    avg_waiting_time: float  # Average steps processes spend in WAITING
    system_throughput: float  # Completed processes / total simulation steps
    total_runs: int  # Number of simulation runs
    successful_runs: int  # Runs that completed without errors
    deadlock_occurred_count: int = 0  # Runs where deadlock was detected (regardless of recovery)
    finished_count: int = 0  # Runs where all processes finished
    deadlock_halted_count: int = 0  # Runs that halted due to deadlock (detection_only)
    timeout_count: int = 0  # Runs that hit max steps

    def display(self) -> str:
        """Format results for display."""
        result = f"\nPolicy: {self.policy_name.upper()}\n"
        result += f"  Runs: {self.total_runs} total\n"

        # Show deadlock occurrences separately from final outcomes
        if self.deadlock_occurred_count > 0:
            result += (
                f"    Deadlocks detected: {self.deadlock_occurred_count}/{self.total_runs} runs "
                f"({self.deadlock_frequency:.2%})\n"
            )
        else:
            result += f"    Deadlocks detected: 0/{self.total_runs} runs (0.00%)\n"

        result += (
            f"    Final outcomes: Finished={self.finished_count}, "
            f"Halted={self.deadlock_halted_count}, Timeout={self.timeout_count}\n"
        )
        result += f"  Resource Utilization: {self.avg_resource_utilization:.2f}%\n"
        result += f"  Avg Waiting Time: {self.avg_waiting_time:.2f} steps\n"
        result += f"  System Throughput: {self.system_throughput:.4f} processes/step"

        return result


def analyze_policy(
    policy_name: str,
    scenario_path: str,
    num_runs: int = 100,
    detect_interval: int = 1,
    verbose_runs: bool = False,
    run_simulation_func=None,
    stop_reason_func=None
) -> Tuple[PolicyComparisonResult, List[RunResult]]:
    """
    Run multiple simulations and collect metrics for a policy.
    
    Args:
        policy_name: Policy to test (avoidance, detection_only, etc.)
        scenario_path: Path to scenario JSON file
        num_runs: Number of simulation runs
        detect_interval: Steps between deadlock detection
        verbose_runs: Enable verbose output for each run (full step-by-step trace)
        run_simulation_func: Function to run simulation (injected from simulator.py)
        stop_reason_func: Function to get stop reason (injected from simulator.py)
        
    Returns:
        Tuple of (PolicyComparisonResult, List[RunResult])
    """
    if run_simulation_func is None:
        raise ValueError("run_simulation_func must be provided")

    # Collect results from all runs
    run_results: List[RunResult] = []

    print(f"\nRunning {num_runs} simulations for policy: {policy_name.upper()}")

    for run_idx in range(num_runs):
        if (run_idx + 1) % 10 == 0:
            print(f"  Progress: {run_idx + 1}/{num_runs} runs complete")

        try:
            # Run simulation and collect metrics
            # Only show verbose output for first run or if verbose_runs enabled
            show_verbose = verbose_runs or (run_idx == 0)

            # Run simulation - catch any errors during simulation itself
            try:
                event_log, metrics, stop_reason = run_simulation_func(
                    policy=policy_name,
                    scenario_path=scenario_path,
                    detect_interval=detect_interval,
                    verbose=show_verbose
                )
            except Exception as sim_error:
                print(f"  Run {run_idx + 1} SIMULATION FAILED: {sim_error}")
                continue

            # Create RunResult - simulation succeeded, store results
            result = RunResult(
                policy=policy_name,
                run_number=run_idx + 1,
                stop_reason=stop_reason,
                total_steps=metrics.total_steps,
                completed_processes=metrics.completed_processes,
                total_processes=metrics.total_processes,
                deadlock_count=metrics.deadlock_count,
                avg_utilization=metrics.get_avg_utilization(),
                avg_waiting_time=metrics.get_avg_waiting_time(),
                throughput=metrics.get_throughput()
            )
            run_results.append(result)

            # Print one-line summary (unless first run with verbose)
            # Printing errors should NOT affect run success
            if not show_verbose:
                try:
                    status = "[OK]" if result.is_successful() else "[FAIL]"
                    deadlock_marker = "[DEADLOCK]" if result.had_deadlock() else ""
                    print(f"    Run {run_idx + 1}: {status} {result.stop_reason} {deadlock_marker}")
                except Exception:
                    # Ignore printing errors - run still succeeded
                    print(f"    Run {run_idx + 1}: [print error, but run succeeded]")

        except Exception as e:
            print(f"  Run {run_idx + 1} UNEXPECTED ERROR: {e}")
            continue

    # Calculate aggregate metrics from run results
    if not run_results:
        return PolicyComparisonResult(
            policy_name=policy_name,
            deadlock_frequency=0.0,
            avg_resource_utilization=0.0,
            avg_waiting_time=0.0,
            system_throughput=0.0,
            total_runs=num_runs,
            successful_runs=0,
            deadlock_occurred_count=0,
            finished_count=0,
            deadlock_halted_count=0,
            timeout_count=0
        ), run_results

    # Categorize run outcomes
    successful_results = [r for r in run_results if r.is_successful()]
    successful_count = len(successful_results)

    # Track deadlock occurrences (regardless of recovery)
    deadlock_occurred_count = sum(1 for r in run_results if r.had_deadlock())
    deadlock_frequency = deadlock_occurred_count / len(run_results) if run_results else 0.0

    # Track final stop reasons
    finished_count = sum(1 for r in run_results if "All processes finished" in r.stop_reason)
    deadlock_halted_count = sum(1 for r in run_results if "Deadlock detected" in r.stop_reason)
    timeout_count = sum(1 for r in run_results if "Maximum steps" in r.stop_reason)

    # Calculate averages across ALL runs (to show realistic performance)
    avg_utilization = statistics.mean([r.avg_utilization for r in run_results])
    avg_waiting = statistics.mean([r.avg_waiting_time for r in run_results])
    avg_throughput = statistics.mean([r.throughput for r in run_results])

    return PolicyComparisonResult(
        policy_name=policy_name,
        deadlock_frequency=deadlock_frequency,
        avg_resource_utilization=avg_utilization,
        avg_waiting_time=avg_waiting,
        system_throughput=avg_throughput,
        total_runs=num_runs,
        successful_runs=successful_count,
        deadlock_occurred_count=deadlock_occurred_count,
        finished_count=finished_count,
        deadlock_halted_count=deadlock_halted_count,
        timeout_count=timeout_count
    ), run_results


def compare_policies(
    policies: List[str],
    scenario_path: str,
    num_runs: int = 100,
    detect_interval: int = 1,
    verbose_runs: bool = False,
    run_simulation_func=None,
    stop_reason_func=None
) -> Tuple[List[PolicyComparisonResult], Dict[str, List[RunResult]]]:
    """
    Compare multiple policies on the same scenario.
    
    Args:
        policies: List of policy names to compare
        scenario_path: Path to scenario JSON file
        num_runs: Number of runs per policy
        detect_interval: Steps between deadlock detection
        verbose_runs: Enable verbose output for each run
        run_simulation_func: Function to run simulation (injected from simulator.py)
        stop_reason_func: Function to get stop reason (injected from simulator.py)
        
    Returns:
        Tuple of (List[PolicyComparisonResult], Dict[policy_name -> List[RunResult]])
    """
    results = []
    all_run_results = {}

    for policy in policies:
        result, run_results = analyze_policy(
            policy,
            scenario_path,
            num_runs,
            detect_interval,
            verbose_runs,
            run_simulation_func,
            stop_reason_func
        )
        results.append(result)
        all_run_results[policy] = run_results

    return results, all_run_results


def generate_comparison_report(
    results: List[PolicyComparisonResult],
    scenario_path: str,
    num_runs: int
) -> str:
    """
    Generate formatted comparison report.
    
    Args:
        results: List of policy comparison results
        scenario_path: Path to scenario file
        num_runs: Number of runs per policy
        
    Returns:
        Formatted string report
    """
    report = "\n" + "="*70 + "\n"
    report += "POLICY COMPARISON REPORT\n"
    report += "="*70 + "\n"
    report += f"Scenario: {scenario_path}\n"
    report += f"Runs per policy: {num_runs}\n"
    report += "="*70 + "\n"

    for result in results:
        report += result.display()
        report += "\n" + "-"*70

    # Add expected patterns analysis
    report += "\n\nEXPECTED PATTERNS (scenario-dependent):\n"
    report += "-"*70 + "\n"
    report += "  AVOIDANCE:\n"
    report += "    - Deadlock Frequency: Always 0% (prevents unsafe states)\n"
    report += "    - Resource Utilization: Lower (conservative allocation)\n"
    report += "    - Waiting Time: Higher (denies requests to maintain safety)\n"
    report += "    - Throughput: Steady when scenario is satisfiable (safe sequence exists)\n"
    report += "      NOTE: Can still lead to indefinite waiting/timeout if initial\n"
    report += "            availability is zero and no process can make progress.\n"
    report += "\n"
    report += "  DETECTION_ONLY:\n"
    report += "    - Deadlock Frequency: Higher in deadlock-prone scenarios\n"
    report += "    - Resource Utilization: Higher (aggressive allocation)\n"
    report += "    - Waiting Time: Lower until deadlock (if it occurs)\n"
    report += "    - Throughput: Lower if deadlock occurs (simulation halts)\n"
    report += "\n"
    report += "  DETECTION_WITH_RECOVERY:\n"
    report += "    - Deadlock Frequency: Same as detection_only (detects but recovers)\n"
    report += "    - Resource Utilization: Moderate (aggressive but with recovery cost)\n"
    report += "    - Waiting Time: Moderate (processes wait during recovery)\n"
    report += "    - Throughput: Moderate (some processes terminated in recovery)\n"
    report += "\n"
    report += "  NOTE: In scenarios without deadlocks, DETECTION_ONLY and \n"
    report += "        DETECTION_WITH_RECOVERY will show similar metrics.\n"
    report += "        Use demo_detection.json to observe deadlock/recovery behavior.\n"
    report += "\n" + "="*70 + "\n"

    # Add insights section
    report += "\nKEY INSIGHTS:\n"
    report += "-"*70 + "\n"

    # Helper to format ties
    def format_best(metric_name: str, results_list: List[PolicyComparisonResult],
                    key_func, format_func, higher_is_better: bool = True):
        """Format best/worst metric, handling ties. Returns empty string if all policies tied."""
        if higher_is_better:
            target_value = max(key_func(r) for r in results_list)
        else:
            target_value = min(key_func(r) for r in results_list)

        # Find all policies with this value
        winners = [r for r in results_list if key_func(r) == target_value]

        # Skip if all policies are tied (meaningless comparison)
        if len(winners) == len(results_list):
            return ""

        if len(winners) == 1:
            return f"  {metric_name}: {winners[0].policy_name.upper()} ({format_func(target_value)})\n"
        else:
            names = ", ".join(w.policy_name.upper() for w in winners)
            return f"  {metric_name}: {names} (tie at {format_func(target_value)})\n"

    # Find best/worst for each metric
    if len(results) > 1:
        insights = []

        insights.append(format_best(
            "Best Resource Utilization",
            results,
            lambda r: r.avg_resource_utilization,
            lambda v: f"{v:.2f}%",
            higher_is_better=True
        ))

        insights.append(format_best(
            "Lowest Deadlock Frequency",
            results,
            lambda r: r.deadlock_frequency,
            lambda v: f"{v:.2%}",
            higher_is_better=False
        ))

        insights.append(format_best(
            "Best System Throughput",
            results,
            lambda r: r.system_throughput,
            lambda v: f"{v:.4f} processes/step",
            higher_is_better=True
        ))

        insights.append(format_best(
            "Lowest Waiting Time",
            results,
            lambda r: r.avg_waiting_time,
            lambda v: f"{v:.2f} steps",
            higher_is_better=False
        ))

        # Filter out empty strings (all-tie cases)
        insights = [i for i in insights if i]

        if insights:
            for insight in insights:
                report += insight
        else:
            report += "  All policies showed identical performance (complete tie across all metrics).\n"

    report += "\n" + "="*70 + "\n"

    return report
