param(
    [switch]$NoBrowser,
    [switch]$SkipPull,
    [ValidateRange(1024, 65535)]
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$docsDir = Join-Path $repoRoot "docs"
$report = Join-Path $repoRoot "reports\daily_market_report.html"
$serverProcess = $null

function Invoke-Git {
    param([string[]]$Arguments)
    & git -C $repoRoot @Arguments
    return $LASTEXITCODE
}

function Test-PortInUse {
    param([int]$CheckPort)
    if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
        return [bool](Get-NetTCPConnection -LocalPort $CheckPort -State Listen -ErrorAction SilentlyContinue)
    }
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $client.Connect("127.0.0.1", $CheckPort)
        return $true
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

function Test-DashboardHealth {
    param([string]$BaseUrl)
    try {
        $rootResponse = Invoke-WebRequest -Uri "$BaseUrl/" -UseBasicParsing -TimeoutSec 2
        $dataResponse = Invoke-WebRequest -Uri "$BaseUrl/data/daily_radar.json" -UseBasicParsing -TimeoutSec 2
        if ($rootResponse.StatusCode -ne 200 -or $dataResponse.StatusCode -ne 200) {
            return $false
        }
        $null = $dataResponse.Content | ConvertFrom-Json
        return $true
    } catch {
        return $false
    }
}

try {
    if ($SkipPull) {
        Write-Host "已略過 git pull（-SkipPull）。"
    } elseif (-not (Get-Command git -ErrorAction SilentlyContinue)) {
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
    if ([string]::IsNullOrWhiteSpace($pythonCommand)) { throw "Python command resolution returned an empty path." }

    $selectedPort = $Port
    while ($selectedPort -lt ($Port + 20)) {
        if (-not (Test-PortInUse $selectedPort)) { break }
        $selectedPort++
    }
    if ($selectedPort -ge ($Port + 20)) { throw ("Dashboard port unavailable: " + $Port + "-" + ($Port + 19)) }

    $serverArgs = @()
    $serverArgs += $pythonArguments
    $serverArgs += "-m"
    $serverArgs += "http.server"
    $serverArgs += [string]$selectedPort
    $serverArgs += "-d"
    $serverArgs += ('"' + $docsDir + '"')
    $serverProcess = Start-Process -FilePath $pythonCommand -ArgumentList $serverArgs -WorkingDirectory $repoRoot -PassThru
    $url = "http://127.0.0.1:$selectedPort"
    $healthy = $false
    for ($attempt = 1; $attempt -le 20; $attempt++) {
        if (Test-DashboardHealth $url) {
            $healthy = $true
            break
        }
        if ($serverProcess.HasExited) { break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $healthy) {
        if ($serverProcess -and -not $serverProcess.HasExited) {
            Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
        }
        throw "Dashboard startup failed: HTTP health check did not pass."
    }

    Write-Host "Dashboard URL: $url/"
    if ($NoBrowser) {
        Write-Host "Browser launch skipped (-NoBrowser)."
    } else {
        Start-Process "$url/"
    }
    exit 0
} catch {
    Write-Host "Dashboard startup failed." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if (Test-Path -LiteralPath $report -PathType Leaf) {
        Write-Host "Fallback: open_daily_report.cmd"
    }
    exit 1
}
