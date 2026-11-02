# GO-MASTER-AUFTRAG — FSEProbe vollständiger Pro-Implementierungsplan + Copy-ready Codepaket

**Trigger:** Die nächste Benutzeräußerung `go` im selben Gespräch bedeutet: diesen gesamten Auftrag sofort und ohne zusätzliche Rückfragen ausführen. Dies ist **der Auftrag für den nächsten Schritt**, nicht die Behauptung, dass der Code bereits existiert.
**Datum der Vorbereitung:** 2026-11-02. **Sprache:** Deutsch; Code-/Dateinamen konsistent Englisch.

## SAC-VORRANG — verbindlich, vor Abschnitt A lesen

**Neu priorisierte Nutzerbedingung:** Auf dem Entwicklungs-PC ist Smart App Control (SAC) problematisch und MUSS aktiv bleiben. Der Coding-Agent darf nicht voraussetzen, dass eine lokal erstellte, unsignierte EXE oder ein unbekanntes Hilfstool dort ausführbar ist. **`SAC_FIRST_ENTWICKLUNGSSTRATEGIE.md` ist gleichrangige Pflichtlektüre und hat bei dieser Frage Vorrang vor älteren Briefings.**

**Nicht verhandelbarer Default:** Entwicklung auf dem geschützten PC, Windows-MSVC-Build/Unit-Tests per GitHub Actions, FSE-Hardwaretests auf separatem physischem Windows-Testsystem oder separater Test-Windows-Installation. Alternativ gültig CA-signierte und auf SAC real gestartete Binaries, falls vorhanden. Keinerlei Änderung am Smart App Control des Dev-PCs, kein Policy-Bypass, keine selbstsignierte Scheinlösung, keine Vermischung „CI gebaut“ mit „SAC erlaubt“ oder „klassischer FSE beobachtet“.

**GO-Leistungsumfang zusätzlich:** Den geplanten vollständigen Code bereits so schreiben, dass Windows CI ihn unmittelbar kompilieren und testen kann, und alle notwendigen Dateien für den SAC-festen Workflow (CI-Workflow, Eventdiagnose, Signaturprüfung, Hardware-Abnahme, ausführbare Tickets) liefern. **Wenn keine SAC-verträgliche Testumgebung nachgewiesen ist, trotzdem Quelle und Build liefern, ausdrücklich `HARDWARE_NOT_EXECUTED`/`BLOCKED_BY_APP_CONTROL` statt FSE-PASS.**

## A. Mission und Erfolgskriterium

Fertige eine qualitativ hochwertige, durch Quellen überprüfte, **umfassende und konkrete Windows-Implementierungsvorlage** für einen schwächeren Coding-Agenten an. Ziel ist eine kleine, native x64-Anwendung `FSEProbe`, mit der ein vorhandenes Screenshot-/Videorecording-Tool reproduzierbar gegen *klassischen* Windows-Fullscreen-Exclusive-Betrieb getestet werden kann. Das Testbild zeigt klar erkennbare synthetische Spieldaten, animierte Grafiken, Framecounter und moderat anpassbare GPU-Last. Das Programm fordert `IDXGISwapChain::SetFullscreenState(TRUE, ...)` auf einer D3D11-Swapchain an. **Der angeforderte oder von DXGI gemeldete Fullscreen-Zustand ist niemals allein ein Beweis für klassischen FSE.** Verifiziere unabhängig über PresentMon/ETW die tatsächlichen `PresentMode`-Framewerte und ihren Zeitbereich. In `strict`-Szenarien gilt fail-closed.

Primärer Nutzen: Euer Recorder wird gezielt und wiederholbar getestet, ohne sich auf unbekannte Präsentationsmodi fremder Spiele verlassen zu müssen. Zweites Erfolgskriterium: Ein schwacher Coding-Agent muss ohne mehrtägiges Herumprobieren einen buildbaren, instrumentierten Basisstand erzeugen können.

**Fertig** ist der GO-Durchlauf erst, wenn außer Plänen **möglichst viel tatsächlich vorhandener, kompletter und direkt verwendbarer Quellcode** mitgeliefert wird; wo ein Windows-Build in der aktuellen Umgebung nicht möglich ist, muss das ehrlich markiert werden. Keine unrealistische Garantie der Fehlerfreiheit oder realer FSE-Verfügbarkeit auf jeder Windows-Maschine abgeben.

## B. Feste technische Entscheidungen — begrenzte Ausnahmen zulässig

