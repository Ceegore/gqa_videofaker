# SAC-FIRST-STRATEGIE — FSEProbe ohne Änderungen am geschützten Entwicklungs-PC

**Stand:** 2026-11-02 | **Priorität:** BLOCKING, vor jeder Build-/Teststrategie zu behandeln.

## 1. Feste Ausgangslage und unverhandelbare Leitplanken

- Der eigentliche **Entwicklungs-PC verwendet Windows 11 und Smart App Control (SAC)**, das schon wiederholt Testprogramme/DLLs blockiert hat. Die bestehende Schutzkonfiguration **bleibt an**. Es ist **nicht zulässig**, das Vorgehen von einer SAC-Abschaltung abhängig zu machen.
- Das Projekt soll klein, nachvollziehbar, kostensparend und von einem schwächeren Coding-Agenten gut umsetzbar bleiben. Der Compiler mag auf dem Dev-PC laufen; **die Ausführung einer neu kompilierten EXE ist dort aber nicht als verfügbar anzunehmen**.
- Das Projekt benötigt zwei unterschiedliche Fähigkeiten: (A) **buildbare Windows-D3D11-Software** und (B) **echte DXGI-/GPU-/Display-Hardwareprüfung**. GitHub Actions kann A zuverlässig unterstützen; ein Hosted Runner, RDP, VM oder Windows Sandbox kann B **nicht stellvertretend** für den physischen Desktop garantieren.
- Keine Registry-Bastelei, keine Verschleierung der Herkunft oder Einbettung unbekannten Codes in vertrauenswürdig signierte Hosts, keine DLL-Injection, kein Entsperren des Betriebssystems, keine globale PowerShell-Policy-Änderung, kein Umgehen von SAC.

## 2. Was SAC tatsächlich bedeutet — und was nicht

Microsoft erklärt, dass bei unbekannten/noch nicht reputierten Anwendungen ein gültiges Zertifikat einer vertrauenswürdigen CA für den SAC-Pfad relevant ist. **Eine beliebige selbstsignierte Zertifikatsdatei ist kein vertrauenswürdiger Ersatz.** Es gibt im SAC-UI derzeit keine einfache einzelne EXE-Freigabe. Die Microsoft-Dokumentation von Oktober/November 2026 unterscheidet dabei die Signaturprüfung von der cloudbasierten Reputationsbewertung. Ein technisch gültiges Authenticode-Signaturlabel ist nicht die Zusicherung, dass jeder Einsatz und jede Abhängigkeit im Zielsystem erlaubt wird.

**Quellen:**
- https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/overview
- https://support.microsoft.com/de-de/windows/security/threat-malware-protection/smart-app-control-frequently-asked-questions
- https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/code-signing-for-smart-app-control
- https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/test-your-app-with-smart-app-control

**Aktualisierung:** Microsofts neuere FAQ sagt, dass mit aktuellen Windows-Updates SAC teilweise wieder einschaltbar ist; andere offizielle Seiten beschreiben noch den älteren Einweg-Schalter. Das ist **kein Grund**, für unser Projekt eine Abschaltung vorzusehen. Der Pro-Durchlauf muss die Versionsabhängigkeit bei Bedarf dokumentieren, aber der Standardworkflow bleibt ohne jede Schutzkonfigurationsänderung.

## 3. Die bevorzugte Architektur: Build und echte Laufzeittests entkoppeln

```text
DEV-PC (SAC bleibt ON)                       GITHUB ACTIONS Windows CI
  - Code/Markdown/Python/PS schreiben  --->    - CMake/MSVC Build x64 Release
  - git diff, Textreviews, unit tests          - clang/static checks soweit verfügbar
  - KEIN unsigned Binary ausführen             - CTest + Python Parser/Protocol Tests
                                               - ZIP + SHA256 + Build-Log
                                                       |
                                                       v
                         Testlauf-Option A: separate Windows-Hardware-Testmaschine
                         Testlauf-Option B: dasselbe physische PC-System, aber
                             separate isolierte Windows-Testinstallation auf eigener SSD
                         Testlauf-Option C: CA-vertrauenswürdig signiertes Release,
                             ausdrücklicher Startversuch im SAC-geschützten Windows
                                                       |
                                                       v
                         PresentMon + physischer Monitor + Recorder
                         => DXGI/PresentMode- und Capture-Resultate
```

**Empfohlene Standardroute:** **Github Actions Windows-CI für Kompilierung/Unit-Tests, danach echte Hardware in einer separaten Windows-Installation**. So ist die Entwicklungsarbeit nicht vom SAC-Startproblem blockiert und es entsteht kein zusätzlicher Signatur-/Verteilungsaufwand für das kleine interne Tool. Ein externes Windows-Testgerät ist noch bequemer, wenn vorhanden.

