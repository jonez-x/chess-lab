# Chess Lab

Lokaler Schachcoach für Jonas. Seit 27.09.2026 unter dem Namen **Chess Lab**. Die Oberfläche baut auf Entwurf 02 auf; die Figuren wurden auf Jonas’ Wunsch durch das klassische Cburnett-Set ersetzt. Kein Konto, keine Cloud und kein API-Schlüssel erforderlich.

**Windows-PC:** Die vollständige Einrichtung steht in [WINDOWS.md](WINDOWS.md). `Start-Windows.cmd` richtet die Python-Umgebung ein; Stockfish und das gewünschte Ollama-Modell separat installieren. Die Plattformdateien und persönlichen Daten sind bewusst nicht in Git enthalten.

**Anderes lokales Modell:** `python server.py --model NAME --coach-timeout 180 --open` (mit dem Python aus der virtuellen Umgebung). Alternativ `CHESSLAB_MODEL` setzen. Der Coach-Info-Dialog zeigt den gewählten Modellnamen. Ein neuer Modellname erfordert einen Neustart des Chess-Lab-Servers, kein Ändern des Quellcodes.

## Starten

Auf diesem Mac ist alles eingerichtet. **`Start.command` doppelklicken**, dann öffnet sich [Chess Lab](http://127.0.0.1:8765). Das Terminalfenster während des Spielens geöffnet lassen; mit `Ctrl+C` beenden. Ein weiterer Start öffnet die bereits laufende App.

Alternativ im Projektordner:

```sh
.venv/bin/python server.py --open
```

## Ausprobieren

1. Onboarding abschließen, Lernniveau, Bot-Stärke und eigene Farbe wählen.
2. Figuren per Klick auswählen und auf ein markiertes Feld ziehen (zweiter Klick). Tastatur: Tab auf das Brett, Pfeiltasten zwischen Feldern, Enter zum Auswählen/Ziehen, Escape zum Abwählen.
3. „Einen Hinweis“ öffnet drei Hilfestufen. Auch der Chat steuert sie: allgemeine Ratlosigkeit führt zum gezielten Figurenhinweis, erneute Ratlosigkeit oder „sag mir den Zug“ zur Lösung samt Pfeil. „Nur ein Hinweis, nicht verraten“ bleibt ohne Lösung. Eigene Züge bleiben während eines fertigen Hinweises möglich.
4. Automatische Lernmomente sind immer überspringbar. Der Gegner wartet während des Lernmoments.
5. Unter „Neues Training → Sizilianisch ausprobieren“ die besprochene Stellung öffnen. `d4 → d5` zeigt den Angriff auf den Springer auf c6. Der Coach behauptet dabei weder einen erzwungenen Springerzug noch einen garantierten Materialgewinn.
6. „Mein Training“ enthält gespeicherte Partien, Hinweise und eigene Gedanken. Alte Partien lassen sich fortsetzen. Neue Partien löschen die alten nicht.

## Enthalten

- Vollständige Zugregeln durch python-chess: Rochade, en passant, Auswahl aller vier Umwandlungsfiguren, Schach, Matt, Patt und Remisregeln.
- Ungetaktete Partien als Weiß oder Schwarz gegen Stockfish 19; drei Skill-Level (0, 6, 14), keine behaupteten Elo-Werte. Auch die leichte Stufe kann für Einsteiger stark sein.
- Getrennte Stockfish-Prozesse für Gegenspiel und Analyse.
- Tatsächlich berechnete Kandidaten auf Anfrage; legal geprüfte Varianten und belegte Brettfakten.
- Fragen → Hinweis → Erklärung, Pfeile und Feldmarkierungen. Automatische Unterbrechungen derzeit nur bei einem Figurenangriff durch die gezogene Figur, höchstens einmal je fünf eigenen Zügen.
- Rücknahme eines eigenen Zuges inklusive Gegenzug, wiederholter Versuch, überspringbare Lernmomente, optionale eigene Notizen.
- Name, Lernniveau, Unterbrechungen, Hell/Dunkel; kurzes Onboarding erneut aufrufbar.
- SQLite-Speicherung nach Änderungen, Wiederaufnahme, Partiearchiv, PGN-Export und konsistente Sicherung der Nutzerdatendatei.
- Veraltete Engine-Antworten werden nach Rücknahme, neuer Partie oder abgebrochenem Hinweis verworfen; parallele Browseransichten können keinen Zug doppelt anwenden.

## Pfeile, Klänge und Coach-Figur

- **Pfeile:** rechte Maustaste halten und von einem Feld zu einem anderen ziehen. Derselbe Pfeil erneut gezeichnet entfernt ihn. Alternativ „Pfeile zeichnen“ aktivieren und Start-/Zielfeld anklicken (auch per Tastatur) oder mit der linken Taste ziehen. In diesem Modus werden keine Schachzüge ausgeführt.
- **Löschen:** „Pfeile löschen“ entfernt nur eigene Pfeile. Escape beendet den Zeichenmodus und löscht eigene Markierungen. Alle Pfeile sind durchgezogene, abgerundete Silhouetten mit feiner heller Kontur. Coach-Pfeile sind etwas kräftiger, die Zeichenvorschau transparenter. Sie bleiben beim Drehen korrekt, verschwinden bei Stellungs-/Partiewechsel und werden nicht dauerhaft gespeichert.
- **Schlagziele:** ein Ring markiert legale Schlagzüge, auch en passant. Normale Zugziele bleiben Punkte. Grundlage ist die Regelprüfung im Backend.
- **Klänge:** kurze unterschiedliche Klänge für Zug und Schlag, auch beim Bot. Unter Einstellungen abschaltbar und über „Klänge anhören“ vorhörbar. Die Einstellung wird lokal gespeichert. Browser geben Audio erst nach einer Interaktion frei. Kein Klang bei Neuladen, Rücknahme oder illegalem Zug.
- **Bewegung:** Figuren gleiten beim eigenen Zug und beim Gegenzug weich auf ihr Zielfeld, heben sich dabei kurz an und setzen mit einem kleinen Impuls auf. Schläge bekommen zusätzlich einen kurzen Abschlussring. Bei aktivierter reduzierter Bewegung des Betriebssystems werden die Animationen übersprungen.
- **Vorteil:** Eine live berechnete Stockfish-Bewertung aus Weißsicht erscheint als ein-/ausblendbare Leiste unter dem Brett. Die Berechnung läuft im Hintergrund und wird verworfen, sobald sich die Stellung ändert.
- **Coach:** ruhige typografische Coach-Kennung ohne Maskottchen. Der hyperrealistische Läufer-Entwurf ist verworfen und wird nicht geladen.

## Bewusste Grenzen dieser ersten Version

### Gesprächsführung und Schachabwehr

Der Dialog erhält aktuelle, aus python-chess berechnete Angreifer und bei Schach
die tatsächlich verfügbaren Kategorien legaler Antworten. Frühere Nachrichten
werden als Gespräch übergeben, nicht als Brettfakten. Versteckte Engine-Kandidaten
bleiben weiterhin zurückgehalten. Bei Verständnisproblemen oder Wiederholungsbeschwerden
in einer Stellung, in der nur Königszüge das Schach abwehren, liefert eine geprüfte
Klarstellung den nächsten Denkschritt. Sie ist als „Coach · Klarstellung“ markiert.
Die App zeichnet dazu die geprüfte Schachlinie; das Modell erfindet keine Pfeile.
Andere freie Antworten bleiben experimentell. Der gemeldete Vier-Nachrichten-Dialog
ist mit `tests/try_conversation.py` am lokalen Modell nachstellbar.

### Konkrete Hilfe auf Nachfrage (27.09.2026)

Die Hilfestufe steigt jetzt auch durch Gesprächsabsicht: „was sollte ich machen?“ → Figurenfokus; erneutes Nichtwissen oder eine ausdrückliche Lösungsfrage → geprüfter Kandidat. Der Chat bleibt dabei erhalten. Kernantworten (konkreter Zug, Erklärung zu diesem Zug, Verteidiger) werden aus Brett- und Engine-Daten erzeugt und funktionieren ohne Modellaufruf. Der Kandidat und höchstens drei Halbzüge einer möglichen Fortsetzung werden ab der passenden Stufe freigegeben; jeder Zug wird erneut ab der passenden Ausgangsstellung auf Legalität geprüft. Die Variante wird als Möglichkeit, nicht als erzwungene Folge beschrieben. Gespielte Züge werden als vergangene Züge erklärt, nicht nochmals empfohlen.

Die Verteidigeranzeige ist eine geometrische Aussage; sie behauptet weder einen legalen Rückschlag noch einen günstigen Abtausch. Freie Modellantworten erhalten diese Fakten und die freigegebene Variante. Nahezu wiederholte Antworten werden, soweit verfügbar, durch die geprüfte Hilfe ersetzt. Deutsche Nachrichten erhalten eine Antwort mit „du“, englische eine englische Antwort.

Reproduktion des gemeldeten Verlaufs: `.venv/bin/python tests/try_help_progression.py`. Ergebnis: `data/help-progression-trial.json`; der erste echte Qwen-Lauf mit weiterhin falschen freien Aussagen ist als `data/help-progression-trial-model-baseline.json` erhalten. Die verlässlicheren Kernantworten belegen die Verbesserung der Gesprächssteuerung, nicht eine gestiegene Schachkompetenz des Modells. Ein Modellwechsel wurde noch nicht vorgenommen oder vergleichend getestet.

### Lokales Sprachmodell: Hinweisdialog (27.09.2026)

Ollama und `qwen3.5:4b` sind auf Jonas’ Mac installiert. `Start-Coach.command`
startet den lokalen Modelldienst auf Port 11434, ohne Cloud-Funktion. Die
Spieloberfläche ergänzt die Standardhinweise um einen deutschen oder englischen Dialog:
„Einen Hinweis“ wählen, eine Frage oder Idee eingeben und „Coach fragen“ drücken.
Ohne Texteingabe fragt der Coach selbst nach. Der Standardhinweis und die
Hilfestufen bleiben verfügbar. Antworten werden lokal mit dem Lernmoment gespeichert.
Bei einer neuen Hilfestufe wird der Dialog zurückgesetzt. Überspringen, ein Zug
oder Partiewechsel entwerten laufende Antworten. Ein Ausfall zeigt eine Meldung,
ohne den Standardhinweis zu entfernen. Der Modellaufruf erhält nur die
freigegebenen Fakten der aktuellen Hilfestufe auf Englisch, keine versteckte
Engine-Variante. Freier Text ist weiterhin nicht vollständig fachlich verifiziert.

Bei laufendem Modelldienst im Projektordner:

```sh
.venv/bin/python tests/try_local_coach.py
```

Die zehn Antworten und Laufzeiten stehen danach in `data/local-coach-trial.json`.
Der erste Lauf ist unter `data/local-coach-trial-baseline.json` erhalten.
Das Modell bekommt kurze Faktenpakete, 4096 Tokens Kontext und maximal 180
Ausgabetokens. JSON-Prüfungen erkennen ungültige oder abgeschnittene Antworten,
beweisen aber keine Schachkorrektheit. Die ersten Antworten wurden manuell
geprüft; der freie Dialog bleibt ein experimenteller Teil der App. Für das Modell entstehen keine API-Gebühren.

**Standardhinweise und konkrete Kernhilfen kommen aus geprüften Vorlagen; andere Rückfragen beantwortet das lokale LLM.** Es gibt noch keine verlässliche semantische Beurteilung eigener Gedanken. Die Absichtserkennung ist regelbasiert und deckt häufige deutsche/englische Formulierungen ab, keine beliebige natürliche Sprache. Das Lernniveau beeinflusst bisher nur zusätzliche Grundlagenerklärungen. Die Historie hält Hilfestufen fest; sie diagnostiziert keine Schwächen und bewertet einen übersprungenen Moment weder als Erfolg noch als Fehler.

Es gibt noch keine zuverlässige Erkennung von taktischen Materialverlusten, keinen Vergleich „mein Zug gegen bester Zug“, keine freie Unterhaltung, keine automatischen Wiederholungsaufgaben und keine statistisch belegte Anpassung. Ein Engine-Kandidat ist keine vollständige Erklärung seiner Qualität. Die Bot-Stufen sind kein Modell menschlicher Anfängerfehler.

Die App lässt sich mit plattformeigenem Python, Stockfish und Ollama auf macOS, Windows und Linux starten. Dateisperre und Engine-Suche berücksichtigen Windows. Eine native Verpackung und ein interaktiver Windows-/GPU-Nutzungstest sind noch offen. Auf schmalen Fenstern stapelt sich die Ansicht; Handy ist kein Produktziel.

## Lokale Daten und Sicherungen

Standarddatei: **`data/schachcoach.sqlite3`** im Projektordner. Sie enthält Profil, Einstellungen, Partien samt vollständigem Zugverlauf, aktive Lernmomente und Beobachtungen. Keine Passwortverschlüsselung. Schreibvorgänge sind SQLite-Transaktionen mit `synchronous=FULL`. Eine `.lock`-Datei verhindert mehrere App-Prozesse auf derselben Nutzerdatendatei. Sie enthält keine Nutzerdaten.

„Mein Training → Sicherung herunterladen“ erzeugt über die SQLite-Backup-Schnittstelle eine konsistente Kopie. PGN exportiert nur die aktuelle Partie, nicht Profil und Lernhistorie.

Wiederherstellen: App stoppen, bestehende Datei sichern und die gewünschte Sicherung als `data/schachcoach.sqlite3` einsetzen. Alternativ eine Kopie ausdrücklich öffnen:

```sh
.venv/bin/python server.py --data /absoluter/pfad/schachcoach-sicherung.sqlite3
```

Die App schreibt in die gewählte Datei. Sicherungen deshalb zum Ausprobieren kopieren. Während der App läuft, die Arbeitsdatei nicht manuell ersetzen. Es gibt noch keine automatische rotierende Datensicherung und keinen Wiederherstellungsdialog.

## Projektstruktur

- `server.py`: lokale HTTP-Oberfläche, nur Loopback; Host-/Origin-Prüfung und JSON-Anfragen mit eigenem Header.
- `game.py`: verbindlicher Spielzustand, Engine-Prozesse, verwerfbare Hintergrundaufgaben, Transaktionen und Archiv.
- `coach.py`: nachvollziehbare Brettfakten und begrenzte Vorlagen für Hilfestufen.
- `static/`: Oberfläche, bestätigte Figurenstile, klassische Cburnett-Figuren; Lucide nur für Bedienelemente.
- `tests/`: Regeln, Coaching, Persistenz, Fehlerfälle und echte Engine-Prüfung.
- `engine/stockfish/`: offizielle Engine samt mitgeliefertem Quellmaterial und Lizenz.

## Installation auf einem weiteren Mac

Python 3.9 oder neuer, eine passende lokale Stockfish-Engine und die Python-Abhängigkeit werden benötigt:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python server.py --open
```

`STOCKFISH_PATH` kann auf eine andere Stockfish-Datei zeigen. Ohne diese Variable wird zuerst `stockfish` im PATH, dann eine zur Plattform passende Datei unter `engine/` gesucht. Der Git-Checkout enthält keine Engine-Binärdatei; siehe [engine/README.md](engine/README.md). Andere Engines sind nicht zugesichert: Die konfigurierten Optionen sind Stockfish-spezifisch.

## Verifikation

```sh
.venv/bin/python -m unittest discover -s tests -v
```

29 automatische Prüfungen inklusive echter Stockfish-Züge/Varianten. Browserprüfungen decken Onboarding, Partie, Rücknahme, Hilfestufen, Überspringen, Beispielstellung, Darstellung, Notizen, Wiederladen, Historie und lokale Zugriffssperren ab. Details und Ergebnisse in `VALIDIERUNG.md`. Das ist technische Verifikation, noch keine pädagogische Wirksamkeitsprüfung oder vollständige 20-Stellungen-Abnahme.

## Nächster funktionaler Ausbau

1. Gemeinsam erste echte Trainingspartien auswerten: störende Unterbrechungen, passende Hilfen, Gegnerstärke.
2. Vergleichbare Engine-Suchen für Originalzug und Alternativen; ein kuratiertes Abnahmeset aus positiven Fällen und Gegenbeispielen.
3. LLM-Anbieter, Modell, Kostenlimit und erlaubte übertragene Daten festlegen. Danach beleggebundene Sprache hinter `coach.py` integrieren, mit Vorlagen als Ausfallpfad.
4. Beobachtungen über unabhängige Stellungen zu vorsichtigen Lernhypothesen verdichten; Wiederholungsaufgaben erst danach.

## Quellen und Drittsoftware

- [python-chess 1.11.2](https://python-chess.readthedocs.io/en/latest/) · GPL-3.0-or-later; [UCI-Anbindung](https://python-chess.readthedocs.io/en/latest/engine.html).
- [Stockfish 19, offizielle Veröffentlichung](https://github.com/official-stockfish/Stockfish/releases/tag/sf_19) · GPL-3.0; Lizenz und Quellmaterial im Engine-Verzeichnis.
- [Cburnett-Figuren von Colin M. L. Burnett](https://github.com/lichess-org/lila/tree/eff61677731721776ccc7b2b1b39c313c8f143eb/public/piece/cburnett) · GPL-2.0-or-later; zwölf unveränderte SVG-Quelldateien, Lizenz und Quellenangabe in `static/pieces/cburnett/`.
- [Lucide](https://lucide.dev/), lokal Version 1.8.0 · nur Bedienelemente; Lizenz in `static/vendor/LUCIDE-LICENSE`.
- Die kurzen Klänge werden lokal mit Web Audio erzeugt und verwenden keine fremden Audioaufnahmen.

Die bestehenden Obsidian-Projektnotizen bleiben der Ort für Entscheidungen und Planung. Die App selbst greift nicht auf den Vault zu.