1. Ziel: Windows 10/11 x64 mit lokalem, interaktivem Desktop und realem Monitor; keine RDP-/VM-/virtuelle Display-Sitzung als Beweis. Eine GTX-1080-Klasse muss grundsätzlich genügen; kein DX12-Zwang.
2. Rendering: C++20, Win32, D3D11, DXGI, HLSL, Windows SDK, CMake, MSVC. Kein Unity, Godot, Electron, SDL, Browser, DLL-Injection, Anti-Cheat-Hook oder GUI-Framework für den Kern. Modernes CMake, nur nötige Win32-Libraries. Wähle eine verständliche Architektur mit wenigen Dateien, nicht ein Overengineering-Framework.
3. Baseline-Modi: `legacy-exclusive` (explizite DXGI-Fullscreen-Anforderung + für diesen QA-Zweck bewusst DXGI_SWAP_EFFECT_DISCARD/Legacy-BLT), `borderless-control` (Fenster, Flip-Model `DXGI_SWAP_EFFECT_FLIP_DISCARD`, KEIN FSE-Aufruf). `flip-fullscreen` nur dann zusätzlich, wenn Quellen/Tests den Nutzen belegen und der Mehraufwand klein bleibt.
4. In der Anwendung ein einziges Hauptfenster mit ein und nur einem aktiven DXGI-Swapchain-Ziel; Text, HUD, Raster und GPU-Last in **derselben** D3D11-Renderpipeline; keine Desktop-/Topmost-Fremdoverlays, die den Präsentationspfad beeinflussen könnten.
5. Unabhängiger Beobachter: PresentMon Console Application als separat heruntergeladenes/konfiguriertes Tool; CLI-Parameter der **konkreten Releaseversion** nachprüfen. Nutze `--process_name` für einen Start *vor* der EXE, danach PID-basierte Filterung, oder verlässlich startbare PID-Filterung. Sichere eindeutige PID + Prozessstartzeit + SwapChainAddress im Report.
6. Für Zeitkorrelation bevorzugt PresentMon `--qpc_time` / `CPUStartQPC` und appseitig `QueryPerformanceCounter` plus `QueryPerformanceFrequency`. Beachte: `CPUStartQPC` referenziert Framebeginn, nicht zwingend den Present-Aufruf; verwende Guard-Bänder. Wenn die Version diesen Modus nicht liefert, baue eine geprüfte alternative Zeitachse. Niemals UTC, relative CSV-Zeit und QPC blind gleichsetzen.
7. `FSE_VERIFIED` nur bei belegten `Hardware: Legacy Flip` oder `Hardware: Legacy Copy to front buffer` für richtige Frames, PID, Swapchain und das relevante Zeitfenster; `Hardware: Independent Flip`, `Hardware Composed: Independent Flip`, `Composed: Flip` sind **kein** Beweis für klassisches Exclusive. Kennzeichne Übergänge und Grenzfälle.
8. **Live-Aussagen** nur nach Validierung der echten Live-Ausgabe-Latenz des verwendeten PresentMon-Builds (`--output_stdout`/SDK), inkl. E2E-Tests. Wenn nicht gesichert, nutze `NOT_LIVE_VERIFIED` in der aktiven Anwendung und erst nach Auswertung `FSE_VERIFIED`; biete keine irreführende Strict-Live-Modus-Anzeige. Wenn Live-Pfad verfügbar: einfacher Supervisor-/IPC-Mechanismus statt fremder Overlay-Injektion.
9. Definiere **unabhängige Resultate**: (a) DXGI-State, (b) ETW-PresentMode, (c) Recorder-Capture-Qualität. Ein gelungener ETW-Test bedeutet nicht automatisch, dass der Recorder richtig funktioniert.
10. GPU-Last über begrenzte HLSL-Shader-Stufen `off|low|medium|high`, FPS-Cap, standardmäßig VSync, Warmup und Timeout; keine endlosen Schleifen, keine Prozentversprechen. Keine permanente Änderung von GPU-/OS-/Display-Treiber-Einstellungen.
11. Keine Admin-Rechte für die Testspiel-EXE; wenn PresentMon/ETW Rechte benötigt, klar getrennt dokumentieren. `--restart_as_admin` niemals still oder zwangsweise aktivieren. **SAC-first:** unsignierte Build-Artefakte nicht auf dem Dev-PC starten; Code + Tests auf CI; reale Tests nur auf rechtmäßig ausführbarem Test-Windows oder mit vertrauenswürdig CA-signiertem Release. SAC nicht umgehen und nicht deaktivieren.
12. Sicherheits-/Rechteprinzip: Kein Recorder-Hooking, kein Download ungeprüfter Binaries, keine ungefragten Registry-Patches, kein Deaktivieren von Schutzfunktionen. Open-Source-Code nur bei nachgewiesener Lizenz/Dateiprovenienz übernehmen; quellenspezifische Notices beilegen.

