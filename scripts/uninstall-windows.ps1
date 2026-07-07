<#
  Removes the Location Display background Scheduled Task.

  Run from this repo:
    powershell -ExecutionPolicy Bypass -File scripts\uninstall-windows.ps1
#>

$ErrorActionPreference = "Stop"
$TaskName = "LocationDisplay"

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "Nothing to remove - '$TaskName' is not installed."
    return
}

Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Removed '$TaskName'. (Any already-running server stops at next log off / reboot,"
Write-Host "or end 'pythonw.exe' in Task Manager to stop it now.)"
