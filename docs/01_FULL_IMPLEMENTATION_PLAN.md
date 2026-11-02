# 01 — Vollständiger Implementierungsplan

## 1. Produktdefinition und bewusst begrenzter Umfang

FSEProbe ist ein Instrument für Recorder-QA, kein Computerspiel und kein Benchmark. Der synthetische Bildinhalt soll Bewegungen, Framefortschritt, Beschnitt und Skalierung sichtbar machen. Die zentrale Eigenschaft ist nicht grafischer Realismus, sondern ein nachvollziehbarer Präsentationspfad mit zeitlich zugeordneten Belegen.

Der Nutzerwunsch „nur und bestätigt exklusiv“ wird in zwei überprüfbare Anforderungen zerlegt: Die Anwendung fordert im Legacy-Modus ausschließlich den vorgesehenen DXGI-Modus an und beendet den Test bei lokal feststellbarem Verlust; die **unabhängige** Bestätigung gibt es erst für den ausgewerteten Lauf. Windows kann FSE-Anforderungen optimieren, ohne dass die App das allein aus `GetFullscreenState` erkennt [S01,S02]. Deshalb wird kein jederzeit garantiert exklusiver Livebetrieb vorgetäuscht. Ein echter verzögerungsbegrenzter Livebeobachter wäre ein eigener validierungspflichtiger Ausbau, nicht ein umbenannter Dateiparser.

Nicht im Umfang: Engine, Assets aus Spielen, Audio-Sync, HDR-Farbmetrik, automatisches Recorder-Hooking, D3D12, Treiberinstallation, Dienst, UI-Overlay, automatische FSO-/SAC-Umschaltung, erzwungener Moduswechsel bei jeder Hardware, thermischer Stresstest oder allgemeine Capture-Zertifizierung.

## 2. Architekturentscheidung

Die Anwendung ist native x64-C++20-Software. Win32 steuert Fenster/Eingaben; D3D11 erzeugt Gerät, Shaders und Renderziele; DXGI steuert Ausgabe und Swapchain. `Microsoft::WRL::ComPtr` übernimmt COM-Lebensdauer. Eigener kleiner Pixeltext vermeidet externe Fonts und Abhängigkeiten. HLSL wird **beim Build** mit dem Windows-SDK-FXC übersetzt und als Bytearray in die EXE eingebettet [S08]. Statische MSVC-Runtime reduziert eigene Laufzeit-DLLs. Das macht die EXE nicht SAC-vertrauenswürdig, verkleinert aber die Abhängigkeitsfläche.

Die Kontrollstrecke nutzt Flip-Discard mit zwei Buffern; die Legacy-Strecke Discard mit einem Backbuffer. Für moderne Anwendungen empfiehlt Microsoft Flip-Model [S05]; unser abweichender Legacy-Pfad ist allein dem Testziel geschuldet. Es gibt keine Fallback-Logik, die einen gescheiterten Legacy-Lauf still als Borderless fortsetzt.

Python-Standardbibliothek übernimmt ausschließlich Offline-Auswertung, synthetische Fixtures und Packaging. PowerShell übernimmt Prozessaufsicht und lesende Windows-Diagnose. Die zwei Interpreter müssen im Testsystem selbst zulässig sein; ein signierter Interpreter ist keine pauschale Freigabe für beliebigen nachgeladenen Code. Scheitert ein Helfer, gibt es keinen FSE-PASS.

## 3. Komponenten und Verantwortlichkeiten

| Datei/Bereich | Verantwortung | Darf nicht |
|---|---|---|
| `core.h` | Optionen, Wertebereiche, JSON-Escaping, Version | Windows-Status erfinden |
| `main.cpp` | Lebenszyklus, Fenster, Fokus, Markierungen, Timeout | unabhängiges FSE behaupten |
| `graphics.cpp` | Adapter/Output, Swapchain, Shader, Present, Cleanup | anderen Modus unterschieben |
| `diagnostic.cpp` | UTC/QPC, JSONL, Present-Ledger | alte Läufe überschreiben |
| `scene.cpp`, `tiny_font.h` | sichtbares Recorder-Testmuster | Fremdoverlay nutzen |
| `run_test.ps1` | getrennte Prozesse, Run-ID, Exitcodes, Evidence-Dateien | App erhöhen, SAC verändern |
| `start_observer.ps1` | optional separat erhöhter, begrenzter ETW-Prozess | global andere Traces stoppen |
| `verify_presentmon.py` | Identität, Zeit, Vollständigkeit, Modusbeleg | fehlende Daten in PASS umdeuten |
| CI und Packaging | reproduzierbarer Build, Offline-Gates, Hashes | physische Abnahme behaupten |

## 4. Datenfluss

