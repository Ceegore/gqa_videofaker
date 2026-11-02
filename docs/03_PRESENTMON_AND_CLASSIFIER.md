# 03 — PresentMon, Zeitzuordnung und Klassifikation

## Festgelegter Beobachter

**Console-Version 2.6.0**, offizielles Asset `PresentMon-2.6.0-x64.exe`. SHA-256:

```text
b2a706bc6ad475749e3b7e3409263aa1e6906d45bdcf993f6dbc0f660188f1af
```

Der Digest wurde aus der GitHub-Release-Assetliste übernommen [S11]; die Binary wurde hier nicht ausgeführt. Pfad, Version und Hash stehen in `tools/presentmon.lock.json`. Der Runner prüft den Hash **vor** Ausführung und kontrolliert die benötigten Flags in der tatsächlichen `--help`-Ausgabe. Kein „latest“-Download, keine automatisch akzeptierte neue CLI-Version.

Die erzeugte Befehlsfolge enthält `--process_name FSEProbe.exe`, `--output_file`, `--qpc_time`, `--v2_metrics`, `--no_console_stats`, eine eindeutige `--session_name`, `--timed` und `--terminate_after_timed`. Es wird weder `--output_stdout` gleichzeitig verwendet noch `--exclude_dropped`, `--no_track_display` oder `--restart_as_admin` gesetzt. Der Observer startet vor dem Zielprozess; nachher wird auf die konkrete PID gefiltert.

## Was „startbereit“ wirklich bedeutet

Ein lebender Prozess nach einer Sekunde ist **kein** validierter ETW-Handshake. Der externe Helfer nennt seinen Zustand deshalb `PROCESS_ALIVE_ONLY_NOT_ETW_PROOF`. Der endgültige Bericht verlangt anschließend vollständige, zeitlich passende Frames. Zu später Tracebeginn, fehlende Daten oder früh gestorbener Observer bleiben UNVERIFIED. Der Ansatz vermeidet eine unbewiesene Livezusage und benötigt kein Fenster über dem Testbild.

## Eingabevertrag

`session.json` beschreibt Run-ID, Modus, Evidence-Typ, Operatorbestätigung physischer Desktop, App-Start/PID/Erstellungs-FILETIME, QPC-Frequenz, Observerstart/Version/Hash, Exitcodes, Timeouts, Runnerfehler und SHA-256 der fünf Belegdateien. Diese Hashes verhindern versehentliche Vermischung/Veränderung, sind aber keine digitale Signatur oder manipulationssichere Attestation.

`app.jsonl` wird strikt zeilenweise gelesen. Ereignis-Sequenz ist lückenlos; QPC darf nicht rückwärts laufen; START und END müssen eindeutig und an den Grenzen stehen. JSON-Doppelschlüssel, unpassende Datentypen und unbekannte Ereignisse werden nicht still akzeptiert. UTC ist nur menschenlesbarer Kontext.

`frames.csv`: `FrameIndex,BeforeQPC,AfterQPC,HResult,Fullscreen,Focus`. Die Frameindices beginnen bei null, sind lückenlos und monoton. Kein Present mit Fehler oder falschem Fokus/Fullscreen wird als normaler Frame behandelt.

PresentMon-Pflichtheader: `Application`, `ProcessID`, `SwapChainAddress`, `PresentRuntime`, `PresentMode`, `CPUStartQPC`, `MsCPUBusy`, `DisplayedTime`. Spalten werden nach Namen gelesen; UTF-8-BOM, andere Reihenfolge, zusätzliche gültig gequotete Spalten sind erlaubt. Fehlende/doppelte Header, unvollständige Zeilen, zu große Dateien und ungültige Zahlen sind kein Erfolg. QPC bleibt Integer; kein Float-Roundtrip über Excel oder JavaScript.

## Zeitmodell und Guard-Bänder

`CPUStartQPC` ist CPU-Framebeginn, nicht Scanout und nicht schlicht die Zeit des Present-Aufrufs. `MsCPUBusy` ist die Zeit bis zur Präsentation [S09]. Der Auswerter berechnet mit Decimal:

```text
estimated_present_qpc = CPUStartQPC + round(MsCPUBusy * qpc_frequency / 1000)
```

