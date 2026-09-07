@echo off
chcp 936 >nul
cd /d "D:\AI仓库文件夹\AI智能助手"
echo ============================================
echo   AI-GZT 推送到 GitHub
echo ============================================
echo.
echo  本地提交已完成（113个文件，commit f9a596d）
echo  即将推送到: https://github.com/cbhooo-jpg/AI-GZT
echo.
echo  *** 如果弹出 GitHub 登录/授权窗口 ***
echo  *** 请在浏览器中登录并点击 Authorize 授权 ***
echo.
echo ============================================
echo.
set /a tries=0
:retry
set /a tries+=1
echo.
echo --------------------------------------------
echo  第 %tries% 次尝试推送（最多 6 次，网络抖动自动重试）
echo --------------------------------------------
git push -u origin main
if %errorlevel%==0 goto success
if %tries% geq 6 goto fail
echo.
echo  [网络波动] 第 %tries% 次失败，5 秒后自动重试...
echo  （授权已完成，不会再弹出登录窗口）
timeout /t 5 /nobreak >nul
goto retry

:success
echo.
echo ============================================
echo  [成功] 推送完成！请刷新 GitHub 仓库页面查看:
echo  https://github.com/cbhoooo-jpg/AI-GZT
echo ============================================
goto end

:fail
echo.
echo ============================================
echo  [失败] 连续 6 次推送失败，退出码 %errorlevel%
echo  这通常是网络问题，请过几分钟后双击本脚本重试，
echo  或把本窗口内容截图发给 AI 助手排查。
echo ============================================

:end
pause