**Wichtig:** Das CI-Artefakt ist weiterhin **unsigniert**, solange kein separater Signierschritt und gültiger Signierschlüssel vorhanden sind. GitHub Actions verleiht heruntergeladenen EXEs **keine SAC-Vertrauensstellung**. Eine Release-ZIP ist kein Sicherheits- oder FSE-Testnachweis.

### Option A — physischer Zweit-PC

Ideal, wenn ohnehin vorhanden. Windows 10/11 x64, installierte D3D11-Grafikkartentreiber, direkter Monitor, lokale Desktop-Sitzung, Test-EXE nach geltender Gerätesicherheitsrichtlinie ausführbar. SAC/WDAC-Status des Test-PCs dokumentieren; Änderungen an Schutzfunktionen auch dort nicht still auslösen. Das Bild muss real am Monitor ausgegeben werden, nicht durch eine Remote-Desktop-Session ersetzt werden. Wenn der Recorder nur am Dev-PC installiert ist, Testgerät bewusst als zusätzliche Einrichtung planen.

### Option B — separate Windows-Installation auf derselben physischen GPU

Wenn nur der eine PC mit der zu prüfenden GPU vorhanden ist: **separate Windows-Installation auf eigener SSD/Datenträger** als Test-Bootsystem erwägen. Sie benutzt denselben physischen Monitor/GPU, bleibt jedoch unabhängig von der SAC-Konfiguration des produktiven Systems. Das erfordert ein tatsächlich unterstütztes und lizenziertes Windows-Setup, vollständige Backups, Prüfung von Bootloader/UEFI/BitLocker-/Recovery-Key-Risiken und ggf. manuelle Einrichtung. **Nicht automatisch durch den Agenten installieren oder Boot-/Sicherheitskonfiguration ändern.** Für diese Option sind ausdrückliche Freigaben und passende Hardware nötig. Den Productive-OS-Datenträger möglichst unangetastet lassen. Erst nach erfolgreicher OS-/Treiber-/Monitoreinrichtung kann echte FSE-Abnahme erfolgen.

### Option C — signierter Release auf dem SAC-PC

Falls kein separates Testsystem gewünscht ist, ist ein **gültig durch eine anerkannte Zertifizierungsstelle signierter** Build der sachgerechte Vertrauenspfad. Microsoft nennt CA-Codesignatur bzw. Artifact Signing. Signierzugriff ist **optional**, niemals Grundvoraussetzung für Codeerstellung. Zertifikat, private Schlüssel, Berechtigungen, CI-Geheimnisse und Kosten getrennt verantworten. Jedes ausgelieferte Programm/ggf. dynamisch geladene eigene Codeartefakt muss geprüft werden. `Get-AuthenticodeSignature`/`signtool verify` testen nur die Signaturkette, nicht die reale SAC-Ausführbarkeit. Gegen SAC **tatsächlichen Prozessstart** und Eventlog kontrollieren.

**Relevante Länder-/Kosten-Einschränkung:** Microsofts *Code signing options for Windows app developers* (Stand Abruf 2026-11-02) nennt Artifact Signing für **Organisationen in der EU**, aber **einzelne Entwickler nur in USA/Kanada**. Für eine Privatperson in Deutschland darf der Agent **Artifact Signing nicht als garantiert nutzbaren Standardweg** verkaufen. CA-OV-Signatur (mit Identitätsprüfung und Kosten) wäre eine mögliche Alternative. Nicht blind Vertrauensstatus oder Preise garantieren. Quelle: https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options

**Microsoft Store/MSIX** nur als spätere Option mit tatsächlichem Bedarf: Paket- und Store-Review, Vollbildsemantik und Full-Trust Win32 müssen separat nachgewiesen werden. Nicht als schneller Trick zur SAC-Umgehung implementieren.

## 4. SAC-Readiness-Check vor Entwicklung und Runtime

