@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
  start "" wscript.exe "%~dp0run_windows.vbs"
  exit /b 0
) else (
  echo Virtual environment not found. Run setup_windows.bat first.
  pause
  exit /b 1
)
