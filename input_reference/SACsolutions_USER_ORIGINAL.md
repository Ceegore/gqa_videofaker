# Windows Smart App Control / Application Control (`0x800711C7`) — Field Guide

**Audience:** AI coding agents and developers working on unsigned .NET projects on
Windows machines with Smart App Control (SAC) or a WDAC/AppLocker policy enabled.

**Purpose:** This error wastes enormous time because it *disguises itself as a code
regression*. This document exists so that never happens again. It is
project-agnostic — keep it at `C:\Projects\SACsolutions.md` and hand it to any agent
that hits `0x800711C7`.

**Provenance:** Compiled 2026-08-31 from two independent investigations on the same
machine — a WinForms/.NET 10 project (`GPTprovenanceDocumentHelper`) and a WPF/.NET 8
project (`ScreenshotBoy`). Findings below are measured, not theorized; where something
is inference rather than measurement it says so.

> **Correction measured 2026-09-02:** SAC deterministically blocked a freshly built
> WPF client DLL even when it was launched by validly Microsoft-signed `dotnet.exe`.
> CodeIntegrity 3033/3077 named `ScreenshotBoy.dll` and the Enterprise signing level.
> A 20-second settle plus three bounded canary retries did not clear the new build.
> Therefore the rate-triggered/transient model below is incomplete: it describes earlier
> observations, not a reliable allowance. A signed host does not transfer trust to an
> unsigned managed entry assembly. Without a CA-trusted signature or a non-enforcing
> test machine, a fresh local GUI build may remain unstartable; wrappers can only detect
> and report this as environment exit 42, not solve it.

---

## 1. Thirty-second triage — READ THIS FIRST

**You are probably here because a test run reported a pile of failures.**

Run this check before believing a single one of them:

```powershell
# Did Windows block our binary during the run?
Get-WinEvent -FilterHashtable @{
    LogName='Microsoft-Windows-CodeIntegrity/Operational'; Id=3033,3077;
    StartTime=(Get-Date).AddMinutes(-15)
} -ErrorAction SilentlyContinue |
  Select-Object TimeCreated, Id, Message | Format-List
```

Or just grep the run output for the HRESULT (**locale-independent**, unlike the message):

```
0x800711C7
```

### Decision

| Finding | Verdict |
|---|---|
| `0x800711C7` present in output, **or** CodeIntegrity 3033/3077 events name your DLL | ⛔ **ENVIRONMENT BLOCK.** The tests did not run. The failure count is meaningless. **Do not debug, do not "fix", do not revert.** Go to §5. |
| Neither present | ✅ Real test results. Treat normally. |

> **The single most expensive mistake** is treating a SAC block as a regression and
> "fixing" or reverting working code because of it. A block can report 179, 278 or 430
> failures — all fake. Always run the check above first.

---

## 2. How it manifests (symptom catalog)

All of these are the *same* underlying block wearing different masks:

| Symptom | Notes |
|---|---|
| `Could not load file or assembly '<X>.dll'. An application control policy has blocked this file. (0x800711C7)` | The canonical form. German locale: `Eine Anwendungssteuerungsrichtlinie hat diese Datei blockiert.` |
| `The active test run was aborted. Reason: Test host process crashed` / `Der Testhostprozess ist abgestürzt` | The block killed the host mid-run |
| Hundreds of unrelated tests "failing" at once, each with a `FileLoadException` stack | Every test fails identically because the assembly never loaded |
| `Skipping: <TestAssembly> (could not load dependent assembly '<TestAssembly>')` | **Misleading.** The *dependency* was blocked, not the named assembly |
| Test discovery reports "no tests available" / "kein Test verfügbar" | Discovery-time variant of the same block |
| Numbers that change between runs (179 → 278 → 430 failures) | vstest retries hosts until it gives up; the count is noise |

---

## 3. Root cause model

SAC/WDAC enforces a code-integrity policy at image-load time. An **unsigned** binary with
no established reputation can be refused. Two independent projects converged on the same
model:

### 3.1 Earlier observation: rate-triggered behavior can occur, but is not guaranteed

This was an important earlier observation, but the 2026-09-02 correction above proves
that it is not a sufficient general model.

- **Measured (project A):** 14 consecutive builds, each producing a verified-new file hash,
  each loaded immediately via the real .NET loader → **14/14 loaded, 0 blocks.** A fresh
  unsigned binary is *not* automatically blocked.
