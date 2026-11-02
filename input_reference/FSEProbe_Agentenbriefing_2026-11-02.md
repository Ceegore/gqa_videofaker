# FSEProbe — Implementierungsbriefing für einen kleinen Coding-Agenten

**Stand:** 2026-11-02  
**Zweck:** Reproduzierbare Tests eines Windows-Screenshot- und Videorecording-Tools unter klassischem Exclusive Fullscreen (FSE) und definierten Kontrollmodi.  
**Zielplattform:** Windows 10/11, x64, lokale interaktive Windows-Sitzung, Direct3D 11-fähige GPU.  
**Priorität:** Zuverlässige Modusverifikation vor optischer Schönheit, minimale Komplexität.

## 0. Zentrale technische Wahrheit

Eine erfolgreiche Rückgabe von `IDXGISwapChain::SetFullscreenState(TRUE, output)` und `GetFullscreenState()==TRUE` **beweist nicht**, dass Windows klassische exklusive Bildschirmausgabe verwendet. Microsoft dokumentiert, dass **Fullscreen Optimizations (FSO)** den angeforderten Fullscreen-Modus transparent durch einen optimierten Borderless-Präsentationspfad ersetzen können, während die App weiter an FSE glaubt.

Der **tatsächliche Präsentationsmodus** muss daher mit einem unabhängigen, ETW-basierten Beobachter, vorzugsweise **PresentMon**, festgestellt werden. Dieser unterscheidet unter anderem:

- `Hardware: Legacy Flip` — App besitzt den Bildschirm; starker Nachweis für klassischen exklusiven Pfad.
- `Hardware: Legacy Copy to front buffer` — App besitzt den Bildschirm; ebenfalls Legacy/Exclusive-Pfad.
- `Hardware: Independent Flip` — Hardware-Scanout ohne exklusive Bildschirmübernahme; **kein** klassischer FSE-Nachweis.
- `Hardware Composed: Independent Flip` — Hardware-Overlay/optimierter Pfad; **kein** klassischer FSE-Nachweis.
- `Composed: Flip` — DWM-komponierter Fenster-/Borderless-Modus; **kein** FSE-Nachweis.

**Regel:** Nie „FSE BESTÄTIGT“ aus Fenstergeometrie, API-Rückgabewert, Monitorauflösung, exklusivem Fokus oder Bildwiederholrate allein ableiten. Ist PresentMon nicht verfügbar, wird maximal `DXGI_FULLSCREEN_REQUESTED_AND_REPORTED`, aber **nicht** `FSE_VERIFIED` ausgegeben.

Der Anzeige-/ETW-Zustand kann sich während des Capture-Vorgangs ändern. Für Aussagen zur Recorder-Kompatibilität muss der relevante Testzeitraum **während aktiver Aufnahme** geprüft werden.

## 1. Genaue Funktionsanforderungen

### Muss (MVP)

1. Natives Windows-Programm `FSEProbe.exe`, **kein Unity/Godot**, kein Browser/Electron, kein SDL als Kern des Fullscreen-Nachweises.
2. Win32-Fenster, D3D11-Gerät auf Hardware-GPU, DXGI-Swapchain; programmgesteuerte Anforderung `SetFullscreenState(TRUE, selectedOutput)`.
3. DXGI-Aufrufstatus mit HRESULT, `GetFullscreenState()`, Output-/Monitor-Identität und Auflösung loggen und wiederholt prüfen.
4. Zwei bewusst unterschiedliche Renderpfade:
   - `legacy-exclusive`: `DXGI_SWAP_EFFECT_DISCARD` (klassisches blt-/Legacy-Verhalten; nur zu QA-Zwecken, nicht als allgemeine Performance-Empfehlung) und DXGI-Fullscreen-Anforderung.
   - `borderless-control`: `DXGI_SWAP_EFFECT_FLIP_DISCARD`, rahmenloses Bildschirmfenster, **kein** `SetFullscreenState(TRUE)`.
   - `flip-fullscreen` kann als dritter, optionaler Vergleichsmodus ergänzt werden.
