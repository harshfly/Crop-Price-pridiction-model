@echo off
echo ===================================================
echo   🌾 KrishiMitra AI - Production Server Start
echo ===================================================

:: Ensure virtual environment is activated implicitly by using full paths
set PYTHON_EXE=.\venv\Scripts\python.exe
set UVICORN_EXE=.\venv\Scripts\uvicorn.exe

echo 🕒 Starting Celery Scheduler (Background Tasks: Auto-fetch ^& Retrain)...
start "KrishiMitra Scheduler" cmd /k "%PYTHON_EXE% -m src.scheduler"

echo 🚀 Starting FastAPI Backend (Port 8000)...
start "KrishiMitra API" cmd /k "%UVICORN_EXE% api.main:app --host 0.0.0.0 --port 8000"

echo 🟢 All production systems are now online and running!
echo    - API available at: http://localhost:8000/docs
echo    - Scheduler running in background console.
