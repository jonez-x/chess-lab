import io
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest

import chess
import chess.pgn
from coach import move_facts, lesson, present
from game import GameService, Conflict, Engine, EXAMPLE_MOVES, Store


class FakeEngine:
    name = 'Test engine'
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.release.set()
        self.fail = False
    def play(self, board, strength):
        self.started.set()
        self.release.wait(3)
        if self.fail:
            raise RuntimeError('controlled test failure')
        return next(iter(board.legal_moves))
    def analyse(self, board):
        move = self.play(board, '')
        return {'engine': self.name, 'candidates': [{'move': move.uci(), 'pv': [move.uci()]}]}
    def close(self):
        self.release.set()


class GameTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = FakeEngine()
        self.path = Path(self.tmp.name) / 'profile.sqlite3'
        self.app = GameService(self.path, self.engine)
        self.cmd('new')
    def tearDown(self):
        self.engine.release.set()
        self.app.close()
        self.tmp.cleanup()
    def cmd(self, action, **kwargs):
        return self.app.command({'revision': self.app.state['revision'], 'action': action, **kwargs})
    def position(self, fen, color='white'):
        with self.app.lock:
            g = self.app.state['game']
            g.update(initial_fen=fen, moves=[], color=color, coach=None, pending=None, result=None, error=None)
            self.app.save()
    def wait_idle(self):
        for _ in range(100):
            if not self.app.snapshot()['game']['pending']:
                return
            time.sleep(.01)
        self.fail('Engine job did not finish')
    def test_capture_targets_include_en_passant(self):
        self.position('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2')
        self.assertIn('e5d6',self.app.snapshot()['game']['capture_moves'])
        self.assertNotIn('e5e6',self.app.snapshot()['game']['capture_moves'])
        self.engine.release.clear();self.cmd('move',move='e5d6')
        self.assertTrue(self.app.snapshot()['game']['moves'][-1]['capture'])

    def test_material_replays_captures_and_undo(self):
        self.position(chess.STARTING_FEN, color='black')
        self.app.state['game']['moves'] = ['e2e4', 'd7d5', 'e4d5', 'd8d5']
        material = self.app.snapshot()['game']['material']
        self.assertEqual(material['captured'], {'white':['p'], 'black':['P']})
        self.assertEqual(material['totals'], {'white':38, 'black':38})
        self.app.state['game']['moves'].pop()
        material = self.app.snapshot()['game']['material']
        self.assertEqual(material['captured']['black'], [])
        self.assertEqual(material['balance_white'], 1)

    def test_material_en_passant_and_promoted_piece_capture(self):
        self.position('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2')
        self.app.state['game']['moves'] = ['e5d6']
        self.assertEqual(self.app.snapshot()['game']['material']['captured']['white'], ['p'])
        self.position('7r/6P1/4k3/8/8/8/8/K7 w - - 0 1')
        self.app.state['game']['moves'] = ['g7g8q', 'h8g8']
        material = self.app.snapshot()['game']['material']
        self.assertEqual(material['captured']['black'], ['Q'])
        self.assertEqual(material['totals'], {'white':0, 'black':5})
    def test_capture_target_is_legal_and_normal_move_is_quiet(self):
        self.cmd('example')
        captures=self.app.snapshot()['game']['capture_moves']
        self.assertIn('d4c5',captures)
        self.assertNotIn('d4d5',captures)
        self.assertTrue(all(m in self.app.snapshot()['game']['legal_moves'] for m in captures))
        self.assertFalse(self.app.snapshot()['game']['moves'][-1]['capture'])
    def test_sound_preference_persists(self):
        self.assertTrue(self.app.snapshot()['profile']['sound'])
        self.cmd('settings',settings={'sound':False})
        self.assertFalse(self.app.store.load()['profile']['sound'])
        with self.assertRaises(ValueError):self.cmd('settings',settings={'sound':'yes'})
    def test_illegal_move_does_not_change_or_save(self):
        old = self.app.snapshot()
        with self.assertRaises(ValueError): self.cmd('move', move='e2e5')
        self.assertEqual(old, self.app.snapshot())
        self.assertEqual([], self.app.store.load()['game']['moves'])
    def test_double_request_is_rejected(self):
        rev = self.app.state['revision']
        self.cmd('settings', settings={'theme': 'dark'})
        with self.assertRaises(Conflict): self.app.command({'action':'new','revision':rev})
    def test_castling_moves_rook(self):
        self.position('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1')
        self.engine.release.clear()
        self.cmd('move',move='e1g1')
        board=self.app.board()
        self.assertEqual(chess.KING,board.piece_type_at(chess.G1))
        self.assertEqual(chess.ROOK,board.piece_type_at(chess.F1))
    def test_castle_through_check_illegal(self):
        self.position('r3k2r/8/8/8/8/5r2/8/R3K2R w KQkq - 0 1')
        with self.assertRaises(ValueError):self.cmd('move',move='e1g1')
    def test_en_passant(self):
        self.position('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2')
        self.engine.release.clear()
        self.cmd('move',move='e5d6')
        self.assertIsNone(self.app.board().piece_at(chess.D5))
        self.assertEqual(chess.PAWN,self.app.board().piece_type_at(chess.D6))
    def test_all_promotions_and_underpromotion(self):
        self.position('4k3/P7/8/8/8/8/8/4K3 w - - 0 1')
        moves=self.app.snapshot()['game']['legal_moves']
        for piece in 'qrbn':self.assertIn('a7a8'+piece,moves)
        with self.assertRaises(ValueError):self.cmd('move',move='a7a8')
        self.cmd('move',move='a7a8n')
        self.assertEqual(chess.KNIGHT,self.app.board().piece_type_at(chess.A8))
        self.assertEqual('1/2-1/2',self.app.snapshot()['game']['result']['score'])
    def test_checkmate(self):
        self.position('7k/5Q2/6K1/8/8/8/8/8 w - - 0 1')
        self.cmd('move',move='f7g7')
        self.assertEqual('1-0',self.app.snapshot()['game']['result']['score'])
        self.assertEqual('Schachmatt',self.app.snapshot()['game']['result']['reason'])
    def test_stalemate(self):
        self.position('7k/5Q2/6K1/8/8/8/8/8 w - - 0 1')
        self.cmd('move',move='f7e6')
        self.assertEqual('Patt',self.app.snapshot()['game']['result']['reason'])
    def test_undo_invalidates_running_bot(self):
        self.engine.release.clear()
        self.cmd('move',move='e2e4')
        self.assertTrue(self.engine.started.wait(1))
        self.cmd('undo')
        self.engine.release.set()
        time.sleep(.07)
        self.assertEqual(chess.STARTING_FEN,self.app.board().fen())
    def test_stale_engine_error_is_ignored(self):
        self.engine.release.clear(); self.engine.fail=True
        self.cmd('move',move='e2e4'); self.engine.started.wait(1)
        self.cmd('undo'); self.engine.release.set();time.sleep(.07)
        self.assertIsNone(self.app.snapshot()['game']['error'])
    def test_new_game_ignores_old_bot(self):
        self.engine.release.clear();self.cmd('move',move='e2e4');self.engine.started.wait(1)
        self.cmd('new');self.engine.release.set();time.sleep(.07)
        self.assertEqual([],self.app.state['game']['moves'])
    def test_example_pauses_and_skip_reveals_nothing(self):
        self.cmd('example');self.cmd('move',move='d4d5')
        snapshot=self.app.snapshot()['game']
        self.assertIsNotNone(snapshot['coach']);self.assertIsNone(snapshot['pending'])
        self.assertEqual([],snapshot['coach']['arrows']);self.assertNotIn('facts',snapshot['coach'])
        self.engine.release.clear();self.cmd('skip')
        snapshot=self.app.snapshot()['game']
        self.assertIsNone(snapshot['coach']);self.assertEqual('bot',snapshot['pending'])
        self.assertEqual('skipped',self.app.store.history()['events'][0]['outcome'])
    def test_hint_skip_cancels_pending_analysis(self):
        self.engine.release.clear();self.cmd('hint');self.engine.started.wait(1)
        self.cmd('skip');self.engine.release.set();time.sleep(.07)
        self.assertIsNone(self.app.snapshot()['game']['coach'])
        self.assertEqual(20,len(self.app.snapshot()['game']['legal_moves']))
    def test_progressive_hints_no_early_solution(self):
        self.cmd('hint');self.wait_idle()
        self.assertEqual([],self.app.snapshot()['game']['coach']['arrows'])
        self.cmd('next');self.assertEqual([],self.app.snapshot()['game']['coach']['arrows'])
        self.cmd('next');self.assertEqual(1,len(self.app.snapshot()['game']['coach']['arrows']))
    def test_reflection_persists_no_comprehension_claim(self):
        self.cmd('example');self.cmd('move',move='d4d5');self.cmd('note',note='Ich greife den Springer an.')
        events=self.app.store.history()['events']
        self.assertEqual('reflection',events[0]['outcome'])
        self.assertEqual('Ich greife den Springer an.',events[0]['note'])
    def test_profile_backup_and_reload(self):
        self.cmd('example');self.cmd('settings',settings={'theme':'dark','level':'returning'})
        before=self.app.board().fen()
        backup=Path(self.tmp.name)/'backup.sqlite3';backup.write_bytes(self.app.store.backup())
        with sqlite3.connect(backup) as db:self.assertEqual('ok',db.execute('PRAGMA integrity_check').fetchone()[0])
        app=GameService(backup,FakeEngine())
        try:
            self.assertEqual(before,app.board().fen())
            self.assertEqual('dark',app.state['profile']['theme'])
        finally:app.close()
    def test_save_failure_rolls_back_memory(self):
        old=self.app.snapshot();save=self.app.store.save
        def fail(*args):raise OSError('Disk full')
        self.app.store.save=fail
        try:
            with self.assertRaises(OSError):self.cmd('settings',settings={'theme':'dark'})
            self.assertEqual(old,self.app.snapshot())
        finally:self.app.store.save=save
    def test_pgn_export_replays_same_position(self):
        self.cmd('example');self.cmd('move',move='d4d5')
        game=chess.pgn.read_game(io.StringIO(self.app.pgn()))
        self.assertEqual(self.app.board().fen(),game.end().board().fen())
    def test_repetition_survives_storage(self):
        with self.app.lock:
            self.app.state['game']['moves']=['g1f3','g8f6','f3g1','f6g8']*2
            self.app.save()
        self.assertTrue(self.app.snapshot()['game']['can_claim_draw'])
        self.cmd('claim_draw');self.assertEqual('1/2-1/2',self.app.snapshot()['game']['result']['score'])
    def test_black_player_turn_and_move(self):
        self.position('rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1','black')
        self.engine.release.clear();self.cmd('move',move='c7c5')
        self.assertEqual(chess.PAWN,self.app.board().piece_type_at(chess.C5))
    def test_archive_resume(self):
        self.cmd('example');game_id=self.app.state['game']['id'];self.cmd('new');self.cmd('resume',game_id=game_id)
        self.assertEqual(EXAMPLE_MOVES,self.app.state['game']['moves'])


