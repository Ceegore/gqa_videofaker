# Run in Windows CI only. Tests do not create a graphics window or change policy.
[CmdletBinding()]
param([string]$Python='python.exe')
. (Join-Path $PSScriptRoot '..\tools\runner_common.ps1')
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).ProviderPath
$count=0
foreach($file in (Get-ChildItem -LiteralPath $root -Recurse -Filter '*.ps1' | Where-Object {$_.FullName -notmatch '[\\/]input_reference[\\/]'})) {
    $tokens=$null;$errors=$null
    $null=[Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$tokens,[ref]$errors)
    if ($errors.Count -gt 0) { throw ($file.FullName+': '+($errors|Out-String)) }
    $count++
}
$temp=Join-Path ([IO.Path]::GetTempPath()) ('fse-runner-'+[Guid]::NewGuid().ToString('N'))
$null=New-Item -ItemType Directory -Path $temp
try {
    $pythonPath=(Get-Command $Python -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
    $values=@('plain','with spaces','C:\some directory\','quote"inside','', 'two\\slashes', 'Gruesse')
    $code='import json,sys; print(json.dumps(sys.argv[1:]))'
    $arguments=@('-c',$code)+$values
    $job=Start-ObservedProcess $pythonPath $arguments $temp
    $r=Finish-ObservedProcess $job 20 (Join-Path $temp 'out.txt') (Join-Path $temp 'err.txt')
    if ($r.ExitCode -ne 0 -or $r.Timeout) { throw 'Subprocess smoke test failed.' }
    # Windows PowerShell 5.1 emits a JSON array from ConvertFrom-Json as one
    # pipeline object; assign first, then normalize to an array. PS7 enumerates
    # during the pipeline, so wrapping the pipeline directly would nest the array.
    $returned=[IO.File]::ReadAllText((Join-Path $temp 'out.txt'))|ConvertFrom-Json
    if($returned -isnot [array]) { $returned=@($returned) }
    if($returned.Count -ne $values.Count) { throw 'Argument count changed.' }
    for($i=0;$i -lt $values.Count;$i++) { if($returned[$i] -cne $values[$i]) { throw ('Argument mismatch '+$i) } }
    $job=Start-ObservedProcess $pythonPath @('-c','import sys; sys.exit(7)') $temp
    $r=Finish-ObservedProcess $job 20 (Join-Path $temp 'exit.txt') (Join-Path $temp 'exit.err.txt')
    if($r.ExitCode -ne 7 -or $r.Timeout) { throw 'Native exit code lost.' }
    $job=Start-ObservedProcess $pythonPath @('-c','import time; time.sleep(10)') $temp
    $r=Finish-ObservedProcess $job 1 (Join-Path $temp 'timeout.txt') (Join-Path $temp 'timeout.err.txt')
    if(-not $r.Timeout) { throw 'Timeout was not recognized.' }
    Write-Host ('RUNNER_TEST_PASS: '+$count+' scripts parsed; quoting, exit and timeout checked. No FSE proof.')
} finally { Remove-Item -LiteralPath $temp -Recurse -Force }
