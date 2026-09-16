param(
    [string]$OutputDirectory = ""
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$source = Join-Path $repoRoot "reports\daily_market_report.html"
$radarJson = Join-Path $repoRoot "docs\data\daily_radar.json"
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $repoRoot "exports\share" }

function Find-PrivacyIssue {
    param([string]$Text)
    $patterns = @(
        '(?i)[A-Z]:\\Users\\',
        '(?i)/Users/[A-Za-z0-9._-]+/',
        '(?i)https?://github\.com/a275618631/tw-stock-chip-radar',
        '(?i)(ghp_|github_pat_|personal access token|github.{0,20}token)',
        '(?i)(api[_ -]?key|access[_ -]?token)\s*[:=]',
        '(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}'
    )
    foreach ($pattern in $patterns) {
        if ($Text -match $pattern) { return $pattern }
    }
    return $null
}

try {
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "找不到來源報告：$source"
    }
    $utf8 = New-Object -TypeName System.Text.UTF8Encoding -ArgumentList $false
    $sourceText = [System.IO.File]::ReadAllText($source, $utf8)
    $sourceIssue = Find-PrivacyIssue $sourceText
    if ($sourceIssue) { throw "來源報告 privacy scan 失敗（$sourceIssue）；停止匯出。" }

    $generated = Get-Date -Format "yyyy-MM-dd HH:mm:ss K"
    $freshness = "未載入"
    if (Test-Path -LiteralPath $radarJson -PathType Leaf) {
        $payload = [System.IO.File]::ReadAllText($radarJson, $utf8) | ConvertFrom-Json
        $freshness = "法人 $($payload.freshness.institutional) · 分點 $($payload.freshness.broker) · Macro $($payload.freshness.macro)"
    }
    $banner = @"
<section class="share-banner" style="max-width:960px;margin:24px auto;padding:24px;border:2px solid #4ecdc4;border-radius:16px;background:#101820;color:#eaeaea;font-family:system-ui,-apple-system,'Segoe UI',sans-serif">
  <p style="margin:0 0 8px;color:#4ecdc4;font-weight:700;letter-spacing:.08em">台股籌碼雷達｜Demo Snapshot</p>
  <h1 style="margin:0 0 12px">固定時間點報告</h1>
  <p style="margin:6px 0">這是固定時間點報告，不會自動更新。</p>
  <p style="margin:6px 0"><strong>Generated:</strong> $generated<br><strong>Data Freshness:</strong> $freshness</p>
  <p style="margin:12px 0 0;color:#ffe66d">僅供研究展示，不是投資建議。</p>
</section>
"@
    $snapshot = $sourceText.Replace("<body>", "<body>$banner")
    if ($snapshot -eq $sourceText) { throw "來源 HTML 缺少可插入的 body 標籤；停止匯出。" }
    $outputDir = [System.IO.Path]::GetFullPath($OutputDirectory)
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
    $filename = "tw_stock_chip_radar_demo_$(Get-Date -Format 'yyyyMMdd_HHmm').html"
    $output = Join-Path $outputDir $filename
    [System.IO.File]::WriteAllText($output, $snapshot, $utf8)

    $outputText = [System.IO.File]::ReadAllText($output, $utf8)
    $outputIssue = Find-PrivacyIssue $outputText
    if ($outputIssue) {
        Remove-Item -LiteralPath $output -Force
        throw "輸出報告 privacy scan 失敗（$outputIssue）；已移除未通過的 snapshot。"
    }
    Write-Host "Share Snapshot 已產生：$output"
    Write-Host "固定時間點檔案，不會自動更新；可直接分享此單一 HTML。"
    exit 0
} catch {
    Write-Host "Share Snapshot 匯出失敗。" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
