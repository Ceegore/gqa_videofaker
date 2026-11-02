# FSEProbe — START HERE / Pro-GO-Vorbereitung (SAC-first)

**Stand:** 2026-11-02. Dies ist **ausschließlich der ausführliche Arbeitsauftrag für den nächsten Schritt**, kein bereits gebautes Windows-Spiel. Die lokale Windows-Hardware wurde nicht getestet.

## Ein Wort startet den Pro-Durchlauf

1. In ChatGPT falls verfügbar **Pro/hohe Denkintensität** selbst im Modellmenü auswählen. Das kann das Paket nicht selbst ändern.
2. **Im selben Chat ausschließlich `go` schreiben.** Dann sind `GO_MASTER_AUFTRAG.md`, `SAC_FIRST_ENTWICKLUNGSSTRATEGIE.md`, das Technik-Audit und das ursprüngliche Briefing verbindlich; das Ergebnis soll ein **komplett ausgearbeitetes Implementierungskit samt möglichst vollständigen, ausführbaren Quellcodes/Tests** als überprüftes ZIP werden.
3. In einem neuen Chat dieses Paket hochladen und schreiben: „Führe GO_MASTER_AUFTRAG.md vollständig aus, SAC_FIRST_ENTWICKLUNGSSTRATEGIE.md hat Vorrang.“

## Wichtigste Abweichung: Dev-PC mit aktivem Smart App Control

**Das Entwicklungs-Windows darf nicht umkonfiguriert werden.** Eine unsignierte, neue EXE wird dort nicht als lauffähig vorausgesetzt. Der Pro-Plan muss zuerst Windows-GitHub-Actions-MSVC-Builds und automatisierte Offline-Tests ermöglichen, **danach** echte physische FSE-Hardwaretests über eine separate Windows-Testmaschine oder isolierte Windows-Testinstallation (eigene SSD, gleiche GPU), oder ein tatsächlich CA-vertrauenswürdig signiertes und erfolgreich erlaubtes Release.

**CI erstellt keine vertrauenswürdige SAC-Signatur automatisch.** Self-signed Zertifikate, Entwickler-Ausnahmen, Injektions-/Registry-Tricks und SAC-Deaktivierung sind *keine* erlaubten Standardwege. Ohne reale GPU-Abnahme muss das Ergebnis `HARDWARE_NOT_EXECUTED` und **nicht** `FSE_VERIFIED` heißen.

## Erwartete Pro-Lieferobjekte

- Ein tief ausgearbeitetes, API-genaues Windows-Implementierungshandbuch, einschließlich SAC-first Architektur und konkreter Handgriffe zur Nutzung.
- Ein wirklich vollständiges, möglichst kompilierbares natives Win32/Direct3D-11-Projekt (C++20, HLSL, CMake), zwei gezielte Präsentationsmodi, synthetischer Spielinhalt, GPU-Laststufen, sauberes Exception-/Device-Cleanup.
- Unabhängige PresentMon/ETW-Klassifikation mit PID-/Swapchain-/QPC- und Recorderzeitfenster-Prüfung, `PASS|FAIL|UNVERIFIED` sowie getrenntem Recordergebnis; kein „Fake-PASS“ aus DXGI-Zustand.
- Read-only SAC-Diagnose, Windows-CI-Workflow, maschinenlesbare Logs/Reports, robuste PowerShell-Start-/Abbruchabläufe, CSV-Fixtures, Python-Tests und Release-Manifeste/Prüfsummen.
- Kopierfertige, kleine Agenten-Tickets mit klaren Build-/Test-Gates; zwei saubere aufeinanderfolgende Review-Durchläufe, soweit technisch ausführbar, exakte Grenzen offenlegen.
- Ein **tatsächlich erzeugtes ZIP** samt Prüfbericht und konkreten Dateien, nicht nur eine textuelle Wunschliste.

## Dateien in diesem Vorbereitungspaket

| Datei | Inhalt |
|---|---|
| `GO_MASTER_AUFTRAG.md` | Verbindlicher Auftrag: Umfang, Code-/Test-Dateien, Release-Blocker, schwacher Coding-Agent |
| `SAC_FIRST_ENTWICKLUNGSSTRATEGIE.md` | Verpflichtende SAC-konforme Build-/Runtime-Architektur, Testmaschinen, Signing und Diagnostik |
| `TECHNIK_AUDIT_UND_QUELLEN.md` | Geprüfte DXGI-/PresentMon-/CI-/SAC-Quellen, bekannte Risiken und offene Prüfpflichten |
| `FSEProbe_Agentenbriefing_2026-11-02.md` | Ursprüngliche ausführliche Spezifikation als Kontext |
| `ABNAHME_MATRIX.csv` | Prüfpunkte, Negativfälle, Gate-Evidenz, Testumgebung |
| `OUTPUT_CONTRACT.json` | Erwartete Zustände, Logfelder und Report-Evidenz; wird im GO-Durchlauf finalisiert |
| `tools/inspect_sac_environment.ps1` | Read-only Windows-SAC-/Signatur-/CodeIntegrity-Diagnose, **kann selbst durch Policy blockiert werden** |
| `CI_WINDOWS_BLUEPRINT.yml` | Ausgangsgerüst für Windows-MSVC-CI **nach** Generierung des Hauptprojekts; keine FSE-Hardwareabnahme |
| `tools/check_preparation_pack.py` | Verifiziert Manifest-Hashes und strukturelle Vorbereitungspaket-Dateien |
| `MANIFEST.json` | SHA-256 für alle Dateien außer dem Manifest selbst |

**Hierarchie:** Offizielle, aktuell verifizierte API-Fakten > `SAC_FIRST_ENTWICKLUNGSSTRATEGIE.md` bei Sicherheits-/SAC-Fragen > `GO_MASTER_AUFTRAG.md` > Technik-Audit > Ursprungsbriefing. Unauflösbare Unklarheiten und fehlende Hardwarebeweise offen darstellen.