- **Measured (project B):** *"Der 0x800711C7-Trigger entstand durch 40+ SEQUENTIELLE Runs,
  nicht durch einzelne."* — the trigger came from **40+ sequential runs**, not individual
  ones. Single filtered runs of ≤30 tests were verified reliable.

**Model:** what provokes the block is sustained churn — long chains of
`rebuild → launch test host → rebuild → launch test host`, each cycle presenting a new
unknown image. It is transient and clears with time.

### 3.2 Not all assemblies are equally exposed

Measured on project A — 80 block events, **100% against one single file**:

| Assembly | `IMAGE_FILE_DLL` | Subsystem | Blocked |
|---|---|---|---|
| Product assembly (`OutputType=WinExe`) | false | **2 = WINDOWS_GUI** | **80×** |
| Test assembly (`OutputType=Exe`) | false | 3 = WINDOWS_CUI | never |
| A NuGet library (`OutputType=Library`) | true | 3 = WINDOWS_CUI | never |

The blocked assembly was the only **GUI-subsystem** one. *(Inference, consistent with the
data: an unsigned GUI executable image is the shape security heuristics treat most
conservatively. A true class library is the least exposed.)*

Check any assembly's PE header:

```powershell
function Get-PeInfo([string]$path) {
  $b = [System.IO.File]::ReadAllBytes($path)
  $pe = [BitConverter]::ToInt32($b, 0x3C)
  [PSCustomObject]@{
    File           = Split-Path $path -Leaf
    IMAGE_FILE_DLL = [bool]([BitConverter]::ToUInt16($b, $pe + 22) -band 0x2000)
    Subsystem      = [BitConverter]::ToUInt16($b, $pe + 92)   # 2=GUI, 3=Console
  }
}
Get-PeInfo "bin\Release\net10.0-windows\YourApp.dll"
```

### 3.3 The verdict follows content, not path

Copying the blocked file to another directory or drive does **not** clear it. Renaming
does not help. Only new content (a rebuild) or elapsed time changes the outcome.

### 3.4 Deterministic builds cache verdicts — this creates a nasty illusion

.NET builds are deterministic by default: rebuilding **unchanged** source yields a
**byte-identical** assembly, which reuses the verdict SAC already made. Any *real* change
(even a one-line `<Version>` bump) yields a new hash needing a **fresh** verdict.

This produces a very misleading experience:

```
change something  → rebuild → BLOCKED
revert the change → rebuild → WORKS   ← looks like "the change broke tests"
```

It did not. The revert merely reproduced an already-approved binary. **Never conclude that
a code change "caused" a SAC block** on this evidence. Verify with §1 instead.

*(Observed directly: a `1.3.2 → 1.4.0` version bump — metadata only, zero behavioural
change — flipped a green suite into a fully blocked one, and reverting flipped it back.)*

---

## 4. What does NOT work — don't burn time on these

| Attempt | Outcome |
|---|---|
| Copy the assembly to another path/drive | ❌ Still blocked (verdict follows content) |
| `rm -rf bin obj` + full clean rebuild | ❌ Still blocked |
| Tight retry loop (e.g. 10 attempts, 20s apart) | ❌ Too fast; does not give it time to clear |
| Switching Debug ↔ Release | ⚠️ "Works" only because it is a *different file* — luck, not a fix |
| Self-signing with a generated certificate | ❌ SAC trusts reputation, not arbitrary certs |
| Assuming the signed test host is at fault | ❌ `testhost.exe` is validly Microsoft-signed; not the problem |

---

## 5. What can help — ordered by cost and with explicit limits

### 5.1 Wait (cheap attempt, not a guarantee)
Some earlier blocks were transient. **Wait 30–60s after a rebuild** before a heavy run;
if already blocked, a later retry may help. The 2026-09-02 ScreenshotBoy client did not
clear after settle plus bounded retries, so waiting must never be described as a fix.

### 5.2 Prefer small, targeted runs (the real day-to-day fix)
```bash
dotnet test YourSolution.sln -c Release --no-build --filter "FullyQualifiedName~SomeTestClass"
```
Earlier runs in project B showed that filtered runs of **≤ ~30 tests** reduced the
frequency and cost of blocks. They are still the preferred iteration size, but they are
not a trust workaround: on 2026-09-02 even a one-test canary could not load a freshly
built ScreenshotBoy client assembly. Run the full suite only when actually needed and
treat exit 42 as an environmental non-result.

### 5.3 Reduce the number of cycles
- **Do not re-run the full suite once it is green.** Repeat full runs are the single
  biggest contributor.
