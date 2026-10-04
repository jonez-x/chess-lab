#!/bin/zsh
cd -- "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv || exit 1
  .venv/bin/python -m pip install -r requirements.txt || exit 1
fi
if curl -fsS --max-time 2 http://127.0.0.1:8765/api/state >/dev/null 2>&1; then
  open http://127.0.0.1:8765
else
  .venv/bin/python server.py --open
fi
