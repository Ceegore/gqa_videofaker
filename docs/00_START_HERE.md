# 00 — Start und kürzester zulässiger Weg

## 1. Was bereits vorhanden ist

Das Kit enthält die Implementierung, nicht nur einen Bauvorschlag. Der Agent muss zuerst den Windows-Build überprüfen und anschließend die Hardwareabnahme ausführen. Die auf Linux ausgeführten Prüfungen stehen in `evidence/`. Ein positiver Parser-Test mit erfundenen Frames heißt `SYNTHETIC_PASS`, niemals `FSE_VERIFIED`.

**Standardweg:** Quellcode im eigenen Repository → manueller Windows-CI-Job → heruntergeladenes unsigniertes Testpaket → erlaubte physische Windows-Testinstallation → getrennte Auswertung der Aufnahme. Auf dem SAC-Dev-PC keine unbekannte EXE-Ausführung voraussetzen. Es ist kein zusätzliches Gerät bereits als vorhanden angenommen.

## 2. Voraussetzungen

Für CI: eigenes freigegebenes GitHub-Repository, aktivierte Actions und ausreichendes Kontingent. Der Workflow wird nur manuell über `workflow_dispatch` ausgelöst. Er verwendet Windows 2025, entdeckt die vorhandene Visual-Studio-Version und installiert Python 3.13 über die offizielle Action. Keine Zugangsdaten oder Signierschlüssel in Dateien eintragen.

Für einen zulässigen lokalen Build auf einem **dafür freigegebenen** System: Visual Studio/Build Tools mit „Desktopentwicklung mit C++“, x64-MSVC, Windows SDK mit `fxc.exe`, CMake ab 3.24 und Python ab 3.10. Die konkrete Visual-Studio-Version muss vom installierten CMake unterstützt werden. `configure_windows.ps1` entdeckt das und stoppt andernfalls. Die App selbst benötigt weder Python noch PresentMon zum Zeichnen; nur der überwachte Auswertungslauf benötigt beide.

Für Hardwareabnahme: lokale interaktive Windows-10/11-x64-Sitzung, reale monitorverbundene GPU mit D3D-Feature-Level 11.0, zugelassene Ausführung aller benötigten Komponenten, installiertes Recorder-Tool. RDP, virtuelle Monitore, Windows Sandbox und CI sind keine Ersatzabnahme. Die erste Abnahme verwendet SDR und normale Desktopauflösung; HDR/VRR/Hybrid-GPU werden erst danach separat getestet.

## 3. Windows-CI zuerst

Entpackte Dateien einschließlich `.github/` in das dafür vorgesehene Repository übernehmen. GitHub → Actions → „Windows build and offline gates - NOT hardware FSE“ → Run workflow. Ohne diesen expliziten Start wird nichts ausgeführt. Der Workflow baut MSVC und vier HLSL-Einstiegspunkte, prüft portable Logik/Python, PowerShell 7/5.1 und einen nichtgrafischen App-Selbsttest. Er startet **keinen Vollbildtest**.

Nach grünem Job das Artefakt `FSEProbe-Windows-x64-UNSIGNED-NOT-HARDWARE-TESTED` entnehmen. Darin liegt das innere Release-ZIP mit SHA-256-Datei. Die enthaltene `BUILD_STATUS.json` unterscheidet CI-PASS, fehlende Signierung und fehlende Hardwareabnahme. Ein roter Job wird anhand seiner tatsächlichen Logs bearbeitet, nicht durch Entfernen von Prüfungen.

Manuelle äquivalente Build-Befehle auf einem freigegebenen Build-/Testsystem, aus der Kit-Wurzel:

```powershell
.\tools\configure_windows.ps1
cmake --build build --config Release --parallel 2
ctest --test-dir build -C Release --output-on-failure
```

Der dritte Befehl führt neue Test-Binaries aus und gehört **nicht** als Standard auf den geschützten Dev-PC. Dort CI nutzen. Die `--self-test`-Ausführung ist ausdrücklich kein Grafiktest.

## 4. PresentMon beschaffen, ohne es automatisch auszuführen

Im Quellkit oder im entpackten Runtime-Paket, unter einem bereits zulässigen Python:

```powershell
python tools/get_presentmon.py --download --output tools/PresentMon-2.6.0-x64.exe
```

Der Helfer lädt nur die festgelegte offizielle Console-Datei und prüft ihren veröffentlichten SHA-256. Er startet sie nicht und entfernt keine Herkunftsmarkierung. Wird der Download oder spätere Start blockiert, bleibt die Schutzkonfiguration unangetastet. Alternativ die offizielle Datei manuell beziehen und ihren Hash mit `tools/presentmon.lock.json` vergleichen. Die Intel-GUI, der Dienst und das neuere `presentmon-cli` sind nicht austauschbar mit dieser Console-EXE.

## 5. Erster Hardwarelauf: Kontrollmodus

Die folgenden Befehle gelten für das **Runtime-Paket**, in dem `bin/FSEProbe.exe` liegt. Im Quellbaum liegt der Release-Build stattdessen unter `build/Release/FSEProbe.exe`. Nicht auf dem SAC-Dev-PC starten, solange dessen Ausführbarkeit nicht rechtmäßig geklärt ist.

```powershell
.\bin\FSEProbe.exe --list-monitors
.\tools\run_test.ps1 -App .\bin\FSEProbe.exe `
  -PresentMon .\tools\PresentMon-2.6.0-x64.exe `
  -PhysicalDesktop -Mode borderless-control -Load low -Duration 30 -AutoMark
```

`-PhysicalDesktop` ist eine bewusste Operatorbestätigung, kein technischer VM-Bypass. Monitor 0 ist die erste angehängte DXGI-Ausgabe, nicht zwingend Windows-Anzeige „1“. Bei mehreren Monitoren mit `--list-monitors` identifizieren und `-Monitor` setzen.

## 6. Legacy-Lauf und Recorder

Recorder vorher konfigurieren; Hotkeys dürfen F8/F9/ESC nicht kollidieren. Kein Alt-Tab nach dem Start. Die Anwendung nötigenfalls einmal innerhalb des anfänglichen Fokusfensters anklicken.

```powershell
.\tools\run_test.ps1 -App .\bin\FSEProbe.exe `
  -PresentMon .\tools\PresentMon-2.6.0-x64.exe `
  -PhysicalDesktop -Mode legacy-exclusive -Load low -Duration 60
```

Nach „READY“ Aufnahme per Recorder-Hotkey starten. F8 markiert den zu bewertenden Beginn. Mindestens fünf Sekunden beobachten und aufnehmen. F9 markiert das Ende; noch mindestens eine Sekunde weiter aufnehmen, dann Recorder stoppen. Bis zum normalen Ende oder nach ausreichendem Nachlauf ESC drücken. Ein früher Abbruch innerhalb des markierten Intervalls wird ungültig. F8/F9 messen **keine** echten Recorder-API-Zeiten.

Falls PresentMon zusätzliche ETW-Rechte braucht: denselben Runner mit `-ExternalObserver` starten. Er zeigt einen konkreten Befehl für `start_observer.ps1` in einer **separat** vom Operator autorisierten erhöhten PowerShell. Nur dieser Beobachter wird erhöht. Der normale Runner verweigert Administratorrechte, damit auch die App nicht versehentlich erhöht läuft.

## 7. Ergebnis lesen

In `logs/<run-id>/summary.json` und `.txt` stehen unabhängige Achsen. Nur `presentation_proof=FSE_VERIFIED` bei `evidence_kind=REAL_WINDOWS_RUN` belegt den klassischen Pfad im markierten und geprüften Zeitraum. `CONTROL_VERIFIED_NOT_FSE` ist ein korrekter Kontrolllauf, kein FSE-PASS. `recorder_result=NOT_EVALUATED` bleibt stehen, bis Ihr das konkrete Bild/Video separat beurteilt habt.

Exitcodes der Auswertung: 0 = der gewählte Vertrag erfüllt; 10 = Gegenbeleg/Fehler; 11 = unzureichende Evidenz; 42 = App-Control-Block. **0 bei einem Kontrolllauf oder einer synthetischen Fixture ist kein FSE-Nachweis.** Die App allein benutzt andere Exitcodes und gibt bei normalem Ende 0 zurück, ohne PresentMon zu kennen.
