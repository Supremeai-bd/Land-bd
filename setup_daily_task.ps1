# PowerShell script to register Windows Task Scheduler for Daily D1 Sync
$TaskName = "RaipurCadastre_DailyD1Sync"
$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument '/c "F:\khotiyan book\RUN_DAILY_SYNC.bat"'
# Trigger at 06:15 AM every day (after 06:00 AM UTC reset)
$Trigger = New-ScheduledTaskTrigger -Daily -At "06:15AM"
# Setting: if missed (e.g. PC was turned off at 6:15 AM), run as soon as possible after startup
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Force
Write-Host "✓ Windows Scheduled Task '$TaskName' registered successfully!"
Write-Host "It will run every morning at 06:15 AM (or immediately after PC startup if turned on later)."

