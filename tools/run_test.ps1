[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$App,
    [Parameter(Mandatory=$true)][string]$PresentMon,
    [string]$Python='python.exe',
    [ValidateSet('legacy-exclusive','borderless-control')][string]$Mode='legacy-exclusive',
    [ValidateSet('off','low','medium','high')][string]$Load='low',
    [ValidateRange(0,31)][int]$Monitor=0,
    [ValidateRange(15,300)][int]$Duration=60,
    [ValidateRange(3,60)][int]$Warmup=8,
    [ValidateRange(15,120)][int]$FpsCap=60,
    [string]$OutputRoot=(Join-Path $PSScriptRoot '..\logs'),
    [switch]$PhysicalDesktop,
    [switch]$AutoMark,
    [switch]$ExternalObserver
)
. (Join-Path $PSScriptRoot 'runner_common.ps1')
if (-not $PhysicalDesktop) { throw 'Use -PhysicalDesktop only after confirming a local physical GPU/display session, not VM/RDP/Sandbox.' }
if ($Duration -lt $Warmup+8) { throw 'Duration must exceed warmup by at least 8 seconds.' }
$principal=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run the app runner without elevation. For ETW elevation use -ExternalObserver and elevate ONLY start_observer.ps1.'
}
$appPath=(Resolve-Path -LiteralPath $App).ProviderPath
$pmPath=(Resolve-Path -LiteralPath $PresentMon).ProviderPath
if ([IO.Path]::GetFileName($appPath) -cne 'FSEProbe.exe') { throw 'Expected the unchanged application filename FSEProbe.exe.' }
$pythonPath=(Get-Command $Python -CommandType Application -ErrorAction Stop).Source
$lock=Assert-PresentMon $pmPath
$runId=[Guid]::NewGuid().ToString('N')
$null=New-Item -ItemType Directory -Path $OutputRoot -Force
$root=(Resolve-Path -LiteralPath $OutputRoot).ProviderPath
$runDir=Join-Path $root $runId
$null=New-Item -ItemType Directory -Path $runDir -ErrorAction Stop
$startedUtc=[datetime]::UtcNow
$observerSeconds=$Duration+45
$session=[ordered]@{
    schema=1;run_id=$runId;evidence_kind='REAL_WINDOWS_RUN';mode=$Mode;
    physical_desktop_attested=$true;application_launch='NOT_STARTED';target_pid=$null;
    process_creation_filetime=$null;qpc_frequency=[Diagnostics.Stopwatch]::Frequency;
    time_axis='qpc_ticks_v2';observer_sha256=$lock.sha256;observer_version=$lock.version;
    observer_started_qpc=$null;observer_exit_code=$null;observer_timeout=$false;
    app_exit_code=$null;app_timeout=$false;app_sha256=(Get-FileHash -LiteralPath $appPath -Algorithm SHA256).Hash.ToLowerInvariant();
    evidence_sha256=@{};runner_error=$null;security_diagnostics='NOT_EXECUTED';
    started_utc=$startedUtc.ToString('o');observer_external=[bool]$ExternalObserver
}
$appJob=$null;$pmJob=$null;$observerReadiness=$null
Write-Host ('Run directory: '+$runDir)
Write-Host 'The application never displays independent live FSE verification. The report is post-run.'
if (-not $AutoMark) { Write-Host 'Start your recorder after warmup, press F8, capture for >=5s, press F9, then keep recording >=1s. Do not Alt-Tab.' }
try {
    $pyJob=Start-ObservedProcess $pythonPath @('--version') $runDir
    $pyResult=Finish-ObservedProcess $pyJob 10 (Join-Path $runDir 'python.version.txt') (Join-Path $runDir 'python.version.stderr.txt')
    if ($pyResult.ExitCode -ne 0 -or $pyResult.Timeout) { throw 'Python could not start. No policy changes or retries attempted.' }
    if ($ExternalObserver) {
        $request=[ordered]@{schema=1;run_id=$runId;presentmon_path=$pmPath;observer_seconds=$observerSeconds}
        Write-JsonFile (Join-Path $runDir 'observer.request.json') $request
        Write-Host 'In a separately authorized elevated PowerShell, run ONLY the following observer:'
        Write-Host ('& ' + (Quote-WindowsArgument (Join-Path $PSScriptRoot 'start_observer.ps1')) + ' -RunDir ' + (Quote-WindowsArgument $runDir))
        $wait=[Diagnostics.Stopwatch]::StartNew()
        while (-not (Test-Path -LiteralPath (Join-Path $runDir 'observer.ready.json'))) {
            if (Test-Path -LiteralPath (Join-Path $runDir 'observer.done.json')) { throw 'External observer failed before readiness; inspect observer.done.json.' }
            if ($wait.Elapsed.TotalSeconds -gt 90) { throw 'External observer readiness timed out.' }
            Start-Sleep -Milliseconds 200
        }
        $observerReadiness=[IO.File]::ReadAllText((Join-Path $runDir 'observer.ready.json'))|ConvertFrom-Json
        if ($observerReadiness.run_id -ne $runId -or $observerReadiness.observer_sha256 -ne $lock.sha256 -or $observerReadiness.qpc_frequency -ne $session.qpc_frequency) {
            throw 'External observer metadata mismatch.'
        }
        $session.observer_started_qpc=$observerReadiness.observer_started_qpc
    } else {
        $helpJob=Start-ObservedProcess $pmPath @('--help') $runDir
        $helpResult=Finish-ObservedProcess $helpJob 10 (Join-Path $runDir 'presentmon.help.txt') (Join-Path $runDir 'presentmon.help.stderr.txt')
        if ($helpResult.Timeout) { throw 'PresentMon help timed out.' }
        $helpText=[IO.File]::ReadAllText((Join-Path $runDir 'presentmon.help.txt'))
        foreach ($flag in @('--process_name','--qpc_time','--v2_metrics','--session_name','--timed','--terminate_after_timed')) {
            if (-not $helpText.Contains($flag)) { throw ('PresentMon help missing '+$flag) }
        }
        $session.observer_started_qpc=[Diagnostics.Stopwatch]::GetTimestamp()
        $pmArguments=Get-PresentMonArguments $runDir $runId $observerSeconds
        $pmJob=Start-ObservedProcess $pmPath $pmArguments $runDir
        Start-Sleep -Seconds 1
        if ($pmJob.Process.HasExited) { throw 'PresentMon exited early. ETW permissions may require the separately elevated observer path.' }
    }
    $appArguments=@('--mode',$Mode,'--load',$Load,'--monitor',[string]$Monitor,'--duration',[string]$Duration,
        '--warmup',[string]$Warmup,'--fps-cap',[string]$FpsCap,'--run-id',$runId,'--log-dir',$runDir)
    if ($AutoMark) { $appArguments += '--auto-mark' }
    $session.application_launch='START_ATTEMPTED'
    $appJob=Start-ObservedProcess $appPath $appArguments $runDir
    $session.target_pid=$appJob.Process.Id
    $session.process_creation_filetime=$appJob.Process.StartTime.ToUniversalTime().ToFileTimeUtc().ToString([Globalization.CultureInfo]::InvariantCulture)
    $session.application_launch='STARTED'
    $appResult=Finish-ObservedProcess $appJob ($Duration+20) (Join-Path $runDir 'app.stdout.txt') (Join-Path $runDir 'app.stderr.txt')
    $appJob=$null
    $session.app_exit_code=$appResult.ExitCode;$session.app_timeout=$appResult.Timeout
    if ($ExternalObserver) {
        $wait=[Diagnostics.Stopwatch]::StartNew()
        while (-not (Test-Path -LiteralPath (Join-Path $runDir 'observer.done.json'))) {
            if ($wait.Elapsed.TotalSeconds -gt $observerSeconds+20) { throw 'External observer completion timed out; external session will time out independently.' }
            Start-Sleep -Milliseconds 200
        }
        $done=[IO.File]::ReadAllText((Join-Path $runDir 'observer.done.json'))|ConvertFrom-Json
        if ($done.run_id -ne $runId) { throw 'External observer completion mismatch.' }
        $session.observer_exit_code=$done.observer_exit_code;$session.observer_timeout=$done.observer_timeout
    } else {
        $pmResult=Finish-ObservedProcess $pmJob ($observerSeconds+15) (Join-Path $runDir 'presentmon.stdout.txt') (Join-Path $runDir 'presentmon.stderr.txt')
        $pmJob=$null
        $session.observer_exit_code=$pmResult.ExitCode;$session.observer_timeout=$pmResult.Timeout
        if ($pmResult.Timeout) { Stop-OwnedTraceSession $pmPath $runId $runDir }
    }
} catch {
    $session.runner_error=$_.Exception.ToString()
    Write-Warning $session.runner_error
} finally {
    if ($null -ne $appJob) {
        try {
            $r=Finish-ObservedProcess $appJob 1 (Join-Path $runDir 'app.stdout.txt') (Join-Path $runDir 'app.stderr.txt')
            $session.app_exit_code=$r.ExitCode;$session.app_timeout=$r.Timeout
        } catch { $session.app_timeout=$true }
    }
    if ($null -ne $pmJob) {
        try {
            $r=Finish-ObservedProcess $pmJob 1 (Join-Path $runDir 'presentmon.stdout.txt') (Join-Path $runDir 'presentmon.stderr.txt')
            $session.observer_exit_code=$r.ExitCode;$session.observer_timeout=$r.Timeout
            if ($r.Timeout) { Stop-OwnedTraceSession $pmPath $runId $runDir }
        } catch { $session.observer_timeout=$true }
    }
    try {
        $diagnosticPath=Join-Path $runDir 'security.json'
        $null=& (Join-Path $PSScriptRoot 'inspect_sac_environment.ps1') -BinaryPaths @($appPath,$pmPath,$pythonPath) -SinceUtc $startedUtc -OutputPath $diagnosticPath
        $diag=[IO.File]::ReadAllText($diagnosticPath)|ConvertFrom-Json
        $session.security_diagnostics=$diag.code_integrity_read
        $text=[string]$session.runner_error
        foreach ($name in @('app.stdout.txt','app.stderr.txt','presentmon.stderr.txt')) {
            $file=Join-Path $runDir $name
            if (Test-Path -LiteralPath $file) { $text += [IO.File]::ReadAllText($file) }
        }
        if ($diag.related_enforced_block -or $text -match '(?i)0x800711c7|0x11c7') {
            $session.application_launch='BLOCKED_BY_APP_CONTROL'
        }
    } catch { $session.security_diagnostics='UNAVAILABLE: '+$_.Exception.Message }
    foreach ($name in @('app.jsonl','frames.csv','presentmon.csv','presentmon.stdout.txt','presentmon.stderr.txt')) {
        $file=Join-Path $runDir $name
        if (Test-Path -LiteralPath $file) { $session.evidence_sha256[$name]=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() }
    }
    $session['finished_utc']=[datetime]::UtcNow.ToString('o')
    Write-JsonFile (Join-Path $runDir 'session.json') $session
}
# Parser is independent of the renderer. A parser launch block cannot become PASS.
try {
    $verifyJob=Start-ObservedProcess $pythonPath @((Join-Path $PSScriptRoot 'verify_presentmon.py'),'--run-dir',$runDir) $runDir
    $result=Finish-ObservedProcess $verifyJob 30 (Join-Path $runDir 'classifier.stdout.txt') (Join-Path $runDir 'classifier.stderr.txt')
    if ($result.Timeout) { throw 'Classifier timed out.' }
    if (-not (Test-Path -LiteralPath (Join-Path $runDir 'summary.json'))) { throw 'Classifier produced no summary.' }
    Write-Host ([IO.File]::ReadAllText((Join-Path $runDir 'summary.txt')))
    Write-Host ('Evidence: '+$runDir)
    exit $result.ExitCode
} catch {
    $blocked=$session.application_launch -eq 'BLOCKED_BY_APP_CONTROL'
    $fallback=[ordered]@{schema=1;verdict=$(if($blocked){'BLOCKED'}else{'UNVERIFIED'});
        reason=$(if($blocked){'BLOCKED_BY_APP_CONTROL'}else{'CLASSIFIER_NOT_EXECUTED'});
        detail=$_.Exception.Message;dxgi_state='NOT_EVALUATED';presentation_proof='UNVERIFIED';
        recorder_result='NOT_EVALUATED';hardware_fse_validation='NOT_EXECUTED';run_id=$runId}
    Write-JsonFile (Join-Path $runDir 'summary.json') $fallback
    Write-Utf8File (Join-Path $runDir 'summary.txt') ($fallback|ConvertTo-Json)
    Write-Warning ('No verified result. Evidence: '+$runDir)
    if($blocked){exit 42}else{exit 11}
}
