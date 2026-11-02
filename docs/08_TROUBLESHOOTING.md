# 08 — Fehlerdiagnose ohne Endlosschleifen

| Befund | Zuerst prüfen | Nicht tun |
|---|---|---|
| EXE startet nicht, 0x800711C7 | zeitlich/pfadbezogene CodeIntegrity-Daten; Diagnose als Umgebungsblock | Rendercode zurückrollen, SAC abschalten |
| Script wird abgewiesen | bereits erlaubte Shell/Eventviewer, genehmigte CI-/Testumgebung | ExecutionPolicy/Mark-of-the-Web automatisch ändern |
| Signatur Valid, Start trotzdem blockiert | konkrete EXE und Abhängigkeiten, reale Startdaten | Zertifikat als allgemeine SAC-Garantie behandeln |
| FSE-Anforderung nicht S_OK | Fokus, Output, lokale Sitzung, andere Exklusivapp, gespeichertes HRESULT | beliebig retryen oder auf Borderless-PASS wechseln |
| DXGI meldet TRUE, PM Independent Flip | FSO/Windows-/Treiberverhalten, neuer kontrollierter Run | GetFullscreenState als Wahrheit über Legacy verwenden |
| ResizeBuffers INVALID_CALL | RTV und alle Backbufferbindungen gelöst? ClearState? keine Zwischenreferenz? | neue Swapchain pro Frame erzeugen |
| Shaderbuild scheitert | installiertes SDK-FXC, Profil SM5, vollständiger Compilerlog | Dummyheader oder Runtime-Compiler als Schnellfix einbauen |
| CMake findet keinen Generator | vswhere-Instanz, CMake-Unterstützung für installierte VS-Version | zufällige VS-Jahreszahl hardcodieren |
| Frame-/Zeitzuordnung UNVERIFIED | Originalheaders, CPUStartQPC integer, QPC-Frequenz, MsCPUBusy, reale before/after-Werte | Guard/Toleranz bis zum PASS vergrößern |
| Observer endet früh | stderr, Rechte, Pinning, eigene ETW-Session | ungefragt Hauptapp als Admin starten |
| Observer meldet Warnung | vollständige Rohwarnung, ob Session tatsächlich vollständig | pauschal stderr löschen |
| Keine Marker | Warmup, F8/F9, Hotkeykonflikt; neuer Run | warmup-only Frames als Aufnahme ausgeben |
| Schwarzer Screenshot trotz FSE-PASS | Recorderbackend und tatsächliche Mediendatei | ETW-Befund als Capture-PASS umdeuten |
| Bild abgeschnitten | Output/Skalierung/Recordercrop/DPI, Eckmarker | unklare Offsetwerte fest in App schreiben |
| Device removed/reset | Present-HRESULT, DeviceRemovedReason, Treiber-/Displayereignis | mit alten Ressourcen still weiterzeichnen |
| Null-/unbekannter Exitcode | Prozesshandle und echte Beendigung | null als 0 interpretieren |
| Eventlog unlesbar | Rechte/Verfügbarkeit separat festhalten | „keine Ereignisse, also SAC-frei“ behaupten |

## Parserdiagnose in fester Reihenfolge

Zuerst `summary.reason`, dann `session.json`, `presentmon.stderr.txt`/stdout und `app.jsonl` lesen. Sind Version und Hash korrekt? Ist `runner_error` leer? Wurde der richtige Prozess wirklich gestartet? Stimmen PID, Erstellungszeit und Frequenz? Liegt ein vollständiges Markerintervall innerhalb des aktiven Abschnitts? Danach einzelne Present-Ledgerzeilen und passende CSV-Zeilen vergleichen. Niemals eine ganze beschädigte Akte durch Entfernen unbequemer Zeilen „reparieren“.

`UNVERIFIED_FRAME_GAP` bedeutet, dass der Datensatz den verlangten Nachweis nicht trägt; das muss nicht zwingend der Recorder verursacht haben. `FAIL_PRESENT_MODE_CHANGED` ist dagegen ein positiver Gegenbefund aus erfassten Frames. `UNVERIFIED_NO_TARGET_FRAMES` ist kein Beweis gegen FSE, sondern fehlende Zuordnung. Diese Unterschiede sind absichtlich maschinenlesbar.

## PowerShell 5.1 und Pfade

Scripts liegen UTF-8 **mit BOM und CRLF** vor; Repositorytext wird explizit als UTF-8 über .NET gelesen. Keine Lokalisierungsfehler aus ANSI-Decodierung als SAC behandeln. Die Prozesshelfer quoten Argumente nach Windows-Regeln und testen Leerzeichen, Quotes und abschließende Backslashes in CI. Falls ein Agent diese Hilfsfunktionen vereinfacht, die Quotingtests zwingend erneut ausführen.

Der Code verwendet `ReadToEndAsync` für beide Pipes und Heartbeats statt eines blockierenden `Tee-Object`-Pipelineschemas. Start/Ende haben harte Timeouts; ein Timeout ist kein Testerfolg. Nur eigene Prozesse/Trace-Session werden beendet. Es werden keine absichtlich gestarteten Kindprozessbäume erzeugt; eine zukünftige Erweiterung mit Kindern benötigt zusätzliche Job-Object-/Tree-Cleanup-Prüfung.

## Wiederholungsbudget

Ein reproduzierbarer Codefehler rechtfertigt einen gezielten Fix. Ein reproduzierbarer Policyblock rechtfertigt den Wechsel zur bereits vorgesehenen CI-/Testumgebung, nicht zwanzig neue Builds am Dev-PC. Der Runner wiederholt blockierte Starts nicht. Ein zweiter Lauf ist erst sinnvoll, wenn Ursache oder zulässige Umgebung tatsächlich verändert bzw. geklärt wurde.
