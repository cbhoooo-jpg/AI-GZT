@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title AI_GZT一键打包脚本
:: 切换到脚本所在目录（项目根目录），保证双击运行时工作路径正确
cd /d "%~dp0"

echo ==============================================
echo          AI智能助手 一键打包工具
echo ==============================================
echo.
echo 本脚本自动完成: 检测Python3.11 ^> 创建/复用虚拟环境 ^> 安装依赖 ^> 执行打包
echo.

:: ===== 配置项 =====
set PYTHON_INSTALL_PATH=%LOCALAPPDATA%\Programs\Python\Python311
set VENV_DIR=%~dp0.venv
set PIP_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple

:: [1/5] 定位 Python 3.11（检测顺序与「Python和依赖安装.bat」保持一致）
echo [1/5] 正在检测Python 3.11环境...
set PYTHON_EXE=
if exist "%PYTHON_INSTALL_PATH%\python.exe" (
    set PYTHON_EXE=%PYTHON_INSTALL_PATH%\python.exe
    goto python_found
)
:: 尝试 py 启动器
for /f "delims=" %%i in ('py -3.11 --version 2^>nul') do set PY_VER_OUTPUT=%%i
echo !PY_VER_OUTPUT! | findstr /c:"3.11" >nul
if !errorlevel! equ 0 (
    for /f "delims=" %%i in ('where py') do set PYTHON_EXE=%%i -3.11
    goto python_found
)
:: 尝试 PATH 中的 python
for /f "delims=" %%i in ('python --version 2^>nul') do set PY_VER_OUTPUT=%%i
echo !PY_VER_OUTPUT! | findstr /c:"3.11" >nul
if !errorlevel! equ 0 (
    for /f "delims=" %%i in ('where python') do set PYTHON_EXE=%%i
    goto python_found
)
echo ❌ 未检测到Python 3.11，请先双击运行「Python和依赖安装.bat」完成环境安装后再执行打包。
goto error_exit

:python_found
echo ✅ 检测到Python环境:
%PYTHON_EXE% --version
echo.

:: [2/5] 创建或复用项目虚拟环境（.venv位于项目根目录，不在build.py打包清单内，不会被打进安装包）
echo [2/5] 正在检查项目虚拟环境（.venv）...
if exist "%VENV_DIR%\Scripts\python.exe" (
    echo ✅ 虚拟环境已存在，直接复用: %VENV_DIR%
) else (
    echo 虚拟环境不存在，正在创建（首次约1-2分钟）...
    %PYTHON_EXE% -m venv "%VENV_DIR%"
    if !errorlevel! neq 0 (
        echo ❌ 虚拟环境创建失败，请检查Python安装是否完整（建议先运行「Python和依赖安装.bat」修复环境）。
        goto error_exit
    )
    echo ✅ 虚拟环境创建完成
)
set VENV_PYTHON=%VENV_DIR%\Scripts\python.exe
echo.
:: [3/5] 虚拟环境内升级pip并安装项目依赖（已安装的包pip自动跳过，不会重复下载）
echo [3/5] 正在安装/校验项目依赖（首次约3.5G，需5-15分钟；已安装时秒过）...
"%VENV_PYTHON%" -m pip install --upgrade pip -i %PIP_MIRROR%
if !errorlevel! neq 0 (
    echo ⚠️ pip升级失败，继续使用现有版本安装依赖...
)
"%VENV_PYTHON%" -m pip install -r requirements.txt -i %PIP_MIRROR%
if !errorlevel! neq 0 (
    echo ❌ 依赖安装失败，请根据上方错误信息排查网络或包冲突问题后重试。
    goto error_exit
)
echo ✅ 依赖安装/校验完成
echo.

:: [4/5] 使用虚拟环境Python执行打包（build.py自动完成PyInstaller绿色包+Inno Setup安装包编译）
echo [4/5] 开始执行打包（PyInstaller编译+依赖内置复制，约3-10分钟）...
echo.
"%VENV_PYTHON%" build.py
if !errorlevel! neq 0 (
    echo.
    echo ❌ 打包执行失败，请查看上方build.py输出的错误信息。
    goto error_exit
)
echo.

:: [5/5] 打包完成，报告产物路径
echo [5/5] 打包流程全部结束
echo ==============================================
echo ✅  打包完成！产物位置:
echo.
echo    绿色版目录: %~dp0dist\AI_GZT\
echo    启动程序:   %~dp0dist\AI_GZT\AI_GZT.exe
if exist "%~dp0dist\AI_GZT_Setup_v1.0.exe" (
    echo    安装包:     %~dp0dist\AI_GZT_Setup_v1.0.exe
) else (
    echo    安装包:     未生成（未安装Inno Setup 6，仅输出绿色版，不影响使用）
)
echo ==============================================
echo.
pause
exit /b 0

:error_exit
echo.
echo ==============================================
echo ❌  打包过程中出现错误，请根据上方提示排查问题后重试。
echo ==============================================
echo.
pause
exit /b 1