```text
Operator bestätigt zulässigen physischen Testdesktop
  -> neuer Run-Ordner + zufällige Run-ID
  -> PresentMon 2.6.0/hashgeprüft startet
  -> Prozess lebt (noch KEIN ETW-Bereitschaftsnachweis)
  -> FSEProbe startet -> PID + Erstellungs-FILETIME
  -> app.jsonl + frames.csv und unabhängig presentmon.csv
  -> sauberes Ende und abgeschlossener Trace
  -> Datei-Hashes + session.json
  -> Auswerter -> summary.json + summary.txt
  -> getrennte manuelle Recorder-Bewertung
```

Alle QPC-Vergleiche erfolgen auf derselben Windows-Maschine. UTC dient der menschlichen Zuordnung und Eventlog-Suche, nicht der Präzisionskorrelation. `.NET Stopwatch` im Runner und `QueryPerformanceCounter` in der App liefern die hochauflösende Systemzeitbasis; die Frequenz muss übereinstimmen [S07]. Die Prozess-Erstellungszeit ergänzt die PID gegen Verwechslung bei wiederverwendeten IDs. Ein zufälliger Run-Ordner und eine benannte Mutex reduzieren Verwechslungen; sie sind keine Manipulationssicherheit.

## 5. Zustandsmaschine der Anwendung

`PARSE → LOG_READY → SINGLE_INSTANCE → ENVIRONMENT_CHECK → OUTPUT_SELECTED → WINDOWED_READY → REQUEST_FULLSCREEN (nur Legacy) → MODE_READY → WARMUP → MARKED_INTERVAL → INTERVAL_CLOSED → CLEANUP → END`.

Die anfängliche Fensteraktivierung hat eine feste Obergrenze; der Benutzer kann das Fenster einmal anklicken. Es werden keine wiederholten `SetForegroundWindow`-/SendKeys-Schleifen verwendet. Nach `MODE_READY` beendet Fokusverlust, Minimierung, Display-/DPI-Änderung oder abweichender DXGI-Zustand den gültigen Lauf. Nach einem Fehler gibt es kein automatisches Re-Entry: frischer Run statt vermischter Segmente.

`WM_SIZE` setzt nur Daten im Fensterzustand. Resize findet im Hauptloop statt, damit keine COM-Ausnahme durch `WndProc` läuft und kein verschachteltes Rendern während eines DXGI-Aufrufs entsteht. Ein Resize innerhalb eines markierten Intervalls invalidiert dieses. Initiale Nachrichten während der Vollbildtransition werden abgearbeitet, bevor der Test scharfgeschaltet wird.

## 6. Render- und Ressourcenplan

Desktopkoordinaten des gewählten Outputs bestimmen Fensterposition und initiale Größe. Auflösung/Refresh werden nicht auf 60 Hz erzwungen; kein `ChangeDisplaySettings`, kein `ALLOW_MODE_SWITCH`, kein automatischer `ResizeTarget`. Das ist eine bewusste Simplifikation für den ersten zuverlässigen Recorder-Test. Nach der Transition wird die tatsächliche Clientgröße abgefragt und der Backbuffer angepasst.

Ein Fullscreen-Triangle füllt den Hintergrund. Der Pixelshader führt höchstens 32 kleine Iterationen aus: off=0, low=4, medium=12, high=32. Ergebnisabhängigkeit verhindert, dass der Compiler alle Zusatzarbeit als unbenutzt entfernt. Der HUD-Pass zeichnet selbst erzeugte farbige Dreiecke mit einer begrenzten dynamischen Vertexbuffer-Kapazität. Das Backbuffer-Renderziel und alle Zustände werden pro Frame erneut gebunden. VSync ist fest an, zusätzlich wird ein CPU-FPS-Cap angewendet. Nicht „GPU 50 %“ versprechen: Auflösung, Treiber und Hardware verändern die reale Arbeit.

GPU-Last beginnt mit low; high ist nur nach erfolgreichem Basistest sinnvoll. Am schwächeren Rechner zunächst off verwenden. Die App behandelt `DXGI_STATUS_OCCLUDED` ebenso wie andere unerwartete Present-Statuswerte als nicht gültige Testpräsentation, statt sie als Erfolg durchzuwinken.

## 7. Instrumentierung und Vollständigkeit

`app.jsonl` enthält Startidentität, Output, Modusanforderung, Zustandsstichproben, Marker und Fehler. `frames.csv` enthält für **jeden** regulären Present-Aufruf Frameindex, QPC direkt davor/danach, HRESULT, DXGI-Status und Fokus. Das Ledger wird laufend geschrieben. Das kostet etwas I/O und verhindert eine Interpretation als reiner Performancebenchmark, macht aber Messlücken erkennbar.

