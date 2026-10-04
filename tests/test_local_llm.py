import io
import json
import unittest
from unittest.mock import MagicMock, patch

from local_llm import respond


class LocalCoachTests(unittest.TestCase):
    def call_with(self, content, done=True, reason='stop', **options):
        response = {'done': done, 'done_reason': reason,
                    'message': {'content': content}, 'eval_count': 12}
        transport = MagicMock()
        transport.open.return_value = io.BytesIO(json.dumps(response).encode())
        with patch('local_llm.urllib.request.build_opener', return_value=transport):
            result = respond(['The king is in check.'], **options)
        request = transport.open.call_args.args[0]
        return result, request

    def test_local_request_has_bounded_context_and_no_thinking(self):
        result, request = self.call_with('{"text":"You cannot castle out of check."}')
        self.assertEqual('You cannot castle out of check.', result['text'])
        self.assertEqual('http://127.0.0.1:11434/api/chat', request.full_url)
        payload = json.loads(request.data)
        self.assertFalse(payload['think'])
        self.assertEqual(4096, payload['options']['num_ctx'])
        self.assertEqual(180, payload['options']['num_predict'])

    def test_rejects_truncation_even_if_json_looks_valid(self):
        with self.assertRaises(ValueError):
            self.call_with('{"text":"A partial thought"}', reason='length')

    def test_selected_model_is_sent_to_ollama(self):
        result, request = self.call_with('{"text":"OK"}', model='larger-local-model')
        self.assertEqual('larger-local-model', json.loads(request.data)['model'])
        self.assertEqual('larger-local-model', result['model'])

    def test_environment_model_can_be_overridden(self):
        with patch.dict('os.environ', {'CHESSLAB_MODEL': 'environment-model'}):
            _, request = self.call_with('{"text":"OK"}')
            self.assertEqual('environment-model', json.loads(request.data)['model'])
            _, request = self.call_with('{"text":"OK"}', model='explicit-model')
            self.assertEqual('explicit-model', json.loads(request.data)['model'])

    def test_rejects_unfinished_response(self):
        with self.assertRaises(ValueError):
            self.call_with('{"text":"A partial thought"}', done=False)

    def test_rejects_invalid_shapes(self):
        for content in ('{"text":42}', '{"text":""}', '{"text":"ok","move":"e2e4"}', 'not json'):
            with self.subTest(content=content), self.assertRaises(ValueError):
                self.call_with(content)

    def test_rejects_unknown_teaching_mode_without_network(self):
        with patch('local_llm.urllib.request.build_opener') as transport:
            with self.assertRaises(ValueError):
                respond([], mode='unsupported')
            transport.assert_not_called()

    def test_repeated_model_answer_uses_grounded_fallback(self):
        repeated = 'Look for checks, captures and threats.'
        response = {'done': True, 'done_reason': 'stop', 'message': {'content': json.dumps({'text': repeated})}}
        transport = MagicMock()
        transport.open.return_value = io.BytesIO(json.dumps(response).encode())
        packet = {'facts': ['The revealed candidate is Nf3.'], 'language': 'de',
                  'history': [{'role': 'assistant', 'text': repeated}],
                  'fallback_reply': 'Mein Vorschlag ist Sf3: Springer von g1 nach f3.'}
        with patch('local_llm.urllib.request.build_opener', return_value=transport):
            answer = respond(packet, 'reply', 'warum?')
        self.assertEqual(packet['fallback_reply'], answer['text'])
        self.assertEqual('guided', answer['source'])
        payload = json.loads(transport.open.call_args.args[0].data)
        self.assertIn('German (informal du)', payload['messages'][0]['content'])