**Entscheidungsregel für den Pro-Durchlauf:** Wenn eine Entscheidung unklar ist, recherchiere sie, wähle **eine** bevorzugte, für schwache Coding-Modelle robuste Variante, dokumentiere die Alternative kurz. Keine große Optionsmatrix, die zentrale Entscheidungen dem kleinen Agenten überlässt.

## C. GO-Lieferobjekte, als reale Dateien zu erstellen

Liefere nach Möglichkeit ein fertig gepacktes ZIP `FSEProbe_IMPLEMENTATION_KIT_<Datum>.zip`, dessen Dateien du tatsächlich erzeugst, überprüfst und verlinkst. Falls die aktuelle Umgebung keinen Windows-Compiler bietet: trotzdem vollständige Quellen und Parser-Tests, aber klar `WINDOWS_BUILD_NOT_EXECUTED` markieren. Kein behaupteter Hardware-PASS.

### Dokumente

1. `00_START_HERE.md`: 5-Minuten-Startanleitung, Voraussetzungen, Installation, Build, Test-Run, Auswertung; Windows-`Developer PowerShell`/MSVC/Windows SDK/CMake/Python/PresentMon genau nennen.
2. `01_FULL_IMPLEMENTATION_PLAN.md`: vollständige technische Begründung, Architektur, API-Sequenz, Datenflüsse, Zustandsmaschine, Zeitachse, Exit-/Fehlerverhalten, Windows 10/11 Fallstricke, Grenzen und konkrete Entscheidungen. Mehr Tiefe als das ursprüngliche Briefing, **keine leeren Kapitel**.
3. `02_API_CALL_SEQUENCE.md`: Schritt-für-Schritt WIN32/DXGI/D3D11: GPU-/Output-Auswahl, DPI/Koordinaten, Fenster/Focus, Device/Swapchain initial windowed, `MakeWindowAssociation`/Alt+Enter, SwapEffect, SetFullscreenState, Target/ResizeBuffers, WndProc/WM_SIZE, RTV, shaders, Present, Cleanup, DeviceRemoved, Restores, Alt-Tab. API-Namen/Parameter/Fehlercodes exakt verifizieren. Ehrliche Kompatibilitätstabelle.
4. `03_PRESENTMON_AND_CLASSIFIER.md`: verifizierte CLI und Header, CSV-Schema, Prozess-/Swapchain-Filter, QPC-Zeitfenster, Warnungen, Regeln und JSON-Schema. Erläutere, welche ETW-Klassifikation welchen Nachweis erlaubt und was nicht.
5. `04_OPERATOR_TEST_MANUAL.md`: explizite Schrittfolge für Screenshot- und Videoaufnahme, Testfenster-Markierungen, FSO an/aus per Windows-UI, Recorder-Eingriff, Alt-Tab, Remote-Session, Multi-Monitor, Format/Crop, Testbelege, Recovery-Anleitung bei schwarzem Bildschirm. Beleg-/Screenshotnamen, Ergebnisvorlage.
6. `05_WEAK_AGENT_EXECUTION_RUNBOOK.md`: **kopierfertige einzelne Agenten-Tickets**, in kleinsten unabhängigen Phasen, je mit Dateien, Reihenfolge, Eingabe, erwarteter Ausgabe, Build/Test-Gate, Selbstcheck, Rückfall, Stop-Regel; keine eigenständige Architekturentscheidung des Agenten nötig.
7. `06_RESEARCH_SOURCES_LICENSES.md`: Primärquellen Microsoft, Intel PresentMon, ggf. Toolkit, Versionen, Lizenzlage, Fundstellen/Datum, Third-Party-Lizenzpflichten, Unsicherheiten. Repositories nie anhand bloßer GitHub-Sichtbarkeit als lizenzfrei behaupten.
8. `07_TEST_MATRIX_AND_RELEASE_CHECKLIST.md`: automatisierbare Fälle vs nur auf realer Windows-GPU ausführbare Fälle, Negativtests und Abnahmekriterien, mindestens zwei saubere Review-Durchläufe soweit technisch möglich.
9. `08_TROUBLESHOOTING.md`: konkrete Fehlerdiagnose für fehlenden FSE-Nachweis, FSO, WndProc, WM_SIZE/ResizeBuffers, HDMI/Monitorauswahl, ETW-Rechte, PresentMon-Versionswechsel, Smart App Control, Shader Compile, PowerShell execution policy, GPU device removed, Recorder-Overlay, beschädigte CSV.
10. `09_ASSUMPTIONS_AND_TEST_EVIDENCE.md`: alle nicht verifizierten Behauptungen, tatsächlich gelaufene Tests und exakte Einschränkungen; keine fingierten Logs.
11. `10_SAC_FIRST_DEV_AND_TEST.md`: **vollständige SAC-Kompatibilitätsstrategie** anhand der beiliegenden Pflichtdatei. Exakte CI-Befehle und Ausweichrouten, ohne Dev-PC-SAC umzuschalten; physische Hardware-Windows-Testalternative; CA-Codesignatur optional und länder-/identitätsabhängig; `citool.exe -lp`/CodeIntegrity Event 3077, Read-only-Befehle, Signaturstatus, Klassifikation `BLOCKED_BY_APP_CONTROL`, Sicherheitsgrenzen.
12. `11_CI_AND_TEST_LAB.md`: GitHub Actions x64-MSVC-Workflow, Artefakte, Logs, SHA256, Sicherheitsberechtigungen, Kosten-/Quota-Bewusstsein, CI-vs.-Hardware-Grenzen, ausführbare Anweisungen für separates Test-Windows auf derselben physischen GPU *ohne* automatische Installations-/Bootänderungen.

