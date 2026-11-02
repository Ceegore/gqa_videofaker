[CmdletBinding()]
param([string]$OutputPath='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
function Read-CimSafe {
    param([string]$ClassName)
    try { return @(Get-CimInstance -ClassName $ClassName -ErrorAction Stop) }
    catch { return @([pscustomobject]@{unavailable=$_.Exception.Message}) }
}
$r=[ordered]@{
    schema=1;read_only=$true;utc=[datetime]::UtcNow.ToString('o');
    os=Read-CimSafe 'Win32_OperatingSystem';
    computer=Read-CimSafe 'Win32_ComputerSystem';
    gpu=Read-CimSafe 'Win32_VideoController';
    monitor=Read-CimSafe 'Win32_DesktopMonitor';
    session_name=$env:SESSIONNAME;
    powershell=$PSVersionTable.PSVersion.ToString();
    qpc_frequency=[Diagnostics.Stopwatch]::Frequency;
    note='Inventory only. No GPU utilisation percentage, physical-display proof or SAC approval inferred.'
}
$json=$r|ConvertTo-Json -Depth 6
if($OutputPath){[IO.File]::WriteAllText($OutputPath,$json,(New-Object Text.UTF8Encoding($false)))}
$json
