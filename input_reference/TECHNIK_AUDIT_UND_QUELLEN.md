# FSEProbe – Vorabrecherche, Korrekturen und technische Risikoanalyse

**Stand:** 2026-11-02. Alle Links sind Ausgangspunkte; die Versionen und APIs im eigentlichen GO-Durchlauf erneut prüfen.

## 1. Die acht wichtigsten technischen Erkenntnisse

### 1. DXGI-API-Rückmeldung ist nicht das PresentMode-Orakel

Microsoft erklärt: Fullscreen Optimizations (FSO) kann im Hintergrund eine FSE-Anforderung als Borderless-/optimierten Pfad ausführen, während die App weiterhin exklusiven Vollbildbetrieb annimmt. Folglich heißt `SetFullscreenState(TRUE)==S_OK` / `GetFullscreenState(TRUE)` *nur*, dass DXGI den anwendungssichtbaren Vollbildzustand meldet. Die konkrete PresentMode-Klasse muss separat beobachtet werden.

Offizielle Quelle: https://devblogs.microsoft.com/directx/demystifying-full-screen-optimizations/
API: https://learn.microsoft.com/en-us/windows/win32/api/dxgi/nf-dxgi-idxgiswapchain-setfullscreenstate

**Korrektur/Verschärfung zum Originalbriefing:** Ein vermeintlich „immer exklusiv und live bestätigt laufendes“ Spiel ist bei FSO und ohne validierten Live-ETW-Feed technisch nicht garantiert. Nur Statusmeldungen mit passender Beweislage anbieten.

### 2. PresentMon unterscheidet die relevanten Präsentationsmodi frameweise

Dokumentierte CSV-Spalten u. a. `ProcessID`, `SwapChainAddress`, `PresentRuntime`, `PresentMode`, optional `CPUStartQPC` mit `--qpc_time`; CLI unterstützt `--process_name`, `--process_id`, `--output_file`, `--output_stdout`, `--timed` und weitere Optionen. `Hardware: Legacy Flip` sowie `Hardware: Legacy Copy to front buffer` bedeuten laut PresentMon, dass die App Besitz am Bildschirm hat; `Hardware: Independent Flip` bedeutet ausdrücklich **keinen** exklusiven Bildschirmbesitz. Das sind starke, framebezogene Signale, kein absolutes Hardwarebeweis-Zertifikat unabhängig vom restlichen Systemzustand.

Konsole + Modus-Tabelle: https://github.com/GameTechDev/PresentMon/blob/main/README-ConsoleApplication.md
CLI-Implementierung: https://github.com/GameTechDev/PresentMon/blob/main/PresentMon/CommandLine.cpp

**Stolperfalle:** Vor dem finalen Plan prüfen, ob die **benutzte EXE** die dokumentierten CLI-Flags unterstützt, ob CSV-Version V1 oder V2 ist und ob stdout rechtzeitig zeilenweise flush-t. `--output_stdout` allein beweist KEINE niedrige Latenz. `--output_file` und `--output_stdout` sind laut aktuellem CLI-Parser konkurrierende Ausgabevarianten, also nicht gedankenlos gleichzeitig nutzen.

### 3. PresentMon-Version 2.6.0 ist neuer als das Beispiel im ursprünglichen Briefing

Am 2026-11-02 führt GitHub **v2.6.0** als Latest (Release 2026-09-21); Intels offizielle Produktseite listet ebenfalls 2.6.0. Das ursprüngliche Briefing nennt v2.3.1 nur als Beispiel für einen älteren Konsolen-Binarynamen. Version und Artefakt deshalb im GO-Durchlauf **aktiv pinnen und tatsächliche EXE `--help` verifizieren**, nicht Namen erfinden.

https://github.com/GameTechDev/PresentMon/releases
https://game.intel.com/de/intel-presentmon/

