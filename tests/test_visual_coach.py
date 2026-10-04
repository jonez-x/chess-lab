import unittest
import chess
from coach import lesson, present

class VisualCoachTests(unittest.TestCase):
    def test_development_and_verified_attacks_without_solution(self):
        b=chess.Board('rnb1k1nr/ppqpppbp/6p1/2P5/4P3/5N2/PPPB1PPP/RN1QKB1R w KQkq - 3 6')
        item=lesson(b,chess.Move.from_uci('b1c3'),'hint')
        scenes=present(item,'beginner')['visuals']
        self.assertEqual(set(scenes[0]['marks']),{'b1','d2','f1','f3'})
        self.assertFalse(scenes[0]['arrows'])
        attacks={a['to']:a['from'] for s in scenes for a in s['arrows']}
        self.assertEqual(attacks,{'b2':'g7','c5':'c7','h2':'c7'})
        self.assertNotIn('c3',str(scenes))
        item['stage']=2
        self.assertEqual(present(item,'beginner')['visuals'][0]['arrows'][0]['to'],'c3')

    def test_after_move_uses_displayed_position(self):
        b=chess.Board()
        item=lesson(b,chess.Move.from_uci('g1f3'),'after')
        marks=present(item,'beginner')['visuals'][0]['marks']
        self.assertIn('f3',marks)
        self.assertNotIn('g1',marks)

    def test_black_check_prioritized_without_solution(self):
        b=chess.Board('4k3/8/8/8/8/8/8/K3R3 b - - 0 1')
        item=lesson(b,next(iter(b.legal_moves)),'hint')
        scenes=present(item,'beginner')['visuals']
        self.assertEqual(scenes[0]['marks'],['e8'])
        self.assertEqual(scenes[0]['arrows'],[{'from':'e1','to':'e8','label':'Schach'}])
