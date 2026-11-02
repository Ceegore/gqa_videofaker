# FSEProbe — Implementierungskit 0.1.0

**Stand: 2. November 2026. Sprache: Deutsch. Ziel: Windows 10/11 x64, physischer Monitor, D3D11.**

Dieses Paket enthält vollständige Quellcodedateien, Offline-Auswertung, Tests, Windows-CI und einen ausführlichen Implementierungs-/Abnahmeplan. Es enthält **keine hier erzeugte Windows-EXE**. Der portable C++-Teil und Python wurden hier ausgeführt; MSVC, FXC, PowerShell, SAC-Start und physischer FSE wurden hier nicht ausgeführt. Maßgeblich sind `KIT_STATUS.json` und `evidence/`.

## Einstieg

1. `docs/00_START_HERE.md`: ausführbarer Weg vom Quellpaket zum Test.
2. `AGENTS.md` und `docs/05_WEAK_AGENT_EXECUTION_RUNBOOK.md`: Arbeitsauftrag für den Coding-Agenten.
3. `docs/01_FULL_IMPLEMENTATION_PLAN.md`: Architektur und verbindliche Entscheidungen.
4. `docs/10_SAC_FIRST_DEV_AND_TEST.md`: Sicherheitsgrenzen, bevor etwas auf dem Dev-PC gestartet wird.

**Grundsatz:** SAC auf dem Entwicklungs-PC bleibt unverändert. Windows-CI baut und prüft; die echte Grafikabnahme erfolgt separat auf zulässiger physischer Windows-Hardware. Ein gebautes ZIP ist weder SAC-Freigabe noch FSE-Nachweis.

## Was das Programm tut

`legacy-exclusive` fordert klassisches DXGI-Vollbild an. `borderless-control` ist der bewusst getrennte Fenstermodus. Die Szene zeichnet Raster, asymmetrische Eckmarker, bewegtes Quadrat, synthetische Spielwerte, Frame-ID, Bitmuster und begrenzte Shader-Arbeit in genau eine Swapchain. ESC beendet; Verlust von Fokus, Monitor oder Modus macht den Test ungültig.

Die unabhängige Bestätigung erfolgt **nach** dem Lauf aus PresentMon 2.6.0 und dem eigenen Present-Protokoll. Im Bild steht deshalb dauerhaft `PRESENTATION NOT YET INDEPENDENTLY VERIFIED`. Einen bereits während jeder Millisekunde unabhängig bestätigten Exklusivzustand garantiert dieses Paket ausdrücklich nicht. Ein unbekannter Zustand wird nie als Erfolg verkauft.

## Verzeichnisse

`src/` ist die Anwendung, `tools/` enthält Auswertung/Runner/Diagnostik, `tests/` enthält portable und synthetische Tests, `schemas/` beschreibt die Verträge, `docs/` erklärt Implementierung und Abnahme, `.github/workflows/` enthält den manuellen Windows-CI-Job. `input_reference/` bewahrt die ursprünglichen Aufträge und SAC-Beobachtungen unverändert; bei Abweichungen gilt die neue Dokumentation, die Korrekturen ausdrücklich erklärt.

Kein Installer, kein Auto-Update, kein Dienst und keine Telemetrie. Keine Drittanbieter-Engine oder Font-Runtime. PresentMon wird getrennt aus der offiziellen Quelle beschafft und anhand des festgelegten SHA-256 geprüft. Das Paketskript startet oder signiert keine Programme.
