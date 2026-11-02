# Prüfrahmen und gefundene Korrekturen

Die Abschlussrunden prüfen die hier verfügbaren Komponenten, nicht einen Windows-/GPU-Lauf. Der Erstellungscontainer ist Linux. GNU-C++ und ein zusätzlicher Clang-Build mit AddressSanitizer/UndefinedBehaviorSanitizer prüfen ausschließlich Core und Szenengeometrie. Python prüft synthetische Auswertung und Dateiprotokolle. PowerShell wurde hier nur als Quelle/Encoding geprüft, weder geparst noch ausgeführt; dafür sind echte PS5.1/7-Gates in Windows-CI vorgesehen.

Vor den Abschlussrunden korrigiert: boolesche Exit-/Schemawerte statt echter Integer, null/ungültige Exitwerte, Null-Anzeigedauer, Runnerfehler als Abbruchgrund, fehlerhafter Legacy-Mode in einer Kontroll-Fixture, Download-Zieldatei statt irrtümlicher Unterverzeichnisbildung, klarer Log-Initialisierungsfehler, zusätzliche Device-Removed-Diagnose und zuletzt dauerhafte Sichtbarkeit der Eck-/Randkalibrierung vor dem bewegten Objekt. Die Ausnahmebehandlung trennt außerdem den stackgebundenen Fensterzustand vor Window-Cleanup.

Die Downloadtests verwenden nur im temporären Verzeichnis erzeugte synthetische Bytes und einen gemockten Netzwerkaufruf. Sie führen keine heruntergeladene EXE aus. Der veröffentlichte PresentMon-Hash wurde anhand der Originalquelle geprüft; der tatsächliche Windows-Binärlauf steht aus.

Die finalen Runden müssen denselben funktionalen Quellstand behalten. Ergebnislogs, Paketmanifest und SHA-256-Dateien sind erzeugte Belege; sie zählen nicht als funktionale Änderungen. REVIEW_RESULTS.json enthält die gemessenen Befehle/Exitcodes und Hashes. Zwei saubere Runden sind keine Garantie der Fehlerfreiheit.
