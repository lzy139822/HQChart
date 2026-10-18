@echo off
chcp 65001 >nul
setlocal
set "PY=G:\Python312\python.exe"
set "BACK=I:\HQChart\HQChart_Train\backend"
set "ROOT=I:\HQChart\webhqchart.demo"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

echo Starting HQChart Train (utf-8 mode)...

REM ---- backend (port 8777) ----
netstat -ano 2>nul | findstr ":8777 " >nul
if errorlevel 1 (
  start "HQChart Backend" /min cmd /k "chcp 65001 >nul && cd /d "%BACK%" && "%PY%" server.py"
) else (
  echo Backend already on :8777
)

REM ---- wait for backend ----
timeout /t 3 >nul

REM ---- frontend static server (port 8000) ----
netstat -ano 2>nul | findstr ":8000 " >nul
if errorlevel 1 (
  start "HQChart Frontend" /min cmd /k "chcp 65001 >nul && cd /d "%ROOT%" && "%PY%" -m http.server 8000"
) else (
  echo Frontend already on :8000
)

REM ---- open browser ----
timeout /t 2 >nul
start "" http://localhost:8000/Demo_hqchart/hq_train.html
start "" http://localhost:8000/samples/minute_train.html

endlocal
