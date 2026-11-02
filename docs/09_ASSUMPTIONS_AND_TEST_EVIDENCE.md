# 09 — Annahmen, tatsächlich ausgeführte Prüfungen und offene Abnahme

## Verbindlicher Status dieses Lieferpakets

Dies ist ein **Quellcode- und Implementierungskit**, kein auf der Zielhardware zertifiziertes Programm. Im Erstellungscontainer stehen Linux, Python und GNU-C++/CMake zur Verfügung. Windows, MSVC, Windows SDK/FXC, PowerShell und ein physischer Windows-Grafikdesktop stehen hier nicht zur Verfügung. Es wurde keine externe GitHub-Aktion in einem Nutzerrepository gestartet.

| Prüfbereich | Status | Bedeutung |
|---|---|---|
| Portable C++-Core-/Szenenlogik | lokal kompiliert und ausgeführt | kein Win32-/DXGI-Build |
| Python-Parser-/Protokolltests | lokal ausgeführt | synthetische Daten, kein Hardwarebeweis |
| Quellenstruktur/UTF-8/JSON/Python-Syntax | lokal geprüft | kein Ersatz für MSVC/FXC/PS |
| ZIP-CRC/Dateipfade/Manifest/SHA-256 | lokal geprüft | Integrität, kein Vertrauenszertifikat |
| Windows-MSVC-Build | NOT_EXECUTED | erster CI-Gate offen |
| HLSL-FXC-Kompilierung | NOT_EXECUTED | Windows-SDK-Gate offen |
| PowerShell 5.1/7-Ausführung | NOT_EXECUTED | nur Source-/Encodingreview hier |
| PresentMon-Binary --help/Lauf | NOT_EXECUTED | Release/Flags/Hash anhand Primärquellen geprüft |
| Start unter SAC | NOT_EXECUTED | keine Zusicherung für den Dev-PC |
| Physisches Legacy-FSE | NOT_EXECUTED | echte Windows-GPU-Abnahme nötig |
| Screenshot-/Videoqualität | NOT_EVALUATED | Recorder-/Mediendaten nicht vorliegend |
| Unabhängige Liveverifikation | nicht implementiert | Post-Run-Verifikation ist der feste Basisumfang |

Die exakten finalen Befehle, Testzahlen und Exitcodes stehen in `evidence/REVIEW_RESULTS.json` und den beiden Rundenlogs. Die Statusdatei `KIT_STATUS.json` kennzeichnet die noch nicht ausgeführten Bereiche maschinenlesbar. Die ausgelieferte Quelle enthält keine angeblich hier gebaute EXE und keine fingierten Windows-Logs.

## Was die vorhandenen Tests tatsächlich leisten

Der portable Build prüft C++-Parsing, Grenzwerte, Zeichenescaping und Szenengeometrie mit strengen Warnungen. Python prüft positive und negative Klassifikationspfade, Identität, integergenaue Zeitverarbeitung auch oberhalb 2^53, fehlende Messdaten, Prozess-/Dateifehler, Manifest-/ZIP-Grenzen und Statuswahrheit. Synthetische Fixture-Akten sind ausdrücklich beschriftet; ihr `SYNTHETIC_PASS` kann nicht als reales `FSE_VERIFIED` ausgegeben werden.

Zwei aufeinanderfolgende saubere Prüfrunden beziehen sich ausschließlich auf die hier ausführbaren Gates. Sie belegen nicht, dass Windows-spezifische API-Aufrufe oder PowerShell unter jeder Version fehlerfrei laufen. Der schwächere Agent erhält deshalb fertig formulierte CI-/Hardwaretickets statt die Lücke verschwiegen zu bekommen.

## Bekannte, bewusst offene Integrationsannahmen

**Zeitkorrelation:** Die Interpretation von PresentMon `CPUStartQPC + MsCPUBusy` als Present-Zeitanker folgt der Versionsdokumentation und Ausgabeimplementierung. Ihre praktische Zuordnung zum App-Ledger wurde hier noch nicht an realen ETW-Daten geprüft. Der Algorithmus verweigert einen Nachweis bei Abweichung. Das ist der wichtigste erste Hardwaregate.

**Vollbildverfügbarkeit:** Kein Windows-/Treiber-/Monitor-Setup wird als garantiert Legacy-fähig behauptet. Das Tool fordert an, misst und berichtet. Eine transparente Windows-Optimierung oder ein Recorder-Overlay kann die beobachtete Klasse ändern.

**SAC:** Die Nutzerdatei zeigt erfolgreiches .NET-Single-File-Publish und zugleich wiederkehrende Blocks anderer Formen. Daraus lässt sich weder die Zulässigkeit dieser C++-EXE noch die aller Python-/PresentMon-Abhängigkeiten ableiten. Selbst eine später erfolgreiche Ausführung gilt zunächst für diesen konkreten Build und diese Umgebung.

**Physischer Desktop:** Der Runner verlangt eine Operatorbestätigung und die App verweigert erkannte RDP-/Session-0-Kontexte. Das ist keine lückenlose Erkennung aller VMs, Capturekarten, virtuellen Displays oder Remote-Steuerverfahren. Die Hardwareakte bleibt erforderlich.

**Recorder:** Es gibt keinen Zugriff auf eine spezifische Recorder-API. Marker sind Operator- oder Diagnosemarker. Capture-Start/Stop, exaktes Frame-Matching und Medienqualität werden nicht automatisch behauptet. Audio und HDR-Referenzmessung gehören nicht zum Basisumfang.

**Wiederherstellung:** Normales Cleanup ist implementiert; ein harter GPU-/Kernelhänger kann es verhindern. Die unabhängige Windows-Abbruchmöglichkeit gehört zur manuellen Abnahme.

## Änderungen gegenüber der vorbereitenden Spezifikation

Die Kernentscheidungen bleiben erhalten. Zusätzlich eingebaut wurde ein vollständiges App-Present-Ledger, um fehlende ETW-Zeilen nicht zu übersehen. Shader werden nicht erst zur Laufzeit kompiliert; es gibt keine DirectXTK-/Font-Abhängigkeit. Die Grafikdateien sind klein aufgeteilt, aber nicht künstlich in ein Framework zerlegt. Der gemeinsame DXGI-Factory-Swapchainpfad wird für beide Modi verwendet; ein optionaler dritter Flip-Fullscreen-Modus wurde zugunsten klarer Abnahme weggelassen.

„Nur bestätigt laufen“ wird nicht als unerfüllte Livezusage kaschiert: Die Anwendung bleibt im HUD ausdrücklich unbestätigt; ein auswertbarer Legacy-Bericht kann anschließend das geprüfte Intervall bestätigen. Die GO-Vorbereitung erlaubt diesen sicheren Post-Run-Basispfad ausdrücklich. Ein echter Livekanal müsste später Messlatenz, Lücken, Prozesszuordnung und Reaktionszeit mit eigenem Testplan beweisen.