### Buildbares Minimalprojekt — Copy-ready statt Pseudocode

```
FSEProbe/
  CMakeLists.txt
  CMakePresets.json             # nur wenn mit verifiziertem lokalen Generator sinnvoll
  README.md
  .gitignore
  src/
    main.cpp                   # CLI, Message-Loop, Lifecycle
    graphics.h/.cpp           # D3D11/DXGI/Swapchains/Fullscreen
    diagnostic.h/.cpp         # HRESULT/QPC/JSONL/Snapshot
    scene.h/.cpp              # raster, corners, moving sprites, counters
    shaders.hlsl              # GPU-Last und Farbwechsel, einfach zu bauen
    tiny_font.h               # kleiner permissiver Bitmapfont ODER eigenständig
  tools/
    run_test.ps1              # orchestriert PresentMon und FSEProbe
    verify_presentmon.py     # parser, report, harte Fail-Closed Regeln
    inspect_environment.ps1  # READ-ONLY Build/Windows/ETW-Checks
    inspect_sac_environment.ps1 # READ-ONLY; CI blocks 3077, signature, citool, no settings changes
    package_release.ps1      # ZIP/manifest, falls sinnvoll
  tests/
    test_presentmon_parser.py
    fixtures/*.csv           # positive/negative/schlechte Realformat-Fälle
    test_protocol.py         # JSONL/Schema, wenn hilfreich
  docs/
    ...                      # sämtliche oben genannten Dokumente
  .github/workflows/windows-ci.yml # Windows-MSVC CI ohne Hardware-FSE-Behauptung
  licenses/
    ...                      # NUR tatsächlich verwendete Drittkomponenten
```

Dateiennamen/Dateien darfst du für echte Simplifikation optimieren, aber **keinen** essentiellen Inhalt weglassen. Einzelne vollständige Dateien dürfen nicht mit `TODO`, `...`, `implement yourself`, `omitted for brevity` oder unerklärten Platzhaltern abgebrochen werden. Baue nach Möglichkeit ein kleines Projekt ohne zusätzliche Runtime-DLLs; falls MSVC CRT-Abhängigkeiten vorhanden sind, lege sie offen. Render-Schrift darf nicht über GDI *auf* den aktiven DXGI-Backbuffer gezeichnet werden. Ein in HLSL/CPU vorbereiteter kleiner Pixel- oder Text-Renderer reicht.

### Kopierfertige Bedienung

