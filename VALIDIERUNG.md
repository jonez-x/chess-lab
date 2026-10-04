# Technischer Teststand · 26.09.2026

Die erste lokal spielbare Version wurde auf diesem Apple-Silicon-Mac mit Python 3.9.22, chess 1.11.2, Stockfish 19 und Google Chrome geprüft. Tests arbeiten mit separaten temporären Dateien; Jonas’ Nutzerdatendatei enthält keine Testpartien.

## Automatische Spielkern-Prüfungen

Ergebnis: **26 Tests bestanden**, Laufzeit des geprüften Laufs 2,774 Sekunden.

Abgedeckt: illegale Züge ohne Zustandsänderung; veraltete Anfragen; Rochade einschließlich verbotenem Durchqueren eines angegriffenen Felds; en passant; vier Umwandlungen und Unterverwandlung; Schachmatt; Patt; Materialremis; Rücknahme und neue Partie während einer laufenden Engine-Aufgabe; veraltete Engine-Fehler; Pausieren bei d5; Überspringen ohne Lösungsverrat; Abbruch laufender Hinweise; drei Hilfestufen; Reflexionsspeicherung ohne behauptetes Verständnis; Sicherung und Wiederherstellung; Rückrollen einer fehlgeschlagenen Einstellungsänderung; PGN-Replay; Stellungswiederholung aus vollständiger Zugfolge; Schwarz als Spieler; Archiv/Fortsetzen; korrekte Angriffsrichtung und Gegenbeispiele; getrennte reale Engines, alle drei Bot-Stufen und legale Analysevarianten.

Der absichtlich ausgelöste `controlled test failure` in der Ausgabe gehört zum Test veralteter Engine-Fehler und ist kein fehlgeschlagener Test.

## Browserdurchlauf

Ergebnis: **bestanden, keine JavaScript-Laufzeitfehler**.

- Onboarding, Niveaustufe, Bot-Auswahl und Start einer Partie.
- Alle 32 Figuren als lokale Lucide-SVGs geladen.
- e2–e4, echter Stockfish-Gegenzug, Rücknahme beider Halbzüge.
- Engine-Hinweis, zwei Stufen ohne Lösungspfeil, dritte Stufe mit Pfeil, Überspringen entfernt Markierungen.
- Sizilianische Ausgangsstellung, d4–d5, Gegner wartet im Lernmoment; Erklärung markiert d5→c6.
- Eigene Notiz wird gespeichert. Ein testweise enthaltener HTML-/Script-Text erscheint als Text und wird nicht ausgeführt.
- Hell/Dunkel und aktive Lernstellung über Seitenneuladen erhalten.
- Historie und Einstellungen; automatische Unterbrechungen abschaltbar.
- Keine horizontale Seitenüberbreite bei 1024, 768 und 390 Pixeln Fensterbreite; 390 ist ein Layoutcheck, kein zugesagtes Handyprodukt.
- Schreibanfrage ohne eigenen App-Header wird abgelehnt.
- Helle und dunkle Darstellung visuell geprüft, ursprüngliche Figurenstile erhalten.

Die erste Browser-Testausführung hat eine zu frühe Abfrage direkt nach dem Klick beanstandet. Der Test wartet jetzt auf den abgeschlossenen Speichervorgang; der vollständige anschließende Durchlauf ist bestanden.

## Noch nicht nachgewiesen

Keine pädagogische Wirksamkeit, keine vollständige kuratierte Abnahme mit 20 Schachstellungen, kein Latenz-Perzentil unter längerem Lasttest, keine systematischen Absturz-/Datenträgerausfalltests, keine Betriebssystemmatrix und keine LLM-Qualitätsprüfung. Erste gemeinsame Trainingspartien mit Jonas stehen aus.

## Coach-Nachprüfung: Angriff ist keine Verteidigungspflicht (2026-09-27)

