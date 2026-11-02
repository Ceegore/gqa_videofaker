# Ausschließlich synthetische Prüfdatensätze

`legacy`, `control` und `mixed` wurden vom eigenen `fixture_factory.py` erzeugt, nicht auf Windows aufgezeichnet. `expected.json` enthält die erwartete Klassifikation. Alle positiven Ergebnisse heißen SYNTHETIC_PASS und beweisen keinerlei Hardwarefunktion. `test_presentmon_parser.py` erzeugt weitere negative Fälle in temporären Verzeichnissen. Die großen QPC-Werte oberhalb 2^53 prüfen verlustfreie Integer-Verarbeitung; sie sind keine Aufzeichnung einer realen Maschine.