5. Auf dem D3D11-Backbuffer animierte, gut erkennbare **synthetische** Testinhalte: Raster, wanderndes Objekt, Eckenmarkierungen, Farbwechsel, fortlaufende Frame-ID, Laufzeit und Dummy-Spielwerte (z. B. Level, HP, Score; ausdrücklich `FAKE/SYNTHETIC`). Kein echtes Spielekonzept notwendig.
6. GPU-Last mittels eines selbst geschriebenen, begrenzten HLSL-Pixelshaders in Stufen `off|low|medium|high`; kein aggressiver Stresstest, **keine** unbeschränkten Shader-Schleifen. FPS-Begrenzung, VSync-Vorgabe und ESC zum sicheren Beenden.
7. Eingebautes DXGI-Diagnostikfeld. Externe Bestätigung über PresentMon-CSV; am Ende für jeden Test `PASS|FAIL|UNVERIFIED`.
8. Start über `run_test.ps1` als Ein-Klick-Workflow: PresentMon starten, Testanwendung starten, ETW erfassen, protokollieren, Bericht erzeugen. Eine benötigte PresentMon-Datei wird explizit konfiguriert und nie als vorhanden vorausgesetzt.
9. `logs/<run-id>/app.jsonl`, `presentmon.csv`, `summary.json`, `summary.txt`; korrelierbare Start-/Endzeiten, PID, Build-Version, gewählter Modus, GPU/Monitor, HRESULTs und Messperiode.
10. Fehlerfälle führen zu sichtbarer Warnung oder markiertem `UNVERIFIED`, niemals zum stillen Rückfall mit angeblichem PASS.

### Absichtlich nicht im MVP

- 3D-Engine, komplexes Asset-System, Audio-Engine, Netzwerk, Overlay-Injection, Hooking des Recorders, Administratorpflicht für die Spiel-App, systemweite Registry-Änderungen, MSIX/Installer, Auto-Updates, Telemetrie-Dienste.
- GPU-Auslastung in Prozent aus dem eingestellten Shader-Level ableiten. Das Lastprofil ist konfiguriert; die **reale** Auslastung/Busy-Time ist separat zu messen und hardwareabhängig.
- DirectX 12 als Ersatz für den klassischen DX11-FSE-Test (DX12-Fullscreen-Semantik ist nicht mit klassischer FSE-Beweisführung gleichzusetzen).

## 2. Empfohlener Projektzuschnitt

```text
FSEProbe/
  CMakeLists.txt
  README.md
  LICENSES.md
  src/
    main.cpp                 # Win32-Fenster, Ereignisschleife, CLI, sichere Beendigung
    GraphicsD3D11.h/.cpp     # Device, Swapchain, Fullscreen-Transition, Resize, Present
    Diagnostics.h/.cpp      # DXGI-Status, HRESULT-Formatierung, JSONL-Log
    Scene.h/.cpp             # synthetische animierte Szene, FPS/Frame-ID, GPU-Last
    shaders.hlsl             # Fullscreen-Triangle/Pixelshader, begrenzte Arbeit
  tools/
    run_test.ps1             # Start & PresentMon-Trace
    verify_presentmon.py    # CSV-Prüfer; nur für Auswertung, nicht Spiel-Runtime
  tests/
    verification_cases.md
  logs/                      # automatisch, nicht einchecken
```

**Minimaltechnik:** C++20 + MSVC + Windows SDK + Direct3D 11 + DXGI + D3DCompiler. CMake zum Bauen. COM über `Microsoft::WRL::ComPtr`. Statische/Standard-Windows-Libraries; keine externe Game Engine. Für Text auf dem Bild entweder kleine eigene Bitmap-Font-Implementierung oder explizit optional `DirectXTK SpriteFont`/`SpriteBatch` (MIT, Copyright-Hinweise beilegen). Keine externen Text-Overlays über das Ziel-Fenster, die den Präsentationsmodus verändern könnten.

### Rendering

- Erzeuge Gerät und Swapchain initial **im Fenstermodus**.
- Nutze beim klassischen FSE-Test `DXGI_SWAP_EFFECT_DISCARD` bewusst als Legacy-Testpfad. Das widerspricht Microsofts Performance-Empfehlung für moderne Spiele, ist für einen Legacy-Kompatibilitätstest aber zweckmäßig.
- Wähle physisch angeschlossenen Monitor sauber aus; platziere das Ausgangsfenster auf dem gewählten Monitor und ermittle das passende DXGI-Output. Standardmäßig **native Desktopauflösung** beibehalten.
- Fordere bei Fokus `SetFullscreenState(TRUE, output)` an und prüfe HRESULT. Danach Zielgrößen/Backbuffers korrekt behandeln. Beim Flip-Modell ist nach der Transition `ResizeBuffers` vorgeschrieben.
- Bei Verlust der exklusiven Fullscreen-Anforderung, Alt-Tab, Geräteverlust, Monitorabzug und Present-Fehler: Zustand auf FAIL/INVALID setzen, Ereignis mit genauer Ursache loggen, sicher bereinigen; keinen falschen PASS anzeigen.
- Vor dem Freigeben der Swapchain `SetFullscreenState(FALSE, nullptr)` aufrufen; Anzeigeeinstellungen nicht unkontrolliert hinterlassen.
- `Present()`-Fehler und `DXGI_ERROR_DEVICE_REMOVED` mit `GetDeviceRemovedReason()` protokollieren.
- Nur eine Swapchain pro Testfenster. Keine Remote-Desktop- oder VM-Sitzung als Ersatz für einen Hardwaretest anerkennen.