Danach muss der Zeitanker in ein tatsächliches `[BeforeQPC, AfterQPC]` aus dem App-Ledger passen, mit 0,25 ms enger Rundungs-/Zuordnungstoleranz. Mehrere CSV-Zeilen dürfen nicht denselben Aufruf als unabhängige Belege mehrfach zählen. Eine zweite Swapchain im relevanten App-Segment wird abgewiesen, statt die bequemere auszuwählen. Der COM-Zeiger der App wird nur diagnostisch geloggt; seine Gleichheit mit einer ETW-Swapchainadresse wird **nicht** unbelegt vorausgesetzt.

Für Marker `[start,end]`: äußerer Prüfbereich `[start−250ms,end+250ms]`; Zählkern `[start+250ms,end−250ms]`. Jede Ledger-Präsentation im äußeren Bereich benötigt einen passenden ETW-Datensatz. Im Kern müssen mindestens 30 Frames mit positivem `DisplayedTime` über mindestens zwei Sekunden vorliegen. `NA` oder 0 zählt nicht als positiv angezeigter Frame. Zwischen relevanten Presents darf keine Lücke größer 500 ms liegen; CPU-Zeiten über 250 ms verhindern diese vereinfachte Guard-Interpretation.

Die exakte Zuordnung dieser Console-Version muss beim ersten echten Windows-Lauf bestätigt werden. Die synthetischen Tests beweisen nur die implementierten Regeln. Bei `UNVERIFIED_TIME_RECONCILIATION` zuerst Daten prüfen, nicht Grenzwerte aufweichen. Die vollständige Abdeckung reduziert falsch positive Ergebnisse; sie beweist nicht, dass ETW oder Treiber unter beliebigen Umständen fehlerfrei sind.

## Modusentscheidung

| Beobachtung im äußeren Bereich | Legacy-Anforderung |
|---|---|
| nur `Hardware: Legacy Flip` / `Hardware: Legacy Copy to front buffer` | Kandidat; alle übrigen Gates müssen zusätzlich bestehen |
| ausschließlich Independent/Hardware Composed/Composed | FAIL_NOT_CLASSIC_EXCLUSIVE |
| mindestens ein nichtklassischer Frame zwischen Legacy-Frames | FAIL_PRESENT_MODE_CHANGED |
| unbekannter Mode, fehlende Zeilen, keine passende PID | UNVERIFIED |

Die beiden Legacy-Labels bilden gemeinsam die akzeptierte Ownership-Familie [S09]. Borderless-Kontrolle darf keines davon enthalten; unterschiedliche nichtklassische Kontrollmodi werden als beobachtete Verteilung protokolliert. Der Kontrolllauf testet „nicht klassisch exklusiv“, nicht eine einzige konkrete DWM-Kompositionsart.

Preflight/Warmup wird getrennt zusammengefasst und kann das Aufnahmefenster niemals ersetzen. Die App-Regeln sind absichtlich noch strenger: Fokus-/Display-/DXGI-Verlust irgendwo nach Scharfschaltung invalidiert den gesamten Lauf, auch kurz außerhalb des markierten Bereichs. Für neue Bedingungen einen neuen Run beginnen.

## Ausgabevertrag

`verdict`: PASS, FAIL, UNVERIFIED, BLOCKED oder SYNTHETIC_PASS. `presentation_proof`: FSE_VERIFIED, CONTROL_VERIFIED_NOT_FSE, synthetische Variante oder unbestätigt. `dxgi_state`, `recorder_result`, `hardware_fse_validation` und `live_verification` bleiben eigenständige Felder. Ein Recorderfehler wird nicht durch erfolgreichen ETW-Nachweis geheilt.

Der Report kennzeichnet Operator-Marker als Näherung und automatische Marker als reine Diagnosezeit. Kein Recorder-API-Anschluss wird erfunden. Die Datei `schemas/recorder-assessment.template.json` wird separat mit Video-/Screenshotpfad, Hash und menschlichen Befunden ausgefüllt; `summary.json` nicht nachträglich auf PASS umschreiben.

## Wiederholung einer vorhandenen Auswertung

```powershell
python tools/verify_presentmon.py --run-dir logs/DEINE_TATSAECHLICHE_RUN_ID
```

Hier den tatsächlich erzeugten Ordner einsetzen. Nie mehrere Runs zusammenkopieren. Für automatisierte Parserprüfungen ausschließlich die mitgelieferten synthetischen Fixtures oder temporären Testdaten verwenden. Ein synthetischer Test hat keinen Anspruch auf beobachtete Hardware.
