#!/bin/zsh
cd -- "${0:A:h}"
if curl --noproxy '*' -fsS --max-time 2 http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
  echo 'Ollama läuft bereits auf diesem Mac.'
  exit 0
fi
OLLAMA_BIN="$(command -v ollama)"
if [[ -z "$OLLAMA_BIN" && -x /opt/homebrew/bin/ollama ]]; then
  OLLAMA_BIN=/opt/homebrew/bin/ollama
fi
if [[ -z "$OLLAMA_BIN" ]]; then
  echo 'Ollama fehlt. Installiere Ollama und lade qwen3.5:4b.'
  exit 1
fi
echo 'Lokaler Coach-Dienst. Dieses Fenster offen lassen; Ctrl+C beendet ihn.'
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_NO_CLOUD=1
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_CONTEXT_LENGTH=4096
exec "$OLLAMA_BIN" serve