### Bildinhalt (Recorder-Orakel)

- Anzeige von `FSEPROBE`, Run-ID, Modusname, Frame-ID, Laufzeit/UTC und `FAKE GAME DATA`.
- Bewegtes Quadrat durchläuft alle vier Bildschirmquadranten und regelmäßig den Rand.
- Deutlich wechselnde, kontrastreiche Farben; kleines Raster für Skalierung/Cropping, vier Eckenmarkierungen.
- Jede Sekunde wechselnde Testfarbkennung + fortlaufende Frame-ID, um eingefrorene/duplizierte Frames und Video-Sequenzfehler beurteilen zu können.
- Einstellbarer HLSL-Aufwand: kein GPU-Lastversprechen in Prozent; keine thermisch riskanten Endlosschleifen. VSync standardmäßig an; FPS-Cap z. B. 60.
- Statusanzeige unterscheidet strikt `DXGI: requested`, `DXGI: active`, `PresentMode: verified / unavailable / wrong`. Wenn externe Rückmeldung noch nicht vorliegt: `NOT YET VERIFIED`.

## 3. Zustandsmaschine und objektive Bewertung

```text
STARTUP
  -> WINDOWED_READY
  -> REQUESTING_FULLSCREEN
  -> DXGI_FULLSCREEN_ACTIVE  (API Erfolg + GetFullscreenState=true)
  -> VERIFYING_PRESENTATION (ETW-Beobachtung)
  -> FSE_VERIFIED            (nur passende ETW-Befunde im Testintervall)
  -> RECORDING_TEST_ACTIVE   (Aufnahmezeitfenster, laufend überwacht)
  -> PASS / FAIL / UNVERIFIED
```

**Unterscheide zwei Ergebnisse:**

- **App-/DXGI-Ergebnis**: `DXGI_OK` / `DXGI_FAIL`.
- **Beobachteter Präsentationspfad**: `CLASSIC_EXCLUSIVE` / `INDEPENDENT_FLIP` / `COMPOSED` / `UNKNOWN`.

**Strikte FSE-PASS-Bedingung:**

1. `legacy-exclusive` wurde angefordert; alle relevanten DXGI-Aufrufe erfolgreich, `GetFullscreenState()==TRUE` zur Prüfung.
2. Richtiger Monitor und Hardware-GPU; tatsächliche Frame-Präsentationen im Aufnahmezeitfenster vorhanden.
3. PresentMon-Trace enthält **für die richtige PID/Swapchain** nach einer klar definierten Start-/Warm-up-Phase mindestens 2 s **und** mindestens 30 aufeinanderfolgende passende Frame-Präsentationen mit ausschließlich `Hardware: Legacy Flip` (alternativ `Hardware: Legacy Copy to front buffer`). Bei langsamen Systemen Testintervall entsprechend verlängern, nicht blind PASS setzen.
4. Während des expliziten relevanten Capture-Zeitfensters darf kein abweichender PresentMode und kein Fullscreen-/Focus-Verlust auftreten. Bei Wechsel: `FAIL_MODE_CHANGED`. Wenn Zeitbezug unzureichend oder Trace nicht auswertbar: `UNVERIFIED`, niemals PASS.
5. Die Aufnahme selbst wird unabhängig durch das aufzunehmende Tool beurteilt (Bild/Video vorhanden, optische Testmuster/Frame-IDs korrekt). Ein FSE-PASS allein besagt noch nicht, dass das Recording-Tool korrekt funktioniert.

Weitere Fehlercodes: `FAIL_DXGI`, `FAIL_NO_FOCUS`, `FAIL_WRONG_MONITOR`, `FAIL_NO_ETW_FRAMES`, `FAIL_MODE_CHANGED`, `UNVERIFIED_PRESENTMON_MISSING`, `UNVERIFIED_PERMISSION`, `UNVERIFIED_INSUFFICIENT_DATA`, `FAIL_DEVICE_REMOVED`.