class FactsTests(unittest.TestCase):
    def test_example_claims_only_actual_attack(self):
        b=chess.Board()
        for move in EXAMPLE_MOVES:b.push_uci(move)
        facts=move_facts(b,chess.Move.from_uci('d4d5'))
        self.assertEqual(['attack-d5-c6'],[f['id'] for f in facts])
        self.assertTrue(b.is_attacked_by(chess.WHITE,chess.D4))
        self.assertTrue(b.is_attacked_by(chess.BLACK,chess.D4))
    def test_black_pawn_attack_direction(self):
        b=chess.Board('4k3/8/3p4/8/2N5/8/8/4K3 b - - 0 1')
        facts=move_facts(b,chess.Move.from_uci('d6d5'))
        self.assertEqual('c4',facts[0]['to'])
    def test_no_false_attack_of_own_piece(self):
        b=chess.Board('4k3/8/2N5/8/3P4/8/8/4K3 w - - 0 1')
        self.assertEqual([],move_facts(b,chess.Move.from_uci('d4d5')))
    def test_pinned_piece_does_not_create_illegal_hint(self):
        b=chess.Board('k3r3/8/8/8/8/8/4R3/4K3 w - - 0 1')
        with self.assertRaises(AssertionError):move_facts(b,chess.Move.from_uci('e2d2'))


class RealEngineTests(unittest.TestCase):
    def test_stockfish_play_and_analysis_are_legal(self):
        engine=Engine()
        try:
            self.assertIsNot(engine.player,engine.analyst)
            board=chess.Board()
            for strength in ('Leicht','Mittel','Anspruchsvoll'):
                move=engine.play(board,strength);self.assertIn(move,board.legal_moves)
            analysis=engine.analyse(board)
            self.assertGreaterEqual(len(analysis['candidates']),1)
            for candidate in analysis['candidates']:
                replay=board.copy()
                for uci in candidate['pv']:
                    move=chess.Move.from_uci(uci);self.assertIn(move,replay.legal_moves);replay.push(move)
            evaluation=engine.evaluate(board)
            self.assertIsInstance(evaluation['cp'], int)
            self.assertIsNone(evaluation['mate'])
            self.assertTrue(evaluation['engine'])
        finally:engine.close()

if __name__=='__main__':unittest.main()
