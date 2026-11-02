# 02 — Exakte Windows-/DXGI-Aufrufreihenfolge

## A. Ohne Grafik ausführbare Pfade

`wWinMain` verwendet `CommandLineToArgvW`, wandelt UTF-16 strikt nach UTF-8, validiert die Optionen und gibt den Argumentblock mit `LocalFree` frei. `--help`, `--version` und `--self-test` erstellen kein Fenster/Device. Der Selbsttest prüft nur Parser, JSON und QPC. `--list-monitors` enumeriert DXGI-Ausgaben, erstellt aber keine Swapchain. Auch diese neuen Binaries dürfen auf dem geschützten Dev-PC nicht als bereits ausführbar angenommen werden.

## B. Startidentität und Windows-Fenster

1. Neuen Logpfad öffnen; vorhandene `app.jsonl`/`frames.csv` nicht überschreiben.
2. `CreateMutexW` im `Local\`-Namespace; vorhandene Instanz oder nicht zugänglicher Mutex → Exit 23. Kein globales Privileg nötig. Sessionübergreifende Konflikte bleiben Sache von DXGI/Observer.
3. `GetCurrentProcessId`, `GetProcessTimes`, `QueryPerformanceFrequency`, `QueryPerformanceCounter`, `GetSystemMetrics(SM_REMOTESESSION)` und `ProcessIdToSessionId` protokollieren. Remote-/Session-0-Grafiktest verweigern.
4. DPI-Awareness ist bereits im Manifest `PerMonitorV2`; nicht nach Fenstererstellung umschalten. `CreateDXGIFactory1`, `EnumAdapters1`, `EnumOutputs`, `GetDesc1`/`GetDesc`; Softwareadapter und nicht angehängte Outputs überspringen.
5. `WNDCLASSW` registrieren, `CreateWindowExW` mit `WS_POPUP` auf `DesktopCoordinates`, `ShowWindow`, `UpdateWindow`. Keine Topmost-Overlays. Windows-Displaynummer und DXGI-Index nicht gleichsetzen.

## C. D3D11-Gerät und Swapchain

`D3D11CreateDevice(selectedAdapter, D3D_DRIVER_TYPE_UNKNOWN, nullptr, 0, [D3D_FEATURE_LEVEL_11_0], 1, D3D11_SDK_VERSION, ...)`. Bei explizitem Adapter ist UNKNOWN der richtige Treibertyp [S06]. Kein stiller WARP-/Softwarefallback. Feature-Level 11.0 ist für die SM5-Shader erforderlich.

Die Factory wird über den gewählten Adapter ermittelt; Device und Factory stammen so aus derselben Adapterfamilie. `DXGI_SWAP_CHAIN_DESC` setzt RGBA8_UNORM, SampleCount 1, RefreshRate 0/1, RenderTargetOutput, HWND, `Windowed=TRUE`, Flags 0. Legacy: DISCARD/BufferCount 1. Kontrolle: FLIP_DISCARD/BufferCount 2. `CreateSwapChain` ist hier der bewusst gemeinsame, kleine HWND-Pfad; keine zweite aktive Swapchain.

`MakeWindowAssociation(hwnd, DXGI_MWA_NO_ALT_ENTER)` verhindert den unkontrollierten Alt+Enter-Wechsel [S04]. WndProc unterdrückt zusätzlich die entsprechende Tastenbehandlung. Kein `DXGI_MWA_NO_WINDOW_CHANGES` als Ersatz für notwendige Lifecycle-Behandlung.

Die vier mit FXC erzeugten Shader-Bytearrays werden per `CreateVertexShader`/`CreatePixelShader` geladen. `CreateInputLayout` beschreibt float2 POSITION und float4 COLOR. Dynamischer 16-Byte-Constantbuffer und begrenzter Vertexbuffer dienen der Animation. `GetBuffer(0)` und `CreateRenderTargetView` initialisieren den Backbuffer; die temporäre Textur-Referenz verlässt danach den Scope.

## D. Legacy-Transition

Erst lokalen Vordergrundfokus abwarten, höchstens zehn Sekunden. Keine dauerhaft fokuserzwingende Schleife. Dann `SetFullscreenState(TRUE, selectedOutput)` [S02]. **Nur S_OK** wird als abgeschlossene Anforderung behandelt. `DXGI_ERROR_NOT_CURRENTLY_AVAILABLE`, `DXGI_ERROR_NOT_FOUND`, `DXGI_STATUS_MODE_CHANGE_IN_PROGRESS` oder andere Rückgaben beenden diesen Lauf nachvollziehbar. Ein HRESULT mit positivem Status ist nicht automatisch das erwartete Ergebnis.

Nach der Transition Clientgröße lesen; `OMSetRenderTargets(0,...)`, `ClearState`, RTV freigeben, `Flush`, `ResizeBuffers(0,w,h,DXGI_FORMAT_UNKNOWN,0)`, anschließend Backbuffer/RTV neu beziehen [S03]. Keine noch gebundene Backbuffer-Referenz behalten. Den Vorgang nicht aus `WndProc` heraus aufrufen.

`ResizeTarget` ist im Default **bewusst nicht vorhanden**: keine gewünschte andere Auflösung, keine erzwungene Refresh-Rate, kein zusätzlicher Displaymoduswechsel. Eine spätere Auflösungstestfunktion müsste Mode-Enumeration, Restoration und separate Abnahme ergänzen; nicht nebenbei einbauen.

`GetFullscreenState` muss TRUE liefern, `GetContainingOutput` zum ausgewählten HMONITOR passen. Danach initiale Nachrichten abarbeiten und `MODE_READY` protokollieren. Das bestätigt den API-Zustand, nicht den tatsächlichen Legacy-Präsentationspfad.

## E. Frame und Nachrichtenschleife

Nachrichten mit `PeekMessageW`, `TranslateMessage`, `DispatchMessageW` abarbeiten. Fokus/Minimierung/Displaywechsel prüfen; `WM_SIZE` außerhalb kritischer Segmente mit sicherem Resize behandeln. Im markierten Segment: Resize → ungültig. `GetFullscreenState` pro Loop, Outputprüfung regelmäßig. Keine GUI-Nachricht darf einen unwirksamen „FSE_VERIFIED“-Status setzen.

CPU erstellt Szene, `Map(WRITE_DISCARD)`/`Unmap` aktualisieren Constant-/Vertexbuffer. OM/RS/IA/VS/PS erneut binden; Background Draw(3); HUD Draw(vertexCount). QPC unmittelbar vor `Present(1,0)` und unmittelbar danach protokollieren. Bei jeder von S_OK abweichenden Rückgabe Fehler loggen; `GetDeviceRemovedReason` zusätzlich ausgeben. `DXGI_ERROR_DEVICE_REMOVED`, `DEVICE_RESET` und `DXGI_STATUS_OCCLUDED` nie in einen normalen Frame umdeuten.

Der feste VSync-Aufruf begrenzt zusammen mit `--fps-cap` die Arbeit. Der CPU-Cap nutzt eine nachrichtenfähige Wartefunktion und holt verpasste Frames nicht mit Bursts nach. Das sind keine Echtzeit- oder exakten FPS-Garantien.

## F. Beendigung und Ausnahmebehandlung

ESC, WM_CLOSE, Dauerende oder Fehler beenden den Loop. Ein offenes Capturefenster wird als unvollständig markiert. Im Legacy-Pfad vor Freigabe der Swapchain `SetFullscreenState(FALSE,nullptr)` versuchen und HRESULT aufzeichnen. Kontrolle liefert Cleanup-S_OK ohne exklusiven Eintritt. Device-Context leeren/flushen, ComPtrs freigeben, HWND zerstören, END schreiben.

`GWLP_USERDATA` verweist auf stackgebundenen Fensterzustand. Bei einer Ausnahme wird dieser Zeiger vor nachfolgendem Fenster-Cleanup getrennt; sonst könnten synchrone Fensternachrichten nach Stack-Unwinding auf ungültigen Speicher zugreifen. Im Normalfall wird das Fenster zerstört, bevor der Zustand seinen Scope verlässt.

## Kompatibilität, nicht unbelegt zugesichert

| Umgebung | Geplanter Umgang | Abnahme hier |
|---|---|---|
| Windows 10/11 x64, D3D11 FL11, lokaler SDR-Monitor | Hauptziel | Nicht ausgeführt |
| FSO aktiv | unabhängig messen; Nicht-Legacy ist kein Pass | Nicht ausgeführt |
| Mehrere Monitore/HiDPI | DXGI-Ausgabe ausdrücklich wählen | Nicht ausgeführt |
| HDR/VRR/MPO/hybride Grafik | eigener späterer Test, keine pauschale Zusage | Nicht ausgeführt |
| RDP/Session 0 | verweigert | Nur Source-Review |
| VM/Sandbox/Cloud | keine physische FSE-Abnahme | Nicht zulässig als Ersatz |
| Linux | nur portable Core-/Parser-Prüfungen | Ausgeführt |
