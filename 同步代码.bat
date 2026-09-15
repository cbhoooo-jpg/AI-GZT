@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

rem ============================================================
rem  AI智能助手 · 双机一键同步脚本（以 Gitee 为中转）
rem ------------------------------------------------------------
rem  用法:
rem    同步代码.bat            双击交互模式（结束暂停，可选择顺带推 GitHub）
rem    同步代码.bat gitee      静默模式:只与 Gitee 双向同步（AI 助手收到"同步"提醒时调用）
rem    同步代码.bat all        静默模式:同步 Gitee 成功后顺带推送 GitHub
rem    同步代码.bat pull       静默模式:仅拉取，不推送
rem ------------------------------------------------------------
rem  安全承诺:
rem    1) 绝不自动 commit，只有已提交的内容才会被同步；
rem    2) 未提交的已跟踪改动先 stash 保护，同步后自动恢复；
rem    3) 两台机器都有新提交（分叉）时立即停止，不强行合并；
rem    4) stash 恢复发生冲突时保留 stash 不丢弃，交由人工处理；
rem    5) GitHub 推送失败只警告，不影响 Gitee 同步成果；
rem    6) 瘦身保护（2026-09-15）:plugins/ 与「视频剪辑工具/」已迁出主仓库
rem       （插件→独立插件集仓库，由插件市场按需安装；视频剪辑工具→独立仓库），
rem       任何机器拉取/同步都不得把它们重新纳入git跟踪，第8.5步自动纠偏，无需人工说明。
rem ============================================================

set "MODE=%~1"
if "%MODE%"=="" set "MODE=interactive"
set "QUIET=0"
set "DO_GITHUB=0"
set "PULL_ONLY=0"
if /i "%MODE%"=="gitee" set "QUIET=1"
if /i "%MODE%"=="all"   set "QUIET=1" & set "DO_GITHUB=1"
if /i "%MODE%"=="pull"  set "QUIET=1" & set "PULL_ONLY=1"

cd /d "%~dp0"
title AI智能助手 - 代码同步

echo ============================================================
echo   AI智能助手 · 双机代码同步（Gitee 中转）
echo   模式:%MODE%    时间:%date% %time%
echo ============================================================
echo.

rem ---------- 1. 环境校验:必须在 git 仓库内 ----------
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo [错误] 当前目录不是 Git 仓库:%cd%
    goto fail_end
)

rem ---------- 2. 校验 gitee 远程与当前分支 ----------
git remote get-url gitee >nul 2>&1
if errorlevel 1 (
    echo [错误] 未配置名为 gitee 的远程仓库，请先执行:
    echo        git remote add gitee https://gitee.com/chen-bohan3000/ai-gzt.git
    goto fail_end
)
for /f "delims=" %%b in ('git branch --show-current') do set "BRANCH=%%b"
if "%BRANCH%"=="" (
    echo [错误] 当前处于分离头指针状态，请先 git checkout main
    goto fail_end
)
echo [信息] 当前分支:%BRANCH%

for /f "delims=" %%h in ('git rev-parse --short HEAD') do set "HEAD_BEFORE=%%h"
echo [信息] 同步前提交:%HEAD_BEFORE%
echo.

rem ---------- 3. 未提交的已跟踪改动:stash 保护（不含未跟踪文件，避免收纳大视频） ----------
set "STASHED=0"
git diff --quiet HEAD --
if errorlevel 1 (
    echo [保护] 检测到未提交的已跟踪改动，先临时保存（stash）...
    git stash push -m "auto-sync-%date:/=%%time::=%"
    if errorlevel 1 (
        echo [错误] 改动临时保存失败，为安全起见中止同步。
        goto fail_end
    )
    set "STASHED=1"
    echo [保护] 改动已安全暂存，同步结束后自动恢复。
) else (
    echo [正常] 工作区无未提交的已跟踪改动。
)

rem 未跟踪文件仅提示:它们不会被同步，也不会被移动
for /f %%c in ('git status --porcelain ^| find /c "??"') do set "UNTRACKED=%%c"
if not "%UNTRACKED%"=="0" (
    echo [提示] 存在 %UNTRACKED% 个未跟踪文件/目录（如参赛材料、本地配置），不纳入同步。
)
echo.

rem ---------- 4. 拉取 Gitee 最新引用 ----------
echo [步骤] 正在连接 Gitee 拉取最新状态...
git fetch gitee
if errorlevel 1 (
    echo [错误] 连接 Gitee 失败（网络/认证问题），本次未做任何改动。
    if "!STASHED!"=="1" (
        echo [恢复] 正在还原你刚才的未提交改动...
        git stash pop
    )
    goto fail_end
)

rem ---------- 5. 判断本地与 gitee/分支 的领先/落后关系 ----------
set "AHEAD=0"
set "BEHIND=0"
for /f "tokens=1,2" %%a in ('git rev-list --left-right --count HEAD...gitee/%BRANCH% 2^>nul') do (
    set "AHEAD=%%a"
    set "BEHIND=%%b"
)
echo [状态] 本地领先 !AHEAD! 个提交，远程领先 !BEHIND! 个提交。
echo.
rem ---------- 6. 分叉保护:两台机器都有新提交时立即停止 ----------
if not "!AHEAD!"=="0" if not "!BEHIND!"=="0" (
    echo [停止] 本地与 Gitee 已分叉:本地有 !AHEAD! 个提交未推送，远程有 !BEHIND! 个提交未拉取。
    echo        脚本不会强行合并。正在先还原你的未提交改动，然后请人工执行:
    echo          git pull --rebase gitee %BRANCH%
    echo        解决冲突后重新运行本脚本即可。
    if "!STASHED!"=="1" (
        echo [恢复] 正在还原同步前的未提交改动...
        git stash pop
    )
    goto fail_end
)

