# 12 — Finaler Status und Ticketabschluss

**Stand:** 2. November 2026. Dieses Dokument fasst den tatsächlich geprüften Stand zusammen. Es ersetzt keine Hardwareabnahme und keine SAC-Freigabe.

## Statusmatrix

| Bereich | Status | Beleg |
|---|---|---|
| Quellstruktur, 97 Python-Tests, PS 7/5.1 | PASS | lokale Gates + CI |
| Windows-MSVC-/FXC-Build (`/W4 /WX`) | PASS | CI-Lauf 41491801315 |
| CLI-Smoke (`--version`, `--help`, ungültig → 2) | PASS | CI-Lauf 41491801315 |
| CTest `core`, `python`, `app_self_test` | 3/3 PASS | CI-Lauf 41491801315 |
| Unsigniertes ZIP, Manifest, AMD64-PE32+ | PASS | CI-Artefakt, SHA-256 `9950d691…56aeb` |
| Borderless-Direktlauf, GTX 1080 | PASS (DXGI-Pfad) | `manual/borderless`, Exit 0, 900 Frames |
| Legacy-Direktlauf, GTX 1080 | PASS (DXGI-Anforderung) | `manual/legacy3`, `SET_FULLSCREEN_RESULT=0x0`, 876 Frames |
| PresentMon/ETW-Erfassung | BLOCKED | `access denied`, keine Trace-Session |
| Klassifikator ohne ETW | korrekt UNVERIFIED, Exit 11 | Lauf `586ce26b…` |
| Unabhängige FSE-Verifikation | NOT_EXECUTED | keine PresentMon-Daten |
| Recorderbewertung | NOT_EVALUATED | kein Recorder/Medium |
| SAC | einmalige Ausführung beobachtet, keine dauerhafte Freigabe | Registrystand 1, keine Policy-Änderung |

## Ticketabschluss nach docs/05

| Ticket | Status | Begründung |
|---|---|---|
| 00 Arbeitsstand/Schutzgrenzen | PASS | Kit übernommen, Integrität geprüft, keine Schutzänderung |
| 01 CI ohne Grafik | PASS | Workflow `workflow_dispatch`, `contents: read`, Lauf 41491801315 |
| 02 Windows-/HLSL-Build | PASS | MSVC 19.51, FXC, vier Shader, `/W4 /WX` |
| 03 Offline-Gates/Prozesshelfer | PASS | 97 Python-Tests, PS 7/5.1, Runner-Quoting/Timeout |
| 04 Abnahmefähiges Paket | PASS | 37 ZIP-Einträge, PE32+, Manifest/SHA-256 |
| 05 Testumgebung/Beobachter | BLOCKED | physischer Desktop vorhanden; ETW-Rechte fehlen |
| 06 Borderless/Zeitzuordnung | TEILWEISE | Direktlauf PASS; PresentMon-Zeitachse nicht prüfbar |
| 07 Legacy/negative Hardwarefälle | TEILWEISE | FSE-Anforderung PASS; kein unabhängiger PresentMode-Nachweis |
| 08 Recorderfunktion | NOT_EXECUTED | kein Recorder und keine Mediendatei vorhanden |
| 09 Abschluss/Review | PASS (offline) | zwei saubere Offline-Runden; Hardwarefelder bleiben offen |

## Die eine harte Grenze: ETW

PresentMon 2.6.0 schreibt seinen Hilfe-Text nach stderr (der Runner prüft seit dem Fix beide Ströme). Der eigentliche Trace startet auf diesem Konto nicht:

```text
error: failed to start trace session: access denied.
PresentMon requires either administrative privileges or to be run by a user in the
"Performance Log Users" user group.
```

Das Konto ist Mitglied von `Administratoren`, läuft aber UAC-gefiltert; `Performance Log Users` ist leer. Ohne erhöhte, separat autorisierte PowerShell bzw. ohne diese Gruppenmitgliedschaft gibt es keine ETW-Daten. Eine Rechte- oder UAC-Änderung wurde nicht vorgenommen. Der Runner bricht in diesem Fall korrekt mit `UNVERIFIED`/Exit 11 ab und erzeugt keinen falschen PASS.

## Reproduktion

```powershell
# bereits ausgeführt, direkter DXGI-Pfad
.\runtime\bin\FSEProbe.exe --mode borderless-control --load low --duration 15 --warmup 4 --auto-mark `
  --run-id manual-borderless-1 --log-dir .\manual\borderless

.\runtime\bin\FSEProbe.exe --mode legacy-exclusive --load low --duration 15 --warmup 4 --auto-mark `
  --run-id manual-legacy-3 --log-dir .\manual\legacy3
```

Für die unabhängige Auswertung muss der Observer in einer **separat erhöhten** PowerShell gestartet werden; anschließend ist der Runner mit `-ExternalObserver` zu verwenden. Erst dann können `presentation_proof=FSE_VERIFIED` und ein belastbares `hardware_fse_validation` entstehen.

## Nicht behauptet

- `SET_FULLSCREEN_RESULT=0x0` oder `GetFullscreenState=TRUE` ist **kein** klassischer FSE-Nachweis.
- Die direkten Läufe sind DXGI-/Rendering-Evidenz, keine unabhängige Präsentationsprüfung.
- Das unsignierte CI-Artefakt ist keine SAC-Freigabe und keine Hardwarezertifizierung.
- Ohne Recorder-Medium bleibt `recorder_result=NOT_EVALUATED`.

Aktuelle Details: `evidence/IMPLEMENTATION_2026-11-02.json`, CI-Lauf 41491801315.
