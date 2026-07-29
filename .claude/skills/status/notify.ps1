# Pops a Windows balloon reminder telling you to run /status.
# Reminder text lives in reminders.json (UTF-8) so this script stays pure ASCII
# and avoids Windows PowerShell 5.1 Cyrillic-encoding pitfalls.
# Pass -Text "..." to show that exact text instead of a reminders.json entry
# (used by track_tick.py for the per-project "draft ready" notification).
param([string]$Type = "update", [string]$Text = "")

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($Text) {
    $text = $Text
} else {
    $msgs = Get-Content -Raw -Encoding UTF8 (Join-Path $here "reminders.json") | ConvertFrom-Json
    $text = $msgs.$Type
    if (-not $text) { $text = $msgs.update }
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Information
$n.BalloonTipTitle = "Status Agent"
$n.BalloonTipText = $text
$n.Visible = $true
$n.ShowBalloonTip(10000)
Start-Sleep -Seconds 8
$n.Dispose()
