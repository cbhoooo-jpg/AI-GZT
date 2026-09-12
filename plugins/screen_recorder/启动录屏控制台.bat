@echo off
rem ============================================================
rem 录屏小控制台启动脚本（双击即用，无需打开工作台）
rem 自动切换到本脚本所在目录，保证 control_panel.py 能 import main
rem 使用 pythonw 后台启动，不弹黑色命令行窗口
rem ============================================================
cd /d "%~dp0"
start "" pythonw "control_panel.py"
exit