1. Auf dem Dev-PC **nur lesen**, nicht ändern: Windows-Sicherheit -> App- & Browsersteuerung -> Smart App Control; `citool.exe -lp`; CodeIntegrity-Eventlog, IDs `3076` (Audit), `3077` (enforced block). Microsoft-Dokumentation: https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/test-your-app-with-smart-app-control
2. Einen vorhandenen Block zeitlich und nach Dateipfad zuordnen; `3077` weist auf ein Enforcement-Blockereignis hin, aber die konkrete auslösende Richtlinie über `citool`/Details prüfen. Nicht jedes `Access denied` auf SAC schieben.
3. Vorhandenen Signaturstatus des konkreten Binaries optional mit `Get-AuthenticodeSignature` prüfen. `Status=Valid` bedeutet **nicht** automatisch SAC-Freigabe. Nicht mit Rechtsklick auf „Zulassen“ oder SmartScreen-UI-Ausnahmen verwechseln.
4. Im GO-Paket ein **read-only** Diagnoseskript `inspect_sac_environment.ps1` mit begrenztem Logfenster liefern. Das Skript selbst kann unter Anwendungssteuerungsregeln gesperrt sein; dann gibt die Anleitung **manuelle, identische Lesebefehle** an. Es darf keine ExecutionPolicy-Änderung erzwingen.
5. Wenn ein Build lokal nicht startet, protokolliere `BLOCKED_BY_APP_CONTROL` als eigenständiges **Runtime-Environment-Ergebnis** und setze `hardware_fse_validation=NOT_EXECUTED`. Kein Build-/DXGI-Defekt unterstellen.

### Manuelle Lesebefehle als Fallback

Wenn das Diagnoseskript selbst von einer Richtlinie blockiert wird, kann dieselbe Untersuchung mit den folgenden **rein lesenden** Befehlen in einer bereits erlaubten PowerShell-Sitzung durchgeführt werden:

```powershell
# Aktive App-Control-/SAC-Policies ansehen; nicht bearbeiten:
& "$env:windir\System32\CiTool.exe" -lp

# Nur die jüngsten App-Control-Block-/Auditereignisse einsehen:
Get-WinEvent -FilterHashtable @{
  LogName='Microsoft-Windows-CodeIntegrity/Operational'
  Id=3076,3077
  StartTime=(Get-Date).AddHours(-2)
} -MaxEvents 20 | Select-Object TimeCreated,Id,Message

# Signatur der von Euch selbst gebauten EXE nur prüfen:
Get-AuthenticodeSignature -FilePath 'C:\TESTPFAD\FSEProbe.exe' |
  Select-Object Status,StatusMessage,SignerCertificate
```

Falls PowerShell ebenfalls eingeschränkt ist, verwenden: **Windows-Sicherheit** für SAC-Modus sowie **Ereignisanzeige → Anwendungs- und Dienstprotokolle → Microsoft → Windows → CodeIntegrity → Operational**. Weder `Set-ExecutionPolicy`, `Unblock-File`, Registry-Anpassungen noch WHQL-/WDAC-Richtlinienmanipulationen sind Bestandteil unseres Workflows. Die `3077`-Ereignisse können auch von anderen App-Control-Richtlinien stammen: Pfad/Zeit/Richtlinie zuordnen, nicht blind SAC diagnostizieren.

## 5. GitHub Actions CI — so sieht die Pflichtstrecke aus

- `windows-2025` Windows-Runner, gepinnte Major-Versionen der Actions, auf dem Runner verfügbare MSVC-/SDK-Version ausgeben, konkrete Generatorwahl überprüfen. Kein blindes Erzwingen nicht vorhandener Visual-Studio-Versionen.
- CMake `configure -> build Release x64 -> CTest -> Python standard-library unit tests -> SHA256 manifest -> ZIP artifact`; jeder Build- und Parserfehler beendet den Job mit rotem Status. Codeanalyse ohne unsignierte binary auf dem SAC-Rechner.
- GitHub-Workflow `permissions: contents: read`, kein selbstgewählter Code-Signing-Key, kein Secrets-Exfiltration, keine unaufgeforderten Releases oder externen Uploads, standardmäßig manuell `workflow_dispatch` plus optional kontrollierte Push-Trigger. Artefakte als **UNSIGNED / NOT SAC VERIFIED / NOT FSE HARDWARE TESTED** markieren.
- Kosten/Quotas bei privaten GitHub-Repos variieren mit Tarif; kurze Builds und aufräumbare Artefakte vorsehen. Keine Zusage „immer kostenlos“.
- Host-Runners dürfen optional nichtgrafische Hilfsprogramme und FSEProbe `--help` ausführen, falls der Session-Kontext es erlaubt. **Hardware-FSE/Presents und Recorder-Overlay niemals als erfolgreich simulieren**.
- Auf einem Runner blockierte EXE bedeutet nicht automatisch, dass der Quellcode falsch ist; CI soll `run`-Tests sinnvoll nach Ausführungsvoraussetzung trennen.

## 6. Weitere Pflichtfunktion: Crash-/SAC-Sicherheitsverhalten der App

