# Copilot Instructions: Deadlock & Resource Management Simulator

## Project Overview
**Python-based** educational simulator for CSE323 demonstrating OS-level deadlock handling strategies with performance analysis. This is **NOT a user-facing application** - it focuses on internal OS decision-making, policy comparison, and system-level thinking. Output is **terminal-only** (no GUI).

**Core Purpose**: Simulate resource allocation, demonstrate why deadlocks occur, and compare performance of different OS policies through measurable metrics.

## Architecture & Core Components

### System Structure (Python Modules)
```
simulator.py              # Main entry point with policy selection
models/
  ├── process.py         # Process model (PID, priority, arrival_step, max_demand, allocation)
  ├── resource.py        # Resource model (types, instances, availability)
  └── system_state.py    # Global state tracker (snapshot only for preemption, not termination)
algorithms/
  ├── detection.py       # Matrix-based deadlock detection (Work/Finish algorithm)
  ├── avoidance.py       # Banker's Algorithm implementation
  └── recovery.py        # Termination/pre-emption strategies
analysis/
  ├── analyzer.py        # Library module for policy comparison
  ├── metrics.py         # Metric accumulator and event processing
  └── events.py          # Event model (allocation, denial, deadlock, recovery events)
utils/
  └── logger.py          # Step-by-step allocation logging
```

**Note**: `analyzer.py` is a library module called by `simulator.py --analyze`, not a standalone CLI tool. System state snapshots are only required for resource preemption (rollback), not for process termination (which just releases resources).

