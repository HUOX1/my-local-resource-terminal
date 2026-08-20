@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m app.main
  set "APP_EXIT=%ERRORLEVEL%"
  echo.
  echo Application exited with code %APP_EXIT%.
  pause
  exit /b %APP_EXIT%
) else (
  echo Virtual environment not found. Run setup_windows.bat first.
  pause
  exit /b 1
)
