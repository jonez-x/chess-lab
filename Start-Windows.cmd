@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    where py >nul 2>nul
    if errorlevel 1 (
        python -m venv .venv
    ) else (
        py -3 -m venv .venv
    )
    if errorlevel 1 goto :failed
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" server.py --open %*
if errorlevel 1 goto :failed
exit /b 0
:failed
echo.
echo Start fehlgeschlagen. Hinweise stehen oben und in WINDOWS.md.
pause
exit /b 1