### Mandatory Data Structures
- **Allocation Matrix** `[P][R]`: Current resources held by each process
- **Max Demand Matrix** `[P][R]`: Maximum resource need declared by each process
- **Available Vector** `[R]`: Free resource instances by type
- **Request Matrix** `[P][R]`: Current **pending** resource requests (what process is blocked waiting for)
- **Need Matrix** `[P][R]`: Computed as `Max - Allocation` (used only for Banker's safety check)
- **Work Vector** `[R]`: Temporary vector for detection algorithm (copy of Available)
- **Finish Vector** `[P]`: Boolean array tracking which processes can complete

## Critical Implementation Requirements

### FR1: Process & Resource Modeling
```python
# Process must store: PID, priority, arrival_step, max_demand[], allocation[], current_request[]
# Resource must track: type_id, total_instances, available_instances
# Use dataclasses for clean representation
# Priority: lower value = higher priority (for victim selection)
# Arrival_step: simulation step when process entered system
```

**Process Lifecycle**:
- Process makes requests from scenario file at specified steps
- **Events-based model**: Process can explicitly release resources or finish via `events` array
- **Auto-finish fallback**: If using old `requests` format, process auto-finishes when allocation[] == max_demand[]
- Upon finishing (explicit or auto), process releases all allocated resources immediately
- Process transitions: READY → RUNNING → (WAITING if denied) → FINISHED

### FR2: Deadlock Detection (Matrix-Based Algorithm)
- Use **matrix-based detection** (Work/Finish algorithm) for multi-instance resources
- Algorithm: Initialize Work = Available; for each process, if **Request[i] ≤ Work** (current pending request, NOT Need), mark Finish[i] = true and add Allocation[i] to Work
- **Critical distinction**: Detection uses Request[] (what process is blocked waiting for NOW), not Need[] (maximum possible future request)
- Deadlock exists if any Finish[i] = false after algorithm completes
- Mark all processes with Finish[i] = false as `DEADLOCKED`
- Run detection **every step** by default (configurable via `--detect-interval N`)

### FR3: Deadlock Avoidance (Banker's Algorithm)
- Check safe state BEFORE granting any request
- Run safety algorithm: try to find sequence where all processes can finish
- If request cannot be granted (insufficient resources OR unsafe state):
  - Process enters `WAITING` state
  - Request remains in Request Matrix as pending
  - Simulator re-attempts pending requests each step
- If safe: grant allocation and clear pending request
- Log reason for denial/grant clearly

### FR4: Deadlock Recovery
- **Process Termination**: Select victim(s) to break cycle (lowest priority, fewest resources held)
- **Resource Preemption**: Forcibly take resources from process and rollback state
- Recovery should restore system to safe state

### FR5: Simulation Control
- User selects policy: `AVOIDANCE`, `DETECTION_ONLY`, or `DETECTION_WITH_RECOVERY`
- `AVOIDANCE`: Banker's Algorithm prevents unsafe states
- `DETECTION_ONLY`: Grant requests whenever `request <= available` (skip Banker safety check); if `request > available`, process enters WAITING. Detect deadlocks, halt when found.
- `DETECTION_WITH_RECOVERY`: Detect deadlocks and automatically recover by terminating victims
- Simulation runs step-by-step with clear terminal output after each decision
- Deterministic and reproducible - same scenario + seed produces same output

**Step Ordering (for deterministic execution)**:
1. Apply releases/finishes from events (if any)
2. Retry pending requests in PID order
3. Apply new requests scheduled for this step (PID order)
4. Run detection (depending on `--detect-interval`)
5. If deadlock and recovery enabled → recover, then retry pending once

### FR6: Output & Logging
```python
# Every allocation decision must be logged:
# "Step 5: P2 requests R1[2] - GRANTED (Safe state maintained)"
# "Step 12: P1 requests R3[1] - DENIED (Unsafe state detected, process enters WAITING)"
# "Step 13: P1 retries pending request R3[1] - DENIED (Still unsafe)"
# "Step 18: DEADLOCK DETECTED - Processes in deadlock: [P1, P3, P4]"
# "Step 19: RECOVERY - Terminated P3 (priority=5, holding R1[1], R2[2])"
```

## Performance Analysis Component (Critical)

### Required Metrics
Simulator MUST track and report:
1. **Deadlock Occurrence Frequency**: Number of deadlocks detected / total simulation runs
2. **Resource Utilization %**: Average of (Σ allocated instances across all resources / Σ total instances) × 100 per step
3. **Process Waiting Time**: Average steps each process spends in WAITING state (sum across all processes / number of processes)
4. **System Throughput**: Completed processes / total simulation steps

**Calculation Rules**:
- Sample metrics at each simulation step
- Waiting time starts when request denied/blocked, ends when granted or process terminates
- Utilization measured instantaneously each step, then averaged across simulation
- Throughput counts only processes reaching FINISHED state (not DEADLOCKED or TERMINATED)

### Policy Comparison
Generate comparative analysis showing:
- `AVOIDANCE` vs `DETECTION_ONLY` vs `DETECTION_WITH_RECOVERY` trade-offs
- Expected patterns:
  - AVOIDANCE: 0 deadlocks, possibly lower utilization (conservative)
  - DETECTION_ONLY: some deadlocks, higher utilization until deadlock
  - DETECTION_WITH_RECOVERY: deadlocks resolved, moderate throughput
- Present results in tables or simple charts (ASCII or matplotlib)

## Development Conventions

### Python-Specific Patterns
```python
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Process:
    pid: int
    priority: int          # Lower = higher priority for victim selection
    arrival_step: int      # When process entered system
    max_demand: List[int]
    allocation: List[int]
    state: str  # READY, RUNNING, WAITING, FINISHED, DEADLOCKED, TERMINATED

# Use numpy for matrix operations
import numpy as np
allocation_matrix = np.array([[1, 0, 2], [0, 1, 0]])

# NO threading/multiprocessing - this is algorithmic simulation
# Requests come from scenario files, NOT generated randomly (deterministic)
```

### Terminal Output Format
- Use clear section headers with separators (`====`, `----`)
- Display matrices in readable grid format
- Highlight state changes (use colors if colorama installed, but optional)
- Show system state snapshot after each step

### Process States
- `READY`: Process can execute if resources granted
- `RUNNING`: Process currently executing (simulated)
- `WAITING`: Blocked on resource acquisition (has pending request in Request Matrix)
- `FINISHED`: Execution complete (received all max_demand), resources released voluntarily
- `DEADLOCKED`: Confirmed in deadlock (Finish[i] = false in detection)
- `TERMINATED`: Killed by recovery mechanism

### Testing Strategy
Create test scenarios in `tests/scenarios/` (developer-only regression tests):
1. `guaranteed_deadlock.json`: Configuration causing deadlock
2. `safe_sequence.json`: All requests satisfy Banker's algorithm
3. `edge_single_resource.json`: Single resource type, multiple processes
4. `no_deadlock.json`: Normal execution without issues

Shipping examples in `scenarios/` (user-facing, CLI defaults):
1. `demo_banker.json`: Demonstrates safe/unsafe state decisions
2. `demo_detection.json`: Shows deadlock detection in action
3. `demo_recovery.json`: Illustrates victim selection and recovery

## Critical Workflows

### Running Simulations
```bash
# Policy selection required
python simulator.py --policy detection_only --scenario scenarios/demo_detection.json
python simulator.py --policy avoidance --scenario scenarios/demo_banker.json --verbose
python simulator.py --policy detection_with_recovery --scenario scenarios/demo_recovery.json

# Configure detection frequency (default: every step)
python simulator.py --policy detection_only --detect-interval 3

# Generate performance comparison (uses analyzer.py module internally)
python simulator.py --analyze --compare-policies --runs 100 --scenario scenarios/demo_detection.json
```

### Debugging Checklist
- Verify need matrix calculation: `Need[i][j] = Max[i][j] - Allocation[i][j]`
- Check safe state algorithm doesn't modify actual allocation (use copy)
- Verify Work vector properly initialized: `Work = Available.copy()`
- **Validate detection uses Request[i], not Need[i]** (common mistake)
- Ensure detection returns ALL processes with Finish[i] = false
- Ensure detection runs at specified interval (default every step)
- Verify pending requests are retried each step until granted or deadlock
- Confirm scenario-driven requests (not random) for reproducibility

## Academic Context (CSE323 Evaluation)

### Documentation Requirements
- Comment algorithm time complexity: O(P²×R) for matrix-based detection, O(P²×R) for Banker's safety
- Reference Silberschatz's OS Concepts Chapter 7 for algorithm pseudocode
- Explain WHY deadlock occurs in comments, not just WHAT code does
- Include design rationale: "Fixed resource pool chosen because dynamic allocation adds complexity beyond OS scope"
- **Map four deadlock conditions explicitly in code comments**:
  - **Mutual Exclusion**: Resource.allocate() - only one process can hold instance
  - **Hold and Wait**: Process keeps allocation[] while making new requests
  - **No Preemption**: Resources released only voluntarily (FINISHED) or by recovery (TERMINATED)
  - **Circular Wait**: Manifests as unsatisfiable pending requests; detection algorithm identifies processes that cannot complete

### Key Concepts to Demonstrate
- Mutual Exclusion, Hold and Wait, No Preemption, Circular Wait (comment where these appear)
- Safe vs Unsafe state distinction (explain in Banker's implementation)
- Trade-offs between policies (document in analysis output)

## Dependencies & Setup
```bash
pip install numpy  # Matrix operations
pip install colorama  # Optional: colored terminal output
pip install matplotlib  # Optional: performance charts

# No GUI libraries (Tkinter, PyQt) - terminal only
# No actual threading - algorithmic simulation
```

## File Organization
```
scenarios/          # User-facing: shipping examples, CLI defaults (demo_*.json)
tests/scenarios/    # Developer-only: regression test fixtures
results/            # Output: simulation logs with timestamps
analysis/           # Performance comparison reports (generated)
logs/               # Debug traces (optional, for development)
```

**Directory Conventions**:
- `scenarios/` contains example scenarios users can run immediately
- `tests/scenarios/` contains test fixtures only used by automated tests
- **Scenario JSON schema** (events-based):
```json
{
  "processes": [{
    "pid": 1,
    "priority": 1,
    "arrival_step": 0,
    "max_demand": [3, 2, 1],
    "initial_allocation": [0, 0, 0],
    "events": [
      {"step": 1, "type": "request", "resource_type": 0, "amount": 2},
      {"step": 3, "type": "release", "resource_type": 0, "amount": 1},
      {"step": 5, "type": "finish"}
    ]
  }],
  "resources": [{"type_id": 0, "total_instances": 5}]
}
```
- **Backward compatibility**: Old `requests` format auto-converts to `events` on load:
```json
"requests": [{"step": 1, "resource_type": 0, "amount": 2}]  
// Auto-converted to: [{"step": 1, "type": "request", ...}]
// Auto-finish added when allocation == max_demand
```
- **Event types**: `request`, `release`, `finish`
- **Validation**: releases can't exceed current allocation, requests can't exceed max_demand
- **Initial allocation**: If omitted, defaults to [0, 0, ...]; if specified, Available must account for it

## Key Files
- [README.md](README.md) - Update with setup instructions and usage examples
- [Project Requirements Document (PRD).md](Project%20Requirements%20Document%20(PRD).md) - Source of truth for requirements

## Implementation Priority
1. Data structures (Process, Resource, System State)
2. Banker's Algorithm (avoidance is foundational)
3. Matrix-based detection (Work/Finish algorithm)
4. Recovery mechanisms
5. Performance metrics tracking
6. Policy comparison analysis
