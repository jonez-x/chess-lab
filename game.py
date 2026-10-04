"""Authoritative chess state, durable storage, revisioned background engine jobs."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
import io
import json
import os
import shutil
import sqlite3
import threading
import uuid

import chess
import chess.engine
import chess.pgn
from coach import lesson, move_facts, present, german_san, CONCEPTS, english_lesson
from conversation import context as conversation_context, prepare_turn

ROOT = Path(__file__).resolve().parent
EXAMPLE_MOVES = ['e2e4', 'c7c5', 'g1f3', 'b8c6', 'd2d4', 'd7d6']


def now():
    return datetime.now(timezone.utc).isoformat()


class Conflict(Exception):
    pass


def find_stockfish(executable=None, root=ROOT, windows=None):
    path = executable or os.environ.get('STOCKFISH_PATH') or shutil.which('stockfish')
    if path:
        return str(path)
    windows = os.name == 'nt' if windows is None else windows
    patterns = ('stockfish*.exe',) if windows else ('stockfish', 'stockfish-macos-*', 'stockfish-ubuntu-*', 'stockfish-linux-*')
    for pattern in patterns:
        for candidate in sorted((root / 'engine').rglob(pattern)):
            if candidate.is_file() and (windows or os.access(candidate, os.X_OK)):
                return str(candidate)
    raise RuntimeError('Stockfish fehlt. Lade die passende Version von https://stockfishchess.org/download/ nach engine/ oder setze STOCKFISH_PATH. Siehe WINDOWS.md.')


class Engine:
    def __init__(self, executable=None):
        path = find_stockfish(executable)
        self.path = path
        self.player = chess.engine.SimpleEngine.popen_uci(path, timeout=8)
        try:
            self.analyst = chess.engine.SimpleEngine.popen_uci(path, timeout=8)
        except Exception:
            self.player.quit()
            raise
        for engine in (self.player, self.analyst):
            engine.configure({'Threads': 1, 'Hash': 32})
        self.play_lock = threading.Lock()
        self.analysis_lock = threading.Lock()
        self.name = self.analyst.id.get('name', 'Stockfish')

    def ensure(self, attribute):
        engine = getattr(self, attribute)
        if engine.returncode.done():
            engine = chess.engine.SimpleEngine.popen_uci(self.path, timeout=8)
            engine.configure({'Threads': 1, 'Hash': 32})
            setattr(self, attribute, engine)
        return engine

    def play(self, board, strength):
        with self.play_lock:
            self.ensure('player')
            self.player.configure({'Skill Level': {'Leicht': 0, 'Mittel': 6, 'Anspruchsvoll': 14}[strength]})
            result = self.player.play(board, chess.engine.Limit(time=.35))
            return result.move

    def analyse(self, board):
        with self.analysis_lock:
            self.ensure('analyst')
            infos = self.analyst.analyse(board, chess.engine.Limit(time=.6), multipv=min(3, board.legal_moves.count()))
        candidates = []
        for info in infos:
            if not info.get('pv'):
                continue
            pv = []
            check = board.copy()
            for move in info['pv'][:6]:
                if move not in check.legal_moves:
                    break
                pv.append(move.uci())
                check.push(move)
            score = info['score'].pov(board.turn)
            candidates.append({'move': pv[0], 'pv': pv, 'cp': score.score(), 'mate': score.mate(), 'depth': info.get('depth')})
        if not candidates:
            raise RuntimeError('Keine analysierbare Fortsetzung.')
        return {'engine': self.name, 'budget_seconds': .6, 'perspective': 'white' if board.turn else 'black', 'candidates': candidates}

    def evaluate(self, board):
        """Return a compact live evaluation from White's perspective."""
        with self.analysis_lock:
            self.ensure('analyst')
            info = self.analyst.analyse(board, chess.engine.Limit(time=.25), info=chess.engine.INFO_SCORE)
        score = info['score'].pov(chess.WHITE)
        return {'cp': score.score(), 'mate': score.mate(), 'depth': info.get('depth'), 'engine': self.name}

    def close(self):
        for engine in (self.player, self.analyst):
            try:
                engine.quit()
            except chess.engine.EngineError:
                pass


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            if db.execute('PRAGMA user_version').fetchone()[0] > 1:
                raise ValueError('Diese Profildatei stammt aus einer neueren App-Version.')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS games (id TEXT PRIMARY KEY, updated TEXT NOT NULL, json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, game_id TEXT NOT NULL, created TEXT NOT NULL, json TEXT NOT NULL);
                PRAGMA user_version=1;
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(str(self.path), timeout=10)
        db.execute('PRAGMA synchronous=FULL')
        try:
            with db:
                yield db
        finally:
            db.close()

    def load(self):
        with self.connect() as db:
            row = db.execute('SELECT json FROM state WHERE id=1').fetchone()
        return json.loads(row[0]) if row else None

    def save(self, state, events):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO state VALUES(1,?)', (json.dumps(state),))
            game = state.get('game')
            if game:
                db.execute('INSERT OR REPLACE INTO games VALUES(?,?,?)', (game['id'], now(), json.dumps(game)))
            for event in events:
                db.execute('INSERT INTO events VALUES(?,?,?,?)', (event['id'], event['game_id'], event['created'], json.dumps(event)))

    def history(self):
        with self.connect() as db:
            games = [json.loads(r[0]) for r in db.execute('SELECT json FROM games ORDER BY updated DESC LIMIT 20')]
            events = [json.loads(r[0]) for r in db.execute('SELECT json FROM events ORDER BY created DESC LIMIT 50')]
        return {'games': [{'id': g['id'], 'created': g['created'], 'moves': len(g['moves']), 'bot': g['bot'], 'result': g.get('result'), 'example': g.get('example', False)} for g in games], 'events': events}

    def get_game(self, game_id):
        with self.connect() as db:
            row = db.execute('SELECT json FROM games WHERE id=?', (game_id,)).fetchone()
        if not row:
            raise ValueError('Diese Partie wurde nicht gefunden.')
        return json.loads(row[0])

    def backup(self):
        # SQLite backup API yields a consistent standalone file, even while the app runs.
        with self.connect() as source, closing(sqlite3.connect(':memory:')) as target:
            source.backup(target)
            # serialize is only available in newer Python; a temp file also works on 3.9.
            import tempfile
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / 'schachcoach.sqlite3'
                with closing(sqlite3.connect(str(path))) as dest:
                    target.backup(dest)
                return path.read_bytes()


