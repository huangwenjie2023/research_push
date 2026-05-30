param(
    [string]$ProjectRoot = "E:\workshop\obsidian_file\research_push"
)

Set-Location $ProjectRoot

if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
        }
    }
}

if (-not $env:HTTP_PROXY) {
    $env:HTTP_PROXY = "http://127.0.0.1:7890"
}
if (-not $env:HTTPS_PROXY) {
    $env:HTTPS_PROXY = "http://127.0.0.1:7890"
}

$env:PYTHONPATH = Join-Path $ProjectRoot ".system"
New-Item -ItemType Directory -Force ".\.system\logs" | Out-Null
python -m research_push daily *> ".\.system\logs\daily_$(Get-Date -Format yyyyMMdd_HHmmss).log"