**Keine automatisierte OS-Änderung:** Falls Windows Fullscreen Optimizations dazwischenfunkt: Anleitung für `.exe` → Eigenschaften → Kompatibilität → „Vollbildoptimierungen deaktivieren“ (falls auf der Windows-Version verfügbar), Anwendung neu starten und ETW-Befund erneut prüfen. Den Windows-11-Schalter „Optimierungen für Fensterspiele“ **nicht** als identisch mit dieser Legacy-FSO-Einstellung darstellen.

## 4. Bedienung, die wir im ersten Release erwarten

Ein Klick startet einen dokumentierten Test. Bei Start ohne PresentMon darf die App weiterlaufen, aber muss sehr sichtbar `FSE nicht unabhängig verifiziert` anzeigen.

Beispiel-Aufruf (CLI entwerfen/implementieren):

```powershell
.\FSEProbe.exe --mode legacy-exclusive --monitor 0 --load medium --fps-cap 60 --duration 30
```

Optionaler Referenzaufruf für die installierte PresentMon-Console-Anwendung (Pfad/Dateiname je Version anpassen):

```powershell
.\PresentMon.exe --process_name FSEProbe.exe --output_file .\logs\presentmon.csv --timed 35 --terminate_after_timed --no_console_stats
```

Die endgültige `run_test.ps1`-Implementierung soll die PresentMon-CLI-Argumente anhand der gebündelten/konfigurierten **tatsächlichen** Version verifizieren, PresentMon **vor dem relevanten Zeitraum** starten, Start-/Endzeiten korrelieren, Exitcodes prüfen, die richtige PID zuordnen, den CSV-Header statt fester Spaltenpositionen auswerten und alle Subprozesse sauber schließen. Die EXE darf auch ohne Python lauffähig sein; das Python-Skript ist nur eine einfache Offline-Auswertung.

Falls **echte Live-ETW-Verifikation** der Statusanzeige gewünscht wird, ist das ein **separater Ausbauschritt**: externer PresentMon-Watcher liest Streaming-Ausgabe/API und gibt verifizierte Befunde an die App weiter. Vor Implementierung tatsächliches Streaming der eingesetzten PresentMon-Version prüfen. Keine „Live“-Behauptung, wenn lediglich nach dem Test eine Datei ausgewertet wird.

## 5. Tests und Akzeptanzfälle

| ID | Aktion | Erwarteter Befund |
|---|---|---|
| T01 | Start auf lokalem Windows 11 mit Hardware-GPU | Rendering und Fake-Werte ändern sich; sauberes Log |
| T02 | Legacy Fullscreen anfordern | `SetFullscreenState` HRESULT + DXGI-Zustand sichtbar; nicht allein als FSE-PASS behandelt |
| T03 | Legacy unter deaktivierten FSO testen | Nur bei `Hardware: Legacy Flip` bzw. `Legacy Copy` im ETW-Bereich `FSE_VERIFIED` |
| T04 | FSO aktiv lassen bzw. unabhängig geflippt | `Hardware: Independent Flip` darf niemals klassischen FSE-PASS ergeben |
| T05 | Borderless-Kontrollmodus | Keine exklusive DXGI-Anforderung; Klassifikation nicht Legacy Exclusive |
| T06 | Alt-Tab/Fokusverlust während Test | Modus-/Fokusänderung wird geloggt; relevanter Test wird ungültig |
| T07 | Externes Overlay / Recorder während Test aktivieren | Präsentationsmodus wird während Aufnahme erneut beurteilt; Abweichung markiert |
| T08 | PresentMon fehlt / ETW-Rechte fehlen | `UNVERIFIED` mit Ursache; keine irreführende grüne Bestätigung |
| T09 | Screenshot aufnehmen | Run-ID, Frame-ID, Raster und Eckenmarker sichtbar; optischer Vergleich möglich |
| T10 | Video aufnehmen | Frame-IDs/Farbsequenz/Bewegung zur Prüfung von Freeze, Crop, Timing nutzbar |
| T11 | ESC, Timeout, Device-loss | Sicheres Beenden, Rückkehr zum Desktop; Displaymodus wiederhergestellt |
| T12 | GPU-Last off/low/medium/high | Stufen beeinflussen messbar GPU-Arbeit, ohne ungebremste Last |
| T13 | Wiederholungen gleichen Setups | Berichte enthalten gleiche Parameter und maschinenlesbare Klassifikation |