Die gemeldete Stellung nach 1.e4 c5 2.Sf3 g6 3.d4 Lg7 4.dxc5 Da5 5.Ld2 Dc7 enthält tatsächlich die Angriffe g7–b2, c7–h2 und c7–c5. Daraus wird keine Verteidigungspflicht oder gefahrlose Möglichkeit zum Ignorieren abgeleitet. Entwicklungslektionen erhalten bereits in Stufe 0 einen passenden Fokus ohne Lösungszug. Allgemeine Hilfefragen erhalten hier einen festen Entwicklungsimpuls mit anschließender Prüfung gegnerischer Schlagmöglichkeiten; Schachstellungen und konkrete Nachfragen verwenden diesen Einstieg nicht.

Lokaler Qwen-Test: Nachfrage zur Verteidigung wurde angemessen eingeschränkt beantwortet. Der allgemeine Einstieg blieb trotz Promptänderung beliebig („any legal move“); deshalb wird dieser enge Fall deterministisch beantwortet. Freie Modellantworten bleiben fehlbar. Regressionstest enthält die gemeldete Stellung, Angriffsbeziehungen und das Zurückhalten des Zielfelds.

## Nachprüfung: Figuren im Onboarding

Die prozentualen Sondergrößen für Bauer und Springer waren auch im Onboarding wirksam und überschrieben dort die festen Abmessungen. Diese Regeln gelten jetzt ausschließlich auf dem Schachbrett. Browserprüfung bei 1440, 1024 und 768 Pixeln: alle sechs Onboarding-Figuren in 50 × 64 Pixel großen Elementen, kein horizontaler Überlauf, keine JavaScript-Fehler. Darstellung zusätzlich visuell geprüft. Profil und Partie wurden dabei nicht verändert.

## Ausbau: klassische Figuren, Pfeile, Klänge und Maskottchen

29 Spielkern-Tests bestanden (2,764 Sekunden). Neu geprüft: ausschließlich legale Schlagziele inklusive en passant, Schlagkennzeichnung im Zugverlauf und persistente/typgeprüfte Klang-Einstellung.

Separater Chrome-Durchlauf bestanden, ohne JavaScript-Fehler: zwölf klassische SVG-Assets und PNG-Maskottchen lokal geladen; Ring für Schlagziel gegenüber Punkt für normales Ziel; Rechtsziehen und erneutes Zeichnen zum Entfernen; Zeichenmodus mit zwei Klicks sowie Linkszug-Geste; Zeichnen verändert keine Stellung; Pfeile bleiben beim Drehen auf ihren Feldern; eigene Pfeile löschen entfernt keine Coach-Pfeile; Stellungswechsel entfernt eigene Pfeile. Tatsächliche Web-Audio-Oszillatoren für Zug und Schlag gestartet; Neuladen blieb stumm; gespeicherte Stummschaltung verhindert weitere Zugklänge. Die Klangästhetik muss Jonas noch subjektiv beurteilen. Helle und dunkle Darstellung visuell kontrolliert.

## Visueller Coach (2026-09-27)

Neue Auswahl „Am Brett entdecken“: Entwicklungsfiguren markieren, einzelne gegnerische Angriffe mit Pfeilen ansehen und Coach-Ebene ausblenden. Schach wird zuerst gezeigt. Kandidatenzüge bleiben bis Stufe 3 verborgen. Die Darstellung wird aus python-chess und der aktuellen Lernstufe berechnet; freie Modelltexte erzeugen keine ungeprüften Koordinaten. Bei einem Stellungs- oder Stufenwechsel setzt sich die visuelle Auswahl zurück. Eigene Pfeile bleiben separat.

46 Tests bestanden, darunter ursprüngliche gemeldete Stellung, schwarze Perspektive im Schach und Stellung nach einem Spielerzug. JavaScript-Syntaxprüfung bestanden. Browserprüfung: g7–b2 samt Markierung korrekt, Ausblenden entfernt alle Coach-Markierungen/Pfeile, Brettdrehen transformiert den Pfeil korrekt. Partie blieb unverändert. Screenshot: visual-coach-preview.png.

