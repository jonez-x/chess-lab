"""Replay Jonas' report with real Stockfish and the locally installed model.

Does not open or modify the user's profile database.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chess
from coach import lesson
from conversation import context, prepare_turn
from game import Engine
from local_llm import respond


if __name__ == '__main__':
    board = chess.Board('rnb1k2r/p2ppp1p/1qP3p1/3P4/8/b4N2/P1PB1PPP/R3KB1R w KQkq - 1 12')
    engine = Engine()
    try:
        analysis = engine.analyse(board)
    finally:
        engine.close()
    item = lesson(board, chess.Move.from_uci(analysis['candidates'][0]['move']), 'hint', analysis)
    item['dialogue'] = []
    results = []
    for question in ('was sollte ich da macheb?', 'Die angrfiffe sind technicaly alle gedeckt',
                     'Keine ahnung sag dus mir', 'ich weiß nicht was ich hier machen sollte',
                     'warum hilft mir dieser Zug?'):
        prepare_turn(item, question)
        item['dialogue'].append({'role': 'user', 'text': question})
        packet = context(board, 'white', item, question)
        answer = respond(packet, 'reply', question, timeout=45)
        item['dialogue'].append({'role': 'assistant', 'text': answer['text']})
        result = {'question': question, 'stage': item['stage'], **answer, 'arrows': packet['arrows']}
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    destination = Path(__file__).resolve().parents[1] / 'data/help-progression-trial.json'
    destination.write_text(json.dumps({'fen': board.fen(), 'analysis': analysis, 'turns': results}, ensure_ascii=False, indent=2) + '\n')
