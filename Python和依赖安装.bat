@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title AI_GZT一键环境安装脚本
echo ==============================================
echo          AI智能助手 一键环境安装工具
echo ==============================================
echo.

:: 配置项
set PYTHON_VERSION=3.11.9
set PYTHON_DOWNLOAD_URL=https://mirrors.huaweicloud.com/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-amd64.exe
set PYTHON_INSTALL_PATH=%LOCALAPPDATA%\Programs\Python\Python311
set PIP_MIRROR=https://mirrors.aliyun.com/pypi/simple

:: 第一步:检测是否已安装Python 3.11
echo [1/6] 正在检测Python环境...
set PYTHON_EXE=
if exist "%PYTHON_INSTALL_PATH%\python.exe" (
    set PYTHON_EXE=%PYTHON_INSTALL_PATH%\python.exe
    goto python_found
)

:: 尝试从系统PATH查找Python 3.11
for /f "delims=" %%i in ('py -3.11 --version 2^>nul') do set PY_VER_OUTPUT=%%i
echo !PY_VER_OUTPUT! | findstr /c:"3.11" >nul
if !errorlevel! equ 0 (
    for /f "delims=" %%i in ('where py') do set PYTHON_EXE=%%i -3.11
    goto python_found
)

for /f "delims=" %%i in ('python --version 2^>nul') do set PY_VER_OUTPUT=%%i
echo !PY_VER_OUTPUT! | findstr /c:"3.11" >nul
if !errorlevel! equ 0 (
    for /f "delims=" %%i in ('where python') do set PYTHON_EXE=%%i
    goto python_found
)

:: 未找到Python，开始安装
echo 未检测到Python 3.11，即将自动下载并静默安装...
echo 下载地址:%PYTHON_DOWNLOAD_URL%
echo 安装路径:%PYTHON_INSTALL_PATH%（无需管理员权限）
echo.

:: 下载安装包到临时目录
set INSTALLER_PATH=%TEMP%\python-%PYTHON_VERSION%-amd64.exe
echo 正在下载Python安装包...
powershell -Command "Invoke-WebRequest -Uri '%PYTHON_DOWNLOAD_URL%' -OutFile '%INSTALLER_PATH%' -UseBasicParsing"
if !errorlevel! neq 0 (
    echo 错误:Python安装包下载失败，请检查网络连接后重试。
    goto error_exit
)

:: 静默安装Python
echo 正在静默安装Python %PYTHON_VERSION%，请稍候...
start /wait "" "%INSTALLER_PATH%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1
if !errorlevel! neq 0 (
    echo 错误:Python安装失败，请手动运行安装包排查问题。
    del "%INSTALLER_PATH%" >nul 2>&1
    goto error_exit
)

:: 删除安装包
del "%INSTALLER_PATH%" >nul 2>&1

:: 验证安装结果
if not exist "%PYTHON_INSTALL_PATH%\python.exe" (
    echo 错误:Python安装完成后未找到可执行文件，请手动检查安装路径。
    goto error_exit
)
set PYTHON_EXE=%PYTHON_INSTALL_PATH%\python.exe

:python_found
echo ✅ Python环境检测通过:
%PYTHON_EXE% --version
echo.

:: 第二步:检测并安装VC++ 2015-2022 x64运行库
echo [2/6] 正在检测Microsoft Visual C++ 2015-2022 x64运行库...
set VC_REDIST_URL=https://aka.ms/vs/16/release/vc_redist.x64.exe
set VC_REDIST_PATH=%TEMP%\vc_redist.x64.exe
set VC_INSTALLED=0

:: 通过系统注册表检测运行库是否已安装
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" /v Installed 2>nul | findstr /c:"0x1" >nul
if !errorlevel! equ 0 (
    set VC_INSTALLED=1
)
:: 兼容WOW64重定向注册表路径检测
if !VC_INSTALLED! equ 0 (
    reg query "HKLM\SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" /v Installed 2>nul | findstr /c:"0x1" >nul
    if !errorlevel! equ 0 (
        set VC_INSTALLED=1
    )
)

