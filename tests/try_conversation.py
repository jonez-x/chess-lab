"""Manual local-model regression for the reported conversation loop."""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_conversation import regression_position
from coach import lesson
from conversation import context
from local_llm import respond

if __name__ == '__main__':
    board = regression_position()
    item = lesson(board, next(iter(board.legal_moves)), 'hint')
    item['dialogue'] = []
    results = []
    for question in ['ah my king is in check as well',
                     'my king is attacked by the queen and the bishop by two pawns',
                     'we just said that', 'i dont understand']:
        item['dialogue'].append({'role': 'user', 'text': question})
        packet = context(board, 'white', item, question)
        answer = respond(packet, 'reply', question)
        item['dialogue'].append({'role': 'assistant', 'text': answer['text']})
        results.append({'question': question, **answer, 'arrows': packet['arrows']})
        print(json.dumps(results[-1]), flush=True)
    destination = Path(__file__).resolve().parents[1] / 'data/conversation-regression.json'
    destination.write_text(json.dumps(results, indent=2)+'\n')
