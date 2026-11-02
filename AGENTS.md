# Verbindliche Arbeitsanweisung für den implementierenden Agenten

## Auftrag

Übernimm dieses Projekt unverändert als Ausgangspunkt. Entwickle kein neues Testspiel, keine neue Engine und keinen anderen Präsentationsnachweis. Arbeite die Tickets in `docs/05_WEAK_AGENT_EXECUTION_RUNBOOK.md` in Reihenfolge ab. Die erste Aufgabe ist Windows-CI, nicht der lokale Start einer unbekannten EXE.

## Harte Grenzen

- SAC, Defender, WDAC und Script-Policies des Dev-PCs bleiben unangetastet. Keine Entsperr-, Registry-, Signaturattrappen-, Speicherlade- oder Pfadwechsel-Tricks. Kein `dotnet test` für dieses C++-Projekt und kein Ersatz durch einen signierten Host.
- Bei `0x800711C7` oder zeitlich/pfadbezogenem CodeIntegrity-Block: `BLOCKED_BY_APP_CONTROL`, Exit 42. Tests nicht als ausgeführt werten, Code nicht deswegen zurückrollen. Ein allgemeines Access denied ist dagegen zunächst unbekannte Ursache.
- `GetFullscreenState`, Fenstergröße und erfolgreiche DXGI-Aufrufe beweisen kein klassisches FSE. `Hardware: Independent Flip` ist kein klassischer Exklusivnachweis.
- HUD bleibt unabhängig unbestätigt. Nicht eigenmächtig einen grünen Live-Status, `--require-verified`, Polling-Overlay oder eine IPC-Livebestätigung hinzufügen.
- Parser nie abschwächen, um einen Lauf grün zu bekommen. Keine entfernten Hash-, PID-, QPC-, Frameabdeckungs-, Negativtest- oder Guard-Prüfungen. Synthetische Fixtures bleiben als solche beschriftet.
- Keine Installation, kein Bootloader-/BitLocker-Eingriff, kein fremdes Repository, keine Veröffentlichung, keine Signaturbeschaffung und keine Berechtigungsänderung ohne gesonderten Auftrag.

## Arbeitsweise

Ändere pro Ticket möglichst wenige Dateien. Erst den konkreten Fehler reproduzieren, dann minimal korrigieren, dann den betroffenen Test ausführen. Ein Compilerfehler erlaubt keine Architektur-Neuerfindung. Windows-spezifische Annahmen anhand der Primärquellen in Dokument 06 prüfen. Keine Tests ohne tatsächliche Ausführung als bestanden melden.

Ausgabe pro Ticket: ID, geänderte Dateien, exakter Befehl, echter Exitcode, Belegdatei, Status `PASS|FAIL|BLOCKED_BY_APP_CONTROL|NOT_EXECUTED`, nächstes freigegebenes Ticket. Nach funktionalen Änderungen zwei saubere Abschlussrunden im geeigneten CI-/Testsystem. Nicht auf dem geschützten Dev-PC wiederholt unbekannte Binaries starten.

## Definition des minimalen Abschlusses

Windows MSVC + FXC bauen; CTest und beide PowerShell-Gates bestehen; ZIP/Hashes stimmen. Das ist **OFFLINE_BUILD_ACCEPTED**, nicht Hardwareabnahme. Anschließend ein Borderless-Kontrolllauf, ein belegter Legacy-Lauf und gezielte Negativtests auf physischer Hardware. Aufnahmequalität separat dokumentieren. Ohne diese Belege bleibt die Hardwarefreigabe offen.