- Eindeutiger Startbefehl und Build/Start-Sequenz (PowerShell), ohne auf einer fremden Maschine Pfade zu erfinden.
- Beispiele für `legacy-exclusive`, `borderless-control`, GPU-Stufe, Monitor-Auswahl, 30–60-Sekunden-Capture, Log-Verzeichnis, Exit-Codes.
- Nicht interaktiver `--help`, `--version`, `--self-test` (wenn sinnvoll); Diagnose ohne D3D für nicht unterstützte Umgebungen.
- `tools/run_test.ps1` prüft Abhängigkeiten/Exitcodes, startet **PresentMon vor** dem definierten Testzeitfenster, verhindert PID-Kollision und wertet nach Beendigung aus. Bei fehlendem PM/Berechtigungen kein Erfolg.
- UX: Vollbild-Spiel mit Run-ID, gut lesbarer bewegter Scene und Status `REQUESTED | DXGI_ACTIVE | FSE_UNVERIFIED | FSE_VERIFIED` **nur wenn entsprechende Live-Daten tatsächlich ankommen**. Für den Standard-Post-Run-Modus im Spiel ausdrücklich `PRESENTATION NOT YET INDEPENDENTLY VERIFIED`.
- Ein strukturierter Ergebnisbericht `summary.json` und menschlich lesbares `summary.txt` mit eindeutigen separaten Aussagen zu DXGI/ETW/Recorder.

## D. Mess- und Resultatvertrag — unbedingt technisch lösen

1. Starte eine einzige klar identifizierbare EXE, notiere PID, Startzeit und App-Version; keine zwei aktiven Testinstanzen gleichzeitig (z. B. benanntes Mutex; angemessen berechtigter Namespace).
2. Für Record-Zeiten: `app.jsonl` schreibt QPC-Frequenz/Ticks und UTC bei START, DXGI-Änderungen, MODE_READY, CAPTURE_MARK_START, CAPTURE_MARK_END, LOST_FOCUS, PRESENT_ERROR, END. Capture-Marker müssen als **operator-markiert** benannt werden, wenn die Recorder-API keinen echten Start/Stop liefert. Keine exakte Recorder-Zeit behaupten, die nicht gemessen wurde.
3. Verwende die echte PresentMon-Spalte `CPUStartQPC` bei `--qpc_time` und die als Integer geloggten Windows-QPC-Ticks; dokumentiere die CPU-Framebeginn-vs.-Present-Semantik, notwendige Sicherheitsabstände und Auflösung. Wenn die Zeitachse nicht sicher vereinbar ist: `UNVERIFIED_TIME_AXIS`.
4. `ProcessID` und `SwapChainAddress` aus CSV filtern; wenn Adressen bei legitimer Resize wechseln, Segmentierung erklären; bei Mehrdeutigkeit verifizieren **nicht** pauschal alle Frames eines Prozesses. `PresentRuntime`, `PresentMode`, optional weitere Originalspalten als Evidence sichern.
5. Standardklassifikation: `Hardware: Legacy Flip` und `Hardware: Legacy Copy to front buffer` = starke Legacy-/Screen-Ownership-Signale. `Hardware: Independent Flip`, `Hardware Composed: Independent Flip`, `Composed: Flip` u. a. = kein klassischer FSE-Beweis. **Nicht** `PresentMode` mit DXGI-Flag verwechseln.
6. Preflight/Warm-up und Aufnahmefenster **getrennt** auswerten. Weder ein einzelner alter Legacy-Frame noch 30 ausschließlich außerhalb der Aufnahme gemessene Frames beweisen FSE **während** des Recordings. Bei unterschiedlichen beobachteten Modi im relevanten Zeitraum `FAIL_PRESENT_MODE_CHANGED` oder dokumentiert abweichender Modus, nicht PASS. Fehlende Daten => UNVERIFIED.
7. Default für gewollten FSE-Nachweis: mindestens 2 Sekunden verwertbare Frames und mindestens 30 nachgewiesene Legacy-Präsentationen im stabilen Prüfbereich **sowie** keine andersartigen erfassten Frames im ganzen einschlägigen, gut zeitlich zugeordneten Capture-Bereich. Ausnahmen auf langsamen Geräten bedeuten längeren Test, **nicht** stilles Absenken.
8. Testergebnis als **3 Achsen**: `dxgi_state`, `presentation_proof`, `recorder_result`. Wer kein Video/Screenshot bewertet hat, schreibt `recorder_result=NOT_EVALUATED`.
9. Bei fehlendem PM, CSV-Datei, benötigten Headerspalten, gutem Zeitanker oder falsch zugeordneten PID immer `UNVERIFIED` (oder klares FAIL bei nachgewiesener Falschklassifikation). Exitcode dokumentieren und automatisierbar machen.
10. `--require-verified` im laufenden Programm nur dann anbieten, wenn unabhängiges Live-Feedback technisch und tatsächlich getestet ist; sonst explizit als **nicht unterstützt** dokumentieren und keine FSE-Garantie vortäuschen. Kompakter Post-Run-Modus bleibt gültige Basis.

