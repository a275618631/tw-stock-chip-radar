@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\export_share_snapshot.ps1" %*
set "exitCode=%errorlevel%"
if not "%exitCode%"=="0" (
  echo Share Snapshot export failed.
  echo See the error message above.
  pause
)
exit /b %exitCode%
