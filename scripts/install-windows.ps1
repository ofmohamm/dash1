<#
  Installs the Location Display server as a background Scheduled Task on Windows.

  - Runs server.py with pythonw.exe (no console window)
  - Starts automatically at every log on
  - Restarts itself if it crashes or is closed
  - Survives closing the terminal and rebooting

  Run from this repo (no admin needed):
    powershell -ExecutionPolicy Bypass -File scripts\install-windows.ps1
#>

$ErrorActionPreference = "Stop"

$TaskName = "LocationDisplay"
$RepoRoot = Split-Path $PSScriptRoot -Parent
$ServerPy = Join-Path $RepoRoot "server.py"

if (-not (Test-Path $ServerPy)) {
    throw "Could not find server.py at $ServerPy"
}

# Find a windowless Python (pythonw.exe preferred, then the 'pyw' launcher).
function Find-Pythonw {
    $cmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) {
        $candidate = Join-Path (Split-Path $python.Source) "pythonw.exe"
        if (Test-Path $candidate) { return $candidate }
    }

    $pyw = Get-Command pyw.exe -ErrorAction SilentlyContinue
    if ($pyw) { return $pyw.Source }

    return $null
}

$Pythonw = Find-Pythonw
if (-not $Pythonw) {
    throw "Couldn't find pythonw.exe. Install Python from python.org (check 'Add to PATH'), then re-run."
}

Write-Host "Python : $Pythonw"
Write-Host "Server : $ServerPy"

$action = New-ScheduledTaskAction -Execute $Pythonw -Argument "`"$ServerPy`"" -WorkingDirectory $RepoRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force `
    -Description "Runs the Location Display server in the background." | Out-Null

Start-ScheduledTask -TaskName $TaskName

Write-Host ""
Write-Host "Installed and started. The server now runs in the background and"
Write-Host "starts automatically when you log in."
Write-Host "Open the display at:  http://127.0.0.1:3000/"
Write-Host ""
Write-Host "To remove it later:  powershell -ExecutionPolicy Bypass -File scripts\uninstall-windows.ps1"