Echte Tests müssen unter Windows auf echter Hardware ausgeführt werden. CI kann Quellcode, Format, Parser und synthetische CSV-Fixtures prüfen, **aber nicht** physisches FSE auf Linux oder ohne Windows-GPU nachweisen.

## 6. Open Source und Lizenzen

- **Intel PresentMon** — https://github.com/GameTechDev/PresentMon — MIT; unabhängige Messung per ETW; als separate Kommandozeile bevorzugen, keine Quellcodeintegration nötig. Für Redistribution Lizenztext und Hinweise zu Drittkomponenten beachten: `LICENSE.txt`, `THIRD_PARTY.txt`.
- **Microsoft DirectXTK** — https://github.com/microsoft/DirectXTK — MIT; optional SpriteFont/SpriteBatch, falls die Eigenimplementierung der Textanzeige zu groß wird. Bei Verwendung MIT-Notices übernehmen.
- **Microsoft DirectX-Graphics-Samples** — https://github.com/microsoft/DirectX-Graphics-Samples — MIT; **insbesondere DX12**-Beispiele nur als allgemeine Referenz, nicht als Nachweis klassischen DX11-FSE übernehmen.
- Windows SDK/D3D11/DXGI APIs sind Plattform-APIs. Fremde Codeauszüge nur verwenden, wenn Datei-/Repository-Lizenz klar ist; Quellen- und Lizenznachweise dokumentieren.
- Für nur interne Nutzung bleibt Lizenzprüfung sinnvoll. Bei Verteilung alle anwendbaren Lizenztexte und Mitteilungen beilegen; nicht behaupten, fremder Code sei ausschließlich selbst erstellt.

## 7. Arbeitsanweisung für einen schwächeren Coding-Agenten (direkt verwendbar)

> Du entwickelst `FSEProbe`, einen **kleinen, verifizierbaren Windows-x64-Direct3D11-Test für Screenshot- und Video-Recorder**. Die obigen Anforderungen sind verbindlich. Deine oberste Priorität ist **keine falsch positive Exclusive-Fullscreen-Bestätigung**. Verwende C++20, Win32, D3D11, DXGI, HLSL und CMake. Arbeite **inkrementell** und meide unnötige Frameworks und Features.
>
> **Phase A — Kern:** Erstelle zuerst einen kompilierenden Win32/D3D11-Minimalbuild mit animierter Szene, FPS-/Frame-ID, sicherem Beenden und Fehlerprotokoll. Prüfe ausdrücklich korrekte Device-/Swapchain-Erstellung, HRESULTs und Resource-Cleanup. Gib klare Build-Befehle an. Baue keine zusätzlichen Features, solange der Kern nicht baut.
>
> **Phase B — Modus:** Implementiere `legacy-exclusive` mit `DXGI_SWAP_EFFECT_DISCARD`, initial windowed Swapchain und `SetFullscreenState(TRUE, selectedOutput)`. Prüfe `GetFullscreenState`, Monitor, Fokus und Present-Fehler. Implementiere `borderless-control` separat mit Flip-Model. Behandle WM_SIZE, Alt-Tab, DXGI-Geräteverlust und Cleanup robust. API-Erfolg darf nicht `FSE_VERIFIED` bedeuten.
>
> **Phase C — Messung:** Ergänze `run_test.ps1`, unabhängigen PresentMon-Trace und `verify_presentmon.py`. Analysiere PresentMode nach PID, Zeitbereich und Swapchain; verwende `PASS|FAIL|UNVERIFIED`. Teste den Parser mit künstlichen CSV-Dateien (nur Legacy Flip; nur Independent Flip; gemischte Frames; fehlende Daten; falsche PID; Spaltenreihenfolge verändert). Logge alle relevanten Quellen und Abbrüche.
>
> **Phase D — Test-Nutzen:** Ergänze GPU-Laststufen, gut sichtbare synthetische Werte, Eckenmarker, Farb-/Bewegungssequenz, Ein-Klick-Testscript und Bericht. Prüfe während aktiver Aufnahme erneut. Falls Live-ETW nachweislich verfügbar ist, kann die App dessen bestätigten Status anzeigen; sonst nicht.
>
> **Wichtige Verbote:** Kein Unity/Godot/SDL als FSE-Implementierung; keine Vermutung, dass Borderless=Exclusive; keine systemweiten Registry-Hacks; keine künstliche Vollbild-Bestätigung ohne unabhängige ETW-Daten; keine unbounded Shader-Last; keine angeblich bestandenen Hardwaretests ohne Ausführung auf Windows-GPU; keine ungeprüften GitHub-Codes ohne Lizenzhinweise.
>
> **Pro Phase liefern:** geänderte Dateien, Build-/Testbefehle, exakte Testausgabe, bekannte Limitationen und verbleibende Prüfpunkte. Behebe Compilerfehler und Parserprobleme vor dem nächsten Schritt. Nach Phase D mindestens zwei zusätzliche Überprüfungen ohne Änderungen an funktionalen Tests, sofern möglich. Wenn physische Hardware oder PresentMon fehlt: ausdrücklich als `NOT TESTED / UNVERIFIED` kennzeichnen.