rem ---------- 7. 快进拉取远程新提交（仅允许快进，绝不产生意外合并提交） ----------
if not "!BEHIND!"=="0" (
    echo [拉取] Gitee 有 !BEHIND! 个新提交，执行快进合并...
    git merge --ff-only gitee/%BRANCH%
    if errorlevel 1 (
        echo [错误] 快进合并失败，已暂存改动保留在 stash 中未丢失。
        echo        请人工执行 git status 检查，确认后 git stash pop 还原改动。
        goto fail_end
    )
    echo [拉取] 本地已更新到 Gitee 最新。
) else (
    echo [拉取] Gitee 无新提交，本地已是最新。
)
echo.

rem ---------- 8. 恢复同步前暂存的未提交改动 ----------
if "!STASHED!"=="1" (
    echo [恢复] 正在还原同步前的未提交改动...
    git stash pop
    if errorlevel 1 (
        echo [警告] 改动与新拉取的内容发生冲突，stash 已保留未删除（git stash list 可查）。
        echo        请手动解决冲突文件，再执行 git stash drop 清理本条暂存。
        goto fail_end
    )
    echo [恢复] 未提交改动已完整还原。
)
echo.

rem ---------- 8.5 瘦身保护:plugins/ 与「视频剪辑工具/」已迁出主仓库，禁止重新跟踪 ----------
rem 背景（2026-09-15）:9个冻结插件迁入独立插件集仓库（由插件市场按需安装），
rem 「视频剪辑工具」迁入独立仓库；二者均已从主仓库HEAD删除，任何机器pull都不会再得到。
rem 此处为双保险:若检测到它们重新出现在git索引（如旧机器误提交带回），立即中止，防止扩散推送。
set "SLIM_CHECK="
for /f "delims=" %%p in ('git ls-files plugins 视频剪辑工具 2^>nul') do set "SLIM_CHECK=%%p"
if defined SLIM_CHECK (
    echo [停止] 检测到已瘦身迁出的文件仍被git跟踪，例如:!SLIM_CHECK!
    echo        plugins/ 与「视频剪辑工具/」已迁出主仓库（插件走插件市场按需安装，视频工具独立仓库）。
    echo        本次同步中止，禁止把它们重新推回远程。请先执行以下命令取消跟踪，再重新同步:
    echo          git rm -r --cached --ignore-unmatch plugins 视频剪辑工具
    echo          git commit -m "chore: 取消跟踪已瘦身迁出的plugins与视频剪辑工具"
    goto fail_end
)

rem ---------- 9. 推送本地新提交到 Gitee ----------
if "!PULL_ONLY!"=="1" (
    echo [模式] pull 仅拉取模式，跳过推送。
    goto success_end
)
if not "!AHEAD!"=="0" (
    echo [推送] 本地有 !AHEAD! 个新提交，正在推送到 Gitee...
    git push gitee %BRANCH%
    if errorlevel 1 (
        echo [错误] 推送到 Gitee 失败（网络/认证问题，或远程期间又有新提交）。
        echo        你的提交已安全保留在本地，网络恢复后重新运行本脚本即可。
        goto fail_end
    )
    echo [推送] Gitee 推送成功。
) else (
    echo [推送] 本地无新提交，Gitee 无需推送。
)
echo.

rem ---------- 10. 静默 all 模式:顺带推送 GitHub（失败只警告） ----------
if "!DO_GITHUB!"=="1" (
    git remote get-url origin >nul 2>&1
    if errorlevel 1 (
        echo [警告] 未配置 origin（GitHub）远程，跳过 GitHub 推送。
    ) else (
        echo [推送] 正在推送到 GitHub（网络较慢，请耐心等待）...
        git push origin %BRANCH%
        if errorlevel 1 (
            echo [警告] GitHub 推送失败（通常是网络原因），不影响 Gitee 同步成果。
            echo        网络恢复后执行:同步代码.bat all
        ) else (
            echo [推送] GitHub 推送成功。
        )
    )
    echo.
)

rem ---------- 11. 交互模式:询问是否顺带推送 GitHub ----------
if "!QUIET!"=="0" (
    git remote get-url origin >nul 2>&1
    if not errorlevel 1 (
        set "GH_CHOICE=n"
        set /p "GH_CHOICE=是否顺带推送到 GitHub？网络可能较慢 [y/N]: "
        if /i "!GH_CHOICE!"=="y" (
            git push origin %BRANCH%
            if errorlevel 1 (
                echo [警告] GitHub 推送失败，不影响 Gitee 同步成果。
            ) else (
                echo [推送] GitHub 推送成功。
            )
        )
    )
)

:success_end
for /f "delims=" %%h in ('git rev-parse --short HEAD') do set "HEAD_AFTER=%%h"
echo ============================================================
echo   [完成] 同步成功结束
echo   同步前:%HEAD_BEFORE%    同步后:%HEAD_AFTER%
echo   纪律:开工前先 pull（同步代码.bat pull），收工前 push（双击本脚本）
echo ============================================================
if "!QUIET!"=="0" pause
exit /b 0

:fail_end
echo ============================================================
echo   [中止] 同步未完成，请按上方提示处理后重试。
echo   本地所有已提交内容都不会丢失。
echo ============================================================
if "!QUIET!"=="0" pause
exit /b 1