- `FSEProbe.exe` muss **ohne** externe Tools startfähig sein, zeigt dann `FSE_UNVERIFIED`; für ehrliches Recorder-Testing kann ein Supervisor PresentMon starten und anschließend die EXE. Nach normalem Exit Anzeigezustand soweit von Windows-APIs möglich wiederherstellen.
- Ein blockierter App-Start muss im `run_test.ps1` als Start-/Policy-Fehler erkennbar sein; kein stilles Retry in anderem Modus und kein `PASS` aus veralteten CSV-Dateien.
- Keine DLLs nachladen, die auf dem SAC-PC an Code-Integrity scheitern; Nutzung der Windows-eigenen D3D11/DXGI-Bibliotheken bevorzugen, keine Hooks oder fremden injizierten Overlays.
- Für App-Control-Diagnose getrennte Felder: `application_launch`, `security_policy_state`, `blocked_module`, `code_integrity_events`, `binary_signature`, `test_environment`, `hardware_fse_validation`. Nicht so tun, als könnten diese vollständig ohne Berechtigung automatisch erkannt werden.
- Wenn keine erlaubte Testumgebung vorhanden ist, **trotzdem komplette Software und Tests erstellen und FSE als HARDWARE_NOT_EXECUTED kennzeichnen**. Die Pro-Ausarbeitung darf nicht mit der Behauptung enden, SAC verhindere jede Entwicklungsarbeit.

## 7. Release-/Testpfad als einfache Entscheidungskette

```text
Ist ein geprüfter physischer Windows-Test-PC vorhanden?
  JA -> dort testen (lokale Sitzung, monitorverbundene GPU, per-device logs)
  NEIN -> separate Windows-Testinstallation auf eigener SSD möglich und gewünscht?
             JA -> separat und manuell einrichten; Produktiv-SAC unberührt
             NEIN -> CA-vertrauenswürdig signiertes Release verfügbar?
                        JA -> echte Start-/CodeIntegrity-Prüfung auf SAC-PC; dann Hardwaretest
                        NEIN -> Windows CI + Offline-Tests vollständig liefern,
                                 Hardwarestatus OPEN/BLOCKED_BY_ENVIRONMENT,
                                 KEINE falsche FSE-Abnahme
```

**Kein Fake-FSE-Workaround:** WSL, Sandbox, Hyper-V-GPU-Partition, Remote-GPU und RDP können für Teilprüfungen nützlich sein, gelten aber **nicht** als Ersatz für einen verifizierten Legacy-Exclusive-PresentMode auf der lokalen Monitor-Pipeline. Die Präsentationsart ist genau das Testobjekt, daher darf die Testumgebung sie nicht verändern.

## 8. Definition of Done und Stop-Gates für SAC

- **SAC-Gate S0:** Dev-PC-SAC unverändert. Es gibt einen read-only Preflight mit manueller Alternative.
- **SAC-Gate S1:** C++ wird auf Windows CI gebaut und Offline-Tests laufen, **ohne** auf dem geschützten Dev-PC eine unsignierte EXE starten zu müssen.
- **SAC-Gate S2:** CI-Artefakt ausdrücklich als unsigned/nicht-hardwaregetestet beschriftet. SHA256 + Herkunft sind nachweisbar.
- **SAC-Gate S3:** Der Agent bietet entweder eine eigene Test-Windows-Installation/ein Testgerät **oder** nachvollziehbares Signierverfahren an. Keine stillschweigende Änderung der Sicherheitseinstellungen.
- **SAC-Gate S4:** `BLOCKED_BY_APP_CONTROL` führt zu unmissverständlichem **NOT_EXECUTED**, niemals zu `PASS` oder einer Reparatur durch unerwünschte Richtlinienänderungen.
- **SAC-Gate S5:** Positive `FSE_VERIFIED`-Aussagen sind nur über eine wirklich laufende Windows-D3D11-Anwendung und passende externe PresentMon-Frame-Evidenz erlaubt.

## 9. Referenzen, vor GO erneut prüfen

- Microsoft SAC Überblick: https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/overview
- Microsoft SAC-FAQ: https://support.microsoft.com/de-de/windows/security/threat-malware-protection/smart-app-control-frequently-asked-questions
- Microsoft SAC-Codesignatur: https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/code-signing-for-smart-app-control
- Microsoft SAC-Tests + `citool`/Events: https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/test-your-app-with-smart-app-control
- Microsoft Codesigning-Optionen/Länder/Kosten: https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options
- GitHub Windows Runner: https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-Readme.md
- DirectX Fullscreen Optimizations: https://devblogs.microsoft.com/directx/demystifying-full-screen-optimizations/
- PresentMon CLI: https://github.com/GameTechDev/PresentMon/blob/main/README-ConsoleApplication.md
