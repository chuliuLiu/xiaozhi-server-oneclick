@echo off
chcp 65001 >nul
setlocal enableextensions
cd /d "%~dp0"

set "ROOT=%~dp0"
set "PYPATH=%ROOT%runtime\python\python.exe"
set "PYW=%ROOT%runtime\python\pythonw.exe"
set "PANEL=%ROOT%app\panel\server.py"
set "WAIT=%ROOT%app\panel\wait_port.py"
set "UNPACK=%ROOT%app\panel\unpack_runtime.py"
set "URL=http://127.0.0.1:8770/"

title 小智本地服务

if not exist "%PYPATH%" (
  echo.
  echo   [x] 没找到便携 Python：%PYPATH%
  echo       安装包不完整，请重新解压一次（不要把 bat 单独复制出来）。
  echo.
  pause
  exit /b 1
)

rem ── 路径检查：中文/空格是部署第一大坑（用 Python 判断，避免 findstr 误判）──
set "BADPATH="
for /f "delims=" %%P in ('"%PYPATH%" "%ROOT%app\panel\check_path.py"') do set "BADPATH=%%P"
if defined BADPATH (
  echo.
  echo   [!] 这个文件夹的路径里有中文或空格：
  echo       %BADPATH%
  echo.
  echo       请把整个文件夹移到 D:\xiaozhi 这类纯英文、无空格的路径再双击。
  echo.
  pause
  exit /b 1
)

rem ── 首次启动：把包内压缩的运行组件还原出来（还原成功即删除压缩包）────
set "NEED_UNPACK="
if exist "%ROOT%runtime\xiaozhi-mqtt-gateway.zip" set "NEED_UNPACK=1"
if exist "%ROOT%runtime\bin\ffmpeg.exe.zip" set "NEED_UNPACK=1"
if exist "%ROOT%runtime\node\node.exe.zip" set "NEED_UNPACK=1"
if defined NEED_UNPACK (
  "%PYPATH%" "%UNPACK%"
  if errorlevel 1 (
    echo.
    echo   [x] 运行组件解压失败，请确认磁盘空间充足后重新双击。
    echo.
    pause
    exit /b 1
  )
)

rem ── 已经开着就直接开浏览器（多开不再起第二个进程）────────────────
"%PYPATH%" "%WAIT%" 8770 0 >nul 2>&1
if not errorlevel 1 (
  start "" "%URL%"
  exit /b 0
)

rem ── 后台静默启动（无黑框）────────────────────────────────────────
if exist "%PYW%" (
  start "" "%PYW%" "%PANEL%" --port 8770 --no-browser
) else (
  start "" /min "%PYPATH%" "%PANEL%" --port 8770 --no-browser
)

"%PYPATH%" "%WAIT%" 8770 20 >nul 2>&1
if errorlevel 1 (
  echo.
  echo   [x] 面板没起来。看这个日志文件里的最后几行：
  echo       %ROOT%data\logs\panel.log
  echo.
  echo       最常见的原因：路径有中文/空格，或者 8770 端口被别的软件占用。
  echo.
  pause
  exit /b 1
)

start "" "%URL%"
exit /b 0
