@echo off
setlocal
cd /d "%~dp0"
where promptfoo >nul 2>&1
if errorlevel 1 (
  echo Promptfoo is not on PATH. Open CMD and check: promptfoo --version
  pause
  exit /b 1
)
call promptfoo view
pause