## E. Schwach-Agent-Strategie: 7 kleine, streng geprüfte Bauschritte

**Schritt 0 — SAC/GitHub CI FIRST:** Finde bzw. erstelle eine **vollständig read-only** SAC-Diagnostik; setze `.github/workflows/windows-ci.yml` so auf, dass Windows-MSVC-CMake-Build, Parser-/Protocoltests, Packaging und Checks unabhängig vom lokalen SAC-PC laufen. Keine lokale Ausführung einer selbst kompilierten unsignierten EXE voraussetzen. Ein möglicherweise notwendiger Signierschritt ist *optional*, nie eine eingebettete Fake-Signatur. Solange CI nicht grün ist, keine Hardware-Abnahme. Debugger-Sonderpfade, WDAC-Registry-Hacks, Defender-Ausnahmen oder PowerShell-Policy-Bypässe sind keine akzeptierten Abkürzungen.

**Schritt 1 — Toolchain + triviales D3D11:** Generiere voll funktionsfähigen Windowed-Build und klare Buildbefehle; erst weiter, wenn durch Windows-Build nachgewiesen, sonst `UNEXECUTED`.
**Schritt 2 — Legacy-Exclusive + Kontrollmodus:** Korrekte DXGI-Transitions, WM_SIZE, Alt-Tab, Device-Removed, Sicherheits-Cleanup. Kein UI-Polish vor stabiler Swapchain.
**Schritt 3 — gut erkennbares Testbild + GPU-Last:** wenige selbstgeschriebene Shader + Bitmapfont; kleine gerenderte Fake-Game-Daten; FPS/Frame-ID/Corners.
**Schritt 4 — ETW/PresentMon + Parser:** exakte Version+CLI; robuste Python-Standardbibliothek, QPC, CSV-Validierung, negativer Parser-Testsatz; kein PASS ohne ETW.
**Schritt 5 — Ein-Klick-Runner + Bericht:** PSDiagnostics, PID-Filter, QPC-Logs, Beispielausgaben, Safe-Cleanup, Exitcodes, Anleitung für das Recording-Tool.
**Schritt 6 — QA + Release:** Windows-Build/testen wenn ausführbar, Parsing-Unit-Tests, mindestens zwei Änderungsprüfrunden hintereinander soweit durchführbar, vollständiger Paketinhalt, Lizenznotizen und reproduzierbare Anleitung.

**Die erste Agenten-Ticketgruppe MUSS SAC/CI behandeln**, damit alle späteren Aufgaben unabhängig von lokal blockierten EXEs erledigbar sind. **Jedes Agenten-Ticket** muss enthalten: Eingabedateien, exakt erlaubte Änderungen, einen Mini-Test, ein Stop-on-error-Kriterium, eine einfache Selbstkontrolle und das Ausgabeformat. Keine parallele Entwicklung mehrerer empfindlicher DXGI-Komponenten durch den schwächeren Agenten. Erst die stabilen Kernfiles, dann Auswertung.

## F. Umfassende Pflicht-Testmatrix

Verwende `ABNAHME_MATRIX.csv`, erweitere sie nach Bedarf. Muss umfassen:

