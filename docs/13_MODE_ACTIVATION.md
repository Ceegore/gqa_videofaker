# 13 — Mini-Anleitung: Modi aktivieren

FSEProbe hat genau zwei Präsentationsmodi. Der Modus wird **beim Start** über `--mode` gewählt; ohne Angabe gilt `legacy-exclusive`.

## Direktstart

```powershell
# Legacy-Exclusive (Default): fordert klassisches DXGI-Vollbild an
.\bin\FSEProbe.exe --mode legacy-exclusive --load low --duration 60

# Borderless-Kontrolle: kein SetFullscreenState, nur ein randloses Fenster
.\bin\FSEProbe.exe --mode borderless-control --load low --duration 60
```

Nützliche Zusatzoptionen:

```text
--load off|low|medium|high     GPU-Last (Default low)
--duration 15..300            Laufzeit in Sekunden
--warmup 3..60                Vorlauf; duration muss warmup+8 überschreiten
--auto-mark                   automatische Diagnose-Marker
--monitor 0..31               DXGI-Ausgabe (vorher --list-monitors)
--fps-cap 15..120             CPU-Frame-Cap; VSync bleibt an
```

## Über den Runner

```powershell
# Kontrolle zuerst
.\tools\run_test.ps1 -App .\bin\FSEProbe.exe `
  -PresentMon .\tools\PresentMon-2.6.0-x64.exe `
  -PhysicalDesktop -Mode borderless-control -Load low -Duration 30 -AutoMark

# Danach Legacy
.\tools\run_test.ps1 -App .\bin\FSEProbe.exe `
  -PresentMon .\tools\PresentMon-2.6.0-x64.exe `
  -PhysicalDesktop -Mode legacy-exclusive -Load low -Duration 30 -AutoMark
```

`-Mode` hat dieselben zwei Werte. Der Runner startet PresentMon vor der App und wertet nach dem Lauf aus. Für ETW-Rechte den Observer in einer separat autorisierten erhöhten PowerShell starten und `-ExternalObserver` verwenden.

## Modus im Log prüfen

In `app.jsonl`:

- `START` enthält `"mode":"borderless-control"` oder `"mode":"legacy-exclusive"`.
- Nur Legacy enthält `REQUEST_FULLSCREEN` und `SET_FULLSCREEN_RESULT`.
- `MODE_READY` zeigt `"fullscreen":false` (Borderless) bzw. `"fullscreen":true` (Legacy-Anforderung).

Im Bericht:

- Borderless: `dxgi_state=WINDOWED_REPORTED`, `presentation_proof=CONTROL_VERIFIED_NOT_FSE`.
- Legacy: `dxgi_state=FULLSCREEN_REPORTED`; erst PresentMon entscheidet, ob wirklich klassisches FSE vorliegt.

## Sicherheitshinweis

- **Borderless zuerst** verwenden: kein Displaymoduswechsel, ESC beendet, Fokusverlust invalidiert den Lauf.
- Legacy fordert exklusives Vollbild an. Normaler Cleanup ist implementiert, Crash-Recovery ist nicht garantiert.
- Die EXE ist **unsigniert** und keine SAC-Freigabe. PresentMon wird separat hashgeprüft bezogen und nicht mitgeliefert.
- `SET_FULLSCREEN_RESULT=0x0` oder `fullscreen=true` ist **kein** klassischer FSE-Nachweis. Das entscheidet die unabhängige PresentMon-Auswertung.
