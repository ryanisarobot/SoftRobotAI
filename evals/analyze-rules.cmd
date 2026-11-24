@echo off
setlocal
cd /d "%~dp0"
if /i "%~1"=="FOUND" goto valid
if /i "%~1"=="CONV" goto valid
if /i "%~1"=="CAPS" goto valid
echo Usage: analyze-rules.cmd FOUND ^| CONV ^| CAPS [RULE-ID]
exit /b 1
:valid
if not "%~2"=="" (
    set "SUFFIX=_%~2"
    set "RULEARG=--rule %~2"
) else (
    set "SUFFIX="
    set "RULEARG="
)
python scripts\summarize_rules.py --family %~1 %RULEARG% --input output\rules_%~1%SUFFIX%_results.json --output-dir output\rules_%~1%SUFFIX%_analysis
if errorlevel 1 ( echo Analysis encountered errors. & pause & exit /b 1 )
start "" "output\rules_%~1%SUFFIX%_analysis\report.md"
pause