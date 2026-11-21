@echo off
setlocal
cd /d "%~dp0"

if not exist ".env" (
    echo ERROR: Missing .env file.
    pause
    exit /b 1
)

FOR /f "tokens=*" %%i IN ('fnm env --use-on-cd') DO CALL %%i
call fnm use 24

call promptfoo.cmd eval --env-file .env

start "" http://localhost:15500
call promptfoo.cmd view

pause