PresentMon kann aus seiner Ausgabe fehlgeschlagene/verlorene Präsentationen auslassen [S10]. Daher genügt „30 gute Zeilen gefunden“ nicht. Der Auswerter rekonstruiert aus `CPUStartQPC + MsCPUBusy` einen Present-Zeitanker und ordnet ihn einem tatsächlichen App-Aufruf zu [S09,S10]. Jede relevante Ledger-Präsentation muss genau einmal im passenden Trace abgedeckt sein. Mehrdeutige Swapchains, widersprüchliche Zeiten oder Lücken führen zu UNVERIFIED.

Diese Rekonstruktion ist anhand der Dokumentation und synthetischer Daten implementiert, aber **noch nicht gegen einen echten Windows-Trace kalibriert**. Die erste Hardwareabnahme muss diese Zuordnung bestätigen. Wenn sie dort nicht funktioniert, darf der kleine Agent nicht die Toleranz beliebig erhöhen: zuerst echte CSV, Source-Version und API-Zeiten untersuchen. Ein nicht bestätigbarer Zeitbezug ist ein ehrliches Nicht-Ergebnis.

## 8. Ergebnisvertrag

Die App sagt nur `FULLSCREEN_REPORTED` oder `WINDOWED_REPORTED`; der Observer liefert PresentMode; die Aufnahme wird separat betrachtet. Ein erfolgreicher Legacy-Bericht benötigt die richtige Run-ID/PID/Erstellungszeit/Frequenz, zulässige lokale Umgebung, erfolgreichen Observer, vollständige Evidence-Dateien, korrekte DXGI-/Fokus-/Output-Zustände, mindestens 30 tatsächlich angezeigte Kernframes über mindestens zwei Sekunden und keine nichtklassische Präsentation im erweiterten Fenster.

Der Beginn/Ende erhält jeweils 250 ms äußeres Guard-Band; gezählt wird zusätzlich ein um 250 ms nach innen verkleinerter Kern. Das ist konservativ, keine Aussage über perfekte Scanout- oder Recorder-Zeiten. Lange CPU-Frames über 250 ms und Pausen über 500 ms verhindern einen kontinuierlichen Nachweis. Der Standardablauf fordert deshalb ein deutlich längeres markiertes Intervall.

`PASS` heißt Vertrag des ausgewählten Modus erfüllt. Bei Borderless lautet der Nachweis ausdrücklich `CONTROL_VERIFIED_NOT_FSE`. Ein synthetischer Positivtest heißt `SYNTHETIC_PASS`. Ein Scope-Fehler darf nicht durch einen grünen aggregierten Gesamtstatus verborgen werden.

## 9. Sicherheit und Fehlergrenzen

Kein App-Administratorrecht, kein UAC-Neustart durch PresentMon, keine Fremdprozess-Injektion. Ein optional erhöhter Observer wird vom Operator getrennt gestartet; seine ETW-Session trägt eine zufällige eigene Kennung. Cleanup beendet nur diese Session. Es wird kein systemweiter PresentMon-Trace gestoppt.

App-Control-Blockaden werden zeitlich und pfadbezogen untersucht. Ein lesbar gültiges Signaturzertifikat ist nicht gleich tatsächlicher SAC-Ausführbarkeit; fehlende Logeinträge ohne erfolgreichen Start beweisen ebenfalls nichts. Eine eigene Testinstallation ist eine manuelle organisatorische Option, keine automatische Lösung oder Freigabe zur Schutzabschaltung.

Normaler Fehlerpfad löst exklusives Vollbild, gibt COM-Ressourcen frei und zerstört das Fenster. Für Treiberhänger, Prozessabsturz oder Stromausfall kann dieser Code keine vollständige Wiederherstellung garantieren. Deshalb enthält die Operatoranleitung ein unabhängiges Abbruchverfahren. Ein Watchdog-Timeout invalidiert den Test und ist keine erfolgreiche Wiederherstellung.

## 10. Umsetzung und Freigabe

Die Dateien sind bereits vorhanden. Abfolge: S0 lesen/CI einrichten; S1 Windows-/Shaderbuild; S2 Offline- und Scriptgates; S3 Paket prüfen; S4 zulässige Hardware nachweisen; S5 Borderless-Kontrolle; S6 Legacy- und Negativläufe; S7 Recorderprüfung. Jeder Schritt hat Stop-Kriterien im Runbook. Die Lösung ist absichtlich nicht auf spätere Live-Entwicklung angewiesen: Ein belastbarer Offline-Bericht genügt für reproduzierbare QA-Läufe, solange die Benutzeroberfläche seine zeitlichen Grenzen klar benennt.
