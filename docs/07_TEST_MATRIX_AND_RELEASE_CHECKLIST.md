# 07 — Testmatrix, negative Gates und Freigabe

## Vier Ebenen, vier getrennte Aussagen

1. **Portable Logik/Dateien:** GNU-C++-Build, Coretests, Python-Parser-/Protokolltests, Quellenstruktur und Paketintegrität. Hier tatsächlich ausgeführt; exakte Logs in `evidence/`.
2. **Windows-Build/Prozesshelfer:** MSVC, FXC, Manifest, PS5.1/7, asInvoker-Start ohne Grafik. Workflow vorhanden, hier nicht ausgeführt.
3. **Physische Präsentation:** D3D11, Monitor, Fokus, FSO, PresentMon, reale Zeitzuordnung und Ledgerabdeckung. Hier nicht ausgeführt.
4. **Recorderqualität:** reale Screenshot-/Videodateien prüfen. Hier nicht ausgeführt.

Ein Bestehen einer Ebene ersetzt keine höhere. Ein synthetischer positiver Test ist keine vierte Ebene und keine Hardwareprobe.

## Automatische Fälle

`tests/test_presentmon_parser.py` deckt positive Legacy Flip/Copy und nichtklassische Kontrolle ab. Negative Fälle umfassen Independent Flip, Hardware Composed, Composed, einen einzigen falschen Frame, falsche/zusätzliche PID, unbekannte Runtime, mehrere Swapchains, verlorene/duplizierte Frames, QPC in Millisekunden statt Ticks, Float-/Overflowwerte, fehlende Zeitspalte, NaN, lange CPU-Zeit, nicht angezeigte Frames, falsche Hashes/Versionen, später Observer, stderr/Warnungen, falsche Run-ID/FILETIME/Frequenz, Fokus-/Displayverlust, falsche Marker, unvollständige Logs und App-Control-Block.

`tests/test_protocol.py` prüft Lockkonsistenz, tatsächlich verwendete Ereignisnamen, fehlende Runtime-Shaderkompilierung, feste Shadergrenze, HUD-Wahrheit, synthetische Dateien, PE-Ablehnung sowie ZIP-Roundtrip/Manipulation/Traversal/Kollision. `core_tests.cpp` prüft CLI-Grenzen, JSON-Escaping, Glyphen und viele erzeugte Vertices. Die vielen Vertexassertionen sind nicht als ebenso viele unabhängige Testfälle zu zählen.

`tests/test_runner.ps1` wird erst in Windows-CI wirklich ausgeführt. Es parst die Scripts und testet Argumentquoting, Leerargumente, Backslashes, Exitcode 7 und Timeout an kurzlebigen Pythonprozessen. Es startet kein Vollbildfenster. `check_source.py` ist eine zusätzliche Struktur-/Encodingprüfung, **kein** Ersatz für einen PowerShell-/MSVC-Compiler.

## Manuelle Hauptmatrix

| ID | Test | Erwartung | Status in diesem Kit |
|---|---|---|---|
| HW-01 | Kontrollmodus ohne Recorder | CONTROL_VERIFIED_NOT_FSE, richtige Ecken/Monitor | NOT_EXECUTED |
| HW-02 | Legacy ohne Recorder | FSE_VERIFIED nur mit vollständigem ETW-Vertrag | NOT_EXECUTED |
| HW-03 | FSO-Zustände getrennt | tatsächlichen Pfad melden, nicht Häkchen interpretieren | NOT_EXECUTED |
| HW-04 | Alt-Tab im Markerfenster | ungültiger Lauf, kein Legacy-PASS | NOT_EXECUTED |
| HW-05 | Recorderoverlay | Moduswechsel/Focusverlust erkennen oder vorhandene Evidenz korrekt auswerten | NOT_EXECUTED |
| HW-06 | ESC/Timeout/normaler Fehler | beenden, Cleanup protokollieren, Desktop prüfen | NOT_EXECUTED |
| HW-07 | Device removed/reset | Fehlergrund, kein Fortsetzen mit Erfolg | NOT_EXECUTED |
| HW-08 | Multi-Monitor/HiDPI | Output wählen; keine Beschneidung/unerklärte Verschiebung | NOT_EXECUTED |
| HW-09 | 59,94/60/hohe Refresh-Rate | keine erzwungene 60-Hz-Umstellung, VSync/Caps transparent | NOT_EXECUTED |
| HW-10 | RDP/Session 0/VM | verweigert bzw. keine physische Attestation | NOT_EXECUTED |
| HW-11 | Falscher Monitor/zweite Instanz | klarer Start-/Umgebungsfehler | NOT_EXECUTED |
| HW-12 | off/low/medium/high | korrekte begrenzte Last, keine Prozentbehauptung | NOT_EXECUTED |
| HW-13 | ETW-Rechte/fehlender Observer | UNVERIFIED, optional Observer separat erhöhen | NOT_EXECUTED |
| HW-14 | SAC-/DLL-/Scriptblock | BLOCKED oder unbekannte Umgebung, kein Produkt-PASS | NOT_EXECUTED |
| CAP-01 | Screenshot | Ecken, Run-ID, Frame-ID, kein Schwarz/Crop | NOT_EXECUTED |
| CAP-02 | Video | plausible Framefolge, Bewegung, keine unerklärten Freezes | NOT_EXECUTED |
| CAP-03 | Capture defekt bei FSE-PASS | Recorder separat FAIL, kein FSE-Belegverlust erfunden | NOT_EXECUTED |
| CAP-04 | Video nicht angesehen | NOT_EVALUATED | NOT_EXECUTED |

Die ursprünglichen 44 Kriterien bleiben in `input_reference/ABNAHME_MATRIX.csv` erhalten. Die erweiterte `docs/ACCEPTANCE_MATRIX.csv` ordnet weitere Fälle zu und startet ohne fingierte Hardwarefreigabe.

## Releaseblocker

API-Flag als FSE-Beweis; Independent Flip als Legacy; falsche PID/Swapchain/Zeiten; fehlende Frames ignoriert; fehlender Observer als PASS; Livebehauptung ohne validierten Livekanal; CI/Sandbox als physische Abnahme; unbekannte Recorderqualität als Erfolg; Script-/SAC-Bypass; nicht getesteter Native-Code als getestet; abgeschnittene Quellcodedateien; beschädigte ZIP-/Hashliste.

## Abschlussprozedur

Nach der letzten Änderung zwei komplette prüfbare Durchläufe. Pro Runde Core ausführen, Python ausführen, Quellenprüfung, Paketprüfung. Danach Quellen unverändert lassen; Ergebnislogs sind zusätzliche Belege. Wird funktionaler Code verändert, beide Runden wiederholen. Auf Windows ebenfalls CI-Gates erneut ausführen; Hardware nur soweit tatsächlich verfügbar. Zwei saubere Runden sind ein Qualitätsgate, **kein mathematischer Beweis der Fehlerfreiheit**.
