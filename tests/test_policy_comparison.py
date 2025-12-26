"""
Policy Comparison Tests

Tests the same scenarios across all three policies to validate expected metric patterns:
- AVOIDANCE: 0 deadlocks, possibly lower utilization (conservative)
- DETECTION_ONLY: some deadlocks, higher utilization until deadlock
- DETECTION_WITH_RECOVERY: deadlocks resolved, moderate throughput
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from simulator import run_simulation
from analysis.analyzer import compare_policies


# Test scenarios directory
SCENARIOS_DIR = project_root / "tests" / "scenarios"


def test_guaranteed_deadlock_policy_comparison():
    """
    Compare all policies on guaranteed_deadlock.json scenario.
    
    Expected:
    - AVOIDANCE: 0 deadlocks (prevents unsafe state)
    - DETECTION_ONLY: 1+ deadlocks (detects and halts)
    - DETECTION_WITH_RECOVERY: 1+ deadlocks but resolved
    """
    print("\n" + "="*60)
    print("POLICY COMPARISON TEST: Guaranteed Deadlock Scenario")
    print("="*60)
    
    scenario_path = str(SCENARIOS_DIR / "guaranteed_deadlock.json")
    
    # Run with all three policies
    results = {}
    for policy in ["avoidance", "detection_only", "detection_with_recovery"]:
        print(f"\nRunning with {policy.upper()}...")
        event_log, metrics, stop_reason = run_simulation(policy, scenario_path, 1, False)
        results[policy] = {
            'event_log': event_log,
            'metrics': metrics,
            'stop_reason': stop_reason
        }
    
    # Analyze results
    print("\n" + "-"*60)
    print("RESULTS ANALYSIS")
    print("-"*60)
    
    # AVOIDANCE should have 0 deadlocks
    avoidance_deadlocks = len([e for e in results['avoidance']['event_log'].events
                               if e.event_type.name == "DEADLOCK"])
    print(f"\nAVOIDANCE:")
    print(f"  Deadlocks detected: {avoidance_deadlocks}")
    print(f"  Stop reason: {results['avoidance']['stop_reason']}")
    assert avoidance_deadlocks == 0, "AVOIDANCE should prevent all deadlocks"
    print("  ✓ No deadlocks (as expected)")

    # DETECTION_ONLY should detect deadlock
    detection_deadlocks = len([e for e in results['detection_only']['event_log'].events
                               if e.event_type.name == "DEADLOCK"])
    print(f"\nDETECTION_ONLY:")
    print(f"  Deadlocks detected: {detection_deadlocks}")
    print(f"  Stop reason: {results['detection_only']['stop_reason']}")
    assert detection_deadlocks > 0, "DETECTION_ONLY should detect deadlock"
    assert "deadlock" in results['detection_only']['stop_reason'].lower(), \
        "Should halt on deadlock"
    print("  ✓ Deadlock detected and halted (as expected)")
    
    # RECOVERY should detect and recover
    recovery_deadlocks = len([e for e in results['detection_with_recovery']['event_log'].events 
                              if e.event_type.name == "DEADLOCK"])
    recovery_events = len([e for e in results['detection_with_recovery']['event_log'].events 
                           if e.event_type.name == "RECOVERY"])
    print(f"\nDETECTION_WITH_RECOVERY:")
    print(f"  Deadlocks detected: {recovery_deadlocks}")
    print(f"  Recovery events: {recovery_events}")
    print(f"  Stop reason: {results['detection_with_recovery']['stop_reason']}")
    assert recovery_deadlocks > 0, "Should detect deadlock"
    assert recovery_events > 0, "Should recover from deadlock"
    print("  ✓ Deadlock detected and recovered (as expected)")
    
    print("\n" + "="*60)
    print("✓ POLICY COMPARISON TEST PASSED")
    print("="*60 + "\n")


def test_safe_sequence_policy_comparison():
    """
    Compare all policies on safe_sequence.json scenario.
    
    Expected:
    - All policies should complete without deadlock
    - AVOIDANCE may have fewer denials (grants safe requests)
    - Throughput should be similar across policies
    """
    print("\n" + "="*60)
    print("POLICY COMPARISON TEST: Safe Sequence Scenario")
    print("="*60)
    
    scenario_path = str(SCENARIOS_DIR / "safe_sequence.json")
    
    # Run with all three policies
    results = {}
    for policy in ["avoidance", "detection_only", "detection_with_recovery"]:
        print(f"\nRunning with {policy.upper()}...")
        event_log, metrics, stop_reason = run_simulation(policy, scenario_path, 1, False)
        results[policy] = {
            'event_log': event_log,
            'metrics': metrics,
            'stop_reason': stop_reason
        }
    
    # Analyze results
    print("\n" + "-"*60)
    print("RESULTS ANALYSIS")
    print("-"*60)
    
    for policy in ["avoidance", "detection_only", "detection_with_recovery"]:
        deadlocks = len([e for e in results[policy]['event_log'].events 
                        if e.event_type.name == "DEADLOCK"])
        finished = results[policy]['metrics'].completed_processes
        print(f"  Deadlocks detected: {deadlocks}")
        print(f"  Processes finished: {finished}")
        
        assert deadlocks == 0, f"{policy} should have no deadlocks in safe sequence"
        assert finished > 0, f"{policy} should have finished processes"
        print(f"  ✓ No deadlocks, {finished} processes finished")
    
    print("\n" + "="*60)
    print("✓ SAFE SEQUENCE COMPARISON TEST PASSED")
    print("="*60 + "\n")


def test_metrics_patterns():
    """
    Validate expected metric patterns across policies.
    
    Run guaranteed_deadlock scenario with each policy and verify:
    - AVOIDANCE: Higher waiting time, lower utilization, all finish
    - DETECTION_ONLY: Higher utilization, processes deadlocked
    - RECOVERY: Moderate metrics, some terminated, some finished
    """
    print("\n" + "="*60)
    print("METRICS PATTERNS TEST")
    print("="*60)
    
    scenario_path = str(SCENARIOS_DIR / "guaranteed_deadlock.json")
    
    # Run with all policies
    results = {}
    for policy in ["avoidance", "detection_only", "detection_with_recovery"]:
        print(f"\nRunning {policy.upper()}...")
        event_log, metrics, stop_reason = run_simulation(policy, scenario_path, 1, False)
        results[policy] = metrics
    
    # Display metrics
    print("\n" + "-"*60)
    print("METRICS COMPARISON")
    print("-"*60)
    
    for policy in ["avoidance", "detection_only", "detection_with_recovery"]:
        metrics = results[policy]
        print(f"\n{policy.upper()}:")
        print(f"  Average Utilization: {metrics.get_avg_utilization():.2f}%")
        print(f"  Average Waiting Time: {metrics.get_avg_waiting_time():.2f} steps")
        print(f"  Processes Finished: {metrics.completed_processes}")
        print(f"  Deadlock Count: {metrics.deadlock_count}")
        print(f"  Throughput: {metrics.get_throughput():.4f}")
    
    # Verify patterns
    print("\n" + "-"*60)
    print("PATTERN VALIDATION")
    print("-"*60)
    
    # AVOIDANCE should have 0 deadlocks
    assert results['avoidance'].deadlock_count == 0, \
        "AVOIDANCE should prevent deadlocks"
    print("✓ AVOIDANCE: 0 deadlocks (prevented)")
    
    # DETECTION_ONLY should have deadlocks
    assert results['detection_only'].deadlock_count > 0, \
        "DETECTION_ONLY should detect deadlocks"
    print("✓ DETECTION_ONLY: Deadlocks detected")
    
    # RECOVERY should detect and terminate victims
    assert results['detection_with_recovery'].deadlock_count > 0, \
        "RECOVERY should detect deadlocks"
    print("✓ RECOVERY: Deadlocks detected and handled")
    
    print("\n" + "="*60)
    print("✓ METRICS PATTERNS TEST PASSED")
    print("="*60 + "\n")


def test_utilization_comparison():
    """
    Compare resource utilization across policies.
    
    Expected pattern:
    - DETECTION_ONLY may have higher utilization (optimistic)
    - AVOIDANCE may have lower utilization (conservative)
    - RECOVERY should be moderate
    """
    print("\n" + "="*60)
    print("UTILIZATION COMPARISON TEST")
    print("="*60)
    
    scenario_path = str(SCENARIOS_DIR / "no_deadlock.json")
    
    # Run with all policies
    utilizations = {}
    for policy in ["avoidance", "detection_only", "detection_with_recovery"]:
        print(f"\nRunning {policy.upper()}...")
        event_log, metrics, stop_reason = run_simulation(policy, scenario_path, 1, False)
        utilizations[policy] = metrics.get_avg_utilization()
    
    print("\n" + "-"*60)
    print("UTILIZATION RESULTS")
    print("-"*60)
    
    for policy, util in utilizations.items():
        print(f"{policy.upper()}: {util:.2f}%")
    
    # All should have reasonable utilization (> 0%)
    for policy, util in utilizations.items():
        assert util > 0, f"{policy} should have non-zero utilization"
    
    print("\n✓ All policies show resource utilization")
    print("="*60 + "\n")


def test_analyzer_module():
    """
    Test the analyzer module's compare_policies function.
    """
    print("\n" + "="*60)
    print("ANALYZER MODULE TEST")
    print("="*60)
    
    scenario_path = str(SCENARIOS_DIR / "safe_sequence.json")
    
    print("\nRunning compare_policies()...")
    try:
        comparison, all_run_results = compare_policies(
            policies=["avoidance", "detection_only", "detection_with_recovery"],
            scenario_path=scenario_path,
            num_runs=1,  # Just 1 run for quick test
            run_simulation_func=run_simulation
        )
        
        print("\n✓ Analyzer module executed successfully")
        print(f"  Policies compared: {len(comparison)}")
        
        # Verify each policy has results (comparison is a list of PolicyComparisonResult objects)
        policy_names = [result.policy_name for result in comparison]
        for policy in ["avoidance", "detection_only", "detection_with_recovery"]:
            assert policy in policy_names, f"Missing results for {policy}"
            print(f"  ✓ {policy} results present")
        
        print("\n" + "="*60)
        print("✓ ANALYZER MODULE TEST PASSED")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n✗ Analyzer module test failed: {e}")
        raise


def run_all_comparison_tests():
    """Run all policy comparison tests."""
    print("\n" + "="*60)
    print("POLICY COMPARISON TEST SUITE")
    print("="*60)
    
    tests = [
        ("Guaranteed Deadlock Comparison", test_guaranteed_deadlock_policy_comparison),
        ("Safe Sequence Comparison", test_safe_sequence_policy_comparison),
        ("Metrics Patterns", test_metrics_patterns),
        ("Utilization Comparison", test_utilization_comparison),
        ("Analyzer Module", test_analyzer_module),
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            failed += 1
            errors.append((test_name, str(e)))
            print(f"✗ Test FAILED: {test_name}")
            print(f"  Reason: {e}\n")
        except Exception as e:
            failed += 1
            errors.append((test_name, str(e)))
            print(f"✗ Test ERROR: {test_name}")
            print(f"  Exception: {e}\n")
    
    # Summary
    print("\n" + "="*60)
    print("COMPARISON TEST SUMMARY")
    print("="*60)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if errors:
        print("\nFailed Tests:")
        for test_name, error in errors:
            print(f"  - {test_name}: {error}")
    
    print("\n" + "="*60)
    
    if failed == 0:
        print("✓ ALL COMPARISON TESTS PASSED")
    else:
        print(f"✗ {failed} TESTS FAILED")
    
    print("="*60 + "\n")
    
    return passed, failed


if __name__ == "__main__":
    passed, failed = run_all_comparison_tests()
    sys.exit(0 if failed == 0 else 1)
