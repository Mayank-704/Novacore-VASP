@echo off
setlocal
cd /d "%~dp0"
if exist .venv\Scripts\python.exe goto install
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
if errorlevel 1 goto try_python
py -3 -m venv .venv
if errorlevel 1 goto setup_error
goto install
:try_python
python -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
if errorlevel 1 goto python_missing
python -m venv .venv
if errorlevel 1 goto setup_error
:install
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if errorlevel 1 goto setup_error
echo.
echo VASP Desk is starting. Open http://127.0.0.1:8000 in your browser.
echo Keep this window open. Press Ctrl+C to stop the server.
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
pause
exit /b
:python_missing
echo Python 3.11 or newer was not found using py or python.
echo Install Python, then restart VS Code and try again.
pause
exit /b 1
:setup_error
echo Setup failed. Check the error above and your internet connection.
pause
exit /b 1
