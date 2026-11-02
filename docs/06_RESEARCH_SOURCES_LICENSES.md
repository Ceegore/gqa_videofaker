# 06 — Quellenregister und Versionsentscheidungen

**Webprüfung: 2. November 2026.** Nur Hersteller-/Originalprojektquellen. Veröffentlichungsdatum und Abrufdatum sind nicht gleich; älteren API-Seiten wird keine fiktive neue Veröffentlichung zugeschrieben. Die vorliegenden Webbefunde ersetzen keinen Binärstart. Quellcode-/Hashprüfungen, lokal ausgeführte Tests und noch ausstehende Tests sind in Dokument 09 getrennt.

| ID | Primärquelle | Verwendeter Befund |
|---|---|---|
| S01 | https://devblogs.microsoft.com/directx/demystifying-full-screen-optimizations/ | FSO kann eine Exklusivanforderung transparent optimieren; API-Flag allein reicht nicht. |
| S02 | https://learn.microsoft.com/en-us/windows/win32/api/dxgi/nf-dxgi-idxgiswapchain-setfullscreenstate | Vollbildanforderung, Fokus-/Remote-/Verfügbarkeitsfehler, Transitionstatus. |
| S03 | https://learn.microsoft.com/en-us/windows/win32/api/dxgi/nf-dxgi-idxgiswapchain-resizebuffers | Backbufferreferenzen lösen, Resize, neues Renderziel. |
| S04 | https://learn.microsoft.com/en-us/windows/win32/api/dxgi/nf-dxgi-idxgifactory-makewindowassociation | Alt+Enter-Behandlung explizit kontrollieren. |
| S05 | https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/for-best-performance--use-dxgi-flip-model | Moderne Flip-Empfehlung, Independent Flip nicht mit Legacy gleichsetzen. |
| S06 | https://learn.microsoft.com/en-us/windows/win32/api/d3d11/nf-d3d11-d3d11createdevice | Expliziter Adapter und D3D_DRIVER_TYPE_UNKNOWN. |
| S07 | https://learn.microsoft.com/en-us/windows/win32/sysinfo/acquiring-high-resolution-time-stamps | QPC-Zeitbasis, Frequenz und Abgrenzung zu UTC. |
| S08 | https://learn.microsoft.com/en-us/windows/win32/direct3dtools/dx-graphics-tools-fxc-syntax | FXC /T, /E, /Fh, /Vn, /WX; Buildzeitkompilierung. |
| S09 | https://raw.githubusercontent.com/GameTechDev/PresentMon/v2.6.0/README-ConsoleApplication.md | Gepinnte Console-Flags, CSV-Spalten und Moduslabels. |
| S10 | https://raw.githubusercontent.com/GameTechDev/PresentMon/v2.6.0/PresentMon/OutputThread.cpp | Output-/Zeitmodell; verlorene/gescheiterte Presents nicht als vollständige CSV voraussetzen. |
| S11 | https://github.com/GameTechDev/PresentMon/releases/expanded_assets/v2.6.0 | Exaktes x64-Console-Asset und publizierter SHA-256, Release September 2026. |
| S12 | https://raw.githubusercontent.com/GameTechDev/PresentMon/v2.6.0/PresentMon/CommandLine.cpp | Konkrete Flag-Verarbeitung statt GUI-/CLI-Namen vermischen. |
| S13 | https://raw.githubusercontent.com/GameTechDev/PresentMon/v2.6.0/LICENSE.txt | MIT-Lizenz; keine Binärredistribution in diesem Kit. |
| S14 | https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/overview | SAC als Ausführungsvoraussetzung, nicht Grafikfehler. |
| S15 | https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/code-signing-for-smart-app-control | Vertrauenswürdige Signaturkette statt beliebiger Selbstsignatur. |
| S16 | https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/test-your-app-with-smart-app-control | Lesende Diagnose: CiTool -lp, CodeIntegrity, Audit/Enforcement unterscheiden. |
| S17 | https://support.microsoft.com/en-us/windows/security/threat-malware-protection/smart-app-control-frequently-asked-questions | Aktuelle FAQ; Abschalten/erneutes Aktivieren kann versionsabhängig beschrieben sein, für dieses Projekt irrelevant. |
| S18 | https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options | Artifact-Signing-Berechtigung nicht für jede deutsche Privatperson voraussetzen. |
| S19 | https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-Readme.md | Windows-Runnerwerkzeuge; Image bewegt sich, daher Generator entdecken. |
| S20 | https://raw.githubusercontent.com/actions/checkout/v4/README.md | checkout v4 mit persist-credentials:false. |
| S21 | https://raw.githubusercontent.com/actions/setup-python/v5/README.md | Python 3.13 x64 in CI. |
| S22 | https://raw.githubusercontent.com/actions/upload-artifact/v4/README.md | v4-Artefakte, begrenzte Aufbewahrung, Fehler bei fehlendem Paket. |

## Festlegungen und bewusst nicht angenommene Zusagen

PresentMon wird auf **2.6.0** festgelegt, nicht auf einen unverifizierten Dateinamen aus einem älteren README-Beispiel. Die veröffentlichte Konsole ist nicht identisch mit Installer, grafischer Oberfläche, Dienst oder dem neueren `presentmon-cli`. SHA-256 in `presentmon.lock.json` und Parserkonstante müssen übereinstimmen. Ein Versionswechsel benötigt neue CLI-/Header-/Negativtests und einen echten Zeitzuordnungstest.

Actions sind auf die dokumentierten Hauptversionen v4/v5/v4 festgelegt, nicht auf den beweglichen `main`-Branch. Hauptversionstags sind weiterhin beweglich; für strengere Lieferkettensicherheit vor einem Produktivrelease verifizierte vollständige Commit-IDs setzen und Aktualisierung bewusst pflegen. Hier werden keine erfundenen Commit-Hashes eingetragen. Auch Windows-Runner-Images und Compilerpatchstände können sich ändern; die Logs sind Teil der Buildherkunft. Byteidentische MSVC-Rebuilds werden nicht versprochen.

Die Abnahme verlangt unabhängig vom CI-Betriebssystem Windows-10/11-Desktophardware. Es wird kein `windows-latest`-Grafiktest als Ersatz verkauft. Es wird kein kostenloses unbegrenztes Actions-Kontingent versprochen; private Repositorykontingente und Tarife separat prüfen. Signierkosten werden nicht als notwendig oder garantiert günstig dargestellt.

## Verhältnis zum Nutzerleitfaden

`input_reference/SACsolutions_USER_ORIGINAL.md` ist die maßgebliche Quelle für die **auf dem konkreten Dev-PC gemessenen** Beobachtungen. Die ältere „nur neu installieren zum Wiederaktivieren“-Formulierung wird hier nicht als zeitlose allgemeine Windows-Tatsache fortgeschrieben. Ebenso wird das beobachtete erfolgreiche .NET-Single-File-Publish nicht zu einer Garantie für FSEProbe umgedeutet. Die Architektur folgt der festen Nutzeranforderung: Hostschutz bleibt unverändert.

## Lizenzprovenienz

Keine externen Quellcodedateien wurden eingebunden; deshalb gibt es keine versteckten Sample-Commits oder Fontlizenzen. PresentMon wird separat referenziert, nicht als eigene Entwicklung ausgegeben. Bei späterer Weitergabe seiner Binärdatei müssen die tatsächlich einschlägigen Lizenztexte/Notices mitgegeben werden. Das Originalprojekt ist permissiv lizenziert; „auf GitHub gefunden“ allein wäre keine ausreichende Freigabe. Vor öffentlichem Repository interne Eingabedokumente redigieren oder entfernen.
