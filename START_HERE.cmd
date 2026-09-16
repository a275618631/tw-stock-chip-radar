@echo off
setlocal
call "%~dp0start_dashboard.cmd" %*
exit /b %errorlevel%
