# Stockfish lokal installieren

Engine-Dateien sind plattformabhängig und werden nicht in Git gespeichert.

1. Passende Version von https://stockfishchess.org/download/ laden.
2. Das gesamte Archiv in diesen Ordner entpacken (einschließlich Netzdateien, falls enthalten).
3. Chess Lab findet `stockfish*.exe` unter Windows bzw. die ausführbare Stockfish-Datei unter macOS/Linux auch in Unterordnern.

Alternativ `STOCKFISH_PATH` auf die ausführbare Datei setzen. Ein über den PATH verfügbares `stockfish` wird ebenfalls erkannt. Konkrete Windows-Schritte: [WINDOWS.md](../WINDOWS.md).

Stockfish ist GPL-3.0; der offizielle Download enthält die Lizenz- und Quellinformationen. Die Anwendung lädt die Engine als getrennten UCI-Prozess.