## Materialübersicht (2026-09-27)

Genommene/verlorene Figuren werden aus den tatsächlichen Schlägen der gespeicherten Zugfolge rekonstruiert, inklusive en passant und geschlagener Umwandlungsfiguren. Restmaterial wird direkt auf dem aktuellen Brett gezählt (1/3/3/5/9, König 0), daher sind auch Umwandlungen und abweichende Startstellungen korrekt berücksichtigt. Anzeige aus Spielersicht, unabhängig von der Brettdrehung. 48 Tests bestanden; JavaScript-Syntax geprüft. Browser zeigt für die bestehende Partie korrekt einen genommenen schwarzen Bauern, keine Verluste, 39:38 und Du +1.

## Kompaktere Spielansicht (2026-09-27)

Dekorative Coach-Zwischenüberschrift entfernt, Abstände und Bedienelemente verdichtet. Visuelle Zusatztexte sind aufklappbar; offene Erklärung bleibt beim Wechsel der Angriffsauswahl erhalten. Material zeigt Gewinne/Verluste nebeneinander sowie die Restwerte in der aufklappbaren Werteerklärung. Chat-Eingabe und Senden nebeneinander; Hinweis-, Notiz-, Zugverlauf- und Brettfunktionen bleiben erreichbar. JavaScript-Syntax und Browserdarstellung geprüft, inklusive Aufklappen und Auswahlwechsel. Keine Änderung der Spielregeln oder gespeicherten Partie.


## Überarbeitung nach sieben Browser-Anmerkungen — 27.09.2026

Jonas möchte eine ruhige Spieloberfläche mit dem Chat im Mittelpunkt. Die vorherige Verdichtung hatte zu viele voneinander getrennte Bereiche übriggelassen.

- **Material:** nur zwei Zeilen „Du“ und „Gegner“ mit den jeweils geschlagenen Figuren. Ein positiver Materialwert erscheint ausschließlich bei der führenden Seite; bei Gleichstand keine Zahl. Figurenwerte und Rekonstruktion bleiben unverändert.
- **Coach:** Standardhinweis und freie Antworten erscheinen gemeinsam im Gesprächsverlauf. Eigene Nachrichten sind eingerückt, die Eingabe steht am unteren Rand. Enter sendet, Shift+Enter erzeugt eine neue Zeile. Hinweise und Weiterspielen bleiben separat erreichbar.
- **Bretthilfe:** eine Auswahl mit Vor/Zurück, Zähler und Sichtbarkeitsschalter ersetzt die Button-Sammlung. So beanspruchen auch viele Angriffslinien nur eine Zeile. Die Erklärung bleibt aufklappbar; alle Koordinaten kommen weiterhin aus Brettdaten.
- **Zugverlauf:** über ein Icon am Brett als Dialog öffnen, kein permanenter Bereich in der Coach-Spalte.
- **Brettwerkzeuge:** eine gruppierte Leiste oberhalb des Bretts, durchgehend Lucide-Icons mit Tooltips und zugänglichen Namen. Zeichnen/Löschen, Rücknahme/Drehen/Vorteil, Zugverlauf/PGN.
- **Kopfzeile:** durchgehende Textnavigation; Einstellungen bekommt dieselbe Behandlung wie Partien und neue Partie.
- **Status:** „Dein Lernmoment“ entfernt. Unter dem Brett steht bei tatsächlicher Unterbrechung „Partie pausiert“, ansonsten wer am Zug ist. Technische Modellinfos liegen unter dem Info-Button des Coaches.

Browserprüfung auf separater Profilkopie: Chat senden, erfolgreich dargestellte Testantwort, Fehlerzustand bei nicht verfügbarem Modell, Entwurfserhalt bei Auswahlwechsel, Angriffspfeile, Ausblenden, Zeichenmodus/Löschen, Zugverlauf und Info-Dialog. Helle und dunkle Darstellung sowie 1024×768 und 820×700 geprüft; kein horizontaler Überlauf, Eingabe und Hauptaktionen erreichbar. Erfolgreiche Chatantwort wurde für den UI-Test deterministisch eingespeist, keine neue Aussage zur Modellqualität. Reale Partie unverändert. JavaScript-Syntaxprüfung bestanden.


