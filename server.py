#!/usr/bin/env python3
"""Local-only HTTP app. All chess mutations stay in GameService."""
import argparse
import json
import os
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import signal
import threading
import webbrowser
from urllib.parse import urlsplit

from game import GameService, Engine, Conflict, ROOT
from local_llm import respond as local_coach, MODEL
from profile_lock import acquire_profile_lock, ProfileInUse


class Handler(BaseHTTPRequestHandler):
    server_version = 'ChessLab/0.1'

    def log_message(self, format, *args):
        if len(args) > 1 and str(args[1]).startswith(('4', '5')):
            super().log_message(format, *args)

    def valid_host(self):
        return self.headers.get('Host') in self.server.hosts

    def respond(self, code, data, mime='application/json; charset=utf-8', filename=None):
        if isinstance(data, (dict, list)):
            data = json.dumps(data, ensure_ascii=False).encode()
        elif isinstance(data, str):
            data = data.encode()
        self.send_response(code)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if filename:
            self.send_header('Content-Disposition', 'attachment; filename="' + filename + '"')
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if not self.valid_host():
            return self.respond(403, {'error': 'Nur lokaler Zugriff erlaubt.'})
        path = urlsplit(self.path).path
        try:
            if path == '/api/state':
                return self.respond(200, self.server.app.snapshot())
            if path == '/api/history':
                return self.respond(200, self.server.app.store.history())
            if path == '/api/export/pgn':
                return self.respond(200, self.server.app.pgn(), 'application/x-chess-pgn; charset=utf-8', 'training.pgn')
            if path == '/api/export/backup':
                return self.respond(200, self.server.app.store.backup(), 'application/vnd.sqlite3', 'schachcoach-sicherung.sqlite3')
            files = {'/': ('index.html', 'text/html; charset=utf-8'), '/style.css': ('style.css', 'text/css'), '/app.js': ('app.js', 'text/javascript'), '/vendor/lucide.min.js': ('vendor/lucide.min.js', 'text/javascript')}
            files['/sounds.js'] = ('sounds.js', 'text/javascript')
            for asset in ('chess-lab-mark.svg', 'chess-lab-logo.svg', 'favicon.svg'):
                files['/brand/' + asset] = ('brand/' + asset, 'image/svg+xml')
            files['/images/coach-bishop.png'] = ('images/coach-bishop.png', 'image/png')
            for color in 'wb':
                for piece in 'PNBRQK':
                    asset = 'pieces/cburnett/' + color + piece + '.svg'
                    files['/' + asset] = (asset, 'image/svg+xml')
            if path not in files:
                return self.respond(404, {'error': 'Nicht gefunden.'})
            filename, mime = files[path]
            return self.respond(200, (ROOT / 'static' / filename).read_bytes(), mime)
        except ValueError as exc:
            self.respond(400, {'error': str(exc)})
        except Exception as exc:
            print('GET error:', repr(exc), flush=True)
            self.respond(500, {'error': 'Die lokalen Daten konnten nicht gelesen werden.'})

    def do_POST(self):
        origin = self.headers.get('Origin')
        if not self.valid_host() or (origin and origin not in self.server.origins) or self.headers.get('X-Schachcoach') != '1':
            return self.respond(403, {'error': 'Diese Anfrage ist nicht erlaubt.'})
        if self.path != '/api/command':
            return self.respond(404, {'error': 'Nicht gefunden.'})
        if self.headers.get_content_type() != 'application/json':
            return self.respond(415, {'error': 'JSON erwartet.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16384:
                return self.respond(413, {'error': 'Die Anfrage ist zu groß oder leer.'})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Ungültige Anfrage.')
            self.respond(200, self.server.app.command(data))
        except Conflict as exc:
            self.respond(409, {'error': str(exc), 'state': self.server.app.snapshot()})
        except (ValueError, KeyError, TypeError) as exc:
            self.respond(400, {'error': str(exc)})
        except Exception as exc:
            print('POST error:', repr(exc), flush=True)
            self.respond(500, {'error': 'Die Änderung konnte nicht gespeichert werden. Bitte erneut versuchen.'})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--data', type=Path, default=ROOT / 'data' / 'schachcoach.sqlite3')
    parser.add_argument('--open', action='store_true')
    parser.add_argument('--model', default=os.environ.get('CHESSLAB_MODEL') or MODEL,
                        help='Name eines lokal in Ollama installierten Modells')
    parser.add_argument('--coach-timeout', type=float, default=90,
                        help='Maximale Antwortzeit des lokalen Modells in Sekunden (Standard: 90)')
    args = parser.parse_args()
    if args.coach_timeout <= 0:
        parser.error('--coach-timeout muss positiv sein')
    # Bind first: a second launch must not open a second writer for the same profile.
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    lockfile = args.data.with_suffix('.lock')
    try:
        lock = acquire_profile_lock(lockfile)
    except ProfileInUse as exc:
        server.server_close()
        raise SystemExit(str(exc))
    try:
        engine = Engine()
        try:
            app = GameService(args.data, engine, coach_client=partial(local_coach, model=args.model),
                              coach_timeout=args.coach_timeout, coach_model=args.model)
        except Exception:
            engine.close()
            raise
    except Exception:
        lock.close()
        server.server_close()
        raise
    server.app = app
    server.hosts = {'127.0.0.1:' + str(args.port), 'localhost:' + str(args.port)}
    server.origins = {'http://' + host for host in server.hosts}
    url = 'http://127.0.0.1:' + str(args.port)
    print('Chess Lab läuft unter ' + url, flush=True)
    print('Lokale Daten: ' + str(args.data), flush=True)
    print('Lokales Coach-Modell: ' + args.model, flush=True)
    if args.open:
        webbrowser.open(url)
    def stop(signum, frame):
        threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        server.serve_forever(poll_interval=.2)
    finally:
        server.server_close()
        app.close()
        lock.close()


if __name__ == '__main__':
    main()
