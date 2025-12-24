@echo off
cd "c:\Users\humai\Downloads\S7\CSE323 - SSI\Deadlock Resource Simulator\Deadlock-Resource-Management-Simulator"
.\.venv\Scripts\python.exe simulator.py --policy detection_only --scenario scenarios\demo_detection.json > test_final.txt 2>&1
type test_final.txt
