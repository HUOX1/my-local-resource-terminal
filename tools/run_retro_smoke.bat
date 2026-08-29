@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

rem Local smoke must exercise the native Windows Qt plugin, not offscreen mode.
set "QT_QPA_PLATFORM="
set "PYTHONFAULTHANDLER=1"

echo ========================================
echo   Retro Local GUI Smoke - v0.5.0.7+
echo ========================================
echo.

if exist ".venv\Scripts\python.exe" goto run_venv
where py >nul 2>nul
if not errorlevel 1 goto run_py
where python >nul 2>nul
if not errorlevel 1 goto run_python

echo [FAIL] Python was not found.
echo Run this from the same project environment you use to start the app.
pause
exit /b 2

:run_venv
".venv\Scripts\python.exe" -X faulthandler tools\retro_smoke_runner.py
set "RC=%ERRORLEVEL%"
goto finish

:run_py
py -3 -X faulthandler tools\retro_smoke_runner.py
set "RC=%ERRORLEVEL%"
goto finish

:run_python
python -X faulthandler tools\retro_smoke_runner.py
set "RC=%ERRORLEVEL%"
goto finish

:finish
echo.
if "%RC%"=="0" (
  echo [PASS] Retro GUI smoke passed.
) else (
  echo [FAIL] Retro GUI smoke failed with exit code %RC%.
  echo Send artifacts\retro-smoke-local\latest.log back for diagnosis.
)
echo.
pause
exit /b %RC%
