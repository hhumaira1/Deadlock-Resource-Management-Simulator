# Deadlock & Resource Management Simulator

**CSE323 - Operating Systems**  
Educational tool for demonstrating OS-level deadlock handling strategies with performance analysis.

## Overview

This Python-based simulator demonstrates three fundamental deadlock handling approaches:
- **Deadlock Avoidance** (Banker's Algorithm): Prevents unsafe states proactively
- **Deadlock Detection Only**: Detects cycles after they form, halts when found
- **Detection with Recovery**: Detects and resolves deadlocks through process termination

The simulator focuses on **internal OS decision-making** and policy comparison through measurable metrics, not user-facing applications.

## Features

- ✅ Matrix-based deadlock detection (Work/Finish algorithm)
- ✅ Banker's Algorithm for safe state validation
- ✅ Process termination and resource preemption recovery
- ✅ Performance metrics: utilization, waiting time, throughput, deadlock frequency
- ✅ Policy comparison analysis
- ✅ Deterministic simulation (same scenario + seed = same results)
- ✅ Step-by-step terminal output with clear decision logging

## Architecture

```
simulator.py              # Main entry point with policy selection
models/
  ├── process.py         # Process model (PID, priority, arrival_step, max_demand, allocation)
  ├── resource.py        # Resource model (types, instances, availability)
  └── system_state.py    # Global state tracker (matrices and vectors)
algorithms/
  ├── detection.py       # Matrix-based deadlock detection (Work/Finish algorithm)
  ├── avoidance.py       # Banker's Algorithm implementation
  └── recovery.py        # Termination/preemption strategies
analysis/
  ├── analyzer.py        # Policy comparison library
  ├── metrics.py         # Metric accumulator and event processing
  └── events.py          # Event model (allocation, denial, deadlock, recovery)
utils/
  └── logger.py          # Step-by-step allocation logging
scenarios/               # User-facing example scenarios
tests/scenarios/         # Developer regression test fixtures
```

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/Deadlock-Resource-Management-Simulator.git
cd Deadlock-Resource-Management-Simulator
```

2. **Create and activate virtual environment**:

**Windows**:
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/macOS**:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install numpy         # Required: Matrix operations
pip install colorama      # Optional: Colored terminal output
pip install matplotlib    # Optional: Performance charts
```

4. **Verify installation**:
```bash
python simulator.py --help
```

## Usage

### Basic Simulation

Run a simulation with a specific policy and scenario:

```bash
# Deadlock avoidance (Banker's Algorithm)
python simulator.py --policy avoidance --scenario scenarios/demo_banker.json

# Detection only (halt on deadlock)
python simulator.py --policy detection_only --scenario scenarios/demo_detection.json

# Detection with automatic recovery
python simulator.py --policy detection_with_recovery --scenario scenarios/demo_recovery.json
```

### Advanced Options

```bash
# Enable verbose logging
python simulator.py --policy avoidance --scenario scenarios/demo_banker.json --verbose

# Configure detection frequency (check every 3 steps)
python simulator.py --policy detection_only --scenario scenarios/demo_detection.json --detect-interval 3

# Performance analysis mode
python simulator.py --analyze --policy avoidance --scenario scenarios/demo_banker.json --runs 100

# Compare all policies
python simulator.py --analyze --compare-policies --scenario scenarios/demo_detection.json --runs 100
```

## Scenario File Format

Scenarios use JSON format with an **events-based model**:

```json
{
  "processes": [
    {
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
    }
  ],
  "resources": [
    {"type_id": 0, "total_instances": 5},
    {"type_id": 1, "total_instances": 3},
    {"type_id": 2, "total_instances": 2}
  ]
}
```

### Event Types

- `request`: Request resource instances
- `release`: Release previously allocated resources
- `finish`: Process completes and releases all resources

### Field Descriptions

- **pid**: Unique process identifier
- **priority**: Lower value = higher priority (for victim selection)
- **arrival_step**: Simulation step when process enters system
- **max_demand**: Maximum resource need declared upfront [R]
- **initial_allocation**: Resources held at start (defaults to [0, 0, ...])
- **events**: Time-ordered list of process actions

### Backward Compatibility

Old `requests` format is auto-converted:
```json
"requests": [{"step": 1, "resource_type": 0, "amount": 2}]
// Auto-converted to: [{"step": 1, "type": "request", ...}]
// Auto-finish added when allocation == max_demand
```

## Output Format

### Step-by-Step Logging

```
Step 5: P2 requests R1[2] - GRANTED (Safe state maintained)
Step 12: P1 requests R3[1] - DENIED (Unsafe state detected, process enters WAITING)
Step 13: P1 retries pending request R3[1] - DENIED (Still unsafe)
Step 18: DEADLOCK DETECTED - Processes in deadlock: [P1, P3, P4]
Step 19: RECOVERY - Terminated P3 (priority=5, holding R1[1], R2[2])
```

### Performance Metrics

- **Deadlock Occurrence Frequency**: Deadlocks detected / total simulation runs
- **Resource Utilization %**: Average (Σ allocated / Σ total) × 100 per step
- **Process Waiting Time**: Average steps in WAITING state
- **System Throughput**: Completed processes / total steps

### Policy Comparison Example

```
============================================================
POLICY COMPARISON REPORT
============================================================

Policy: avoidance
  Deadlock Frequency: 0.00%
  Resource Utilization: 65.23%
  Avg Waiting Time: 2.45 steps
  System Throughput: 0.0875 processes/step
------------------------------------------------------------
Policy: detection_only
  Deadlock Frequency: 15.50%
  Resource Utilization: 82.17%
  Avg Waiting Time: 5.82 steps
  System Throughput: 0.0654 processes/step
------------------------------------------------------------
Policy: detection_with_recovery
  Deadlock Frequency: 15.50%
  Resource Utilization: 75.89%
  Avg Waiting Time: 4.23 steps
  System Throughput: 0.0742 processes/step
------------------------------------------------------------
```

## Key Algorithms

### Deadlock Detection (Matrix-Based)

**Time Complexity**: O(P²×R)

Uses Work/Finish algorithm for multi-instance resources:
1. Initialize `Work = Available`, `Finish = [False] * P`
2. Find process where `Request[i] <= Work` (element-wise)
3. Mark `Finish[i] = True`, add `Allocation[i]` to `Work`
4. Repeat until all finish (no deadlock) or stuck (deadlock)

**Critical**: Uses `Request[i]` (current pending), NOT `Need[i]` (max future)

### Banker's Algorithm (Avoidance)

**Time Complexity**: O(P²×R)

Safety check before granting requests:
1. Tentatively allocate resources
2. Run safety algorithm using `Need` matrix
3. If safe: commit; if unsafe: rollback, process enters WAITING

### Process Lifecycle

- Process makes requests from scenario file
- **Auto-finish**: When `allocation[] == max_demand[]`, process releases all and terminates
- **Explicit finish**: Via `finish` event in scenario
- **Termination**: Killed by recovery mechanism

## Four Deadlock Conditions

The simulator explicitly demonstrates all four necessary conditions:

1. **Mutual Exclusion**: Resource allocation (only one process per instance)
2. **Hold and Wait**: Process keeps allocation while making new requests
3. **No Preemption**: Resources released only voluntarily or by recovery
4. **Circular Wait**: Manifests as unsatisfiable pending requests; detection identifies the cycle

## Testing

Example scenarios included:

### User-Facing (`scenarios/`)
- `demo_banker.json`: Demonstrates safe/unsafe state decisions
- `demo_detection.json`: Shows deadlock detection in action
- `demo_recovery.json`: Illustrates victim selection and recovery

### Developer Tests (`tests/scenarios/`)
- `guaranteed_deadlock.json`: Configuration causing deadlock
- `safe_sequence.json`: All requests satisfy Banker's
- `no_deadlock.json`: Normal execution without issues

## Development

### Running Tests
```bash
# TODO: Add test framework (pytest recommended)
pytest tests/
```

### Code Structure Conventions

- Use `dataclasses` for models
- NumPy for matrix operations
- Type hints for all function signatures
- Docstrings following Google style
- Priority: lower value = higher priority for victim selection

## References

- Silberschatz, A., Galvin, P. B., & Gagne, G. (2018). *Operating System Concepts* (10th ed.). Chapter 7: Deadlocks.
- Algorithm implementations based on standard OS textbook pseudocode

## Author

**Humaira Binta Harun**  
CSE323 - Operating Systems Course Project

---

**Note**: This is a terminal-only simulator focused on OS policy analysis. No GUI is provided.