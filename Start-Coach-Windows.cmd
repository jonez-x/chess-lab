@echo off
setlocal
cd /d "%~dp0"
curl --noproxy "*" -fsS --max-time 2 http://127.0.0.1:11434/api/version >nul 2>nul
if not errorlevel 1 (
    echo Ollama laeuft bereits.
    exit /b 0
)
where ollama >nul 2>nul
if errorlevel 1 (
    echo Bitte Ollama fuer Windows installieren und ein neues Terminal oeffnen.
    echo https://ollama.com/download/windows
    pause
    exit /b 1
)
set OLLAMA_HOST=127.0.0.1:11434
set OLLAMA_NO_CLOUD=1
set OLLAMA_NUM_PARALLEL=1
ollama serve
if errorlevel 1 pause
