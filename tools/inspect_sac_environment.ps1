[CmdletBinding()]
param(
    [string[]]$BinaryPaths = @(),
    [datetime]$SinceUtc = ([datetime]::UtcNow.AddMinutes(-15)),
    [string]$OutputPath = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$report = [ordered]@{
    schema = 1
    collected_utc = [datetime]::UtcNow.ToString('o')
    since_utc = $SinceUtc.ToUniversalTime().ToString('o')
    read_only = $true
    security_policy_state = 'NOT_INFERRED_FROM_SIGNATURE_OR_ABSENCE_OF_EVENTS'
    code_integrity_read = 'NOT_ATTEMPTED'
    code_integrity_error = $null
    code_integrity_events = @()
    signatures = @()
    related_enforced_block = $false
    citool_output = ''
    citool_exit = $null
}
$paths = @()
foreach ($binary in $BinaryPaths) {
    try {
        $full = (Resolve-Path -LiteralPath $binary).ProviderPath
        $paths += $full.ToLowerInvariant()
        $signature = Get-AuthenticodeSignature -LiteralPath $full
        $subject = $null
        if ($null -ne $signature.SignerCertificate) { $subject = $signature.SignerCertificate.Subject }
        $report.signatures += [ordered]@{path=$full;status=[string]$signature.Status;subject=$subject;
            sha256=(Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant();
            meaning='Signature only; not an SAC execution guarantee'}
    } catch {
        $report.signatures += [ordered]@{path=$binary;status='UNREADABLE';error=$_.Exception.Message}
    }
}
try {
    $events = @(Get-WinEvent -FilterHashtable @{
        LogName='Microsoft-Windows-CodeIntegrity/Operational'
        Id=3033,3076,3077
        StartTime=$SinceUtc.ToLocalTime()
        EndTime=Get-Date
    } -MaxEvents 200 -ErrorAction Stop)
    foreach ($event in $events) {
        $xmlText = $event.ToXml()
        $matched = $false
        foreach ($path in $paths) {
            # Event XML can use a native device path. Compare the full path first;
            # keep uncertain cases as raw evidence instead of claiming SAC conclusively.
            if ($xmlText.ToLowerInvariant().Contains($path) -or $event.Message.ToLowerInvariant().Contains($path)) {
                $matched = $true
            }
        }
        if ($matched -and ($event.Id -eq 3033 -or $event.Id -eq 3077)) { $report.related_enforced_block = $true }
        $report.code_integrity_events += [ordered]@{
            id=$event.Id;record_id=$event.RecordId;time_utc=$event.TimeCreated.ToUniversalTime().ToString('o');
            full_path_correlated=$matched;message=$event.Message;xml=$xmlText
        }
    }
    $report.code_integrity_read = 'READ'
} catch {
    if ($_.FullyQualifiedErrorId -like 'NoMatchingEventsFound*') {
        $report.code_integrity_read = 'READ_NO_MATCHING_EVENTS'
    } else {
        $report.code_integrity_read = 'UNAVAILABLE'
        $report.code_integrity_error = $_.Exception.Message
    }
}
$ci = Join-Path $env:windir 'System32\CiTool.exe'
if (Test-Path -LiteralPath $ci) {
    try {
        $report.citool_output = (& $ci -lp 2>&1 | Out-String)
        $report.citool_exit = $LASTEXITCODE
    } catch { $report.citool_output = $_.Exception.Message }
} else { $report.citool_output = 'CiTool unavailable on this Windows build' }
$json = $report | ConvertTo-Json -Depth 10
if ($OutputPath) { [IO.File]::WriteAllText($OutputPath,$json,(New-Object Text.UTF8Encoding($false))) }
$json
