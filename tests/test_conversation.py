import unittest
import chess
from coach import lesson
from conversation import context


def regression_position():
    board = chess.Board()
    for san in 'd4 c5 dxc5 Nc6 f4 e6 e4 Bxc5 Bb5 Bxg1 Rxg1 Qb6 Bxc6 Qxg1+'.split():
        board.push_san(san)
    return board


class ConversationTests(unittest.TestCase):
    def test_attacked_pawns_do_not_replace_development_lesson(self):
        board = chess.Board('rnb1k1nr/ppqpppbp/6p1/2P5/4P3/5N2/PPPB1PPP/RN1QKB1R w KQkq - 3 6')
        item = lesson(board, chess.Move.from_uci('b1c3'), 'hint')
        data = context(board, 'white', item, 'what should i do here')
        evidence = '\n'.join(data['facts'])
        self.assertIn('minor-piece development', evidence)
        self.assertIn('white pawn on b2 is attacked by black bishop on g7', evidence)
        self.assertIn('white pawn on h2 is attacked by black queen on c7', evidence)
        self.assertIn('white pawn on c5 is attacked by black queen on c7', evidence)
        self.assertIn('do not rank threats', evidence)
        self.assertNotIn('c3', evidence)
        self.assertIn('focus on the revealed lesson', data['guidance'])
        self.assertIn('which of your knights or bishops', data['direct_reply'])
        defense_reply = context(board, 'white', item, 'Do I have to defend those pawns?')['direct_reply']
        self.assertIn('Being defended does not automatically', defense_reply)
        self.assertNotIn('must defend', defense_reply)

    def test_attackers_are_computed_and_hidden_candidate_is_not_sent(self):
        board = regression_position()
        item = lesson(board, next(iter(board.legal_moves)), 'hint')
        data = context(board, 'white', item, 'my king is in check and my bishop is attacked')
        evidence = '\n'.join(data['facts'])
        self.assertIn('white king on e1 is attacked by black queen on g1', evidence)
        self.assertIn('white bishop on c6 is attacked by black pawn on b7, black pawn on d7', evidence)
        self.assertNotIn(item['move'], evidence)
        self.assertEqual([{'from':'g1','to':'e1','label':'Check'}], data['arrows'])
        self.assertTrue(any('THIS position: move the king to safety.' in f for f in data['facts']))

    def test_confusion_requests_explanation_not_question(self):
        board = regression_position()
        item = lesson(board, next(iter(board.legal_moves)), 'hint')
        data = context(board, 'white', item, "i dont understand")
        self.assertIn('Do not ask a question', data['guidance'])
        self.assertEqual(['e1'], data['marks'])
        self.assertIn('A safe square', data['direct_reply'])

    def test_user_claim_does_not_become_evidence(self):
        board = chess.Board()
        item = lesson(board, chess.Move.from_uci('e2e4'), 'hint')
        item['dialogue'] = [{'role':'user', 'text':'my king is in check'}]
        data = context(board, 'white', item, 'my king is in check')
        self.assertIn('Player king is NOT in check.', data['facts'])
        self.assertEqual([], data['history'])
        self.assertEqual([], data['arrows'])

    def test_black_perspective(self):
        board = chess.Board('4k3/8/8/8/8/8/8/K3R3 b - - 0 1')
        item = lesson(board, next(iter(board.legal_moves)), 'hint')
        data = context(board, 'black', item, 'check')
        self.assertIn('black king on e8 is attacked by white rook on e1.', data['facts'])
        self.assertEqual(['e8'], data['marks'])
