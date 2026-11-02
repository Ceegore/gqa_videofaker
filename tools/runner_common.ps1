# Source-only helper functions. No policy changes, dynamic compilation, or elevation.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
function Write-Utf8File {
    param([Parameter(Mandatory=$true)][string]$Path, [AllowEmptyString()][string]$Text)
    [IO.File]::WriteAllText($Path, $Text, (New-Object Text.UTF8Encoding($false)))
}
function Write-JsonFile {
    param([Parameter(Mandatory=$true)][string]$Path, [Parameter(Mandatory=$true)]$Value)
    $temp = $Path + '.' + [Guid]::NewGuid().ToString('N') + '.tmp'
    Write-Utf8File -Path $temp -Text ($Value | ConvertTo-Json -Depth 12)
    Move-Item -LiteralPath $temp -Destination $Path -Force
}
function Quote-WindowsArgument {
    param([AllowEmptyString()][string]$Value)
    # CRT / CommandLineToArgvW quoting, including trailing backslashes.
    if ($Value.Length -gt 0 -and $Value -notmatch '[\s"]') { return $Value }
    $b = New-Object Text.StringBuilder
    [void]$b.Append('"')
    $slashes = 0
    foreach ($c in $Value.ToCharArray()) {
        if ($c -eq [char]92) { $slashes++; continue }
        if ($c -eq [char]34) {
            [void]$b.Append(('\' * ($slashes * 2 + 1)))
            [void]$b.Append('"'); $slashes = 0; continue
        }
        [void]$b.Append(('\' * $slashes)); $slashes = 0
        [void]$b.Append($c)
    }
    [void]$b.Append(('\' * ($slashes * 2)))
    [void]$b.Append('"')
    return $b.ToString()
}
function Start-ObservedProcess {
    param([string]$File, [string[]]$Arguments, [string]$WorkingDirectory)
    $psi = New-Object Diagnostics.ProcessStartInfo
    $psi.FileName = $File
    $psi.Arguments = (($Arguments | ForEach-Object { Quote-WindowsArgument $_ }) -join ' ')
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $psi
    if (-not $process.Start()) { throw 'Process.Start returned false' }
    $null = $process.Handle
    $out = $process.StandardOutput.ReadToEndAsync()
    $err = $process.StandardError.ReadToEndAsync()
    return [pscustomobject]@{ Process = $process; Output = $out; Error = $err }
}
function Finish-ObservedProcess {
    param($Job, [int]$TimeoutSeconds, [string]$StdoutPath, [string]$StderrPath)
    $watch = [Diagnostics.Stopwatch]::StartNew()
    $nextHeartbeat = 15
    $timedOut = $false
    while (-not $Job.Process.HasExited) {
        if ($watch.Elapsed.TotalSeconds -ge $TimeoutSeconds) {
            $timedOut = $true
            try { $Job.Process.Kill() } catch { }
            if (-not $Job.Process.WaitForExit(5000)) { throw 'Owned process could not be terminated' }
            break
        }
        if ($watch.Elapsed.TotalSeconds -ge $nextHeartbeat) {
            Write-Host ('Waiting for owned PID {0}; elapsed {1:N0}s' -f $Job.Process.Id, $watch.Elapsed.TotalSeconds)
            $nextHeartbeat += 15
        }
        Start-Sleep -Milliseconds 100
    }
    $Job.Process.WaitForExit()
    if (-not $Job.Output.Wait(5000) -or -not $Job.Error.Wait(5000)) { throw 'Output pipes did not close' }
    Write-Utf8File $StdoutPath $Job.Output.Result
    Write-Utf8File $StderrPath $Job.Error.Result
    $exitCode = $Job.Process.ExitCode
    if ($null -eq $exitCode) { throw 'Null exit code; result is inconclusive' }
    $result = [pscustomobject]@{ ExitCode = [int]$exitCode; Timeout = $timedOut }
    $Job.Process.Dispose()
    return $result
}
function Get-PresentMonLock {
    return ([IO.File]::ReadAllText((Join-Path $PSScriptRoot 'presentmon.lock.json')) | ConvertFrom-Json)
}
function Assert-PresentMon {
    param([string]$Path)
    $lock = Get-PresentMonLock
    if ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $lock.sha256) {
        throw 'PresentMon SHA256 mismatch. No unknown or different-version executable will be started.'
    }
    return $lock
}
function Get-PresentMonArguments {
    param([string]$RunDir, [string]$RunId, [int]$Duration)
    return @('--process_name','FSEProbe.exe','--output_file',(Join-Path $RunDir 'presentmon.csv'),
        '--qpc_time','--v2_metrics','--no_console_stats','--session_name',('FSEProbe-' + $RunId),
        '--timed',[string]$Duration,'--terminate_after_timed')
}
function Stop-OwnedTraceSession {
    param([string]$PresentMon, [string]$RunId, [string]$RunDir)
    # Only the random session owned by this run; never stop the default or another user's trace.
    $job = Start-ObservedProcess $PresentMon @('--session_name',('FSEProbe-' + $RunId),'--terminate_existing_session') $RunDir
    $null = Finish-ObservedProcess $job 10 (Join-Path $RunDir 'trace-cleanup.stdout.txt') (Join-Path $RunDir 'trace-cleanup.stderr.txt')
}