- Alle relevanten DXGI-Rückgaben, falscher Monitor, unsupported GPU, mehrere Monitore, HiDPI, Auflösung/Refresh-Mismatch, Overlay, Alt+Tab, Desktop-Wechsel, ESC/Timeout, DeviceRemoved, RDP/VM, FSO und Windows-11-Windowed-Optimizations.
- Positive PresentMon-Legacy-Frames, negative Independent Flip, Hardware Composed, Composed Flip; gemischte Frames, einzelner Fremdframe, leer, fehlende Spalte, falsche PID/Swapchain, verspätet gestarter Trace, QPC fehlend/ungültig, DateTime-Mismatch, BOM/UTF8/Spaltenreihenfolge, zwei App-Instanzen, CSV-Zeilenkorruption.
- Screenshot/Video: Eckmarker, Textskala, Skalierung/Crop, Frame-ID/Sequenz, Dunkelbild, alt-tab interruption, Videostart/ende, Framedrops; Ergebnisse von Recorder-Funktion und FSE-Nachweis getrennt.
- Sicherheit: keine unkontrollierten Display-/Registry-Persistenzänderungen; Cleanup nach Error; kein stummes Admin-UAC; keine Fremd-EXE ohne Checks; Smart App Control wird diagnostiziert, nicht umgangen.
- SAC: Signaturstatus self-signed / vertrauenswürdig CA-signed / unsigned, CodeIntegrity 3077, CI-Build != SAC-Vertrauen, fehlender physischer Test, keine externe Testumgebung, Read-only Diagnose fehlt, PowerShell-Skript vom Policy-Block betroffen, Test ohne SAC-Änderungen möglich; **Release-Blocker bei falschen „SAC-kompatibel“-/„FSE-getestet“-Behauptungen**.
- CI-/Lab-Routen: Windows MSVC x64-Build, negative Parser-Tests, SHA256-Buildartefakt, Unterschriften-/Herkunftsevidenz, Hardwaretest auf zweiter Windows-Installation/eigenem Test-PC, getrennte Reports `ci_build_status` und `hardware_fse_validation`.
- Unit-Tests sollen auf beliebigem Standard-Python laufen können. Windows-Hardwaretests als manuelle Pflicht kennzeichnen, nicht als CI-PASS ausgeben.

## G. Quellen und Rechtsprüfung

Vor dem Schreiben der endgültigen Antwort erneute Webrecherche in offiziellen Quellen; überprüfe vor allem:

- Microsoft `IDXGISwapChain::SetFullscreenState` und `GetFullscreenState`, `ResizeBuffers`, `ResizeTarget`, DXGI Best Practices, `MakeWindowAssociation`.
- Microsoft's FSO-Dokumentation und `DXGI_SWAP_EFFECT`/DX11 vs DX12-Semantik; beide Windows-11-Optimierungstypen nicht verwechseln.
- Intel PresentMon **aktuelle Releaseversion und Console-CLI** inklusive `--process_name`, `--process_id`, `--output_file`, `--qpc_time`, `--output_stdout`, `--timed`, `--terminate_after_timed`, PresentMode-Labels, Lizenz und Third-Party-Notices.
- Microsoft `Smart App Control`, CodeIntegrity und Code Signing **höchst prioritär**: SAC-Enforcement, Event ID 3077, `citool.exe -lp`, vertrauenswürdig CA-signierte Exe, kein per-Datei-Allowlisting; aktuelle FAQ zu erneutem Einschalten auf manchen Windows-Builds; Signaturzertifikate/Artifact-Signing-Berechtigung für EU-Organisation vs. deutsche Privatperson, Kosten und rechtliche Randbedingungen. Verfasse keine Abschalt-Anleitung für den Dev-PC.
- GitHub Actions `windows-2025` Runner, MSVC-Generator und die konkrete Windows-Image-Toolchain; Workflows mit eingeschränkten Berechtigungen. CI ist keine FSE-Hardwareabnahme.
- Falls fremder Code verwendet: **genauer Commit/Dateipfad/Lizenz/Attribution**, keine ungeprüften Copy-Paste-Snippets aus Foren. Nutze bevorzugt originale selbstgeschriebene kleine Komponenten.

Erläutere Besonderheit: `DXGI_SWAP_EFFECT_DISCARD` ist für den Legacy-Test bewusst gewählt, aber **nicht** die moderne, generell empfohlene App-Architektur; die Borderless-Kontrolle nutzt Flip-Model.

## H. Qualitätssicherung und finaler Lieferstandard

