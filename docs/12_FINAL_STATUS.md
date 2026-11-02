# 12 — Finaler Status und Ticketabschluss

**Stand:** 2. November 2026. Dieses Dokument fasst den tatsächlich geprüften Stand zusammen. Es ersetzt keine Hardwarezertifizierung und keine SAC-Freigabe.

## Statusmatrix

| Bereich | Status | Beleg |
|---|---|---|
| Quellstruktur, 99 Python-Tests, PS 7/5.1 | PASS | lokale Gates + CI |
| Windows-MSVC-/FXC-Build (`/W4 /WX`) | PASS | CI-Lauf 41507241314 |
| CLI-Smoke (`--version`, `--help`, ungültig → 2) | PASS | CI-Lauf 41507241314 |
| CTest `core`, `python`, `app_self_test` | 3/3 PASS | CI-Lauf 41507241314 |
| Unsigniertes ZIP, Manifest, AMD64-PE32+ | PASS | CI-Artefakt, 38 Einträge |
| Borderless-Direktlauf, GTX 1080 | PASS (DXGI-Pfad) | `manual/borderless`, Exit 0 |
| Legacy-Direktlauf, GTX 1080 | PASS (DXGI-Anforderung) | `manual/legacy3`, `SET_FULLSCREEN_RESULT=0x0` |
| PresentMon/ETW mit erhöhtem Observer | **AUSGEFÜHRT** | Control `435124e3…`, Legacy `1e105dfa…` |
| Borderless-Kontrolle mit ETW | **PASS**, `CONTROL_VERIFIED_NOT_FSE` | 1162 Frames, Ledger vollständig |
| Legacy mit ETW | **FAIL**, `FAIL_NOT_CLASSIC_EXCLUSIVE` | 1169 Frames `Hardware: Independent Flip` |
| Unabhängige FSE-Verifikation | **NICHT ERREICHT** | kein `Legacy Flip`/`Legacy Copy` beobachtet |
| Recorderbewertung | NOT_EVALUATED | kein Recorder/Medium |
| SAC | einmalige Ausführung beobachtet, keine dauerhafte Freigabe | Registrystand 1, keine Policy-Änderung |

## Ticketabschluss nach docs/05

| Ticket | Status | Begründung |
|---|---|---|
| 00 Arbeitsstand/Schutzgrenzen | PASS | Kit übernommen, Integrität geprüft, keine Schutzänderung |
| 01 CI ohne Grafik | PASS | Workflow `workflow_dispatch`, `contents: read`, Lauf 41507241314 |
| 02 Windows-/HLSL-Build | PASS | MSVC 19.51, FXC, vier Shader, `/W4 /WX` |
| 03 Offline-Gates/Prozesshelfer | PASS | 99 Python-Tests, PS 7/5.1, Runner-Quoting/Timeout |
| 04 Abnahmefähiges Paket | PASS | 37 ZIP-Einträge, PE32+, Manifest/SHA-256 |
| 05 Testumgebung/Beobachter | PASS | ein UAC-bestätigter erhöhter Observer, App blieb unelevated |
| 06 Borderless/Zeitzuordnung | PASS | reale PresentMon-Zeitachse, Kontrolle vollständig abgeglichen |
| 07 Legacy/negative Hardwarefälle | **STOP / FAIL** | DXGI meldet Fullscreen, PresentMon sieht Independent Flip |
| 08 Recorderfunktion | NOT_EXECUTED | kein Recorder und keine Mediendatei vorhanden |
| 09 Abschluss/Review | PASS (offline) | zwei saubere Offline-Runden; negatives Hardwareergebnis dokumentiert |

## ETW gelöst — und was dabei herauskam

PresentMon 2.6.0 schreibt `--help` nach stderr (Runner prüft beide Ströme). Für den Trace wurde **einmalig** ein UAC-bestätigter, begrenzter PowerShell-Agent gestartet. Er startete pro Run ausschließlich `start_observer.ps1`; die Anwendung selbst lief weiterhin unelevated.

Ergebnis der echten Läufe:

- **Borderless-Kontrolle:** `verdict=PASS`, `presentation_proof=CONTROL_VERIFIED_NOT_FSE`, 1162 Guard-Frames, `ONE_TO_ONE_PRESENT_LEDGER_RECONCILED`.
- **Legacy:** `verdict=FAIL`, `reason=FAIL_NOT_CLASSIC_EXCLUSIVE`, `dxgi_state=FULLSCREEN_REPORTED`, beobachtet: `Hardware: Independent Flip` (1169 Guard-Frames).

Damit ist die entscheidende Trennung belegt: `SetFullscreenState(TRUE)` und `GetFullscreenState=TRUE` bedeuten **nicht** klassisches FSE. Windows/Treiber haben die Legacy-Anforderung als Independent Flip präsentiert. Der Klassifikator hat korrekt fail-closed entschieden; es gibt keinen API-basierten Ersatz-PASS.

Zusätzlich wurde ein realer Schemafehler behoben: PresentMon 2.6.0 `--v2_metrics` schreibt `CPUBusy`, nicht `MsCPUBusy`. Der Klassifikator akzeptiert jetzt beide Spaltennamen; ohne beide endet er weiterhin `UNVERIFIED_SCHEMA`.

## Reproduktion

```powershell
# Kontrolle mit erhöhtem Observer
.\runtime\tools\run_test.ps1 -App .\runtime\bin\FSEProbe.exe `
  -PresentMon .\PresentMon-2.6.0-x64.exe -PhysicalDesktop `
  -Mode borderless-control -Load low -Duration 30 -AutoMark -ExternalObserver

# Legacy mit erhöhtem Observer
.\runtime\tools\run_test.ps1 -App .\runtime\bin\FSEProbe.exe `
  -PresentMon .\PresentMon-2.6.0-x64.exe -PhysicalDesktop `
  -Mode legacy-exclusive -Load low -Duration 30 -AutoMark -ExternalObserver
```

Der Observer muss dafür in einer separat autorisierten erhöhten PowerShell laufen. Ein FSO-Vergleich über die sichtbare Windows-Kompatibilitätseinstellung ist ein **neuer, getrennter Lauf**; Registry- oder Policy-Änderungen sind nicht Teil dieser Abnahme.

## Nicht behauptet

- `SET_FULLSCREEN_RESULT=0x0` oder `GetFullscreenState=TRUE` ist **kein** klassischer FSE-Nachweis.
- `Hardware: Independent Flip` ist kein Legacy-Nachweis; der Legacy-Lauf ist deshalb FAIL, nicht PASS.
- Das unsignierte CI-Artefakt ist keine SAC-Freigabe und keine Hardwarezertifizierung.
- Ohne Recorder-Medium bleibt `recorder_result=NOT_EVALUATED`.

Aktuelle Details: `evidence/IMPLEMENTATION_2026-11-02.json`, CI-Lauf 41507241314.
