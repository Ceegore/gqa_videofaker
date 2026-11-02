# 05 — Kopierfertige Tickets für den schwächeren Agenten

## Startprompt

> Übernimm das vorhandene FSEProbe-Kit, lies AGENTS.md sowie Dokumente 00, 09 und 10. Verändere die Architektur nicht. Arbeite die nachfolgenden Tickets nacheinander ab. Verwende für Windows-Build und Offline-Tests den vorhandenen CI-Workflow; auf dem SAC-Dev-PC keine selbstgebauten Binaries starten. Ein tatsächlicher App-Control-Block ist Exit 42 und kein Produktdefekt. Melde pro Ticket Dateien, exakten Befehl, echte Testausgabe, Exitcode, Beleg und offene Grenze. Fehlende Windows-Hardware niemals als bestanden markieren. Negative Parserprüfungen und Zeit-/Hash-/Identitätsgates nicht entfernen.

## Ticket 00 — Arbeitsstand und Schutzgrenzen

**Eingabe:** gesamtes Kit, `input_reference/SACsolutions_USER_ORIGINAL.md`, `KIT_STATUS.json`. **Erlaubt:** Dokumentation eines vorhandenen Repository-/CI-/Testsystempfads; keine Sicherheitsänderung. **Aktion:** Paketintegrität anhand SHA256SUMS überprüfen und Statusdatei lesen. **Mini-Test:** alle vorgesehenen Dateien vorhanden; kein unbekanntes Binary ausführen. **Stop:** Hashabweichung, unklare Herkunft oder fehlende Freigabe für Repositoryänderung. **Selbstkontrolle:** getrennte Felder für Quellprüfung, Windows-Build, SAC-Ausführung und Hardware. **Ausgabe:** „00 READY“ mit konkreter CI-Route, Hardware sonst NOT_EXECUTED.

## Ticket 01 — CI ohne Grafik einrichten

**Eingabe:** `.github/workflows/windows-ci.yml`, `tools/configure_windows.ps1`, CMake. **Erlaubt:** nur CI-/Toolchainpfade korrigieren, falls der reale Runner dies erfordert. **Aktion:** Dateien in das ausdrücklich vorgesehene Repository übernehmen, manuellen Workflow auslösen. **Mini-Test:** Python/CMakestrukturprüfung und Generatorerkennung. **Stop:** fehlende SDK-/MSVC-Komponente, Actions-Rechte oder Kontingent; nicht lokal auf den SAC-Host ausweichen. **Selbstkontrolle:** permissions contents:read, kein Signierschlüssel, kein Hardware-PASS. **Ausgabe:** konkrete Job-URL und Toolchainversion oder sauberer Blocker.

## Ticket 02 — Windows-/HLSL-Build

**Eingabe:** `src/*`, CMake, realer Compilerlog. **Erlaubt:** minimal nötige Compiler-/SDK-/Typkorrekturen; keine neue Engine. **Aktion:** `cmake --build build --config Release --parallel 2`. **Mini-Test:** alle vier FXC-Header, `FSEProbe.exe`, `probe_core_tests.exe`; null Compilerwarnungen bei /W4 /WX. **Stop:** nicht verstandener Fehler; keine /WX-Abschaltung, keine leeren Shaderattrappen. **Selbstkontrolle:** x64, asInvoker, eingebettete Shader, keine D3DCompile-Runtime. **Ausgabe:** Buildlog + tatsächlicher Status. Falls hier noch nie Windows gebaut wurde, nicht „bereits vorher getestet“ behaupten.

## Ticket 03 — Offline-Gates und Prozesshelfer

**Eingabe:** Tests/Tools, gebaute Binaries. **Erlaubt:** nur reproduzierte Fehler in Parser/Core/Runner beheben. **Aktion:** CTest im CI, `tests/test_runner.ps1` in PS7 und PS5.1. **Mini-Test:** positive synthetische Fälle, mindestens ein einzelner falscher PresentMode, fehlende Zeile, boolescher Exitcode, Timeout und Argumentpfad mit Leerzeichen. **Stop:** Testausführung blockiert/abgebrochen; kein Null-Exit als Erfolg. **Selbstkontrolle:** tatsächliche Testkörper gelaufen, SYNTHETIC_PASS bleibt synthetisch. **Ausgabe:** CTest/JUnit, Script-Ausgabe, CodeIntegrity falls notwendig.

## Ticket 04 — Abnahmefähiges Paket erzeugen

**Eingabe:** erfolgreicher Windows-CI-Lauf, `package_release.py`. **Erlaubt:** Packagingfehler korrigieren, keine Fake-Signatur. **Aktion:** CI-Paketschritt ausführen. **Mini-Test:** ZIP CRC, vollständiger Manifestabgleich, AMD64-PE32+-Header, kein Traversal/Symlink, BUILD_STATUS korrekt. **Stop:** Binärdatei fehlt oder Hash passt nicht. **Selbstkontrolle:** „UNSIGNED / NOT HARDWARE TESTED“ bleibt sichtbar. **Ausgabe:** Artefaktname und SHA-256. CI-PASS ist keine SAC-Freigabe.

