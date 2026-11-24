@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python is not on PATH.
  pause
  exit /b 1
)
if not exist "output\ocean_o_results.json" (
  echo ERROR: Run run-tests-ocean-o.cmd first to create output\ocean_o_results.json.
  pause
  exit /b 1
)

python scripts\compare_ocean_o.py --judge
if errorlevel 1 (
  echo Analysis or cross-level grading did not finish successfully.
  pause
  exit /b 1
)

start "" "output\ocean_o_analysis\report.md"
pause