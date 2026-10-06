@echo off
echo =======================================================
echo    Starting CivicPulse AI (Indore Smart City MVP)
echo =======================================================
cd /d "%~dp0"

if not exist ".venv\Scripts\streamlit.exe" (
    echo [ERROR] Virtual environment not found. Please run:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b
)

echo Starting Streamlit application at http://localhost:8501 ...
.venv\Scripts\streamlit.exe run app.py
pause
