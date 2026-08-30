@echo off
setlocal
cd /d "%~dp0"
set "G3_DEBUG_CONSOLE=1"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m g3_launcher
  set "APP_EXIT=%ERRORLEVEL%"
  echo.
  echo G3 exited with code %APP_EXIT%.
  pause
  exit /b %APP_EXIT%
) else (
  echo Virtual environment not found. Run setup_windows.bat first.
  pause
  exit /b 1
)
