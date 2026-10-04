"""Regressions for a coach that gives more help when the player asks for it."""
import threading
import unittest

import chess

from coach import lesson
from conversation import context, prepare_turn
import test_game


def development_hint():
    board = chess.Board()
    analysis = {'engine': 'Test engine', 'perspective': 'white', 'candidates': [{
        'move': 'g1f3', 'pv': ['g1f3', 'g8f6', 'b1c3', 'b8c6'], 'cp': 25,
    }]}
    return board, lesson(board, chess.Move.from_uci('g1f3'), 'hint', analysis)


class HelpProgressionTests(unittest.TestCase):
    def test_reported_german_help_with_typos_gets_progressively_concrete(self):
        _, item = development_hint()
        prepare_turn(item, 'was sollte ich da macheb?')
        self.assertEqual(1, item['stage'])
        self.assertTrue(item.get('teaching_intent'))
        self.assertTrue(item.get('language'))
        prepare_turn(item, 'ich weiß nicht was ich hier machen sollte')
        self.assertEqual(2, item['stage'])

    def test_explicit_answer_requests_reveal_immediately(self):
        for question in ('Keine ahnung sag dus mir', 'Sag mir bitte den Zug',
                         'just tell me the move'):
            with self.subTest(question=question):
                _, item = development_hint()
                prepare_turn(item, question)
                self.assertEqual(2, item['stage'])

    def test_no_spoilers_request_caps_help_without_hiding_an_existing_reveal(self):
        _, item = development_hint()
        for _ in range(3):
            prepare_turn(item, 'nicht verraten, nur einen Hinweis')
            self.assertEqual(1, item['stage'])
        item['stage'] = 2
        prepare_turn(item, 'nicht verraten, nur einen Hinweis')
        self.assertEqual(2, item['stage'])

    def test_unrelated_rule_question_does_not_reveal_the_move(self):
        for question in ('Warum zieht ein Springer in einem L?',
                         'Sag mir warum Rochieren sinnvoll ist',
                         'Sag mir wie ein Springer zieht',
                         'Ich verstehe, danke'):
            with self.subTest(question=question):
                _, item = development_hint()
                prepare_turn(item, question)
                self.assertEqual(0, item['stage'])

    def test_negated_solution_requests_do_not_reveal(self):
        for question in ('Sag mir nicht den Zug', 'Zeig mir nicht den Zug',
                         "Don't give me the answer",
                         "Don't show me the move", 'Do not tell me the move',
                         'Please do not give me the answer'):
            with self.subTest(question=question):
                board, item = development_hint()
                prepare_turn(item, question)
                self.assertEqual(1, item['stage'])
                packet = context(board, 'white', item, question)
                self.assertNotIn('Nf3', packet.get('direct_reply') or '')
                self.assertFalse(any(a['from'] == 'g1' and a['to'] == 'f3'
                                     for a in packet['arrows']))

    def test_revealed_help_contains_legal_move_effect_and_short_sample_line(self):
        board, item = development_hint()
        prepare_turn(item, 'just tell me the move')
        packet = context(board, 'white', item, 'just tell me the move')
        reply = packet['direct_reply']
        self.assertTrue(reply)
        self.assertIn('Nf3', reply)
        self.assertRegex(reply.lower(), r'develop|starting|back rank|minor piece')
        self.assertIn('Nf6', reply)
        self.assertIn('Nc3', reply)
        self.assertNotIn('Nc6', reply)  # Fourth ply: keep the example short.
        self.assertRegex(reply.lower(), r'example|sample|possible|line|continuation')
        self.assertNotRegex(reply.lower(), r'forced (?:line|sequence|continuation)|must play')
        self.assertTrue(any(a['from'] == 'g1' and a['to'] == 'f3'
                            for a in packet['arrows']))

    def test_black_in_check_gets_a_legal_evasion_and_correct_arrow(self):
        board = chess.Board('4k3/8/8/8/8/8/8/K3R3 b - - 0 1')
        move = chess.Move.from_uci('e8f7')
        item = lesson(board, move, 'hint', {'candidates': [{
            'move': 'e8f7', 'pv': ['e8f7', 'e1e7', 'f7f6'],
        }]})
        question = 'Keine Ahnung, sag dus mir'
        prepare_turn(item, question)
        packet = context(board, 'black', item, question)
        self.assertEqual(2, item['stage'])
        self.assertIn('Kf7', packet['direct_reply'])
        self.assertIn('Schach auf', packet['direct_reply'])
        self.assertIn('The player controls black.', ' '.join(packet['facts']))
        arrows = packet['arrows']
        self.assertEqual(1, len(arrows))
        suggested = chess.Move.from_uci(arrows[0]['from'] + arrows[0]['to'])
        self.assertEqual(move, suggested)
        self.assertIn(suggested, board.legal_moves)
        board.push(suggested)
        self.assertFalse(board.is_attacked_by(chess.WHITE, board.king(chess.BLACK)))

    def test_invalid_pv_reply_is_not_presented_as_a_legal_continuation(self):
        board, item = development_hint()
        item['analysis']['candidates'][0]['pv'] = ['g1f3', 'a8a1', 'b1c3']
        prepare_turn(item, 'just tell me the move')
        packet = context(board, 'white', item, 'just tell me the move')
        reply = packet['direct_reply'] or ''
        self.assertIn('Nf3', reply)
        self.assertNotIn('Rxa1', reply)
        self.assertNotIn('a8a1', reply)
        self.assertNotIn('Nc3', reply)  # Do not continue beyond an invalid ply.

    def test_defended_claim_is_not_promoted_to_a_safe_position_fact(self):
        board = chess.Board('rnb1k1nr/ppqpppbp/6p1/2P5/4P3/5N2/PPPB1PPP/RN1QKB1R w KQkq - 3 6')
        item = lesson(board, chess.Move.from_uci('b1c3'), 'hint')
        question = 'All these pieces are defended, so they are safe, right?'
        prepare_turn(item, question)
        packet = context(board, 'white', item, question)
        evidence = '\n'.join(packet['facts']).lower()
        self.assertNotIn('all these pieces are defended', evidence)
        self.assertNotIn('they are safe', evidence)
        self.assertNotIn('all attacks can safely be ignored', evidence)
        self.assertNotIn('you must defend', (packet.get('direct_reply') or '').lower())

    def test_after_move_hint_discusses_completed_effect_not_another_move(self):
        for opening, uci in (('e4 c5 Nf3 Nc6 d4 d6', 'd4d5'),
                             ('e4 d5', 'e4d5')):
            with self.subTest(move=uci):
                board = chess.Board()
                for san in opening.split():
                    board.push_san(san)
                move = chess.Move.from_uci(uci)
                item = lesson(board, move, 'after')
                board.push(move)
                prepare_turn(item, 'keine Ahnung')
                packet = context(board, 'white', item, 'keine Ahnung')
                self.assertEqual(1, item['stage'])
                self.assertIn('d5', packet['direct_reply'])
                self.assertNotRegex(packet['direct_reply'].lower(),
                                    r'suche einen zug|welche gegnerische figur kann er schlagen|prüfe seine legalen züge')
                self.assertIn('It is black to move.', ' '.join(packet['facts']))

    def test_after_move_solution_explains_the_move_already_played(self):
        board = chess.Board()
        for san in 'e4 c5 Nf3 Nc6 d4 d6'.split():
            board.push_san(san)
        move = chess.Move.from_uci('d4d5')
        item = lesson(board, move, 'after')
        board.push(move)
        prepare_turn(item, 'Keine Ahnung, sag dus mir')
        packet = context(board, 'white', item, 'Keine Ahnung, sag dus mir')
        self.assertIn('d5', packet['direct_reply'])
        self.assertIn('c6', packet['direct_reply'])
        self.assertNotRegex(packet['direct_reply'], r'Zieh|Mein Vorschlag')
        self.assertFalse(any(a['from'] == 'd4' and a['to'] == 'd5'
                             for a in packet['arrows']))

    def test_wrong_root_candidate_is_not_recommended_even_if_still_legal(self):
        original = chess.Board()
        item = lesson(original, chess.Move.from_uci('e2e4'), 'hint', {
            'engine': 'Test engine', 'candidates': [{'move': 'e2e4', 'pv': ['e2e4', 'e7e5']}],
        })
        current = original.copy()
        current.push_san('d4')
        current.push_san('d5')
        self.assertIn(chess.Move.from_uci('e2e4'), current.legal_moves)
        prepare_turn(item, 'just tell me the move')
        packet = context(current, 'white', item, 'just tell me the move')
        self.assertFalse(any(a['from'] == 'e2' and a['to'] == 'e4'
                             for a in packet['arrows']))
        self.assertNotRegex(packet.get('direct_reply') or '', r'\be4\b|e2e4')
        self.assertNotIn('The legal candidate is e4.', '\n'.join(packet['facts']))


