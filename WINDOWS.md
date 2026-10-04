# Chess Lab auf Windows

## Einmal einrichten

Benötigt: Git, Python 3.9 oder neuer, [Ollama für Windows](https://ollama.com/download/windows) und [Stockfish](https://stockfishchess.org/download/). Für den ersten Git-Zugriff am privaten Repository mit dem GitHub-Konto anmelden, das Zugriff hat.

In PowerShell im gewünschten Projektverzeichnis:

```powershell
git clone https://github.com/jonez-x/chess-lab.git
cd chess-lab
```

Stockfish für die Architektur deines PCs herunterladen und das gesamte ZIP nach `engine` entpacken. Ein normaler Intel-/AMD-PC verwendet x86-64. Die Datei darf in einem Unterordner liegen, zum Beispiel `engine\stockfish\stockfish-windows-x86-64.exe`. Chess Lab findet `stockfish*.exe` selbst. Den Mac-Engine-Download nicht auf Windows verwenden.

Ollama nach der Installation öffnen. Der Windows-Installer stellt normalerweise bereits den lokalen Dienst auf Port 11434 bereit ([offizielle Anleitung](https://docs.ollama.com/windows)). Andernfalls `Start-Coach-Windows.cmd` öffnen.

## Modell laden und starten

Mit `ollama list` siehst du installierte Modelle. Für den bisherigen Vergleichsstand:

```powershell
ollama pull qwen3.5:4b
.\Start-Windows.cmd --model qwen3.5:4b
```

Für ein anderes lokales Modell den vollständigen Ollama-Namen eingeben:

```powershell
$coachModel = Read-Host 'Name des lokalen Ollama-Modells'
ollama pull $coachModel
.\Start-Windows.cmd --model $coachModel --coach-timeout 180
```

Der Modell-Download kann mehrere GB groß sein. Welche größere Variante zur GPU und zum RAM passt, ist noch nicht entschieden. Der Start lädt kein Modell automatisch; das Modell muss in Ollama installiert sein und JSON-Ausgabe unterstützen. Die bestehende Anbindung deaktiviert Thinking und begrenzt Antworten auf 180 Ausgabetokens.

Das Startskript legt eine eigene Windows-Python-Umgebung an und installiert die Python-Abhängigkeit. Anschließend öffnet sich http://127.0.0.1:8765/. Das Fenster während des Spielens offen lassen. `Ctrl+C` beendet den Server. Vor einem Modellwechsel den bestehenden Chess-Lab-Server beenden und mit dem neuen `--model` erneut starten. Das gewählte Modell steht im Startprotokoll und im Info-Dialog des Coaches.

Alternativ das Modell über `$env:CHESSLAB_MODEL = 'modellname'` setzen. Ohne Modellwahl gilt weiterhin `qwen3.5:4b`. Bei einem kalten, größeren Modell kann `--coach-timeout 180` mehr Ladezeit zulassen.

## Persönliche Daten vom Mac übernehmen (optional)

Git enthält Code und Assets, keine Partien, Chatprotokolle oder Modelle. Für einen frischen Test einfach starten. Für die bisherige Partie im Mac-Projekt die Sicherung `data/schachcoach.sqlite3` separat übertragen: am besten „Sicherung“ in der App exportieren. Die Windows-App vor dem Einsetzen in `data\schachcoach.sqlite3` beenden. Nicht eine noch aktive Datenbank während eines Schreibvorgangs kopieren.

## Modellvergleich

Die Fragen „sag mir den Zug“, „warum dieser Zug?“ und die Kernhilfen können absichtlich ohne Modell beantwortet werden. Damit misst man die geprüfte Hilfe, nicht die Qualität des neuen Sprachmodells. Für einen echten Vergleich dieselbe Stellung, Hilfestufe und freie Rückfrage verwenden, etwa „Wie hängt die Entwicklung meiner Figuren mit meinem nächsten Plan zusammen?“.

## Prüfen und aktualisieren

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
git pull
```

Die Tests benötigen Stockfish. Ollama ist für die automatischen Tests nicht erforderlich. Das Windows-Verhalten wird zusätzlich im GitHub-Actions-Workflow geprüft. Ein vollständiger interaktiver Windows-/GPU-Test bleibt auf deinem PC erforderlich.