**Vorsicht:** Der 2.6.0-Release nennt die neue `presentmon-cli`-Umgebung und Änderungen am Dienst sowie neue Display-Metadaten. Nicht unterstellen, dass UI, SDK, Console-App und CLI identisch verteilt werden, identische Parameter besitzen oder dieselben Berechtigungen brauchen. Für das Ziel zunächst die dokumentierte *standalone console application* auswählen und ihre konkrete Binary prüfen.

### 4. Für CPU/GPU-/CSV-Zeitkorrelation ist QPC am robustesten

`--qpc_time` dokumentiert `CPUStartQPC` als Performance-Counterwert. Für synchronen Vergleich mit `QueryPerformanceCounter` der Spiel-EXE dieselbe QPC-Tickachse verwenden. `QueryPerformanceFrequency` loggen, Tickwerte als 64-Bit Integer unverändert ausgeben. CPUStartQPC ist der Frame-**Start**-Zeitpunkt, nicht zwangsläufig der Zeitpunkt des Scanout oder Present. Einen Sicherheitsabstand rund um Marker/Transitions verwenden. Keine textuelle lokale DateTime ohne belegte Zeitzone als präzise Synchronisierung verkaufen.

CLI-Dokumentation: https://github.com/GameTechDev/PresentMon/blob/main/README-ConsoleApplication.md
QPC Microsoft: https://learn.microsoft.com/en-us/windows/win32/api/profileapi/nf-profileapi-queryperformancecounter

**Besonders wichtig:** Manuell gesetzter Capture-Marker ist kein automatisch aus dem fremden Recording-Tool gemessener Aufnahmebeginn. Marker als `USER_MARKED_...` bezeichnen, es sei denn es gibt eine echte Recorder-API.

### 5. Die Renderpfade müssen bewusst verschieden sein

Microsoft empfiehlt für moderne Programme Flip-Model-Swapchains; `DXGI_SWAP_EFFECT_DISCARD` ist legacy. Für den Sonderfall „klassisches DXGI-Exclusive“ ist ein Legacy/Blt-Testpfad jedoch bewusst nützlich. Für die Borderless-Kontrolle sollte `DXGI_SWAP_EFFECT_FLIP_DISCARD` benutzt werden. DXGI-Flip-Model erfordert mindestens zwei Buffer, Nachbehandlung von Backbuffer-Bindung und `ResizeBuffers` nach Fullscreen-Transitions.

https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/for-best-performance--use-dxgi-flip-model
https://learn.microsoft.com/en-us/windows/win32/api/dxgi/ne-dxgi-dxgi_swap_effect
https://learn.microsoft.com/en-us/windows/win32/direct3darticles/dxgi-best-practices

**Stolperfallen:** `ResizeBuffers` darf keine noch gebundenen Backbuffer-Referenzen halten; RTV vorher lösen und danach neu erstellen. Bildschirmauflösung/Refresh nicht auf 60.000 Hz hartcodieren; 59.94 Hz und DXGI-Moduswechsel beachten. `D3D11CreateDeviceAndSwapChain` im Legacy-Modus kann einfacher sein; für Flip-Borderless kann `IDXGIFactory2::CreateSwapChainForHwnd` geeigneter sein. Der Pro-Durchlauf soll **genau einen** jeweils validen, minimalen Weg festlegen. Fenster-Styles DXGI nicht mitten in einer automatischen Transition kaputt konfigurieren.

### 6. FSE-Transitionen dürfen scheitern, ohne dass die Anwendung abstürzt

Microsoft nennt `DXGI_ERROR_NOT_CURRENTLY_AVAILABLE`, etwa ohne Fokus, bei Occlusion, Terminal Server oder konkurrierendem Fullscreen. Bei Transitionen `DXGI_STATUS_MODE_CHANGE_IN_PROGRESS`. Mode-Switch kann von Windows selbst rückgängig gemacht werden. Vor dem Freigeben der Swapchain `SetFullscreenState(FALSE,nullptr)` versuchen, Ressourcen sicher freigeben, Ergebnisse loggen; harte Prozessabstürze können dennoch nicht durch normales Cleanup garantiert abgefangen werden. Ein Black-Screen-Recovery-Verfahren für den Operator gehört in die Anleitung.

