"""
Verify sanity checks are working:
1. Resource conservation after every grant/release/terminate
2. Terminated processes don't retry
3. Terminated processes treated as finished in detection
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from utils.scenario_loader import load_scenario
from models.system_state import SystemState, ProcessState
from algorithms.detection import detect_deadlock
from algorithms.recovery import terminate_process
from algorithms.avoidance import retry_pending_requests

# Load demo_recovery scenario
scenario_path = "scenarios/demo_recovery.json"
system_state, _ = load_scenario(scenario_path)  # Returns (system_state, scenario_data)

print("="*60)
print("SANITY CHECK VERIFICATION")
print("="*60)

# Initial state conservation
print("\n1. Initial state conservation check...")
try:
    system_state.assert_resource_conservation("at initial state")
    print("   ✓ Resource conservation verified at initial state")
except AssertionError as e:
    print(f"   ✗ FAILED: {e}")
    sys.exit(1)

# Create a deadlock situation manually
print("\n2. Setting up deadlock scenario...")
p1 = system_state.processes[0]
p2 = system_state.processes[1]
p3 = system_state.processes[2]

# Set pending requests
p1.current_request = [0, 2, 0]
p2.current_request = [0, 0, 2]
p3.current_request = [2, 0, 0]
system_state.refresh_matrices()

deadlock_exists, deadlocked_pids = detect_deadlock(system_state)
print(f"   Deadlock detected: {deadlock_exists}, processes: {deadlocked_pids}")

# Terminate P3
print("\n3. Terminating P3...")
success, message = terminate_process(3, system_state)
print(f"   {message}")
print(f"   P3 state: {p3.state}")

# Verify conservation after termination
print("\n4. Resource conservation after termination...")
try:
    system_state.assert_resource_conservation("after terminating P3")
    print("   ✓ Resource conservation verified after termination")
except AssertionError as e:
    print(f"   ✗ FAILED: {e}")
    sys.exit(1)

# Verify P3 doesn't retry
print("\n5. Verify TERMINATED process doesn't retry...")
retry_results = retry_pending_requests(system_state, set(), 'detection_only')
retry_pids = [pid for pid, _, _, _, _ in retry_results]
if 3 not in retry_pids:
    print(f"   ✓ P3 (TERMINATED) not in retry list: {retry_pids}")
else:
    print(f"   ✗ FAILED: P3 should not retry but found in: {retry_pids}")
    sys.exit(1)

# Verify P3 treated as finished in detection
print("\n6. Verify TERMINATED process treated as finished in detection...")
deadlock_exists, deadlocked_pids = detect_deadlock(system_state)
if 3 not in deadlocked_pids:
    print(f"   ✓ P3 (TERMINATED) not in deadlock list: {deadlocked_pids}")
else:
    print(f"   ✗ FAILED: P3 should be treated as finished, but in deadlock: {deadlocked_pids}")
    sys.exit(1)

# Verify negative available check would trigger
print("\n7. Verify negative available check (simulated violation)...")
try:
    original_available = system_state.available_vector[0]
    system_state.available_vector[0] = -1
    system_state.assert_resource_conservation("negative available test")
    print("   ✗ FAILED: Should have caught negative available")
    sys.exit(1)
except AssertionError as e:
    system_state.available_vector[0] = original_available
    print(f"   ✓ Negative available properly detected")

print("\n" + "="*60)
print("ALL SANITY CHECKS PASSED ✓")
print("="*60)
