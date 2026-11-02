# 04 — Bedien- und Hardwareabnahmehandbuch

## Vorbereitung und Testaufbau

Zuerst bestimmen, **welches Windows** getestet wird. Der geschützte Entwicklungs-PC bleibt unverändert. Ein separater physischer Test-PC oder ein bereits zulässiges separates Test-Windows ist die Standardroute. Eine auf einem anderen Windows beobachtete Freigabe ist kein Nachweis für den SAC-Dev-PC. Recorder und FSEProbe müssen im selben zu untersuchenden Windows laufen.

Notiere Windows-Build, GPU/Treiberversion, Monitor/Anschluss, Auflösung/Refresh, Skalierung, HDR/VRR, Anzahl Monitore, Recorder-Version und konkretes Capture-Backend. Ohne Kenntnis des Backends kann ein gutes Video verschiedene Recorder-Wege verdecken. Kein zusätzliches Overlay zum Statusanzeigen aktivieren. PresentMon hat seine Konsole unterdrückt; das Renderfenster zeichnet den Status selbst.

Aus einer bereits erlaubten PowerShell:

```powershell
.\tools\inspect_environment.ps1 -OutputPath .\environment.json
.\tools\inspect_sac_environment.ps1 -BinaryPaths @('.\bin\FSEProbe.exe','.\tools\PresentMon-2.6.0-x64.exe') -OutputPath .\security-preflight.json
.\bin\FSEProbe.exe --list-monitors
```

Die Befehle sind nur im freigegebenen Testsystem auszuführen; insbesondere der letzte startet die neue EXE. Scheitert bereits eine Script-Policy, die manuellen Leseschritte aus Dokument 10 verwenden. Keine Policy verändern.

## Lauf A — Instrumentenkontrolle ohne Recorder

`borderless-control`, low, AutoMark, 30 Sekunden. Prüfen, dass der Monitor stimmt, alle vier asymmetrischen Ecken sichtbar sind, Frame-ID und Quadrat fortschreiten und der HUD nicht „FSE bestätigt“ behauptet. Der Bericht muss kontrolliert nichtklassisch sein, nicht FSE. Wenn schon dieser Lauf an Zeitzuordnung, Prozessstart oder CSV-Schema scheitert, zuerst die Messkette korrigieren; keine echten Recorderfolgerungen ableiten.

`legacy-exclusive`, low, AutoMark, gleicher Monitor. Stimmen die DXGI-Anforderung und der unabhängige PresentMode? Wenn nur Independent Flip beobachtet wird, handelt es sich nicht um einen erfolgreichen klassischen Legacy-Test. Das kann eine tatsächliche Windows-/Treiberbedingung sein, nicht automatisch ein Programmfehler.

## Lauf B — FSO kontrolliert vergleichen

Für die konkrete FSEProbe-EXE in Windows Eigenschaften → Kompatibilität die Einstellung „Vollbildoptimierungen deaktivieren“ nur dann manuell prüfen, wenn sie auf diesem System angeboten wird. Das ist eine benutzersichtige Vollbildeinstellung, **keine** Änderung an SAC/Defender. Ausgangszustand dokumentieren; jeden Zustand in einem neuen Run messen. Nicht behaupten, dass allein dieses Häkchen Legacy erzwingt.

Windows-11-„Optimierungen für Fensterspiele“ ist eine andere Funktion als Legacy-FSO. Nicht alle Schalter gleichzeitig ändern. Registry-Anpassungen oder Treiber-Tuning sind kein Teil der Abnahme. Fehlt die UI-Option oder bleibt Legacy unerreichbar, Ergebnis ehrlich als nicht nachgewiesen festhalten.

## Lauf C — Screenshot

Recorder so vorbereiten, dass der Screenshot ohne Alt-Tab ausgelöst wird. Nach Warmup F8 setzen, im aktiven Markerfenster Screenshot aufnehmen, weiterlaufen lassen, F9, mindestens eine Sekunde Nachlauf. Screenshot als `screenshot-<run-id>-<nummer>.png` speichern. Vollständiger Bericht plus Bild müssen dieselbe Run-ID erkennen lassen.

Bewertung: keine schwarzen/leeren Bilder, richtige Szene, lesbare Run-ID/Frame-ID, alle vier Ecken, keine abgeschnittenen Kanten, kein ungewolltes Resize, nachvollziehbare Skalierung. Ein einzelner Screenshot kann nicht die Framekontinuität eines Videos beweisen. Seine exakte Triggerzeit ist ohne Recorder-API nur operatorseitig dokumentiert.

