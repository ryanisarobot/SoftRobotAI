@echo off
setlocal
cd /d "%~dp0"

if not exist ".env" (
    echo ERROR: Missing evals\.env with OPENAI_API_KEY.
    pause
    exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not on PATH.
    pause
    exit /b 1
)

python -c "import yaml" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Missing PyYAML. Run: python -m pip install PyYAML
    pause
    exit /b 1
)

python scripts\generate_ocean_o.py
if errorlevel 1 (
    pause
    exit /b 1
)

where fnm >nul 2>&1
if not errorlevel 1 (
    FOR /f "tokens=*" %%i IN ('fnm env --use-on-cd') DO CALL %%i
    call fnm use 24
)

where promptfoo.cmd >nul 2>&1
if errorlevel 1 (
    echo ERROR: Promptfoo not found on PATH.
    pause
    exit /b 1
)

call promptfoo.cmd eval --config promptfooconfig.ocean-o.yaml --env-file .env --no-cache --output output\ocean_o_results.json
if errorlevel 1 (
    echo Evaluation failed. Check the errors above.
    pause
    exit /b 1
)

start "" http://localhost:15500
call promptfoo.cmd view
pause
