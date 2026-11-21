@echo off
setlocal
cd /d "%~dp0"
if not exist ".env" (
  echo Missing .env file. Copy .env.example to .env and add your OpenAI API key.
  echo This local file must never be committed to GitHub.
  pause
  exit /b 1
)
where promptfoo >nul 2>&1
if errorlevel 1 (
  echo Promptfoo is not on PATH. Open CMD and check: promptfoo --version
  pause
  exit /b 1
)
call promptfoo eval --env-file .env
set "EVAL_EXIT=%errorlevel%"
echo.
echo Eval finished with exit code %EVAL_EXIT%. Failed assertions can cause a nonzero exit code.
echo Opening results in your browser...
call promptfoo view
pause
exit /b %EVAL_EXIT%
