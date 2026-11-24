@echo off
setlocal
cd /d "%~dp0"
if /i "%~1"=="FOUND" goto valid
if /i "%~1"=="CONV" goto valid
if /i "%~1"=="CAPS" goto valid
echo Usage: run-tests-rules.cmd FOUND ^| CONV ^| CAPS [RULE-ID]
exit /b 1
:valid
if not exist ".env" (
    echo ERROR: Missing local .env OPENAI_API_KEY.
    pause
    exit /b 1
)
where python >nul 2>&1
if errorlevel 1 ( echo Python not on PATH. & pause & exit /b 1 )
python -c "import yaml" >nul 2>&1
if errorlevel 1 ( echo Install PyYAML: python -m pip install PyYAML & pause & exit /b 1 )
if not "%~2"=="" (
    python scripts\generate_rules.py --family %~1 --rule %~2 --output output\rules_tests.json
    set "SUFFIX=_%~2"
) else (
    python scripts\generate_rules.py --family %~1 --output output\rules_tests.json
    set "SUFFIX="
)
if errorlevel 1 ( pause & exit /b 1 )
where fnm >nul 2>&1
if not errorlevel 1 (
    FOR /f "tokens=*" %%i IN ('fnm env --use-on-cd') DO CALL %%i
    call fnm use 24
)
where promptfoo.cmd >nul 2>&1
if errorlevel 1 ( echo Promptfoo not on PATH. & pause & exit /b 1 )
call promptfoo.cmd eval --config promptfooconfig.rules.yaml --env-file .env --no-cache --output output\rules_%~1%SUFFIX%_results.json
if errorlevel 1 ( echo Promptfoo failed. & pause & exit /b 1 )
echo Saved output\rules_%~1%SUFFIX%_results.json
call promptfoo.cmd view
pause