[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$RunDir)
# Optional second-console path: elevate ONLY this observer when ETW rights require it.
. (Join-Path $PSScriptRoot 'runner_common.ps1')
$RunDir=(Resolve-Path -LiteralPath $RunDir).ProviderPath
$requestPath=Join-Path $RunDir 'observer.request.json'
$request=[IO.File]::ReadAllText($requestPath)|ConvertFrom-Json
if ($request.run_id -notmatch '^[a-f0-9]{32}$') { throw 'Invalid run ID' }
if (Test-Path (Join-Path $RunDir 'observer.ready.json')) { throw 'Observer already started for this run' }
$pm=(Resolve-Path -LiteralPath $request.presentmon_path).ProviderPath
$lock=Assert-PresentMon $pm
$readyPath=Join-Path $RunDir 'observer.ready.json'
$donePath=Join-Path $RunDir 'observer.done.json'
$job=$null
try {
    $help=Start-ObservedProcess $pm @('--help') $RunDir
    $helpResult=Finish-ObservedProcess $help 10 (Join-Path $RunDir 'presentmon.help.txt') (Join-Path $RunDir 'presentmon.help.stderr.txt')
    $helpText=[IO.File]::ReadAllText((Join-Path $RunDir 'presentmon.help.txt'))
    foreach ($flag in @('--process_name','--qpc_time','--v2_metrics','--session_name','--timed','--terminate_after_timed')) {
        if (-not $helpText.Contains($flag)) { throw ('PresentMon help missing '+$flag) }
    }
    if ($helpResult.Timeout) { throw 'PresentMon help timed out' }
    $start=[Diagnostics.Stopwatch]::GetTimestamp()
    $args=Get-PresentMonArguments $RunDir $request.run_id ([int]$request.observer_seconds)
    $job=Start-ObservedProcess $pm $args $RunDir
    Start-Sleep -Seconds 1
    if ($job.Process.HasExited) { throw 'PresentMon exited before app launch; inspect observer logs' }
    Write-JsonFile $readyPath ([ordered]@{schema=1;run_id=$request.run_id;observer_started_qpc=$start;
        observer_pid=$job.Process.Id;observer_sha256=$lock.sha256;observer_version=$lock.version;
        readiness='PROCESS_ALIVE_ONLY_NOT_ETW_PROOF';qpc_frequency=[Diagnostics.Stopwatch]::Frequency})
    $result=Finish-ObservedProcess $job ([int]$request.observer_seconds+15) (Join-Path $RunDir 'presentmon.stdout.txt') (Join-Path $RunDir 'presentmon.stderr.txt')
    $job=$null
    if ($result.Timeout) { Stop-OwnedTraceSession $pm $request.run_id $RunDir }
    Write-JsonFile $donePath ([ordered]@{schema=1;run_id=$request.run_id;observer_exit_code=$result.ExitCode;observer_timeout=$result.Timeout})
} catch {
    if ($null -ne $job) {
        try {
            $null=Finish-ObservedProcess $job 1 (Join-Path $RunDir 'presentmon.stdout.txt') (Join-Path $RunDir 'presentmon.stderr.txt')
            Stop-OwnedTraceSession $pm $request.run_id $RunDir
        } catch { }
    }
    Write-JsonFile $donePath ([ordered]@{schema=1;run_id=$request.run_id;observer_exit_code=$null;observer_timeout=$false;error=$_.Exception.Message})
    throw
}
