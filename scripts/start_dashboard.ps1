$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$docsDir = Join-Path $repoRoot "docs"

function Invoke-Git {
    param([string[]]$Arguments)
    & git -C $repoRoot @Arguments
    return $LASTEXITCODE
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Warning "找不到 Git；將使用本機現有資料啟動 Dashboard。"
} else {
    $status = (& git -C $repoRoot status --porcelain)
    if ($status) {
        Write-Warning "工作區有未提交修改，保留現況，不執行 pull："
        $status | ForEach-Object { Write-Host "  $_" }
    } else {
        $branch = (& git -C $repoRoot branch --show-current).Trim()
        if ($branch -ne "main") {
            $switchCode = Invoke-Git @("switch", "main")
            if ($switchCode -ne 0) { Write-Warning "無法切換 main；將使用目前資料。" }
        }
        if ((& git -C $repoRoot branch --show-current).Trim() -eq "main") {
            $pullCode = Invoke-Git @("pull", "--ff-only", "origin", "main")
            if ($pullCode -ne 0) { Write-Warning "main 更新失敗；將使用本機 cached data。" }
        }
    }
}

$pythonPath = Join-Path $repoRoot ".venv\Scripts\python.exe"
$pythonCommand = $pythonPath
$pythonArguments = @()
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $pythonCommand = "py"
        $pythonArguments = @("-3")
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonCommand = "python"
    } else {
        throw "找不到 Python。請先建立 .venv 或安裝 Python 3。"
    }
}

$port = 8765
while ($port -lt 8785) {
    $occupied = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if (-not $occupied) { break }
    $port++
}
if ($port -ge 8785) { throw "找不到可用的 Dashboard port（8765-8784）。" }

$serverArgs = $pythonArguments + @("-m", "http.server", "$port", "--directory", $docsDir)
Start-Process -FilePath $pythonCommand -ArgumentList $serverArgs -WorkingDirectory $repoRoot
Start-Sleep -Milliseconds 800
$url = "http://127.0.0.1:$port/"
Write-Host "台股籌碼雷達 Dashboard：$url"
Start-Process $url
