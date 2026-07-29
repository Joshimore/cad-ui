<#
.SYNOPSIS
    Register (or remove) the CAD UI status-skill automation as Windows Task Scheduler tasks.

.DESCRIPTION
    Creates three daily tasks that drive the bundled status skill:
      Status-StartWork  -> post_bookend.py --type start   (auto-sends "Начало дня")
      Status-Track      -> track_tick.py                   (drafts a "Трек", never sends)
      Status-EndWork    -> post_bookend.py --type end      (auto-sends "Конец дня" + stages summary)

    Portable: resolves the repo root and a Python interpreter automatically (prefers the
    repo .venv). The scripts are stdlib-only, so any Python 3.11+ works. Windows-only.

    NOTE: Task Scheduler does NOT wake the machine by default — a task only fires if the
    computer is on (and, for the balloon notifications, you are logged in) at that time.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .claude\skills\status\register_tasks.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .claude\skills\status\register_tasks.ps1 -Remove
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .claude\skills\status\register_tasks.ps1 -StartTime 08:30 -EndTime 21:00
#>
param(
    [string]   $StartTime = "09:00",
    [string[]] $TrackTimes = @("12:00", "15:00", "18:00", "21:00"),
    [string]   $EndTime   = "22:00",
    [switch]   $Remove
)

$ErrorActionPreference = "Stop"

if ($Remove) {
    Get-ScheduledTask -TaskName "Status-*" -ErrorAction SilentlyContinue |
        Unregister-ScheduledTask -Confirm:$false
    Write-Host "Removed Status-StartWork / Status-Track / Status-EndWork (if they existed)."
    return
}

# --- resolve paths -----------------------------------------------------------
$skillDir = $PSScriptRoot                                        # .claude/skills/status
$repo     = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$bookend  = Join-Path $skillDir "post_bookend.py"
$tick     = Join-Path $skillDir "track_tick.py"

# Prefer the repo venv's windowless interpreter; fall back to system pythonw, then python.
$venvPy = Join-Path $repo ".venv\Scripts\pythonw.exe"
if (Test-Path $venvPy) {
    $python = $venvPy
} else {
    $sys = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    $python = if ($sys) { $sys.Source } else { "pythonw" }
    Write-Warning "Repo .venv not found ($venvPy). Using '$python'. Tip: run start.bat first to create the venv."
}

# --- (re)register ------------------------------------------------------------
function Register-StatusTask {
    param([string]$Name, [string]$Script, [string]$Args, $Triggers, [string]$Desc)
    $action = New-ScheduledTaskAction -Execute $python `
        -Argument ('"{0}"{1}' -f $Script, $(if ($Args) { " $Args" } else { "" })) `
        -WorkingDirectory $repo
    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $Triggers `
        -Description $Desc -Force | Out-Null
}

Register-StatusTask -Name "Status-StartWork" -Script $bookend -Args "--type start" `
    -Triggers (New-ScheduledTaskTrigger -Daily -At $StartTime) `
    -Desc "CAD UI status skill: auto-send day-start message."

Register-StatusTask -Name "Status-Track" -Script $tick -Args "" `
    -Triggers ($TrackTimes | ForEach-Object { New-ScheduledTaskTrigger -Daily -At $_ }) `
    -Desc "CAD UI status skill: draft a per-project track update (does not send)."

Register-StatusTask -Name "Status-EndWork" -Script $bookend -Args "--type end" `
    -Triggers (New-ScheduledTaskTrigger -Daily -At $EndTime) `
    -Desc "CAD UI status skill: auto-send day-end message + stage daily summary."

# --- report ------------------------------------------------------------------
Write-Host ""
Write-Host "Registered CAD UI status tasks:" -ForegroundColor Green
Write-Host "  interpreter : $python"
Write-Host "  working dir : $repo"
Write-Host "  Status-StartWork  daily $StartTime          -> post_bookend.py --type start"
Write-Host "  Status-Track      daily $($TrackTimes -join ', ')  -> track_tick.py"
Write-Host "  Status-EndWork    daily $EndTime          -> post_bookend.py --type end"
Write-Host ""
Write-Host "Windows-only. The machine must be on at those times (Task Scheduler won't wake it)."
Write-Host "Remove later with:  register_tasks.ps1 -Remove"
