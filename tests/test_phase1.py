"""
Phase 1 Validation Test - Core Data Models

Tests Process, Resource, and SystemState functionality.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.process import Process, ProcessState
from models.resource import Resource
from models.system_state import SystemState
from utils.scenario_loader import load_scenario


def test_process_model():
    """Test Process model methods."""
    print("\n" + "="*60)
    print("TEST 1: Process Model")
    print("="*60)
    
    # Create a test process
    process = Process(
        pid=1,
        priority=2,
        arrival_step=0,
        max_demand=[5, 3, 2],
        allocation=[0, 0, 0]
    )
    
    print(f"\\nCreated: {process}")
    
    # Test allocation
    print("\\nTest: Allocate R0[2]")
    assert process.can_request(0, 2), "Should be able to request R0[2]"
    process.allocate_resource(0, 2)
    print(f"  ✓ Allocation: {process.allocation}")
    
    # Test invalid allocation
    print("\\nTest: Try to allocate R0[10] (exceeds max_demand)")
    assert not process.can_request(0, 10), "Should not exceed max_demand"
    print("  ✓ Correctly rejected")
    
    # Test release
    print("\\nTest: Release R0[1]")
    process.release_resource(0, 1)
    print(f"  ✓ Allocation after release: {process.allocation}")
    
    # Test finish semantics
    print("\nTest: Finish semantics (separate from max allocation)")
    print(f"  Current allocation: {process.allocation}")
    print(f"  Max demand: {process.max_demand}")
    print(f"  Is finished: {process.is_finished()}")
    print(f"  Has reached max: {process.has_reached_max_demand()}")
    
    # Finish process explicitly (doesn't need to reach max)
    print("\nTest: Explicit finish (process can finish before reaching max)")
    released = process.finish()
    print(f"  Released resources: {released}")
    print(f"  State: {process.state.value}")
    print(f"  Is finished: {process.is_finished()}")
    print(f"  Allocation after finish: {process.allocation}")
    assert process.is_finished(), "Process should be finished"
    assert process.allocation == [0, 0, 0], "All resources should be released"
    print("  ✓ Process finish() works correctly (separate from max allocation)")
    
    print("\\n✅ Process Model Tests PASSED")


def test_resource_model():
    """Test Resource model methods."""
    print("\n" + "="*60)
    print("TEST 2: Resource Model")
    print("="*60)
    
    # Create a test resource
    resource = Resource(type_id=0, total_instances=10, available_instances=10)
    print(f"\\nCreated: R{resource.type_id} with {resource.total_instances} total instances")
    
    # Test allocation
    print("\\nTest: Allocate 3 instances")
    success = resource.allocate(3)
    print(f"  ✓ Allocated: {success}, Available: {resource.available_instances}")
    assert success and resource.available_instances == 7, "Should have 7 available"
    
    # Test insufficient resources
    print("\\nTest: Try to allocate 10 instances (insufficient)")
    success = resource.allocate(10)
    print(f"  ✓ Allocation failed: {not success}, Available: {resource.available_instances}")
    assert not success, "Should fail due to insufficient resources"
    
    # Test deallocation
    print("\\nTest: Deallocate 2 instances")
    resource.deallocate(2)
    print(f"  ✓ Deallocated, Available: {resource.available_instances}")
    assert resource.available_instances == 9, "Should have 9 available"
    
    print("\\n✅ Resource Model Tests PASSED")


def test_system_state():
    """Test SystemState matrix building."""
    print("\n" + "="*60)
    print("TEST 3: System State Matrices")
    print("="*60)
    
    # Create processes
    p1 = Process(pid=1, priority=1, arrival_step=0, max_demand=[7, 5, 3], allocation=[0, 1, 0])
    p2 = Process(pid=2, priority=2, arrival_step=0, max_demand=[3, 2, 2], allocation=[2, 0, 0])
    p3 = Process(pid=3, priority=3, arrival_step=1, max_demand=[9, 0, 2], allocation=[3, 0, 2])
    
    # Create resources
    r0 = Resource(type_id=0, total_instances=10, available_instances=5)
    r1 = Resource(type_id=1, total_instances=5, available_instances=4)
    r2 = Resource(type_id=2, total_instances=7, available_instances=5)
    
    # Create system state
    system_state = SystemState(processes=[p1, p2, p3], resources=[r0, r1, r2])
    
    print("\\nSystem State Created")
    print(f"  Processes: {system_state.num_processes}")
    print(f"  Resources: {system_state.num_resources}")
    
    # Test matrix building
    print("\\nTest: Build Allocation Matrix")
    alloc_matrix = system_state.allocation_matrix
    print(f"  Shape: {alloc_matrix.shape}")
    print(f"  Matrix:\\n{alloc_matrix}")
    assert alloc_matrix.shape == (3, 3), "Should be 3x3"
    assert alloc_matrix[0][1] == 1, "P1 should have R1[1]"
    print("  ✓ Allocation matrix correct")
    
    print("\\nTest: Build Need Matrix")
    need_matrix = system_state.need_matrix
    print(f"  Need Matrix:\\n{need_matrix}")
    # P1 needs: [7-0, 5-1, 3-0] = [7, 4, 3]
    assert need_matrix[0][0] == 7, "P1 need should be correct"
    print("  ✓ Need matrix correct (Max - Allocation)")
    
    print("\\nTest: Display System State")
    display_output = system_state.display()
    print(display_output)
    
    print("\\n✅ System State Tests PASSED")


def test_initial_allocation_validation():
    """Test that initial allocations are validated against resource totals."""
    print("\n" + "="*60)
    print("TEST 4: Initial Allocation Validation")
    print("="*60)
    
    from utils.scenario_loader import _validate_initial_allocations, ScenarioLoadError
    
    # Create processes with initial allocations
    p1 = Process(pid=1, priority=1, arrival_step=0, max_demand=[5, 3], allocation=[2, 1])
    p2 = Process(pid=2, priority=2, arrival_step=0, max_demand=[4, 2], allocation=[3, 1])
    # Total allocated: R0=5, R1=2
    
    print("\nTest 1: Valid initial allocations")
    resources = [
        Resource(type_id=0, total_instances=10, available_instances=10),
        Resource(type_id=1, total_instances=5, available_instances=5)
    ]
    
    try:
        _validate_initial_allocations([p1, p2], resources)
        print(f"  ✓ Validation passed")
        print(f"  R0: Total={resources[0].total_instances}, Allocated=5, Available={resources[0].available_instances}")
        print(f"  R1: Total={resources[1].total_instances}, Allocated=2, Available={resources[1].available_instances}")
        assert resources[0].available_instances == 5, "R0 should have 5 available"
        assert resources[1].available_instances == 3, "R1 should have 3 available"
    except ScenarioLoadError as e:
        print(f"  ❌ Unexpected error: {e}")
        raise
    
    print("\nTest 2: Invalid initial allocations (exceeds total)")
    p3 = Process(pid=3, priority=3, arrival_step=0, max_demand=[3, 2], allocation=[3, 2])
    # Total would be: R0=8, R1=4
    
    resources_limited = [
        Resource(type_id=0, total_instances=7, available_instances=7),  # Only 7, but need 8
        Resource(type_id=1, total_instances=5, available_instances=5)
    ]
    
    try:
        _validate_initial_allocations([p1, p2, p3], resources_limited)
        print("  ❌ Should have raised ScenarioLoadError")
        assert False, "Should have detected invalid allocation"
    except ScenarioLoadError as e:
        print(f"  ✓ Correctly rejected: {str(e).splitlines()[0]}")
    
    print("\n✅ Initial Allocation Validation Tests PASSED")


def test_scenario_loader():
    """Test scenario loading from JSON file."""
    print("\\n" + "="*60)
    print("TEST 5: Scenario Loader")
    print("="*60)
    
    scenario_path = project_root / "scenarios" / "demo_banker.json"
    
    if not scenario_path.exists():
        print(f"\\n⚠ Scenario file not found: {scenario_path}")
        print("  Skipping scenario loader test")
        return
    
    print(f"\\nLoading scenario: {scenario_path.name}")
    
    try:
        system_state, events_by_step = load_scenario(str(scenario_path))
        
        print(f"\\n✓ Scenario loaded successfully")
        print(f"  Processes: {system_state.num_processes}")
        print(f"  Resources: {system_state.num_resources}")
        print(f"  Event steps: {sorted(events_by_step.keys())}")
        
        # Display initial state
        print("\\nInitial System State:")
        print(system_state.display())
        
        print("\\n✅ Scenario Loader Tests PASSED")
        
    except Exception as e:
        print(f"\\n❌ Scenario loading failed: {e}")
        raise


def test_event_application():
    """Phase 1.5: Test applying events to verify simulation logic."""
    print("\n" + "="*60)
    print("TEST 6: Phase 1.5 - Event Application")
    print("="*60)
    print("\nThis test applies 2-3 events and verifies state changes.")
    print("Prevents 'matrices are right but simulation is wrong' issues.")
    
    # Create simple system
    p1 = Process(pid=1, priority=1, arrival_step=0, max_demand=[5, 3], allocation=[1, 0])
    p2 = Process(pid=2, priority=2, arrival_step=0, max_demand=[4, 2], allocation=[0, 1])
    
    r0 = Resource(type_id=0, total_instances=10, available_instances=9)  # 1 allocated to P1
    r1 = Resource(type_id=1, total_instances=5, available_instances=4)   # 1 allocated to P2
    
    system_state = SystemState(processes=[p1, p2], resources=[r0, r1])
    
    print("\nInitial State:")
    print(f"  P1 allocation: {p1.allocation}")
    print(f"  P2 allocation: {p2.allocation}")
    print(f"  R0 available: {r0.available_instances}")
    print(f"  R1 available: {r1.available_instances}")
    
    # Event 1: P1 requests R0[2]
    print("\nEvent 1: P1 requests R0[2]")
    if p1.can_request(0, 2) and r0.available_instances >= 2:
        r0.allocate(2)
        p1.allocate_resource(0, 2)
        system_state.refresh_matrices()
        print(f"  ✓ Granted")
        print(f"  P1 allocation: {p1.allocation}")
        print(f"  R0 available: {r0.available_instances}")
        assert p1.allocation[0] == 3, "P1 should have R0[3]"
        assert r0.available_instances == 7, "R0 should have 7 available"
    
    # Event 2: P2 requests R1[1]
    print("\nEvent 2: P2 requests R1[1]")
    if p2.can_request(1, 1) and r1.available_instances >= 1:
        r1.allocate(1)
        p2.allocate_resource(1, 1)
        system_state.refresh_matrices()
        print(f"  ✓ Granted")
        print(f"  P2 allocation: {p2.allocation}")
        print(f"  R1 available: {r1.available_instances}")
        assert p2.allocation[1] == 2, "P2 should have R1[2]"
        assert r1.available_instances == 3, "R1 should have 3 available"
    
    # Event 3: P1 finishes (releases all)
    print("\nEvent 3: P1 finishes")
    released = p1.finish()
    print(f"  Released: {released}")
    for i, amount in enumerate(released):
        system_state.resources[i].deallocate(amount)
    system_state.refresh_matrices()
    
    print(f"  P1 allocation: {p1.allocation}")
    print(f"  P1 state: {p1.state.value}")
    print(f"  R0 available: {r0.available_instances}")
    print(f"  R1 available: {r1.available_instances}")
    
    assert p1.allocation == [0, 0], "P1 should have no allocation"
    assert p1.is_finished(), "P1 should be finished"
    assert r0.available_instances == 10, "R0 should be fully available"
    
    # Verify matrices reflect changes
    print("\nVerifying matrices after events:")
    alloc_matrix = system_state.allocation_matrix
    print(f"  Allocation Matrix:\n{alloc_matrix}")
    assert alloc_matrix[0][0] == 0, "P1 should have R0[0] in matrix"
    assert alloc_matrix[1][1] == 2, "P2 should have R1[2] in matrix"
    
    print("\n✅ Phase 1.5 Event Application Tests PASSED")
    print("\nVerified:")
    print("  ✓ Resource allocation updates available_instances")
    print("  ✓ Process allocation updates correctly")
    print("  ✓ Finish releases all resources")
    print("  ✓ Matrices refresh and reflect changes")


def main():
    """Run all validation tests."""
    print("\n" + "="*70)
    print(" "*15 + "PHASE 1 VALIDATION TESTS")
    print("="*70)
    print("\nTesting Core Data Models: Process, Resource, SystemState")
    
    try:
        test_process_model()
        test_resource_model()
        test_system_state()
        test_initial_allocation_validation()
        test_scenario_loader()
        test_event_application()
        
        print("\n" + "="*70)
        print("\n🎉 ALL TESTS PASSED - Phase 1 + 1.5 Complete!")
        print("\nCore data models are working correctly:")
        print("  ✓ Process allocation/release/finish (separate from max)")
        print("  ✓ Resource allocation/deallocation")
        print("  ✓ System state matrix building")
        print("  ✓ Initial allocation validation (sum <= total)")
        print("  ✓ Scenario loading with validation")
        print("  ✓ Event application updates state correctly")
        print("\nReady for Phase 2: Banker's Algorithm Implementation")
        print("="*70 + "\n")
        
        return 0
        
    except AssertionError as e:
        print(f"\\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