## Ticket 05 — Testumgebung und Beobachter

**Eingabe:** Paket, erlaubte physische Testinstallation, PresentMonlock. **Erlaubt:** lesende Diagnose und vom Operator ausdrücklich freigegebener Start; keine Policy-/Boot-/Treiberinstallation. **Aktion:** Dokumente 00/04/10 befolgen; PresentMon offiziell beziehen/hashprüfen. **Mini-Test:** alle gestarteten Programme wirklich lauffähig; Monitorindex korrekt; nicht RDP/VM. **Stop:** keine geeignete Umgebung oder Ausführungsblock. **Selbstkontrolle:** erhöhte ETW-Rechte nur für separaten Beobachter; Hauptapp uneleviert. **Ausgabe:** Environment-/Securitybelege oder HARDWARE_NOT_EXECUTED.

## Ticket 06 — Borderless und Zeitzuordnung

**Eingabe:** reale Control-Logs. **Erlaubt:** nachgewiesene API-/Tracezuordnungsfehler minimal korrigieren, Tests ergänzen. **Aktion:** 30-Sekunden-Control-AutoMark-Run. **Mini-Test:** eine Swapchain, eine PID, QPC-Frequenz stimmt überein, vollständige Present-Ledger-Abdeckung, Kontrollstatus nicht FSE. **Stop:** UNVERIFIED_TIME_RECONCILIATION, Observerdiagnostik oder Frame-Lücke. **Selbstkontrolle:** keine Toleranzänderung ohne gemessene Ursache; keine künstlichen Frames in realer Akte. **Ausgabe:** Rawlogs und Kontrollbericht. Dies ist die erste reale Kalibrierung des Auswerters.

## Ticket 07 — Legacy und negative Hardwarefälle

**Eingabe:** erfolgreicher Kontrolllauf, Operatorplan. **Erlaubt:** neue Runs und dokumentierte benutzersichtige FSO-Vergleiche; keine Sicherheitsänderung. **Aktion:** Legacy-AutoMark, dann Operator-Marker; Alt-Tab-/Overlay-Negativlauf. **Mini-Test:** klassischer Ownership-Pfad während des richtigen Fensters; nichtklassischer Einzelbefund verwirft den Lauf. **Stop:** Legacy auf diesem System nicht nachgewiesen; keinen API-basierten Ersatz-PASS einführen. **Selbstkontrolle:** DXGI-Status und externe Verifikation getrennt. **Ausgabe:** positive und negative reale Belegakten oder offen erklärte Hardwaregrenze.

## Ticket 08 — Recorderfunktion

**Eingabe:** konkreter Recorder, dokumentiertes Backend, Screenshot und Video. **Erlaubt:** Recorder-Testkonfiguration, keine Hooks in FSEProbe oder Fremdprozesse. **Aktion:** Dokument 04, separate Bewertungsvorlage ausfüllen. **Mini-Test:** Ecken, Crop, Framefortschritt, Freeze, Auflösung, erwartete Samplingrate. **Stop:** fehlende/ungeprüfte Mediendatei. **Selbstkontrolle:** ETW-PASS allein macht kein Capture-PASS; übersprungene Frame-IDs bei niedrigerer Recorder-FPS nicht pauschal Fehler. **Ausgabe:** Assessment mit Hash und reproduzierbaren Befunden.

## Ticket 09 — Abschluss ohne Regressionsschleife

**Eingabe:** letzter korrigierter Commit, alle Belege. **Erlaubt:** reine Berichts-/Paketkorrekturen oder gezielte Fehlerbehebung. **Aktion:** zwei vollständige prüfbare Review-/Testdurchläufe ohne neue Änderungen. Bei Änderung beginnt die Zählung erneut. Wiederholte native Tests nur auf CI/Testsystem, nicht auf geschütztem Dev-PC. **Mini-Test:** Commands/Docs stimmen, negative Fälle bleiben negativ, Manifest stimmt. **Stop:** offene P0-Fehler; keine falsche Gesamtfreigabe. **Selbstkontrolle:** Windows-/Hardware-/Recordergrenzen stehen explizit im Abschluss. **Ausgabe:** finale Statusmatrix, ZIP, offene Punkte statt „garantiert fehlerfrei“.

## Einheitliches Ticketprotokoll

```text
Ticket:
Commit / Paket-Hash:
Geänderte Dateien:
Befehl:
Echter Exitcode:
Belegdatei:
Ergebnis: PASS / FAIL / BLOCKED_BY_APP_CONTROL / NOT_EXECUTED
Was dieses Ergebnis NICHT beweist:
Nächster freigegebener Schritt:
```

Ein leerer Beleg wird nicht mit erfundener Testausgabe ersetzt. Im Paket vorhandene Dateien sind bereits Implementierung; sie sollen nicht durch den Agenten erneut frei entworfen werden.
