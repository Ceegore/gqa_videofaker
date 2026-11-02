# 11 — CI und Testlabor

## Windows-CI-Vertrag

Der manuelle Workflow verwendet `windows-2025`, `contents: read`, keine persistierten Checkout-Credentials und keine Signiergeheimnisse. Ein 20-Minuten-Joblimit begrenzt Fehlerschleifen; Artefakte werden sieben Tage aufbewahrt. Das sind Workfloweinstellungen, keine Zeit-/Kostenversprechen. Auf privaten Repositories tatsächliches Actions-Kontingent prüfen.

`configure_windows.ps1` ruft `vswhere` für vorhandene x64-C++-Installationen auf und gleicht den VS-Hauptstand gegen `cmake -E capabilities` ab. Dadurch wird weder VS2022 noch ein künftiges Image still vorausgesetzt. CMake findet SDK-FXC unter den installierten Kit-Bin-Verzeichnissen oder einem ausdrücklich angegebenen `FXC_EXECUTABLE`. Fehlende Komponenten stoppen den Build; es erfolgt kein ungefragter Installerstart.

Pipeline: Checkout → Python 3.13 → Quellenprüfung → Configure → Release-MSVC/FXC → PS7-Gate → PS5.1-Gate → CTest mit begrenzten Prozessen → Paketskript → Artefakte. Die CTest-Ziele sind portable Coretests, Python und `FSEProbe --self-test` ohne Grafik. Kein Desktop-/FSE-Test wird auf dem gehosteten Runner als bestanden behauptet.

## Reproduktion

Auf einem dafür freigegebenen Build-/Testsystem:

```powershell
.\tools\configure_windows.ps1
cmake --build build --config Release --parallel 2
.\tests\test_runner.ps1
ctest --test-dir build -C Release --output-on-failure
python tools/package_release.py --exe build/Release/FSEProbe.exe `
  --output dist/FSEProbe-Windows-x64-UNSIGNED.zip
```

Ohne `--ci-build-pass` setzt der Packager CI-Status auf NOT_ATTESTED. Das Flag darf nur nach wirklich erfolgreich abgeschlossenen CI-Gates verwendet werden; der Workflow tut dies im entsprechenden Erfolgszweig. Packaging kann allein keinen Test beweisen. Der Packager prüft den PE-Header als AMD64/PE32+, kopiert nur die tatsächlich vorhandene Datei, erzeugt Hashmanifest/ZIP und startet oder signiert nichts.

Für reine portable Arbeit in einem erlaubten Linux-/CI-System:

```sh
cmake -S . -B build-portable -DFSEPROBE_PORTABLE_TESTS_ONLY=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build-portable --parallel 2
ctest --test-dir build-portable --output-on-failure
```

Diese Befehle erzeugen ausschließlich den portablen Testteil, keine Windows-App. `check_source.py` ist ein ergänzender statischer Check. Er prüft unter anderem PowerShell-BOM/CRLF und verhindert bestimmte verbotene aktive Policyoperationen, kann aber weder vollständige Sicherheit noch PowerShell-Semantik beweisen.

## Abnahmelabor in drei Stationen

**Station A — Build:** Ausgabeartefakt, Toolchain, Quellstand, JUnit/Logs, ZIP-SHA-256. Ergebnis kann CI_BUILD_PASS sein; kein SAC- oder FSE-Feld wird dadurch positiv.

**Station B — Präsentationskette:** lokale Windows-10/11-Sitzung, passende GPU, realer Monitor, eindeutig ausgewähltes Output. Zuerst Control und Zeitzuordnung, dann Legacy. Alle ETW-/Appdateien im eigenen Run-Ordner. Operatorattestation ergänzt, aber ersetzt nicht die Belegkette. Erst hier kann `FSE_VERIFIED` für den markierten Abschnitt entstehen.

**Station C — Recorder:** identisches Testsystem, konkrete Recorderkonfiguration, vorher vorbereitete Hotkeys. Screenshot/Video prüfen und Hashes sichern. Ein guter FSE-Bericht kann zusammen mit einem schlechten Recorderergebnis vorliegen; das ist ein wertvoller reproduzierbarer Fehlerfall.

## Nicht automatisch vorhandene Infrastruktur

Ein zweiter PC, zusätzliche SSD, Windows-Lizenz, Codesigning-Zertifikat, Recorderinstallation oder nutzbares GitHub-Kontingent wird nicht als vorhanden behauptet. Ohne freigegebenes Labor wird die Quelle trotzdem gebaut und offline geprüft; die Hardwarefelder bleiben NOT_EXECUTED. Der Agent darf weder im Hintergrund Infrastruktur bestellen noch eigenmächtig einen Boot-/Sicherheitsumbau durchführen.

## Versionswechsel und Wartung

PresentMon-Haupt-/Patchwechsel nicht automatisch akzeptieren. Neuen offiziellen Hash, CLI, CSV-Header, Timingsemantik, synthetische Regressionen und echte Referenzläufe prüfen. Windows-/Treiberupdates können den Präsentationspfad ändern; den Softwarestand pro Run protokollieren und nach relevanten Updates Control/Legacy/Recorder neu prüfen. Automatische Überwachung oder geplante Tests sind in diesem Kit nicht eingerichtet.