- Consider combining build+test into **one** `dotnet test` invocation (without
  `--no-build`) instead of separate build/test cycles — project B recorded this as a
  measurable reduction in triggers.
- **Run coverage once, at the end.** `--collect:"XPlat Code Coverage"` roughly triples run
  time and was by far the most block-prone path observed.

### 5.4 Wrap the runner so a block can never be misread (highest value)
Do not let a block masquerade as a test failure. A wrapper should:

1. **Settle** — pause ~20s after a build before the first test-host launch.
2. **Canary** — run one cheap test first; a block then costs seconds, not minutes.
3. **Detect** — two independent detectors:
   - the string `0x800711C7` in run output (locale-independent), and
   - new CodeIntegrity **3033/3077** events naming your assembly during the run window.
4. **Back off and retry** — e.g. 4 attempts, `30s × attempt`.
5. **Exit with a distinct code** — e.g. **42** for an environment block, so it can never be
   confused with `1` (real failure).

Reference implementation:
`<projects>\GPTprovenanceDocumentHelper\scripts\run_tests_sac_safe.ps1`

**Validated under a live block (2026-08-31):** with SAC actively blocking, the wrapper
surfaced 19 `[FAIL]` lines from the canary, correctly identified them as `0x800711C7`,
refused to report them as test results, retried with backoff, and exited **42**. Without
it, those 19 failures would have been read as a real regression — which is exactly the
mistake this whole document exists to prevent. Once SAC settled, the same wrapper
returned a clean `0` on a 1090-test suite.

### 5.4.1 Two implementation traps when you write such a wrapper

Both were hit for real and both produce *silent, misleading* behaviour:

**(a) Piping `dotnet` output makes it look frozen.** `dotnet test` block-buffers stdout
whenever stdout is not a console — e.g. `dotnet test ... | Tee-Object`. The result is a
run that prints **nothing for 20 minutes** and looks hung. Do not pipe it. Instead:

```powershell
$p = Start-Process dotnet -ArgumentList $args -NoNewWindow -PassThru `
        -RedirectStandardOutput $out -RedirectStandardError $err