- Zuerst APIs und Annahmen auditieren, dann Daten- und Fehlervertrag festlegen, dann Code erzeugen, dann Tests. **Nicht** mit hübschen UI-Bildern anfangen.
- Keine ausgelassenen Teile des geforderten Codes, keine Pseudo-EXE oder erfundenen build logs. Wenn ein C++-Build vor Ort nicht ausführbar ist, deklariere präzise `NOT_COMPILED_HERE` und liefere trotzdem die durchdachteste vollständige Quellcodevorlage.
- Sämtliche .md/.py/.ps1/.cpp/.h/.hlsl/.json/.csv-Dateien müssen in einem tatsächlichen ZIP sein. Das ZIP mit `zipfile.testzip`, Textencoding, Dateipfaden, Symlink-/Path-Traversal-Prüfung und SHA-256-MANIFEST überprüfen. Testdateien im Paket ausdrücklich mitzählen.
- Für Parser/Python-Tests: tatsächliche Ausführung mit vollständigen Results, nicht erfunden. CMake/Compiler nur behaupten, wenn wirklich vorhanden.
- **Review 1:** Fehler/API-Semantik, Build-/Run-Konsistenz, Status-Klassifikation, Zeitzonen-/QPC-Logik, Fehlermeldungen, Lizenz/Links.
- **Review 2:** unabhängiger Negativtest (nach Fehlerkorrekturen erneut), Dateiintegrität, keine falschen PASSs, README-Befehle deckungsgleich mit echtem Code.
- Bei gefundenen Änderungen nach Review 2 erneut überprüfen, bis (soweit praktisch möglich) zwei aufeinanderfolgende prüfbare Durchläufe ohne neue Änderungen abgeschlossen sind. Nicht behaupten, dass das eine Garantie der Fehlerfreiheit wäre.
- Abschließende Zusammenfassung: erzeugte Dateien, Umfang, tatsächlich bestandene Tests, notwendige letzte Hardware-Prüfschritte, Limitierungen, Downloadlink zu einem **existierenden** ZIP und optional einzelne Hauptdokumente.
- Keine unnötigen Rückfragen; übernehme sinnvolle Defaults. Falls der Durchlauf an Grenzen stößt, **so viel brauchbaren Code und Tests wie möglich liefern**, Lücken transparent markieren statt Ergebnisse zu erfinden.

## I. Akzeptanz-Hauptregeln (Release Blocker)

**Release Blocker 1:** `FSE_VERIFIED` aus `SetFullscreenState`, Fenstergröße oder `GetFullscreenState` ohne ETW.
**Release Blocker 2:** `FSE_VERIFIED` bei nur `Hardware: Independent Flip` oder `Composed: Flip`.
**Release Blocker 3:** CSV-Parser akzeptiert falsche PID oder Frames außerhalb des Capture-Fensters.
**Release Blocker 4:** Live-FSE-Status ohne verifizierte Live-Quelle.
**Release Blocker 5:** Replay ohne QPC/identifizierbaren Frame-Zeitbezug behauptet FSE während Recording.
**Release Blocker 6:** Kein sicherer Desktop-/Fullscreen-Cleanup auf ESC/normalen Fehlern; Crash-Recovery muss dokumentiert sein, nicht garantiert.
**Release Blocker 7:** Keine Negativtests/kein Parser-Test, keine Fehler-/Exit-Codes, kein aussagefähiger human-readable Report.
**Release Blocker 8:** Fremdcode ohne Lizenzprüfung oder nicht überprüfbare Tool-/Versionsangaben.
**Release Blocker 9:** Unkompilierter Quellcode oder ungetestete Hardware wird als getestet ausgegeben.
**Release Blocker 10:** Der schwächere Agent muss erst Architektur erfinden, weil nur ein Konzept statt vollständiger Projektdateien geliefert wurde.
**Release Blocker 11:** Der Workflow erfordert zum Bauen, Offline-Testen oder Weiterentwickeln, dass auf dem SAC-Dev-PC unbekannte/unsignierte Binaries ausgeführt oder Schutzfunktionen deaktiviert werden.
**Release Blocker 12:** CI-gebautes unsigned Artefakt wird als SAC-freigegeben oder als Hardware-FSE-validiert ausgewiesen.
**Release Blocker 13:** Der Agent schlägt vor, Schutzmechanismen zu umgehen (Registry, WDAC-Policy, bekannte Hosts/Pseudo-Signaturen), statt CI/Test-Lab/trusted Signing zu nutzen.
**Release Blocker 14:** Kein operativ umsetzbarer, schriftlicher Plan für echte GPU-/Monitor-Hardwaretests trotz aktivem SAC, inklusive getrenntem Status bei Testblockade.

## J. Startsignal

Wenn die unmittelbar folgende Benutzerantwort nur `go` lautet: Nutze dieses Dokument **vollständig**, berücksichtige `SAC_FIRST_ENTWICKLUNGSSTRATEGIE.md` **zuerst**, anschließend das ursprüngliche Briefing und den Quellenaudit. Erstelle im selben Antwortdurchlauf den vollständigen Plan plus maximal sinnvoll vollständige Dateien und Tests, final ein überprüftes ZIP. Das ist ein neuer **sofortiger** Arbeitsauftrag, kein Hintergrundprozess. Vorliegender Text allein ist nur die GO-Vorbereitung.
