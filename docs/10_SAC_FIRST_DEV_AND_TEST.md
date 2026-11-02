# 10 — SAC-first: entwickeln, ohne den Dev-PC zu entsichern

## Maßgebliche Erfahrungen aus der Nutzerdatei

`input_reference/SACsolutions_USER_ORIGINAL.md` dokumentiert konkrete Messungen auf dem Entwicklungs-PC, nicht eine universelle Windows-Gesetzmäßigkeit. Die Korrektur vom 2. September 2026 zeigt blockierte eigene GUI-DLLs auch unter signiertem `dotnet.exe`. Die Ergänzung vom 3. Oktober zeigt, dass selbst eine echte Core-Klassenbibliothek blockiert werden kann. Am 8. Oktober ist eine blockierte native Python-Abhängigkeit unter einem Benutzerprofil dokumentiert. Die Beobachtung vom 14. Oktober zeigt erfolgreiche .NET-Single-File-Veröffentlichungen, erklärt die Ursachen jedoch selbst nur als Hypothese.

Daraus folgen verbindlich: kein Vertrauenstransfer durch signierten Host; kein pauschaler erlaubter Pfad; kein „Bibliothek statt EXE“ als Heilmittel; ein einmaliger Start beweist keine dauerhafte Freigabe. Eine CA-signierte Datei und tatsächlicher Start sind verschiedene Prüfungen. Ein GitHub-Build erlangt keine zusätzliche SAC-Reputation allein durch seinen Buildort.

## Standardroute

**Dev-PC:** Dateien bearbeiten, Reviews, erlaubte bestehende Werkzeuge verwenden. Keine neue unsigned FSEProbe-/Testhostausführung voraussetzen. Selbst ein schon installierter Python kann zusätzliche native Bibliotheken nachladen; deshalb Offline-Tests standardmäßig in CI ausführen, wenn die vorhandene lokale Vertrauenskette unklar ist.

**Windows-CI:** Quellcode kompilieren, Shader übersetzen, nichtgrafische Test-Binaries ausführen, Python und PowerShell testen, unsigniertes ZIP erstellen. Blockiert eine dortige Richtlinie die Ausführung, wird das als Blockade markiert und der Job nicht als bestandener Test veröffentlicht. Die Richtlinie wird auch im Runner nicht abgeschaltet.

**Physische Abnahme:** ein bereits geeigneter Test-PC mit lokalem Monitor und zulässiger Programmausführung oder manuell organisierte separate Test-Windows-Installation. Dieselbe GPU kann in einer separaten Installation untersucht werden, aber das beweist nicht die Ausführbarkeit im produktiven Windows. Beide Programme, Recorder und Probe, müssen im tatsächlichen Test-Windows vorhanden sein.

## Separate Installation ist kein automatischer Workaround

Dieses Kit partitioniert keine Platte, verändert keinen Bootloader und schaltet keine Schutzfunktion um. Eine zusätzliche Installation erfordert eine eigene Nutzerentscheidung, gültige Windows-Nutzungsrechte, geeigneten Datenträger, Backup, Prüfung von UEFI/BitLocker-/Recovery-Schlüsseln und einen sicheren Installationsprozess. Auch das Test-Windows muss nach seiner geltenden Sicherheitsrichtlinie die Tools zulassen. Ist das nicht gegeben, bleibt Hardwareabnahme offen; der Agent darf daraus keinen Auftrag zur Abschaltung ableiten.

## Optionaler vertrauenswürdig signierter Build

Nur wenn tatsächlich vorhandene Berechtigungen, Identitätsprüfung und Signiermaterial bestehen. Microsoft nennt anerkannte Codesigning-Optionen [S15,S18]. Artifact Signing ist laut geprüftem Angebot nicht als allgemein nutzbarer Standard für jede deutsche Privatperson anzunehmen; EU-Organisationen und Privatentwickler haben unterschiedliche Voraussetzungen. Keine Kosten oder Zulassung garantieren.

Privater Schlüssel gehört nicht ins Repo oder ZIP. Signing ist hier nicht eingebaut; deshalb bleibt das CI-Paket ausdrücklich unsigniert. Eine spätere Signierung ändert den EXE-Hash und benötigt neue Herkunfts-/Integritätsdaten. `Get-AuthenticodeSignature` prüft die Signatur, **nicht** erfolgreiche SAC-Ausführung. Endgültig zählt der erlaubte tatsächliche Start zusammen mit Logs aller relevanten Module.

## Lesende Diagnose

Das Script `inspect_sac_environment.ps1` liest Signaturen, SHA-256, begrenzte CodeIntegrity-Ereignisse und `CiTool -lp`. Es ändert keine Policy. IDs 3033/3077 werden nur bei plausibler zeitlicher und vollständiger Pfadzuordnung als zugehöriger Block gewertet; 3076 ist Audit, nicht automatisch verhindertes Ausführen. Native Gerätepfade können den einfachen Pfadabgleich verhindern: dann Roh-XML manuell prüfen und das Ergebnis unklar lassen, statt falsch SAC zu diagnostizieren.

Falls das Script selbst blockiert ist, in einer bereits erlaubten Shell nur die folgenden Befehle nutzen oder direkt die Ereignisanzeige öffnen:

```powershell
& "$env:windir\System32\CiTool.exe" -lp
Get-WinEvent -FilterHashtable @{
  LogName='Microsoft-Windows-CodeIntegrity/Operational'
  Id=3033,3076,3077
  StartTime=(Get-Date).AddMinutes(-15)
} -MaxEvents 40 | Select-Object TimeCreated,Id,Message
Get-AuthenticodeSignature -LiteralPath .\bin\FSEProbe.exe |
  Select-Object Status,StatusMessage,SignerCertificate
```

Diese Befehle können ebenfalls mangels Rechten scheitern; das ist kein Freigabenachweis. GUI-Alternative: Windows-Sicherheit für SAC-Zustand und Ereignisanzeige → Anwendungs- und Dienstprotokolle → Microsoft → Windows → CodeIntegrity → Operational. Keine identische Wirkung von SmartScreen-„Zulassen“, Herkunftsmarkierung und SAC-Ausnahme unterstellen.

## Laufzeitklassifikation

`BLOCKED_BY_APP_CONTROL`/Exit 42 bedeutet: Der beabsichtigte Test konnte nicht ordnungsgemäß ausgeführt werden. Eine blockierte Testassembly kann hunderte scheinbare Fehler erzeugen, ohne dass ein Testkörper lief. Nicht debuggen oder zurückrollen, als wäre das ein Beweis für eine Code-Regression.

Allgemeine Start-/Zugriffsfehler ohne passenden Nachweis bleiben `UNVERIFIED_LAUNCH`/Umgebung unbekannt. Fehlende Eventlogrechte werden separat ausgegeben. Keine Blockereignisse in einem bloßen Build-/Dateihashfenster beweisen keine Laufzeitverträglichkeit. Der Runner macht keine automatischen Churn-/Retryserien.

## Quellenkonflikte und enger Geltungsbereich

Ältere Windows-Dokumente beschreiben SAC-Reaktivierung nur nach Neuinstallation, neuere FAQs teilweise differenzierter. Diese historische Änderung ist kein Anlass, Schutzschalter für dieses Projekt anzufassen. Die in der Nutzerdatei beschriebene ausdrücklich begrenzte Wegwerf-Sandbox-Ausnahme aus einem anderen Projekt wird **nicht** automatisch auf dieses Tool, einen Host oder einen persistenten Runner übertragen. Sandbox kann Funktionstests erleichtern, ersetzt aber gerade die hier zu untersuchende physische Präsentationskette nicht.
