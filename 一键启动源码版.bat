@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title AI_GZT源码环境一键启动
:: 切换到脚本所在目录（项目根目录），保证双击运行时工作路径正确
cd /d "%~dp0"

echo ==============================================
echo        AI智能助手 源码环境一键启动
echo ==============================================
echo.

:: ===== 配置项 =====
set PYTHON_INSTALL_PATH=%LOCALAPPDATA%\Programs\Python\Python311
set VENV_PYTHON=%~dp0.venv\Scripts\python.exe

:: [1/3] 定位Python解释器:优先项目虚拟环境（.venv，与「一键打包.bat」共用，依赖最全），其次全局Python 3.11
echo [1/3] 正在定位Python运行环境...
set PYTHON_EXE=
set ENV_MODE=

if exist "%VENV_PYTHON%" (
    set PYTHON_EXE=%VENV_PYTHON%
    set ENV_MODE=项目虚拟环境（.venv）
    goto python_found
)

if exist "%PYTHON_INSTALL_PATH%\python.exe" (
    set PYTHON_EXE=%PYTHON_INSTALL_PATH%\python.exe
    set ENV_MODE=全局Python 3.11（默认安装路径）
    goto python_found
)

:: 尝试 py 启动器，并解析出python.exe真实路径（避免"py -3.11"含空格无法加引号调用）
for /f "delims=" %%i in ('py -3.11 -c "import sys;print(sys.executable)" 2^>nul') do set PYTHON_EXE=%%i
if defined PYTHON_EXE if exist "!PYTHON_EXE!" (
    set ENV_MODE=全局Python 3.11（py启动器）
    goto python_found
)

:: 尝试 PATH 中的 python（where返回完整路径）
for /f "delims=" %%i in ('where python 2^>nul') do (
    "%%i" --version 2>nul | findstr /c:"3.11" >nul
    if !errorlevel! equ 0 (
        set PYTHON_EXE=%%i
        set ENV_MODE=全局Python 3.11（PATH）
        goto python_found
    )
)

echo ❌ 未检测到Python 3.11运行环境。
echo 请先双击运行「Python和依赖安装.bat」完成环境安装，再启动源码版。
goto error_exit

:python_found
echo ✅ 运行环境: !ENV_MODE!
"%PYTHON_EXE%" --version
echo.
:: [2/3] 快速校验核心依赖（仅import探测，秒级完成；不做安装，缺依赖时给出明确指引）
echo [2/3] 正在快速校验核心依赖...
set MISSING_DEPS=
"%PYTHON_EXE%" -c "import PySide6" 2>nul || set MISSING_DEPS=!MISSING_DEPS! PySide6
"%PYTHON_EXE%" -c "import fastapi" 2>nul || set MISSING_DEPS=!MISSING_DEPS! fastapi
"%PYTHON_EXE%" -c "import uvicorn" 2>nul || set MISSING_DEPS=!MISSING_DEPS! uvicorn

if defined MISSING_DEPS (
    echo ❌ 当前Python环境缺少核心依赖:!MISSING_DEPS!
    echo.
    echo 请按以下任一方式补齐后再启动:
    echo   1^) 双击「Python和依赖安装.bat」安装到全局环境
    echo   2^) 双击「一键打包.bat」自动创建.venv并安装全部依赖（推荐，与打包环境一致）
    goto error_exit
)
echo ✅ 核心依赖校验通过
echo.

:: [3/3] 启动源码版主程序
echo [3/3] 正在启动AI智能助手源码版...
echo ==============================================
echo  启动方式: !ENV_MODE!
echo  工作目录: %CD%
echo  关闭本窗口或程序退出后即停止运行
echo ==============================================
echo.
"%PYTHON_EXE%" main.py
set EXIT_CODE=!errorlevel!

if !EXIT_CODE! neq 0 (
    echo.
    echo ==============================================
    echo ❌  程序异常退出，退出码: !EXIT_CODE!
    echo 请查看上方报错信息，或将web_log.html日志反馈排查。
    echo ==============================================
    echo.
    pause
    exit /b !EXIT_CODE!
)

echo.
echo ✅ 程序已正常退出
pause
exit /b 0

:error_exit
echo.
echo ==============================================
echo ❌  启动前检查未通过，请根据上方提示处理后重试。
echo ==============================================
echo.
pause
exit /b 1