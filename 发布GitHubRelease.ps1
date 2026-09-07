# ============================================================
# 发布GitHubRelease.ps1 — AI-GZT v1.0 GitHub Release 发布脚本
# 功能:
#   1. 创建 v1.0 草稿 Release（草稿状态外界不可见）
#   2. 上传 dist\AI_GZT_Setup_v1.0.exe（约199MB），失败自动重试6次
#   3. 上传成功后自动将草稿转为正式发布
# 凭据:复用 Git Credential Manager 已缓存的 GitHub 授权，无需重新登录
# 用法:powershell -ExecutionPolicy Bypass -File 发布GitHubRelease.ps1 -Step All
# ============================================================

param(
    [ValidateSet('Draft','Upload','All')]
    [string]$Step = 'All'
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ===== 配置 =====
$Repo      = 'cbhoooo-jpg/AI-GZT'
$Tag       = 'v1.0'
$ExePath   = Join-Path $PSScriptRoot 'dist\AI_GZT_Setup_v1.0.exe'
$AssetName = 'AI_GZT_Setup_v1.0.exe'
$InfoFile  = Join-Path $PSScriptRoot 'release_info.json'
$ApiBase   = "https://api.github.com/repos/$Repo"

# ===== Release 说明文案 =====
$ReleaseNotes = @'
# AI-GZT v1.0 正式版 🎉

本地优先的 AI 桌面助手:所有数据本地存储，支持离线部署本地大模型。

## ✨ 核心功能

- **大语言模型对话**:自然语言交互，支持云端 API 与本地模型离线部署
- **RAG 私有知识库**:内置 gte-small-zh 中文向量模型，支持代码库/文档智能检索问答
- **插件化扩展架构**，开箱即用多个插件:
  - 📁 文件格式转换（图片/文档/表格互转）
  - 🎨 AI 图片生成（文生图/图生图/多角度卡片）
  - 🛡️ 本地进程监控与恶意程序分级处置
  - 🌐 网页信息采集（财经/新闻/行业动态结构化整理）
  - 🔧 安全文件编辑引擎（防截断/防误改）
  - 💬 企业微信消息通道
- **定时任务调度**:可视化计划任务管理
- **文件仓库 / 网页日志 / 悬浮对话窗** 等桌面配套功能

## 📦 下载安装

下载下方 **AI_GZT_Setup_v1.0.exe**（约 199 MB），双击安装即可，支持 Windows 10 / 11（64 位）。

## 🔒 隐私说明

所有对话数据、知识库索引、配置文件均保存在本地，不上传任何第三方服务器。

---

**完整提交记录**:https://github.com/cbhoooo-jpg/AI-GZT/commits/main
'@

# ===== 工具函数:从 Git 凭据管理器取 token（不打印明文） =====
# 注意:不能用 PowerShell 管道向 git 喂 stdin —— 在 chcp 65001(UTF-8) 控制台下，
# PS5.1 向原生命令管道写数据会带 BOM/宽字节前缀，git 收到的首行不是 protocol=，
# 直接报 "fatal: refusing to work with credential missing protocol field"。
# 改用临时文件 + Start-Process 标准输入/输出重定向，字节级传递，不受任何代码页影响。
function Get-GitHubToken {
    $tmpIn  = [System.IO.Path]::GetTempFileName()
    $tmpOut = [System.IO.Path]::GetTempFileName()
    $tmpErr = [System.IO.Path]::GetTempFileName()
    try {
        # git credential 协议:纯 ASCII、无 BOM，以空行结束请求
        [System.IO.File]::WriteAllText($tmpIn, "protocol=https`r`nhost=github.com`r`n`r`n", [System.Text.Encoding]::ASCII)
        $proc = Start-Process -FilePath 'git' -ArgumentList @('credential','fill') `
            -RedirectStandardInput $tmpIn -RedirectStandardOutput $tmpOut -RedirectStandardError $tmpErr `
            -NoNewWindow -Wait -PassThru
        $cred = [System.IO.File]::ReadAllLines($tmpOut, [System.Text.Encoding]::UTF8)
        $line = $cred | Where-Object { $_ -match '^password=' } | Select-Object -First 1
        if (-not $line) {
            $errText = ([System.IO.File]::ReadAllText($tmpErr, [System.Text.Encoding]::UTF8)).Trim()
            throw "未能从 Git 凭据管理器获取 GitHub 授权。git 返回: $errText`n请先双击运行 推送到GitHub.bat 完成一次授权。"
        }
        return ($line -replace '^password=','')
    } finally {
        Remove-Item $tmpIn, $tmpOut, $tmpErr -Force -ErrorAction SilentlyContinue
    }
}

function New-ApiHeaders($token) {
    return @{ Authorization = "token $token"; 'User-Agent' = 'AI-GZT-Release'; Accept = 'application/vnd.github+json' }
}
# ===== 步骤1:创建草稿 Release（已存在则自动复用，不会重复创建） =====
function New-DraftRelease($token) {
    $headers = New-ApiHeaders $token
    # 注意:releases/tags/{tag} 端点查不到 draft 状态的 release（草稿尚未真正打 tag），
    # 必须列出全部 release 按 tag_name 匹配，否则重跑会重复创建草稿。
    $list = Invoke-RestMethod -Uri "$ApiBase/releases?per_page=100" -Headers $headers -TimeoutSec 15
    $existing = $list | Where-Object { $_.tag_name -eq $Tag } | Select-Object -First 1
    if ($existing) {
        Write-Host "[提示] Release $Tag 已存在 (id=$($existing.id), draft=$($existing.draft))，直接复用"
        return $existing
    }
    $body = @{
        tag_name         = $Tag
        target_commitish = 'main'
        name             = 'AI-GZT v1.0 正式版'
        body             = $ReleaseNotes
        draft            = $true
        prerelease       = $false
    } | ConvertTo-Json -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
    $r = Invoke-RestMethod -Uri "$ApiBase/releases" -Method Post -Headers $headers -ContentType 'application/json; charset=utf-8' -Body $bytes -TimeoutSec 20
    Write-Host "[OK] 草稿 Release 已创建，id=$($r.id)"
    return $r
}

# ===== 步骤2:上传安装包附件（失败自动重试 6 次） =====
function Upload-Asset($token, $releaseId) {
    if (-not (Test-Path $ExePath)) { throw "安装包不存在: $ExePath" }
    $sizeMB = [math]::Round((Get-Item $ExePath).Length / 1MB, 1)
    Write-Host "[信息] 待上传文件: $ExePath ($sizeMB MB)"

    $headers = New-ApiHeaders $token
    # 同名附件已存在（重跑场景）则先删除，避免冲突
    $rel = Invoke-RestMethod -Uri "$ApiBase/releases/$releaseId" -Headers $headers -TimeoutSec 15
    $old = $rel.assets | Where-Object { $_.name -eq $AssetName }
    foreach ($a in $old) {
        Write-Host "[清理] 删除已存在的同名附件 id=$($a.id)"
        Invoke-RestMethod -Uri "$ApiBase/releases/assets/$($a.id)" -Method Delete -Headers $headers -TimeoutSec 15 | Out-Null
    }

    $uploadUrl = "https://uploads.github.com/repos/$Repo/releases/$releaseId/assets?name=$AssetName"
    $maxTries  = 6
    for ($i = 1; $i -le $maxTries; $i++) {
        Write-Host ""
        Write-Host "--------------------------------------------"
        Write-Host "  第 $i 次尝试上传（最多 $maxTries 次，网络波动自动重试）"
        Write-Host "--------------------------------------------"
        try {
            $bytes = [System.IO.File]::ReadAllBytes($ExePath)
            $resp = Invoke-RestMethod -Uri $uploadUrl -Method Post -Headers $headers -ContentType 'application/octet-stream' -Body $bytes -TimeoutSec 1800
            Write-Host "[成功] 附件上传完成: $($resp.name)"
            Write-Host "       下载地址: $($resp.browser_download_url)"
            return $resp
        } catch {
            Write-Host "[失败] 第 $i 次上传出错: $($_.Exception.Message)"
            if ($i -lt $maxTries) {
                Write-Host "  8 秒后自动重试..."
                Start-Sleep -Seconds 8
            }
        }
    }
    throw "连续 $maxTries 次上传失败，请检查网络后重新双击运行（草稿会自动复用，不会重复创建）。"
}
# ===== 步骤3:将草稿转为正式发布 =====
function Publish-Release($token, $releaseId) {
    $headers = New-ApiHeaders $token
    $body = @{ draft = $false; prerelease = $false } | ConvertTo-Json -Compress
    $r = Invoke-RestMethod -Uri "$ApiBase/releases/$releaseId" -Method Patch -Headers $headers -ContentType 'application/json; charset=utf-8' -Body $body -TimeoutSec 20
    Write-Host "[OK] Release 已正式发布！"
    Write-Host "     页面地址: $($r.html_url)"
    return $r
}

# ===== 主流程 =====
Write-Host "============================================"
Write-Host "  AI-GZT v1.0 GitHub Release 发布工具"
Write-Host "============================================"
Write-Host ""

$token = Get-GitHubToken
Write-Host "[OK] 已从凭据管理器获取 GitHub 授权（用户 cbhoooo-jpg），无需重新登录"

if ($Step -eq 'Draft') {
    $rel = New-DraftRelease $token
    @{ release_id = $rel.id; html_url = $rel.html_url; upload_url = $rel.upload_url } | ConvertTo-Json | Set-Content $InfoFile -Encoding UTF8
    Write-Host "[完成] 草稿信息已保存到 release_info.json"
    return
}

if ($Step -eq 'Upload') {
    if (-not (Test-Path $InfoFile)) { throw '未找到 release_info.json，请先执行 Draft 步骤' }
    $info = Get-Content $InfoFile -Raw -Encoding UTF8 | ConvertFrom-Json
    Upload-Asset $token $info.release_id | Out-Null
    Publish-Release $token $info.release_id | Out-Null
    Write-Host ""
    Write-Host "============================================"
    Write-Host "  [全部完成] 请刷新 GitHub Releases 页面查看"
    Write-Host "============================================"
    return
}

# Step = All:创建草稿 -> 上传 -> 发布，一条龙
$rel = New-DraftRelease $token
Upload-Asset $token $rel.id | Out-Null
Publish-Release $token $rel.id | Out-Null
Write-Host ""
Write-Host "============================================"
Write-Host "  [全部完成] v1.0 已发布，访客可直接下载安装包"
Write-Host "  https://github.com/cbhoooo-jpg/AI-GZT/releases"
Write-Host "============================================"