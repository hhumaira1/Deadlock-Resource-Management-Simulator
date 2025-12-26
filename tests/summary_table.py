"""
Summary table generator for Phase 7 test results.
Creates a comparison table: Scenario × Policy → Metrics
"""

from typing import List, Dict, Tuple
from pathlib import Path


class TestResultSummary:
    """Collects and displays test results in table format."""
    
    def __init__(self):
        self.results = []
    
    def add_result(self, test_name: str, scenario: str, policy: str, 
                   deadlocks: int, denials: int, finished: int, 
                   terminated: int, stop_reason: str, passed: bool):
        """Add a test result to the summary."""
        self.results.append({
            'test_name': test_name,
            'scenario': Path(scenario).stem,
            'policy': policy,
            'deadlocks': deadlocks,
            'denials': denials,
            'finished': finished,
            'terminated': terminated,
            'stop_reason': stop_reason,
            'passed': 'PASS' if passed else 'FAIL'
        })
    
    def print_table(self):
        """Print formatted summary table."""
        print("\n" + "="*140)
        print("PHASE 7 TEST RESULTS SUMMARY TABLE")
        print("="*140)
        
        # Header
        print(f"{'Test':<5} {'Scenario':<25} {'Policy':<20} {'DL':>3} {'Deny':>5} {'Fin':>4} {'Term':>4} {'Stop Reason':<25} {'Result':<6}")
        print("-"*140)
        
        # Data rows
        for r in self.results:
            test_num = r['test_name'].split(':')[0].replace('Test ', '')
            scenario = r['scenario'].replace('_', ' ')[:24]
            policy = r['policy'].replace('detection_with_recovery', 'RECOVERY')[:19]
            
            print(f"{test_num:<5} {scenario:<25} {policy:<20} "
                  f"{r['deadlocks']:>3} {r['denials']:>5} {r['finished']:>4} {r['terminated']:>4} "
                  f"{r['stop_reason']:<25} {r['passed']:<6}")
        
        print("="*140)
        
        # Summary stats
        total = len(self.results)
        passed = sum(1 for r in self.results if r['passed'] == 'PASS')
        failed = total - passed
        
        print(f"\nOverall: {passed}/{total} tests passed, {failed} failed")
        print("="*140 + "\n")
    
    def print_policy_comparison(self):
        """Print policy comparison grouped by scenario."""
        print("\n" + "="*100)
        print("POLICY COMPARISON BY SCENARIO")
        print("="*100)
        
        # Group by scenario
        scenarios = {}
        for r in self.results:
            scenario = r['scenario']
            if scenario not in scenarios:
                scenarios[scenario] = []
            scenarios[scenario].append(r)
        
        for scenario_name, results in scenarios.items():
            print(f"\n{scenario_name.replace('_', ' ').upper()}")
            print("-"*100)
            print(f"{'Policy':<25} {'Deadlocks':>10} {'Denials':>10} {'Finished':>10} {'Terminated':>10} {'Stop Reason':<25}")
            print("-"*100)
            
            for r in results:
                policy = r['policy'].replace('detection_with_recovery', 'RECOVERY')
                print(f"{policy:<25} {r['deadlocks']:>10} {r['denials']:>10} "
                      f"{r['finished']:>10} {r['terminated']:>10} {r['stop_reason']:<25}")
        
        print("="*100 + "\n")


def create_summary_table():
    """Factory function to create a new summary table."""
    return TestResultSummary()
