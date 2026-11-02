[CmdletBinding()]
param([string]$BuildDir=(Join-Path $PSScriptRoot '..\build'),[string]$Python='python.exe')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).ProviderPath
$vswhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (-not (Test-Path -LiteralPath $vswhere)) { throw 'Install Visual Studio Build Tools, Desktop development with C++, and a Windows SDK first.' }
# PS 5.1 returns the whole JSON array as one pipeline object; normalize after
# assignment so a single VS installation is not treated as a nested array.
$installs=(& $vswhere -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -format json | ConvertFrom-Json)
if ($installs -isnot [array]) { $installs=@($installs) }
if ($LASTEXITCODE -ne 0 -or $installs.Count -eq 0) { throw 'No usable MSVC x64 installation found.' }
$cap=(& cmake -E capabilities | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0) { throw 'CMake capabilities query failed.' }
$selected=$null;$generator=$null
foreach($install in ($installs | Sort-Object { [version]$_.installationVersion } -Descending)) {
    $major=([version]$install.installationVersion).Major
    $name=@($cap.generators | Where-Object {$_.name -match ('^Visual Studio '+$major+' ')})
    if ($name.Count -eq 1) { $selected=$install;$generator=$name[0].name;break }
}
if ($null -eq $selected) { throw 'Installed Visual Studio and CMake generators do not match. Update CMake or use a matching installed MSVC. Do not switch to MinGW.' }
$pythonPath=(Get-Command $Python -CommandType Application -ErrorAction Stop).Source
Write-Host ('Generator: '+$generator+'; VS: '+$selected.installationVersion+'; Python: '+$pythonPath)
& cmake -S $root -B $BuildDir -G $generator -A x64 "-DCMAKE_GENERATOR_INSTANCE=$($selected.installationPath)" "-DPython3_EXECUTABLE=$pythonPath"
if ($LASTEXITCODE -ne 0) { throw 'CMake configure failed.' }