class GameService:
    def __init__(self, db_path, engine, coach_client=None, coach_timeout=90, coach_model=None):
        self.store = Store(db_path)
        self.engine = engine
        self.coach_client = coach_client
        self.coach_timeout = coach_timeout
        self.coach_model = coach_model
        self.coach_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='local-coach')
        self.coach_future = None
        self.lock = threading.RLock()
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='chess')
        self.closed = False
        self.events = []
        self.state = self.store.load() or {'version': 1, 'revision': 0, 'profile': {'name': 'Jonas', 'level': 'beginner', 'theme': 'light', 'bot': 'Leicht', 'color': 'white', 'auto_coach': True, 'onboarded': False}, 'game': None}
        self.state['profile'].setdefault('sound', True)
        self.state['profile'].setdefault('show_advantage', True)
        with self.lock:
            if self.state['game']:
                self.state['game']['pending'] = None
                self.state['game']['error'] = None
                if self.state['game'].get('coach'):
                    self.state['game']['coach'].pop('llm_job', None)
            self.save()
            self.schedule_bot()
            self.schedule_evaluation()

    def board(self):
        g = self.state['game']
        board = chess.Board(g['initial_fen'])
        for uci in g['moves']:
            board.push_uci(uci)
        return board

    def save(self):
        self.state['revision'] += 1
        self.store.save(self.state, self.events)
        self.events.clear()

    def event(self, outcome, item=None, **extra):
        g = self.state['game']
        item = item or g.get('coach')
        if not item:
            return
        self.events.append({'id': str(uuid.uuid4()), 'game_id': g['id'], 'created': now(),
                            'concept': item['concept'], 'concept_label': CONCEPTS[item['concept']],
                            'outcome': outcome, 'stage': item['stage'], 'fen': self.board().fen(),
                            'move': item['move'], 'facts': item['facts'], 'analysis': item.get('analysis'),
                            'note': item.get('note', ''), **extra})

    def ended(self, board):
        g = self.state['game']
        outcome = board.outcome()
        if outcome:
            reasons = {chess.Termination.CHECKMATE: 'Schachmatt', chess.Termination.STALEMATE: 'Patt',
                       chess.Termination.INSUFFICIENT_MATERIAL: 'Nicht genügend Material',
                       chess.Termination.SEVENTYFIVE_MOVES: '75-Züge-Regel', chess.Termination.FIVEFOLD_REPETITION: 'Fünffache Stellungswiederholung'}
            g['result'] = {'score': outcome.result(), 'reason': reasons.get(outcome.termination, 'Partie beendet')}
            g['coach'] = None
            g['pending'] = None
        return bool(g.get('result'))

    def snapshot(self):
        with self.lock:
            g = self.state['game']
            result = {'revision': self.state['revision'], 'profile': deepcopy(self.state['profile']), 'engine': self.engine.name, 'local_coach': self.coach_client is not None, 'coach_model': self.coach_model, 'game': None}
            if not g:
                return result
            board = self.board()
            replay = chess.Board(g['initial_fen'])
            moves = []
            captured = {'white': [], 'black': []}
            values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
            for uci in g['moves']:
                move = chess.Move.from_uci(uci)
                victim = replay.piece_at(move.to_square)
                if replay.is_en_passant(move):
                    victim = chess.Piece(chess.PAWN, not replay.turn)
                if replay.is_capture(move) and victim:
                    captured['white' if replay.turn else 'black'].append(victim.symbol())
                moves.append({'uci': uci, 'san': german_san(replay.san(move)), 'capture': replay.is_capture(move), 'color': 'white' if replay.turn else 'black', 'number': replay.fullmove_number})
                replay.push(move)
            active = not g.get('result')
            totals = {name: sum(values[p.piece_type] for p in board.piece_map().values() if p.color == color)
                      for name, color in [('white', chess.WHITE), ('black', chess.BLACK)]}
            for pieces in captured.values():
                pieces.sort(key=lambda symbol: values[chess.Piece.from_symbol(symbol).piece_type], reverse=True)
            human_turn = board.turn == (g['color'] == 'white')
            playable = active and human_turn and not g['pending'] and (not g['coach'] or g['coach']['kind'] == 'hint')
            result['game'] = {'id': g['id'], 'fen': board.fen(), 'pieces': {chess.square_name(s): p.symbol() for s, p in board.piece_map().items()},
                              'moves': moves, 'bot': g['bot'], 'color': g['color'], 'turn': 'white' if board.turn else 'black',
                              'material': {'captured': captured, 'totals': totals, 'balance_white': totals['white'] - totals['black']},
                              'check': chess.square_name(board.king(board.turn)) if board.is_check() else None,
                              'legal_moves': [m.uci() for m in board.legal_moves] if playable else [],
                              'capture_moves': [m.uci() for m in board.legal_moves if board.is_capture(m)] if playable else [],
                              'pending': g['pending']['kind'] if g['pending'] else None, 'error': g.get('error'),
                              'evaluation': deepcopy(g.get('evaluation')), 'evaluation_pending': bool(g.get('evaluation_pending')),
                              'result': g.get('result'), 'can_claim_draw': active and human_turn and board.can_claim_draw(),
                              'coach': present(g['coach'], self.state['profile']['level']) if g['coach'] else None,
                              'example': g.get('example', False)}
            return result

    def schedule_bot(self):
        g = self.state['game']
        if self.closed or not g or g.get('result') or g['coach'] or g['pending'] or g.get('error'):
            return
        board = self.board()
        if board.turn == (g['color'] == 'white') or board.is_game_over():
            return
        if board.can_claim_draw():
            g['result'] = {'score': '1/2-1/2', 'reason': 'Trainingspartner reklamiert Remis'}
            self.save()
            return
        job = str(uuid.uuid4())
        g['pending'] = {'id': job, 'kind': 'bot'}
        self.save()
        self.pool.submit(self.engine_job, g['id'], job, 'bot', board, g['bot'])

    def schedule_evaluation(self):
        """Evaluate the current position in the background without blocking play."""
        if self.closed or not hasattr(self.engine, 'evaluate'):
            return
        with self.lock:
            g = self.state['game']
            if not g or g.get('result'):
                return
            board = self.board()
            fen = board.fen()
            if g.get('evaluation_fen') == fen and (g.get('evaluation') is not None or g.get('evaluation_pending')):
                return
            job = str(uuid.uuid4())
            g['evaluation'] = None
            g['evaluation_fen'] = fen
            g['evaluation_pending'] = job
            self.save()
            self.pool.submit(self.evaluation_job, g['id'], job, fen, board)

    def evaluation_job(self, game_id, job, fen, board):
        try:
            value = self.engine.evaluate(board)
            with self.lock:
                g = self.state['game']
                if self.closed or not g or g['id'] != game_id or g.get('evaluation_pending') != job or self.board().fen() != fen:
                    return
                g['evaluation'] = value
                g['evaluation_pending'] = None
                self.save()
        except Exception as exc:
            with self.lock:
                g = self.state['game']
                if not self.closed and g and g['id'] == game_id and g.get('evaluation_pending') == job:
                    g['evaluation_pending'] = None
                    self.save()
            print('Evaluation error:', type(exc).__name__, str(exc), flush=True)

    def engine_job(self, game_id, job, kind, board, strength=None):
        try:
            value = self.engine.play(board, strength) if kind == 'bot' else self.engine.analyse(board)
            with self.lock:
                g = self.state['game']
                if self.closed or not g or g['id'] != game_id or not g['pending'] or g['pending']['id'] != job:
                    return
                if kind == 'bot':
                    if value not in board.legal_moves:
                        raise ValueError('Die Engine hat keinen legalen Zug geliefert.')
                    g['evaluation'] = None
                    g['evaluation_fen'] = None
                    g['evaluation_pending'] = None
                    g['moves'].append(value.uci())
                    self.ended(self.board())
                else:
                    candidate = chess.Move.from_uci(value['candidates'][0]['move'])
                    g['coach'] = lesson(board, candidate, 'hint', value)
                    self.event('offered')
                g['pending'] = None
                self.save()
            self.schedule_evaluation()
        except Exception as exc:
            with self.lock:
                g = self.state['game']
                if not self.closed and g and g['id'] == game_id and g['pending'] and g['pending']['id'] == job:
                    g['pending'] = None
                    g['error'] = 'Die Engine konnte nicht antworten. Du kannst es erneut versuchen.'
                    self.save()
            print('Engine error:', type(exc).__name__, str(exc), flush=True)

    def coach_job(self, game_id, job, item, facts, question):
        try:
            if facts.get('direct_reply'):
                answer = {'text': facts['direct_reply'], 'source': 'guided'}
            else:
                answer = self.coach_client(facts, 'reply' if question else ('explain' if item['stage'] == 2 else 'question'),
                                           question, timeout=self.coach_timeout)
            error = None
        except Exception:
            answer = None
            error = 'Lokaler Coach nicht erreichbar oder Antwort unvollständig. Starte Ollama und prüfe, ob das gewählte Modell installiert ist. Der Standardhinweis bleibt verfügbar.'
        with self.lock:
            g = self.state['game']
            c = g.get('coach') if g else None
            if self.closed or not g or g['id'] != game_id or not c or c.get('llm_job') != job:
                return
            c.pop('llm_job', None)
            c['llm_error'] = error
            if answer:
                c['llm_arrows'] = facts.get('arrows', [])
                c['llm_marks'] = facts.get('marks', [])
                c.setdefault('dialogue', []).append({'role': 'assistant', 'text': answer['text'], 'source': answer.get('source', 'model')})
                c['dialogue'] = c['dialogue'][-8:]
            self.save()

    def command(self, data):
        with self.lock:
            if data.get('revision') != self.state['revision']:
                raise Conflict('Die Partie hat sich inzwischen geändert. Die Ansicht wurde aktualisiert.')
            old = deepcopy(self.state)
            previous_events = list(self.events)
            try:
                self.mutate(data)
                self.save()
            except Exception:
                self.state = old
                self.events = previous_events
                raise
            if data['action'] == 'hint' and self.state['game']['pending']:
                g = self.state['game']
                self.pool.submit(self.engine_job, g['id'], g['pending']['id'], 'hint', self.board())
            if data['action'] == 'coach_chat':
                g = self.state['game']
                c = g['coach']
                # Chat intent can advance the reveal stage. The candidate/PV
                # still stays hidden while the player only wants a hint.
                facts = conversation_context(self.board(), g['color'], c, str(data.get('text', '')).strip())
                self.coach_future = self.coach_pool.submit(self.coach_job, g['id'], c['llm_job'], deepcopy(c), facts, str(data.get('text', '')).strip())
            self.schedule_bot()
            self.schedule_evaluation()
            return self.snapshot()

    def mutate(self, data):
        action = data.get('action')
        g = self.state['game']
        if action == 'settings':
            values = data.get('settings', {})
            options = {'level': ('beginner', 'returning', 'confident'), 'theme': ('light', 'dark'),
                       'bot': ('Leicht', 'Mittel', 'Anspruchsvoll'), 'color': ('white', 'black')}
            for key, allowed in options.items():
                if key in values:
                    if values[key] not in allowed:
                        raise ValueError('Ungültige Einstellung: ' + key)
                    self.state['profile'][key] = values[key]
            for key in ('auto_coach', 'onboarded', 'sound', 'show_advantage'):
                if key in values:
                    if type(values[key]) is not bool:
                        raise ValueError('Ungültige Einstellung.')
                    self.state['profile'][key] = values[key]
            if 'name' in values:
                self.state['profile']['name'] = str(values['name']).strip()[:40] or 'Jonas'
            return
        if action in ('new', 'example'):
            if g and g.get('coach'):
                self.event('interrupted')
            p = self.state['profile']
            self.state['game'] = {'id': str(uuid.uuid4()), 'created': now(), 'initial_fen': chess.STARTING_FEN,
                                  'moves': list(EXAMPLE_MOVES) if action == 'example' else [], 'color': 'white' if action == 'example' else p['color'],
                                  'bot': p['bot'], 'coach': None, 'pending': None, 'result': None, 'error': None,
                                  'last_auto_ply': -10, 'example': action == 'example', 'evaluation': None,
                                  'evaluation_fen': None, 'evaluation_pending': None}
            self.state['profile']['onboarded'] = True
            return
        if action == 'resume':
            if g and g.get('coach'):
                self.event('interrupted')
            self.state['game'] = self.store.get_game(str(data.get('game_id')))
            self.state['game']['pending'] = None
            self.state['game']['error'] = None
            self.state['game']['evaluation'] = None
            self.state['game']['evaluation_fen'] = None
            self.state['game']['evaluation_pending'] = None
            if self.state['game'].get('coach'):
                self.state['game']['coach'].pop('llm_job', None)
            return
        if not g:
            raise ValueError('Starte zuerst eine Partie.')
        board = self.board()
        if action == 'coach_chat':
            if not self.coach_client or not g.get('coach') or g.get('result'):
                raise ValueError('Fordere zuerst einen Hinweis an.')
            if self.coach_future and not self.coach_future.done():
                raise ValueError('Der lokale Coach antwortet noch. Bitte kurz warten.')
            question = str(data.get('text', '')).strip()
            if len(question) > 1000:
                raise ValueError('Bitte höchstens 1000 Zeichen senden.')
            c = g['coach']
            if not c.get('dialogue_intro'):
                c['dialogue_intro'] = {'text': present(c, self.state['profile']['level'])['text'], 'stage': c['stage']}
            old_stage = c['stage']
            prepare_turn(c, question)
            if c['stage'] != old_stage:
                c.pop('llm_arrows', None)
                c.pop('llm_marks', None)
                self.event('solution_shown' if c['stage'] == 2 else 'hint_shown')
            c['llm_job'] = str(uuid.uuid4())
            c['llm_error'] = None
            if question:
                c.setdefault('dialogue', []).append({'role': 'user', 'text': question})
                c['dialogue'] = c['dialogue'][-8:]
        elif action == 'move':
            if g['result'] or g['pending'] or board.turn != (g['color'] == 'white') or (g['coach'] and g['coach']['kind'] != 'hint'):
                raise ValueError('Gerade ist kein eigener Zug möglich.')
            try:
                move = chess.Move.from_uci(str(data.get('move', '')))
            except ValueError:
                raise ValueError('Dieser Zug ist ungültig.')
            if move not in board.legal_moves:
                raise ValueError('Dieser Zug ist in der Stellung nicht erlaubt.')
            had_hint = bool(g['coach'])
            if g['coach']:
                self.event('move_after_help', attempted_move=move.uci())
            g['coach'] = None
            g['error'] = None
            g['evaluation'] = None
            g['evaluation_fen'] = None
            g['evaluation_pending'] = None
            g['moves'].append(move.uci())
            if self.ended(self.board()):
                return
            facts = move_facts(board, move)
            if not had_hint and self.state['profile']['auto_coach'] and len(g['moves']) - g['last_auto_ply'] >= 10 and any(f['kind'] == 'attack' for f in facts):
                g['coach'] = lesson(board, move)
                g['last_auto_ply'] = len(g['moves'])
                self.event('offered')
        elif action == 'hint':
            if g['result'] or g['pending'] or g['coach'] or board.turn != (g['color'] == 'white'):
                raise ValueError('Ein Hinweis ist gerade nicht verfügbar.')
            g['error'] = None
            g['pending'] = {'id': str(uuid.uuid4()), 'kind': 'hint'}
        elif action == 'next':
            if not g['coach']:
                raise ValueError('Kein aktiver Lernmoment.')
            g['coach']['stage'] = min(2, g['coach']['stage'] + 1)
            g['coach'].pop('llm_job', None)
            g['coach'].pop('llm_error', None)
            g['coach']['dialogue'] = []
            g['coach'].pop('dialogue_intro', None)
            g['coach'].pop('llm_arrows', None)
            g['coach'].pop('llm_marks', None)
            self.event('solution_shown' if g['coach']['stage'] == 2 else 'hint_shown')
        elif action == 'note':
            if not g['coach']:
                raise ValueError('Kein aktiver Lernmoment.')
            note = str(data.get('note', '')).strip()[:1000]
            g['coach']['note'] = note
            self.event('reflection', reflection=note)
        elif action == 'skip':
            self.event('skipped')
            g['coach'] = None
            if g['pending'] and g['pending']['kind'] == 'hint':
                g['pending'] = None
            g['error'] = None
        elif action in ('undo', 'retry'):
            if not g['moves']:
                raise ValueError('Noch kein Zug zum Zurücknehmen.')
            self.event('retry' if action == 'retry' else 'interrupted')
            g['pending'] = None
            g['coach'] = None
            g['error'] = None
            g['evaluation'] = None
            g['evaluation_fen'] = None
            g['evaluation_pending'] = None
            g['result'] = None
            board.pop()
            g['moves'].pop()
            if board.turn != (g['color'] == 'white') and g['moves']:
                board.pop()
                g['moves'].pop()
        elif action == 'retry_engine':
            g['error'] = None
        elif action == 'claim_draw':
            if g['result'] or board.turn != (g['color'] == 'white') or not board.can_claim_draw():
                raise ValueError('Hier kann kein Remis reklamiert werden.')
            self.event('interrupted')
            g['pending'] = None
            g['coach'] = None
            g['evaluation_pending'] = None
            g['result'] = {'score': '1/2-1/2', 'reason': 'Remis reklamiert'}
        elif action == 'resign':
            if g['result']:
                raise ValueError('Die Partie ist bereits beendet.')
            self.event('interrupted')
            g['pending'] = None
            g['coach'] = None
            g['evaluation_pending'] = None
            g['result'] = {'score': '0-1' if g['color'] == 'white' else '1-0', 'reason': 'Aufgegeben'}
        else:
            raise ValueError('Unbekannte Aktion.')

    def pgn(self):
        with self.lock:
            if not self.state['game']:
                raise ValueError('Noch keine Partie vorhanden.')
            g = self.state['game']
            game = chess.pgn.Game.from_board(self.board())
            game.headers['Event'] = 'Chess Lab Training'
            game.headers['Date'] = g['created'][:10].replace('-', '.')
            game.headers['White'] = self.state['profile']['name'] if g['color'] == 'white' else 'Stockfish · ' + g['bot']
            game.headers['Black'] = self.state['profile']['name'] if g['color'] == 'black' else 'Stockfish · ' + g['bot']
            if g.get('result'):
                game.headers['Result'] = g['result']['score']
            return str(game) + '\n'

    def close(self):
        with self.lock:
            self.closed = True
        self.pool.shutdown(wait=True)
        self.coach_pool.shutdown(wait=True)
        self.engine.close()