https://learn.microsoft.com/en-us/windows/win32/api/dxgi/nf-dxgi-idxgiswapchain-setfullscreenstate
https://learn.microsoft.com/en-us/windows/win32/api/dxgi/nf-dxgi-idxgifactory-makewindowassociation

**Weitere Stolperfalle:** DXGI kann Alt+Enter selbst behandeln. Ein explizites `MakeWindowAssociation`-Flag ist zu prüfen, um unbeabsichtigte Wechsel zu verhindern; dokumentierte kontrollierte Test-Tastaturbefehle vorsehen.

### 7. Smart App Control ist eine **Architekturvorgabe**, kein DXGI-Bug

**Neu 2026-11-02 verifiziert:** Unbekannte, unsignierte EXEs werden in SAC-Enforcement häufig blockiert. Es gibt laut Microsoft keine per-Datei-Ausnahme. Ein self-signed Zertifikat löst die Anforderung einer im Trusted Root Program anerkannten CA nicht. Ein GitHub-Actions-Build wird dadurch nicht automatisch vertrauenswürdig. `citool.exe -lp` zeigt relevante Richtlinien, `CodeIntegrity/Operational` protokolliert Blockevents (ID 3077, Audit 3076). Ein Policy-Block darf weder als Fehler des DXGI-Codes noch als behobene Blockade durch Erzeugen einer Release-ZIP interpretiert werden.

**Designkorrektur:** Der Dev-PC wird als **SAC-geschütztes Authoring-System** betrachtet; Windows-Kompilierung/Unit-Tests über GitHub Actions, echtes FSE auf separater **physischer** Windows-Testumgebung (alternativer eigener Windows-Boot auf zweiter SSD oder anderer PC). Ein CA-signiertes Release für die Ausführung im SAC-OS bleibt ein Optionalpfad. Die Microsoft-Dokumentation nennt für Azure Artifact Signing derzeit **EU-Organisationen, aber keine Einzelpersonen in Deutschland** als Berechtigte. Kein unbedingtes „günstig signieren“-Versprechen.

Offizielle Quellen:
https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/overview
https://support.microsoft.com/de-de/windows/security/threat-malware-protection/smart-app-control-frequently-asked-questions
https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/test-your-app-with-smart-app-control
https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/code-signing-for-smart-app-control
https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options

**Quellenwiderspruch/-alterung:** Neuere Microsoft FAQ nennt unter aktualisierten Windows-Versionen SAC-Reaktivierung ohne Neuinstallation, während einzelne Microsoft-Learn-Testseiten den älteren Einweg-Wechsel weiterhin beschreiben. **Für uns irrelevant:** Das Design ändert die SAC-Policy nicht. Die nicht-desktruktive Vorabprüfung ist in `SAC_FIRST_ENTWICKLUNGSSTRATEGIE.md` detailliert.

### 8. Windows CI ist nicht die physische Abnahme

Microsofts `actions/runner-images` dokumentiert Windows 2025 mit MSVC/CMake/Windows SDK. Eine CI-Umgebung kann Windows-C++ bauen, Parser testen und Artefakte erzeugen, aber ihr Displaypfad ist **kein Beleg für FSE auf dem benutzten Monitor/GPU**. Deshalb sind `CI_BUILD_PASS`, `SAC_ALLOWED`, `HARDWARE_FSE_VERIFIED` getrennte Resultate, und ein fehlender Test-PC wird als `HARDWARE_NOT_EXECUTED` dokumentiert.

Quelle: https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-Readme.md

## 2. Vorab geprüfte Open-Source-Lizenzen