## 8. Windows Smart App Control (SAC) und Testumgebung

Wenn auf dem Testrechner **Smart App Control im Erzwingungsmodus** läuft, kann Windows eine unbekannte, unsignierte `FSEProbe.exe` blockieren. Das ist **kein** DXGI-/Fullscreen-Fehler. Den Startfehler separat ausweisen und nach Möglichkeit mit vertrauenswürdig signiertem Test-Build bzw. auf einer dafür vorgesehenen Testmaschine testen. **SAC nicht stillschweigend deaktivieren oder „umgehen“**. Auch Skripte und weitere Binary-Abhängigkeiten im Startworkflow können von Windows-Schutzrichtlinien betroffen sein.

Für aussagekräftige FSE-Ergebnisse möglichst **lokale interaktive Sitzung mit physischem Monitor** verwenden; RDP, virtuelle Monitore, VM-/Cloud-Desktops und USB-Displayadapter können die DXGI-Semantik ändern. Multi-Monitor-Hardware und Capture-Hooks sind in Ergebnisdateien zu dokumentieren.

## 9. Referenzen (Microsoft / Originalprojekte)

1. Microsoft DirectX Developer Blog — Fullscreen Optimizations: https://devblogs.microsoft.com/directx/demystifying-full-screen-optimizations/
2. Microsoft DXGI `SetFullscreenState`: https://learn.microsoft.com/en-us/windows/win32/api/dxgi/nf-dxgi-idxgiswapchain-setfullscreenstate
3. Microsoft — DXGI Flip-Modell und Independent Flip: https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/for-best-performance--use-dxgi-flip-model
4. Microsoft Windows 11 — Optimizations for windowed games (separate Einstellung): https://support.microsoft.com/en-us/windows/hardware/display-graphics/optimizations-for-windowed-games-in-windows-11
5. Intel PresentMon Console CLI und PresentMode-Klassifikationen: https://github.com/GameTechDev/PresentMon/blob/main/README-ConsoleApplication.md
6. Microsoft DirectXTK (MIT): https://github.com/microsoft/DirectXTK
7. Microsoft DX12 Swap-Chain-Dokumentation (DX12-Fullscreen-Semantik; kein Ersatz für DX11-FSE): https://github.com/MicrosoftDocs/win32/blob/docs/desktop-src/direct3d12/swap-chains.md
8. Microsoft Smart App Control (Signierung unbekannter Binaries): https://learn.microsoft.com/windows/apps/develop/smart-app-control/overview

## 10. Einschätzung und Grenzen

Der Kern (Direct3D11-Rendering mit Swapchain und kontrollierter Fullscreen-Anforderung) ist für einen Coding-Agenten gut beherrschbar, sofern er unter Windows kompilieren kann. Die schwierigste Komponente ist **nicht** das Zeichnen, sondern die unabhängige, zeitlich korrelierte Bestätigung des tatsächlichen Präsentationsmodus — insbesondere bei Aufnahmen, Overlays, mehreren Bildschirmen und Windows-Fullscreen-Optimierungen.

Ein absichtlich klassischer DX11-Legacy-Testpfad ist für diese spezielle QA-Aufgabe sinnvoll, **nicht** als generelle Empfehlung für Spieleentwicklung. Falls die Zielmaschine mit ihren Treibern/Windows-Einstellungen keinen `Hardware: Legacy Flip` zulässt, soll der Test dies dokumentieren und keine Garantie behaupten. Diese Datei ist eine recherchierte Spezifikation, **kein bereits auf Windows kompilierter oder real getesteter Build**.
