[CmdletBinding()]
param([string]$BuildDir=(Join-Path $PSScriptRoot '..\build'),[switch]$AuthorizedCi)
. (Join-Path $PSScriptRoot 'runner_common.ps1')
if (-not $AuthorizedCi -or $env:CI -ne 'true') { throw 'This execution gate is for authorized CI only, not the protected development host.' }
$build=(Resolve-Path -LiteralPath $BuildDir).ProviderPath
$started=[datetime]::UtcNow
$job=Start-ObservedProcess (Get-Command ctest -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source @('--test-dir',$build,'-C','Release','--output-on-failure','--timeout','120','--output-junit',(Join-Path $build 'ctest.xml')) $build
$r=Finish-ObservedProcess $job 300 (Join-Path $build 'ctest.stdout.txt') (Join-Path $build 'ctest.stderr.txt')
Write-Host ([IO.File]::ReadAllText((Join-Path $build 'ctest.stdout.txt')))
$code=$r.ExitCode
if ($code -ne 0 -or $r.Timeout) {
    $out=Join-Path $build 'ci-security.json'
    $null=& (Join-Path $PSScriptRoot 'inspect_sac_environment.ps1') -BinaryPaths @((Join-Path $build 'Release\FSEProbe.exe'),(Join-Path $build 'Release\probe_core_tests.exe')) -SinceUtc $started -OutputPath $out
    $diag=[IO.File]::ReadAllText($out)|ConvertFrom-Json
    $text=[IO.File]::ReadAllText((Join-Path $build 'ctest.stdout.txt'))+[IO.File]::ReadAllText((Join-Path $build 'ctest.stderr.txt'))
    if ($diag.related_enforced_block -or $text -match '(?i)0x800711c7') {
        Write-Host 'BLOCKED_BY_APP_CONTROL: test bodies may not have executed; no product regression established.'
        exit 42
    }
    if ($r.Timeout) { throw 'CTest timeout; test result is incomplete.' }
    exit $code
}