| Bestandteil | Repository/Lizenznachweis | Strategie |
|---|---|---|
| Intel PresentMon | https://github.com/GameTechDev/PresentMon/blob/main/LICENSE.txt | Lizenztext entspricht einer MIT-artigen permissiven Lizenz; konkretes Release-Paket und Third-Party-Notices vor Weiterverteilung prüfen. Bevorzugt auf separat installierte Console-EXE verweisen. |
| Microsoft DirectX Tool Kit | https://github.com/microsoft/DirectXTK/blob/main/LICENSE | MIT. Nur bei tatsächlicher Verwendung einbinden; einfacher eigener Font-Renderer bevorzugt. |
| Windows D3D11/DXGI APIs | Offizielle SDK-Header, Microsoft Learn | Plattform-APIs, keine Notwendigkeit zum Kopieren fremder Samples. |

Kein GitHub-Sample ungeprüft übernehmen. Insbesondere Logos, Fonts und Testgrafiken dürfen nicht einfach als lizenzfrei gelten. Für die synthetischen „Fake-Spieldaten“ besser eigenen kleinen Shader-/Bitmaprenderer schreiben.

## 3. Offene Fragen, die der GO-Durchlauf **durch Recherche entscheiden** muss

**SAC-first-Pflichten vor allem anderen:** Welche GitHub-Actions-Visual-Studio-/SDK-Kombination steht wirklich bereit? Welche CI-Offline-Tests laufen ohne Hardware/GPU-Sitzung? Wie bewertet der Agent 3077 und `citool.exe -lp` lesend? Ist eine tatsächlich nutzbare Test-Windows-Installation vorhanden? Wenn unbekannt, default: CI fertig bauen und `HARDWARE_NOT_EXECUTED`, nicht Nutzer-Rückfrage oder Sicherheitsänderung. Wie kann CA-Signierung **optional** eingeschaltet werden, wenn reale Identitätsprüfung/Schlüssel/Zertifikat bereits vorliegen?

1. Welche *konkrete* PresentMon-Binary ist für einen einfachen, portablen Console-CSV-Workflow die beste? Dateiname, Release-Asset, SHA-256-Bezug und tatsächliche Flags beweisen; versionieren.
2. Kann die gewählte Console-EXE auf einer realen Windows-Maschine Live-CSV mit niedriger, verifizierter Latenz ausgeben? Wenn nicht: sichere Post-Run-Auswertung statt falsche `STRICT_LIVE`-Versprechen.
3. Wie prüft der Launcher deterministisch, dass PresentMon startbereit ist, ehe der FSE-Test beginnt? Prüfe Readiness-Handshake, Warmup oder konservativen Trace-Start; fehlende ETW-Frames müssen UNVERIFIED ergeben.
4. Welches CMake-/Win11-SDK-Setup ist mit geringster Installationslast reproduzierbar, ohne eine nicht installierte Visual-Studio-Version zu behaupten?
5. Wie lassen sich Display-GPU/Output exakt erfassen und ausgeben (LUID, `IDXGIOutput::GetDesc`, Display Device, Monitor-Handle)? Wie wird Monitor-ID eindeutig angegeben?
6. Welche PowerShell-/Python-Versionen sind nötig, um eine CSV mit QPC-64-bit-Werten verlustfrei zu verarbeiten?
7. Wie werden echte Recorder-Start/Stop-Zeiten korreliert, **ohne** das fremde Produkt zu hooken? Manuelle Marker explizit als Näherung; eine optionale Recorder-API nur bei klarer Dokumentation.
8. Wie ist `--strict` sinnvoll umzusetzen, wenn unabhängig verifiziertes Live-Feedback nicht existiert? Antwort darf sein: *nicht möglich ohne Zusatzkomponente*, ehrlicher Post-Run-Gate. Kein „wird schon Fullscreen sein“.
9. Wie verhindert man Mehrfachinstanzen, PID-Reuse, vertauschte Trace-Files, Swapchain-Neuerstellung und fehlerhafte Zuordnung? Alle diese Fälle mit Negativtests abdecken.
10. Wann wird `FAIL` vs `UNVERIFIED` gemeldet? Nachgewiesener falscher Präsentationsmodus ⇒ FAIL; fehlende Evidenz ⇒ UNVERIFIED; fehlgeschlagene DXGI-Anforderung ⇒ FAIL_DXGI; Recorderprüfung separat.