class HelpChatIntegrationTests(unittest.TestCase):
    setUp = test_game.GameTests.setUp
    tearDown = test_game.GameTests.tearDown
    cmd = test_game.GameTests.cmd
    wait_idle = test_game.GameTests.wait_idle

    def hint(self):
        self.cmd('hint')
        self.wait_idle()

    def test_explicit_request_retains_chat_reveals_arrow_and_persists_stage(self):
        calls = []
        def client(*args, **kwargs):
            calls.append(True)
            raise OSError('Local model is offline')
        self.app.coach_client = client
        self.hint()
        with self.app.lock:
            item = self.app.state['game']['coach']
            item['dialogue'] = [{'role': 'assistant', 'text': 'Which move would you consider?'}]
            candidate = item['move']
        before = self.app.board().fen()
        question = 'Keine ahnung sag dus mir'
        self.cmd('coach_chat', text=question)
        self.app.coach_future.result(2)
        snapshot = self.app.snapshot()['game']
        self.assertEqual(before, snapshot['fen'])
        self.assertEqual(2, snapshot['coach']['stage'])
        self.assertEqual(0, snapshot['coach']['dialogue_intro']['stage'])
        self.assertNotEqual(snapshot['coach']['text'], snapshot['coach']['dialogue_intro']['text'])
        self.assertTrue(snapshot['coach']['revealed'])
        self.assertEqual('Which move would you consider?', snapshot['coach']['dialogue'][0]['text'])
        self.assertEqual(question, snapshot['coach']['dialogue'][-2]['text'])
        self.assertEqual([], calls)
        answer = snapshot['coach']['dialogue'][-1]
        self.assertEqual('guided', answer['source'])
        self.assertIn(candidate[:2], answer['text'])
        self.assertIn(candidate[2:4], answer['text'])
        self.assertFalse(snapshot['coach']['llm_error'])
        self.assertTrue(any(a['from'] == candidate[:2] and a['to'] == candidate[2:4]
                            for a in snapshot['coach']['arrows']))
        stored = self.app.store.load()['game']['coach']
        self.assertEqual(2, stored['stage'])
        self.assertEqual(snapshot['coach']['dialogue'], stored['dialogue'])

    def test_answer_arriving_after_move_is_discarded(self):
        started, release = threading.Event(), threading.Event()
        def slow(*args, **kwargs):
            started.set()
            release.wait(2)
            return {'text': 'Old recommendation'}
        self.app.coach_client = slow
        self.hint()
        candidate = self.app.state['game']['coach']['move']
        self.engine.release.clear()
        try:
            self.cmd('coach_chat', text='Why is development useful?')
            self.assertTrue(started.wait(1))
            self.cmd('move', move=candidate)
        finally:
            release.set()
        self.app.coach_future.result(2)
        self.assertIsNone(self.app.state['game']['coach'])
        self.assertEqual(candidate, self.app.state['game']['moves'][0])

    def test_answer_arriving_after_skip_is_discarded(self):
        started, release = threading.Event(), threading.Event()
        def slow(*args, **kwargs):
            started.set()
            release.wait(2)
            return {'text': 'Old recommendation'}
        self.app.coach_client = slow
        self.hint()
        try:
            self.cmd('coach_chat', text='Why is development useful?')
            self.assertTrue(started.wait(1))
            self.cmd('skip')
        finally:
            release.set()
        self.app.coach_future.result(2)
        self.assertIsNone(self.app.snapshot()['game']['coach'])


if __name__ == '__main__':
    unittest.main()
