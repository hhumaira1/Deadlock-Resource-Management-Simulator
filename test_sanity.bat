@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe verify_sanity_checks.py > sanity_check_output.txt 2>&1
type sanity_check_output.txt