## 4. Zielzustand und Risikogrößen

**Wirklich erfüllt**: Windows-EXE fordert DXGI-Fullscreen an; selbsttätig gerenderte Testgrafik ist stabil; unabhängiger PresentMon-Trace klassifiziert Frames im markierten Aufnahmezeitfenster; Abweichungen bzw. fehlende Evidenz führen nicht zu False-Positive; ein schwächeres Modell bekommt vollständige und kleine Code-Dateien samt Tests.

**Nicht garantiert**: Jede Kombination aus Windows-Version, GPU-Treiber, FSO, Monitor, HDR, MPO und Recorder kann einen klassischen Legacy-FSE-Pfad herstellen. Die tatsächliche Verfügbarkeit hängt von der Testmaschine ab; das Werkzeug ist ein Diagnoseinstrument, keine Methode zum Erzwingen beliebiger Präsentationspfade.

**Bestätigungsgrad** (strikte Trennung):

- A: `API_REPORTED_FULLSCREEN` — lokale DXGI-Aussage, kein unabhängiger Beweis.
- B: `CLASSIC_PRESENT_PATH_OBSERVED` — framebezogener unabhängiger ETW-Beleg für einen bestimmten Zeitraum; wenn Zeit-/PID-/Swapchain-Prüfung stimmt, `FSE_VERIFIED` für diesen Zeitraum.
- C: `RECORDER_CAPTURE_OK` — zusätzlich separat durch Bild/Video-Validierung gezeigt; aus B allein nicht ableitbar.

## 5. Quellen-Baseline (Primärquellen)

- Microsoft — Fullscreen Optimizations: https://devblogs.microsoft.com/directx/demystifying-full-screen-optimizations/
- Microsoft — DXGI `SetFullscreenState`: https://learn.microsoft.com/en-us/windows/win32/api/dxgi/nf-dxgi-idxgiswapchain-setfullscreenstate
- Microsoft — DXGI Flip Model: https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/for-best-performance--use-dxgi-flip-model
- Microsoft — DXGI Best Practices: https://learn.microsoft.com/en-us/windows/win32/direct3darticles/dxgi-best-practices
- Microsoft — `MakeWindowAssociation`: https://learn.microsoft.com/en-us/windows/win32/api/dxgi/nf-dxgi-idxgifactory-makewindowassociation
- Microsoft — D3D11/DXGI Swap Effects: https://learn.microsoft.com/en-us/windows/win32/api/dxgi/ne-dxgi-dxgi_swap_effect
- Microsoft — Smart App Control: https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/overview
- Intel/GitHub — PresentMon Console CLI: https://github.com/GameTechDev/PresentMon/blob/main/README-ConsoleApplication.md
- Intel/GitHub — PresentMon CLI Parsing: https://github.com/GameTechDev/PresentMon/blob/main/PresentMon/CommandLine.cpp
- Intel/GitHub — PresentMon Releases: https://github.com/GameTechDev/PresentMon/releases
- Intel — PresentMon v2.6.0: https://game.intel.com/de/intel-presentmon/
- Intel/GitHub — PresentMon License: https://github.com/GameTechDev/PresentMon/blob/main/LICENSE.txt
- Microsoft/GitHub — DirectXTK License: https://github.com/microsoft/DirectXTK/blob/main/LICENSE

- Microsoft SAC Test/Event-IDs: https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/test-your-app-with-smart-app-control
- Microsoft EU Code-Signing-Optionen: https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options
- GitHub Actions Windows Runner: https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-Readme.md
