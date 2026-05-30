param(
    [string]$TaskName = "research_push_daily",
    [string]$ProjectRoot = "E:\workshop\obsidian_file\research_push",
    [string]$At = "08:30"
)

$script = Join-Path $ProjectRoot ".system\scripts\run_daily.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`" -ProjectRoot `"$ProjectRoot`""
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Daily research_push Obsidian update" -Force
Write-Host "Installed task $TaskName at $At"
