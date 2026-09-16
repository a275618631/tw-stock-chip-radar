@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\open_daily_report.ps1" %*
exit /b %errorlevel%
