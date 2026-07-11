@echo off
set "PYTHON_EXE=C:\Windows\py.exe"
set "BAN_SCRIPT=C:\Users\M S I\Desktop\internet-security-project\backend\ban_account.py"

if exist "%PYTHON_EXE%" (
  "%PYTHON_EXE%" -3 "%BAN_SCRIPT%"
) else (
  python "%BAN_SCRIPT%"
)

exit /b %ERRORLEVEL%
