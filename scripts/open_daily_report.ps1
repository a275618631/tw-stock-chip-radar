$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$report = Join-Path $repoRoot "reports\daily_market_report.html"

if (Get-Command git -ErrorAction SilentlyContinue) {
    $status = (& git -C $repoRoot status --porcelain)
    if ($status) {
        Write-Warning "工作區有未提交修改，保留現況，不執行 pull。"
    } else {
        $branch = (& git -C $repoRoot branch --show-current).Trim()
        if ($branch -eq "main") {
            & git -C $repoRoot pull --ff-only origin main
            if ($LASTEXITCODE -ne 0) { Write-Warning "更新失敗，以下開啟本機 cached report。" }
        } else {
            Write-Warning "目前分支為 $branch，未切換分支；以下開啟本機 cached report。"
        }
    }
}

if (-not (Test-Path -LiteralPath $report -PathType Leaf)) {
    throw "找不到 $report；請先執行 GitHub Actions 或 generate_daily_report.py。"
}

Write-Host "開啟本機 daily HTML report：$report"
Start-Process -FilePath $report -WorkingDirectory (Split-Path -Parent $report)
