@echo off
setlocal
set "ROOT=%~dp0"
set "PY=%ROOT%runtime\python\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%ROOT%tools\uninstall.py" --menu
exit /b %ERRORLEVEL%