# ...then tail $out yourself with FileShare.ReadWrite while $p is alive
```

Also print a **heartbeat** every ~30s, and enforce a **hard timeout** that kills the
process tree — a wrapper that can hang forever is worse than no wrapper.

**(b) `Start-Process -PassThru` gives `$null` for `ExitCode`.** Unless the native handle
is cached *while the process is still running*, `$proc.ExitCode` is unreadable after exit.
A `$null` exit code silently compares as "not 0" and turns **every passing run into a
reported failure**. Fix — immediately after `Start-Process`:

```powershell
try { $null = $proc.Handle } catch { }   # caches the handle so ExitCode works later
```

Then guard it anyway: treat `$null` as *inconclusive*, never as pass or fail.

**(c) Distinguish "no tests matched the filter" from "tests failed."** A typo'd `--filter`
produces `No test matches the given testcase filter` / `Kein Test entspricht...`. Give it
its own exit code, or you will chase a nonexistent regression.

Minimal detector core:
```powershell
$blocked = $false
if ($runOutput -match '0x800711C7') { $blocked = $true }
if (-not $blocked -and $exitCode -ne 0) {
    $ev = Get-WinEvent -FilterHashtable @{
        LogName='Microsoft-Windows-CodeIntegrity/Operational'
        Id=3033,3077; StartTime=$runStartedAt
    } -ErrorAction SilentlyContinue
    if ($ev | Where-Object { $_.Message -match 'YourAssemblyName' }) { $blocked = $true }
}
```

### 5.5 Structural fix (when it becomes constant, not intermittent)
Make the assembly your tests load a **true class library** rather than a GUI executable
image:

- Move all logic into `YourApp.Core` (`OutputType=Library`, subsystem 3, `IMAGE_FILE_DLL`
  set).
- Leave a thin `YourApp` (`WinExe`) containing only the entry point.
- Tests reference `YourApp.Core` and therefore never load a GUI executable image.

This structural refactor reduces GUI coupling and may reduce build/test cost, but it
does not guarantee SAC acceptance. ScreenshotBoy measured a block of a true Core
class library on 2026-10-03; see section 10. Schedule the refactor deliberately and
verify actual CodeIntegrity events rather than assuming the image shape fixes trust.

---

## 6. Related but DIFFERENT problem: the published apphost

Do not conflate these two:

| | Test-time block | Publish/launch block |
|---|---|---|
| **Artifact** | Your product **.dll** loaded by `testhost.exe` | A self-contained **.exe** apphost or a managed GUI **.dll** loaded by `dotnet.exe` |
| **Symptom** | `0x800711C7`, fake test failures | "Process exited prematurely" / "Main window was not created" |
| **Nature** | Often rate-triggered, but a fresh assembly can remain blocked | A fresh unsigned native apphost is blocked; a fresh managed GUI DLL can also be blocked independently of the signed host |
| **Supported response** | Use §5 to limit cost and detect the non-result | CA-trusted signing or a separate non-enforcing test machine; the wrapper can only report exit 42 |

Static package verification remains possible without launching the executable. A
framework-dependent `dotnet YourApp.dll` launch is useful as a diagnostic startgate,
but is not a guaranteed SAC workaround.

---

## 7. Hard rules

1. **Never disable SAC, Defender, or any security setting to make a build run.** On
   Windows 11, SAC can only be re-enabled by reinstalling Windows. It is the machine
   owner's decision, never the agent's.
2. **Never report a SAC block as a product defect.** Record it as
   *skipped — environment* and move on.
3. **Never revert or "fix" code based on a blocked run.** Nothing was proven.
4. **Never trust a doc that claims your test path is "SAC-free"** without checking the
   CodeIntegrity log. Project A's `AGENTS.md` asserted exactly that; it was wrong, and the
   wrong claim is what caused an agent to misdiagnose a block as a regression. Verify, then
   correct the doc.
5. **Prefer static verification when blocked.** If tests genuinely cannot run, you can
   still verify: `dotnet build` with `-warnaserror`, file/structure assertions, and
   targeted `Select-String` checks. Say plainly that tests were blocked rather than
   implying they passed.

### 7.1 ScreenshotBoy disposable-Sandbox exception (2026-09-02)

ScreenshotBoy deliberately separates two gates:

- **Functional iteration:** `tools\start-fast-sandbox.ps1` may disable SAC only inside
  the newly created, disposable Windows Sandbox guest. The host policy is never touched,
  the guest change disappears when the Sandbox closes, and this mode proves only product
  functionality (client, server, microphone, recording and transcription).
- **Full local gate:** `tools\start-windows-sandbox-tests.ps1 -Wait` uses the same narrow
  guest-only SAC exception for Release build and all test suites. It does not use
  `ExecutionPolicy Bypass` or `Unblock-File`; test-count and coverage gates run read-only
  on the unchanged host after the guest finishes.
- **Distribution trust:** an end-customer candidate must be a Microsoft Store-signed
  MSIX and must start on a SAC-enforcing system without any exception. The functional
  Sandbox is not evidence for this release gate.

This narrow exception does not authorize disabling SAC, WDAC, Defender or execution
policy on a host, persistent VM, CI runner or customer machine. `-TrustMode Strict`
keeps the Sandbox guest policy unchanged and is available for explicit trust diagnosis.

---

## 8. Checklist for an agent hitting this cold

```
[ ] Grep run output for 0x800711C7
[ ] Query CodeIntegrity log (3033/3077) for the run window
[ ] If blocked: STOP. Do not debug the "failures". Do not revert anything.
[ ] Tell the user plainly: environment block, tests did not run
[ ] Wait a few minutes; retry with a TARGETED --filter run
[ ] If still blocked: verify statically (build 0/0 + structural checks) and report honestly
[ ] Before finishing: make sure the project's AGENTS.md documents this
[ ] Never touch SAC/Defender settings
```

---

## 9. Measured source-only GUI path on this machine (2026-09-04)

ClipPlayer provided an additional, narrowly scoped result on the same SAC-enforcing
machine. A source-only WPF application ran successfully in the validly
Microsoft-signed Windows PowerShell 5.1 host with the host policy left unchanged.

Measured configuration:

- `powershell.exe` Authenticode status: `Valid`, signer `Microsoft Windows`.
- Effective local Execution Policy: `RemoteSigned`.
- The application loaded only inbox `PresentationCore`, `PresentationFramework`,
  `WindowsBase` and `Microsoft.VisualBasic` assemblies. It did not use `Add-Type` to
  compile code and did not load a custom managed assembly.
- Launch used `-NoLogo -NoProfile -STA -File`; it did **not** use
  `ExecutionPolicy Bypass`, `Unblock-File`, a policy exception or a security-setting
  change.
- A real UI Automation run confirmed WPF window creation, MediaPlayer autoplay,
  pause/resume, left/right selection with autoplay, four-player preloading and Recycle
  Bin deletion. Code Integrity logged zero related 3033/3077 events.

This does **not** contradict the 2026-09-02 correction: a signed host does not confer
trust on an unsigned managed GUI DLL. In this measured path there is no custom PE image
to load; PowerShell interprets local source and calls signed Windows components.

Limits and rules:

1. This is a measured option for small internal tools, not a universal SAC guarantee.
   WDAC/AppLocker/enterprise script rules can prohibit it on other machines.
2. A downloaded script carrying Mark-of-the-Web can be refused by `RemoteSigned`.
   Never use `Unblock-File` or `ExecutionPolicy Bypass` as a product installation step.
3. Keep the script source-only. Runtime compilation creates a new unsigned assembly
   and returns to the original trust problem.
4. Use a local, well-quoted installation path and register the exact signed host path.
   A failed `Start-Process` argument split can look like a launch failure but produces
   no Code Integrity event; distinguish it from SAC with the §1 event check.
5. A public/commercial binary distribution still needs Store/CA trust. The source-only
   route is appropriate only where the applicable script policy explicitly permits it.

### 9.1 Shared-workstation test rule (measured 2026-09-04)

A long GUI stress test that repeatedly used `AppActivate` plus `SendKeys` made the
shared workstation effectively unusable because it reclaimed keyboard focus several
times per second. UI Automation `InvokePattern` loops can have the same practical
effect. This is a test-harness defect even when all product assertions pass.

For unattended endurance tests on a workstation that remains in use:

- launch the test window with `ShowActivated=false`, minimized and without a taskbar
  entry;
- use an application-owned IPC/test command channel that is enabled only by an
  explicit background-test switch;
- route test commands and real keyboard/button commands through the same small
  command dispatcher;
- use UI Automation read-only to prove that the real window exists;
- never call `AppActivate`, `SendKeys`, `SetFocus` or repeated UI click/invoke methods.

ClipPlayer measured this pattern successfully under 100% CPU load. Its background
test kept the global input focus untouched while verifying real MediaPlayer position,
preloading, pause/resume, track changes and Recycle Bin handling. Keep destructive
test commands narrowly restricted to generated fixture paths.

### 9.2 A transient unsigned-DLL pass is not a trust result (measured 2026-09-04)

On the same unchanged host, the unsigned `ClipPlayer.App.dll` test suite first ran
successfully and was later rejected in full with `FileLoadException` / `0x800711C7`
after another clean build. All tests in the later process were blocked before their
test bodies ran. The source-only player continued to pass in the Microsoft-signed
PowerShell host with zero related Code Integrity events.

Therefore, never treat one early successful load of a newly built unsigned PE as
evidence that SAC will continue to trust it. SAC/cloud reputation enforcement may be
observed asynchronously. Recheck after a settle interval and classify any later
`0x800711C7` as an environment block; use a non-PE/source-only architecture or a
properly trusted distribution instead of depending on the transient pass.

### 9.3 Windows PowerShell 5.1 text encoding in source-only gates (measured 2026-09-04)

Windows PowerShell 5.1 on this machine decoded a BOM-less UTF-8 Markdown file through
`Get-Content` as the active ANSI code page. An assertion containing German umlauts
then failed even though the file was correct and `rg`/PowerShell 7 displayed it
correctly. This was an encoding false negative, not a SAC or application failure.

For gates that run in the Microsoft-signed 5.1 host, keep executable `.ps1` files as
UTF-8 with BOM and CRLF. When a script reads repository text that intentionally stays
BOM-less UTF-8 (for example Markdown or C#), use `[IO.File]::ReadAllText(path)` or an
explicit UTF-8 `StreamReader` instead of relying on the legacy `Get-Content` default.
Do not misclassify mojibake-based pattern failures as policy enforcement; confirm
Code Integrity events independently.

---

## 10. A true class library can also be blocked (measured 2026-10-03)

ScreenshotBoy extracted its actual replay resampler into the BCL-only net10.0
`ScreenshotBoy.Replay.Audio.Core` library. The isolated test graph references only
Core, with no GUI app or Windows Desktop Framework. Strict Core.Tests and Client.Tests
builds completed with zero warnings/errors. PE inspection of the blocked Core library
confirmed `IMAGE_FILE_DLL=true` and subsystem 3; the app remains subsystem 2.

The first bounded Host run failed before test execution: the fixed Canary was not
executed and the SAC-aware wrapper returned 42. CodeIntegrity recorded 14 events 3033
and 14 events 3077 naming `ScreenshotBoy.Replay.Audio.Core.dll` loaded by testhost.exe.
Evidence is archived under
`C:\Projects\ScreenshotBoy\artifacts\audit\fixes13\audio-core-pll-pipeline-silence30-host\`
and PE shapes/hashes in `audio-core-pe-shapes.json` in the same fixes13 parent.

Therefore the structural Library split may reduce build/payload cost and GUI coupling,
but it does NOT guarantee SAC acceptance. Do not change PE shape, rename/copy binaries,
revert the extraction, self-sign, or weaken policy based on this non-result. Keep the
Host policy unchanged and run functional acceptance in the authorized disposable Sandbox.
## 11. A user-profile path is not a blanket allowance (measured 2026-10-08)

A fresh read of the live CodeIntegrity Operational channel found event 3077, record
493882, emitted on 2026-10-07 at 20:33:04 local time. It blocked
`C:\Users\<user>\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\DLLs\libcrypto-3-x64.dll`
under policy `{0283ac0f-fff1-49ae-ada1-8a933130cad6}`. The process was the Python host
inside the same user-profile tree. The complete original XML and event evidence are
preserved in `ScreenshotBoy/artifacts/audit/fixes13/native285-user-profile-policy-evidence/`.

This directly contradicts a blanket rule that this policy accepts all unsigned code
inside user-profile paths. The message's phrase "Enterprise signing level requirements"
does not by itself identify an allowed-root rule. A successful run in another project
can be real without proving that moving its directory caused acceptance. Compare the
actual file hashes, loaded dependencies, active policy and completed execution before
attributing a difference to location. This observation does not prove that paths can
never matter in other configured application-control policies.

Do not move blocked ScreenshotBoy binaries into the user profile as a trust workaround.
Keep host protections unchanged; use the authorized disposable functional Sandbox and
separate genuine distribution-trust gates. Absence of related log events in a build or
metadata-only verification window is not proof that the product can execute.
## 12. Self-contained single-file apps start on the SAC host (measured 2026-10-14)

ScreenshotBoy, development PC, Smart App Control **on**, host policy unchanged.

| Artifact | Built where | Result on the SAC host |
|---|---|---|
| Client, `dotnet publish -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true` (one 209 MB `ScreenshotBoy.exe`) | **locally** on the dev PC | **starts and runs**; no CodeIntegrity 3033/3077 for it (process running, log read 2026-10-14 22:10) |
| Same client, release ZIP from GitHub Actions | CI | starts after the user ticked "Zulassen" (Properties) on the downloaded file |
| Acceptance client (single-file, `SSB_ACCEPTANCE_BUILD`) | CI | starts after "Zulassen" |
| Server, self-contained **multi-file** (`PublishSingleFile=false`, many unsigned DLLs), release ZIP | CI | starts and serves (console host) |
| `Start-ScreenshotBoy-Server.cmd` double-clicked from the extracted ZIP | CI | **blocked**: event 3033 "explorer.exe attempted to load ...\cmd.exe" (2026-10-14 20:25) |
| `dotnet build` output, `dotnet test` / testhost with fresh unsigned test and product DLLs | locally | blocked (sections 2-3, 9-11) - still forbidden on the dev PC |

What this means for agents:

- **Manual UI iteration without Sandbox or CI is possible:** publish the app self-contained single-file
  locally (ScreenshotBoy: `powershell -NoProfile -File tools\publish-local-client.ps1`) and let the
  user start the exe by hand. Before claiming "works", read the CodeIntegrity log for 3033/3077 naming
  the exe (section 1); a blocked start shows one Windows Security notice and changes nothing.
- **Why (hypothesis, not proven):** SAC evaluates every image Windows maps from disk. A single-file
  bundle loads its managed assemblies from memory, so only the one exe is evaluated; `dotnet build`
  output and test hosts map dozens of fresh unsigned DLLs. The CI multi-file server also passing shows
  the DLL count alone is not the whole story (content/reputation, section 3.3-3.4). Treat each new
  artifact shape as unverified until the log is clean; a pass can be transient (section 9.2).
- **Do not** start a `.cmd`/`.bat` from an extracted download on this host: the script host is blocked;
  start the `.exe` directly with the same arguments instead.
- Nothing here relaxes section 7: no policy change, no `Unblock-File`, no self-signing, no ExecutionPolicy
  bypass. "Zulassen" is set by the user on one downloaded file only. Tests still run in CI or in the
  disposable Sandbox, never as `dotnet test` on the host.