## Chess Lab — Rebranding, 27.09.2026

Auf Jonas’ Wunsch heißt die App jetzt **Chess Lab**. Eine eigene monochrome SVG-Marke verbindet Bauernkopf und Figurensockel mit einem Laborkolben. „Chess“ steht in Serifenschrift, „LAB“ in kleinerer serifenloser Schrift. Die alte Unterzeile „Raum zum Denken“ entfällt in der Kopfzeile. Kein Maskottchen.

Umgesetzt in App-Kopfzeile, Browsertitel, Favicon, Ladeansicht, Server-Startmeldung und neu exportierten PGN-Eventnamen. Die bestehenden Datenpfade und Projektordner bleiben zur Kompatibilität erhalten. SVG-Dateien unter `outputs/schachcoach/static/brand/`; Kopien der Marken-Assets liegen im Materialordner dieses Obsidian-Projekts.

48 bestehende Tests bestanden. SVG-Auslieferung mit korrektem Dateityp, PGN-Eventname, JavaScript-Syntax sowie helle/dunkle Darstellung geprüft. Jonas’ Bewertung der neuen Marke steht noch aus.


## Konkrete Hilfe im Coach-Dialog — 27.09.2026

Jonas meldet wiederholte allgemeine Fragen trotz ausdrücklicher Lösungsbitte. Ursache: Chat änderte die Hilfestufe nicht; dem Modell wurden Kandidat und Variante vorenthalten, während der Prompt die Lösung verbot. Im echten Qwen-4B-Nachtest kamen auch nach Behebung der Informationslücke falsche freie Aussagen vor (unbelegte Sicherheit und Matt). Der Versuch ist in `data/help-progression-trial-model-baseline.json` erhalten.

Umgesetzt: regelbasierte Gesprächsabsicht steuert Stufe 1/2/3; direkte Lösungsbitten werden unmittelbar beantwortet, „nicht verraten“ bleibt ohne neue Lösung. Kernhilfen und Verteidigerbeschreibungen stammen aus Brettdaten; empfohlener Zug und maximal drei Halbzüge werden gegen die konkrete Ausgangsstellung geprüft. „Warum dieser Zug?“ erklärt Entwicklung und eine belegte Fortsetzung. Bereits gespielte Züge werden nicht erneut empfohlen. Der Gesprächseinstieg bleibt bei automatischem Stufenwechsel erhalten, damit die Antwort nicht doppelt erscheint. Freie Modellantworten folgen der erkannten Sprache; nahezu gleiche Antworten erhalten, soweit verfügbar, die geprüfte Hilfe.

64 Tests bestanden (3,034 s), JavaScript-Syntax geprüft. Neue Prüfungen: deutsche Tippfehler, direktes Verraten, negierte Lösungsbitten, unpassende/illegale Varianten, schwarze Schachabwehr, schon ausgeführte Züge, Persistenz, Hilfe ohne Modell sowie verworfene verspätete Antworten nach Zug/Skip. Gemeldeten Verlauf mit echter Stockfish-Analyse nachgestellt (`data/help-progression-trial.json`). Endgültige fünf Kernantworten werden deterministisch erzeugt: das ist keine Verbesserung der generativen Modellqualität. Browserprüfung auf separater Datenkopie: direkte Lösungsfrage zeigt genau eine Antwort, passenden f1–d3-Pfeil und behält die Stellung; keine Browserfehler. Vorschau: `coach-konkrete-hilfe.png`.

Live-Backend nach gesicherter Profildatei neu gestartet. Kein Modellwechsel. Freie Gespräche außerhalb dieser Kernhilfen bleiben experimentell; keine vollständige semantische Validierung oder pädagogische Gesamt-Abnahme.
