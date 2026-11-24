@echo off
setlocal
cd /d "%~dp0"
set "TRAIT=%~1"
if "%TRAIT%"=="" set "TRAIT=C"
if /I not "%TRAIT%"=="O" if /I not "%TRAIT%"=="C" if /I not "%TRAIT%"=="E" if /I not "%TRAIT%"=="A" if /I not "%TRAIT%"=="N" (
  echo ERROR: Use O, C, E, A, or N.
  exit /b 1
)
for %%T in (O C E A N) do if /I "%TRAIT%"=="%%T" set "TRAIT=%%T"
set "SLUG=o"
if "%TRAIT%"=="C" set "SLUG=c"
if "%TRAIT%"=="E" set "SLUG=e"
if "%TRAIT%"=="A" set "SLUG=a"
if "%TRAIT%"=="N" set "SLUG=n"
python scripts\compare_ocean.py --trait %TRAIT% --judge
if errorlevel 1 (
  echo Cross-level analysis failed. See the error above.
  pause
  exit /b 1
)
start "" "output\ocean_%SLUG%_analysis\report.md"
pause