# Changelog

## 0.1.0 — 2026-11-02

Erste veröffentlichte FSEProbe-Diagnoseversion.

### Enthalten

- Native Win32/D3D11-Anwendung mit `legacy-exclusive` und `borderless-control`.
- App-Present-Ledger, QPC-/Fokus-/Output-Diagnose und automatische Markierungen.
- PresentMon-2.6.0-Auswertung mit fail-closed Klassifikation, Guard-Bändern und Ledger-Abgleich.
- Offline-Tests, PowerShell-Runner, Windows-CI und unsigniertes Runtime-Paket.
- Windows-CI-Lauf 41509867768: MSVC/FXC-Build, CLI-Smoke, PS 7/5.1, CTest 3/3.
- Reale ETW-Läufe: Borderless-Kontrolle PASS (`CONTROL_VERIFIED_NOT_FSE`); Legacy FAIL (`FAIL_NOT_CLASSIC_EXCLUSIVE`, beobachtet `Hardware: Independent Flip`).

### Behobene Fehler

- PowerShell 5.1: verschachtelte JSON-Arrays aus `ConvertFrom-Json` im Runner-Test und in der VS-Erkennung.
- Windows-CI: mehrere `python.exe`-Treffer wurden zu einem ungültigen Pfad verkettet.
- PresentMon 2.6.0: `--help` wird nach stderr geschrieben; Runner und Observer prüfen beide Ströme.
- PresentMon 2.6.0: `--v2_metrics` verwendet `CPUBusy` statt `MsCPUBusy`; der Klassifikator akzeptiert beide Namen.
- Stabile LF/CRLF-Regeln und regenerierte SHA-256-Manifeste.

### Bekannte Grenzen

- Das Artefakt ist **unsigniert** und keine SAC-Freigabe.
- Klassisches Legacy-FSE wurde auf dem getesteten Windows/GPU-Pfad nicht beobachtet; `FSE_VERIFIED` wird nicht behauptet.
- Recorderqualität ist `NOT_EVALUATED`; es liegt kein Recorder/Medium vor.
- Live-Verifikation ist bewusst nicht implementiert; die Auswertung erfolgt nach dem Lauf.