## Lauf D — Video

Recorder-Hotkeys vor dem Test prüfen; F8/F9/ESC gehören FSEProbe. Aufnahme **vor** F8 beginnen, F8 erst nach READY. Mindestens fünf Sekunden aufnehmen; längerer Abschnitt ist günstiger für Freeze-/Drop-Prüfungen. F9 setzen, noch mindestens eine Sekunde aufnehmen, dann Recorder stoppen. Keine Dialoge öffnen, kein Fokuswechsel während des Laufes. Aufzeichnungsstart/-stopp-Hotkeys, die einen Overlay/Fokuswechsel erzeugen, sind selbst Gegenstand eines separaten Negativtests.

Video als `video-<run-id>.<tatsaechliche-endung>` zusammen mit Dateihash und Recorderparametern erfassen. Die bewegte Figur soll alle Quadranten durchlaufen; Frame-ID, Sekundencode und 24-Bit-Muster helfen beim Vergleich. Der sichtbare Bitcode codiert nur die unteren 24 Bits des App-Framezählers, links beginnend beim niederwertigsten Bit. Er ersetzt keine robuste automatische Videoanalyse.

Die App ist auf VSync/FPS-Cap begrenzt. Ein 30-fps-Recorder einer 60-fps-App darf erwartbar Frame-IDs überspringen. Das allein ist kein Recorderdefekt. Bewerten: unerwartete Freezes, sehr lange gleiche Frame-ID, falsche Reihenfolge, Crop, unerklärte Schwarzbilder, abweichende Dauer oder Auflösung. Encoderdrops und Frametiming nur mit den tatsächlich vorliegenden Recorderdaten beziffern. Audio-Synchronität wird von dieser Version nicht getestet.

## Lauf E — gezielte Negativfälle

Je Fall neuer Run: Alt-Tab im markierten Intervall; Recorder-Overlay aktivieren; falscher Monitorindex; vorhandene zweite FSEProbe; PresentMon fehlt/falscher Hash; ETW-Rechte fehlen; Marker fehlen; F9 zu früh/ESC vor Ende; Displayabzug nur nach vorbereiteter Recovery; unabhängiger Flip statt Legacy. Ergebnis muss FAIL, BLOCKED oder UNVERIFIED sein, niemals ein unbegründeter FSE-PASS.

Ein Monitorabzug kann den Desktop beeinträchtigen. Zuerst normale Tests abschließen und eine sichere Bedienmöglichkeit vorsehen. Erzwungenen Treibercrash nicht auf dem produktiven Rechner erzeugen. Device-Loss bleibt als offener manueller Test dokumentiert, wenn keine sichere reproduzierbare Auslösung verfügbar ist.

## Abbruch und schwarzer Bildschirm

Zuerst ESC. Reagiert die App nicht, normale Windows-Sicherheitsoberfläche über Strg+Alt+Entf und Task-Manager nutzen; nur FSEProbe bzw. eindeutig zugehörige Testprozesse beenden. Ein Monitor-/Treiberproblem kann weitere manuelle Wiederherstellung erfordern; nicht blind Display-/Sicherheitsregistry ändern. Der Runner hat eine harte Zeitbegrenzung, ist aber kein garantierter Recovery-Dienst bei einem OS-/Treiberhänger.

Nach Notabbruch: Aufnahme nicht als bestanden werten, App-/Observer-Exitstatus und CodeIntegrity sichern, Desktopauflösung/Refresh prüfen. Der erneute Start muss einen neuen Run-Ordner erhalten. Überlebende eigene ETW-Sessions nur anhand ihrer Run-ID beenden, niemals pauschal alle PresentMon-Sessions.

## Abschlussakte

Zusammen aufbewahren: `environment.json`, `security*.json`, gesamter `logs/<run-id>/`, Bild/Video samt SHA-256, ausgefüllte `recorder-assessment.template.json`, Screenshot der relevanten FSO-/Recorder-Einstellung und konkrete Testmatrixzeile. In öffentlichen Tickets Pfade/Benutzernamen redigieren, die ursprünglichen Rohbelege intern erhalten. FSE- und Recorder-Ergebnisse werden nebeneinander berichtet, nicht in einem unklaren „alles grün“ versteckt.