if !VC_INSTALLED! equ 1 (
    echo ✅ VC++运行库已安装，跳过安装步骤
    goto vc_done
)

echo 未检测到VC++运行库，即将自动下载并静默安装...
echo 下载地址:%VC_REDIST_URL%
powershell -Command "Invoke-WebRequest -Uri '%VC_REDIST_URL%' -OutFile '%VC_REDIST_PATH%' -UseBasicParsing"
if !errorlevel! neq 0 (
    echo 错误:VC++运行库安装包下载失败，请检查网络连接后重试。
    goto error_exit
)

echo 正在静默安装VC++ 2015-2022 x64运行库，请稍候...
:: 静默安装参数:/quiet 无界面 /norestart 不自动重启
start /wait "" "%VC_REDIST_PATH%" /quiet /norestart
set VC_INSTALL_EXIT=!errorlevel!
:: 自动清理安装包
del "%VC_REDIST_PATH%" >nul 2>&1

:: 安装退出码:0=成功 3010=成功但需要重启（无需立即重启，不影响运行）
if !VC_INSTALL_EXIT! neq 0 if !VC_INSTALL_EXIT! neq 3010 (
    echo 错误:VC++运行库安装失败，退出码:!VC_INSTALL_EXIT!
    echo 可手动访问以下地址下载安装后重试:%VC_REDIST_URL%
    goto error_exit
)

echo ✅ VC++运行库安装完成
:vc_done
echo.

:: 第三步:升级pip并配置国内源
echo [3/6] 正在配置pip国内镜像并升级pip...
%PYTHON_EXE% -m pip install --upgrade pip -i %PIP_MIRROR%
if !errorlevel! neq 0 (
    echo 警告:pip升级失败，将继续使用现有版本安装依赖...
)
%PYTHON_EXE% -m pip config set global.index-url %PIP_MIRROR%
echo ✅ pip配置完成
echo.

:: 第四步:安装项目依赖
echo [4/6] 正在安装项目依赖包（总大小约3.5G，预计5-15分钟，请耐心等待）...
echo 依赖清单:requirements.txt
%PYTHON_EXE% -m pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo 错误:依赖安装失败，请根据上方错误信息排查网络或包冲突问题。
    goto error_exit
)
echo ✅ 所有依赖安装完成
echo.

:: 第五步:校验核心依赖
echo [5/6] 正在校验核心依赖安装结果...
set CHECK_FAILED=0
%PYTHON_EXE% -c "import PySide6; print(f'✅ PySide6 {PySide6.__version__} 安装成功')" 2>nul || (
    echo ❌ PySide6 安装失败
    set CHECK_FAILED=1
)
%PYTHON_EXE% -c "import fastapi; print(f'✅ FastAPI {fastapi.__version__} 安装成功')" 2>nul || (
    echo ❌ FastAPI 安装失败
    set CHECK_FAILED=1
)
%PYTHON_EXE% -c "import torch; print(f'✅ PyTorch {torch.__version__} 安装成功')" 2>nul || (
    echo ❌ PyTorch 安装失败
    set CHECK_FAILED=1
)
%PYTHON_EXE% -c "import transformers; print(f'✅ Transformers {transformers.__version__} 安装成功')" 2>nul || (
    echo ❌ Transformers 安装失败
    set CHECK_FAILED=1
)
echo.

if !CHECK_FAILED! equ 1 (
    echo 警告:部分核心依赖校验失败，请重新运行脚本或手动执行pip install安装对应包。
    goto error_exit
)

:: 第六步:完成提示
echo [6/6] 环境配置全部完成！
echo ==============================================
echo ✅  AI智能助手运行环境安装成功！
echo.
echo Python路径:%PYTHON_EXE%
echo 你现在可以直接运行 main.py 启动程序:
echo     %PYTHON_EXE% main.py
echo ==============================================
echo.
pause
exit /b 0

:error_exit
echo.
echo ==============================================
echo ❌  环境安装过程中出现错误，请根据上方提示排查问题后重试。
echo ==============================================
echo.
pause
exit /b 1