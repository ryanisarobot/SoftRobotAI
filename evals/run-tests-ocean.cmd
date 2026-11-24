@echo off
setlocal
cd /d "%~dp0"
if not exist ".env" (
  echo ERROR: Missing .env with OPENAI_API_KEY
  pause
  exit /b 1
)
set "TRAIT=%~1"
if "%TRAIT%"=="" set "TRAIT=C"
if /I not "%TRAIT%"=="O" if /I not "%TRAIT%"=="C" if /I not "%TRAIT%"=="E" if /I not "%TRAIT%"=="A" if /I not "%TRAIT%"=="N" (
  echo ERROR: Use O, C, E, A, or N as the first argument.
  exit /b 1
)
for %%T in (O C E A N) do if /I "%TRAIT%"=="%%T" set "TRAIT=%%T"
set "SLUG=o"
if "%TRAIT%"=="C" set "SLUG=c"
if "%TRAIT%"=="E" set "SLUG=e"
if "%TRAIT%"=="A" set "SLUG=a"
if "%TRAIT%"=="N" set "SLUG=n"
python -c "import yaml" >nul 2>&1
if errorlevel 1 (
  echo Install PyYAML: python -m pip install PyYAML
  pause
  exit /b 1
)
python scripts\generate_ocean.py --trait %TRAIT% --output output\ocean_tests.json
if errorlevel 1 exit /b 1
where fnm >nul 2>&1
if not errorlevel 1 (
  FOR /f "tokens=*" %%i IN ('fnm env --use-on-cd') DO CALL %%i
  call fnm use 24
)
call promptfoo.cmd eval --config promptfooconfig.ocean.yaml --env-file .env --no-cache --output output\ocean_%SLUG%_results.json
if errorlevel 1 (
  echo Promptfoo evaluation failed.
  pause
  exit /b 1
)
echo OCEAN-%TRAIT% export created. Run analyze-ocean.cmd %TRAIT% for cross-level analysis.
pause