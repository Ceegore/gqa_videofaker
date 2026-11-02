# FSEProbe — Windows-Fullscreen-Diagnose 0.1.0

**Stand: 2. November 2026. Sprache: Deutsch. Ziel: Windows 10/11 x64, physischer Monitor, D3D11.**

Dieses Repository enthält die vollständige native Win32/D3D11-Implementierung, Offline-Auswertung, Tests und den manuellen Windows-CI-Job. Der Windows-Build mit MSVC und FXC (`/W4 /WX`) sowie alle Offline-Gates liefen am 2. November 2026 in GitHub Actions erfolgreich (`41491801315`, CLI-Smoke, CTest 3/3, PowerShell 7 und 5.1). Das erzeugte ZIP ist **unsigniert** und bleibt **kein SAC- oder Hardware-FSE-Nachweis**; physisches FSE und Recorder sind `NOT_EXECUTED`/`NOT_EVALUATED`.

Der portable C++-Teil und die Python-Tests laufen auch ohne Windows. Maßgeblich für den aktuellen Nachweisstand sind `SHA256SUMS.json` und `evidence/IMPLEMENTATION_2026-11-02.json`.

Ein direkter DXGI-Test auf der physischen GTX 1080 war erfolgreich: `borderless-control` und die Legacy-Vollbildanforderung liefen mit Exit 0, `SET_FULLSCREEN_RESULT=0x0`, Fokus und korrektem Output. **PresentMon/ETW konnte ohne erhöhte Rechte keine Trace-Session starten**; deshalb bleibt die unabhängige Präsentationsprüfung `UNVERIFIED` und Hardware-FSE `NOT_EXECUTED`.

## Einstieg

1. `docs/00_START_HERE.md`: ausführbarer Weg vom Quellpaket zum Test.
2. `AGENTS.md` und `docs/05_WEAK_AGENT_EXECUTION_RUNBOOK.md`: Arbeitsauftrag für den Coding-Agenten.
3. `docs/01_FULL_IMPLEMENTATION_PLAN.md`: Architektur und verbindliche Entscheidungen.
4. `docs/10_SAC_FIRST_DEV_AND_TEST.md`: Sicherheitsgrenzen, bevor etwas auf dem Dev-PC gestartet wird.

**Grundsatz:** SAC auf dem Entwicklungs-PC bleibt unverändert. Windows-CI baut und prüft; die echte Grafikabnahme erfolgt separat auf zulässiger physischer Windows-Hardware. Ein gebautes ZIP ist weder SAC-Freigabe noch FSE-Nachweis.

## Build und Test

Auf einem freigegebenen Windows-x64-System mit Visual Studio C++, Windows SDK/FXC, CMake ab 3.24 und Python ab 3.10:

```powershell
.\tools\configure_windows.ps1
cmake --build build --config Release --parallel 2
.\tests\test_runner.ps1
ctest --test-dir build -C Release --output-on-failure
python tools\package_release.py --exe build\Release\FSEProbe.exe `
  --output dist\FSEProbe-Windows-x64-UNSIGNED.zip
```

Der manuelle CI-Job liegt unter [Windows build and offline gates](https://github.com/Ceegore/gqa_videofaker/actions/workflows/windows-ci.yml) und wird ausschließlich per `workflow_dispatch` gestartet. Er veröffentlicht das unsignierte Testpaket `FSEProbe-Windows-x64-UNSIGNED-NOT-HARDWARE-TESTED`.

## Was das Programm tut

`legacy-exclusive` fordert klassisches DXGI-Vollbild an. `borderless-control` ist der bewusst getrennte Fenstermodus. Die Szene zeichnet Raster, asymmetrische Eckmarker, bewegtes Quadrat, synthetische Spielwerte, Frame-ID, Bitmuster und begrenzte Shader-Arbeit in genau eine Swapchain. ESC beendet; Verlust von Fokus, Monitor oder Modus macht den Test ungültig.

Die unabhängige Bestätigung erfolgt **nach** dem Lauf aus PresentMon 2.6.0 und dem eigenen Present-Protokoll. Im Bild steht deshalb dauerhaft `PRESENTATION NOT YET INDEPENDENTLY VERIFIED`. Einen bereits während jeder Millisekunde unabhängig bestätigten Exklusivzustand garantiert dieses Paket ausdrücklich nicht. Ein unbekannter Zustand wird nie als Erfolg verkauft.

## Verzeichnisse

`src/` ist die Anwendung, `tools/` enthält Auswertung/Runner/Diagnostik, `tests/` enthält portable und synthetische Tests, `schemas/` beschreibt die Verträge, `docs/` erklärt Implementierung und Abnahme, `.github/workflows/` enthält den manuellen Windows-CI-Job. `input_reference/` bewahrt die ursprünglichen Aufträge und SAC-Beobachtungen; interne Benutzerpfade wurden vor der Veröffentlichung durch Platzhalter ersetzt. Bei Abweichungen gilt die neue Dokumentation, die Korrekturen ausdrücklich erklärt.

Kein Installer, kein Auto-Update, kein Dienst und keine Telemetrie. Keine Drittanbieter-Engine oder Font-Runtime. PresentMon wird getrennt aus der offiziellen Quelle beschafft und anhand des festgelegten SHA-256 geprüft. Das Paketskript startet oder signiert keine Programme.
