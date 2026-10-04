"""Start the actual backend on a temporary profile; no Ollama/download required."""
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

if __name__ == '__main__':
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    with tempfile.TemporaryDirectory() as tmp:
        process = subprocess.Popen([sys.executable, str(ROOT / 'server.py'), '--port', str(port),
                                    '--data', str(Path(tmp) / 'test.sqlite3'), '--model', 'test-local-model'],
                                   cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError(process.stdout.read())
                try:
                    with opener.open(f'http://127.0.0.1:{port}/api/state', timeout=1) as response:
                        state = json.load(response)
                    break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Server did not become ready')
            assert state['coach_model'] == 'test-local-model', state
            assert state['game'] is None, state
            print('HTTP backend ready; model selection and empty test profile verified.')
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            process.stdout.close()
