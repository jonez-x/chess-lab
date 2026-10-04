import threading
import unittest

import test_game


class CoachChatTests(unittest.TestCase):
    setUp = test_game.GameTests.setUp
    tearDown = test_game.GameTests.tearDown
    cmd = test_game.GameTests.cmd
    wait_idle = test_game.GameTests.wait_idle

    def hint(self):
        self.cmd('hint')
        self.wait_idle()

    def test_answer_is_saved_without_changing_position_or_revealing_candidate(self):
        seen = []
        def client(facts, *args, **kwargs):
            seen.extend(facts['facts'])
            return {'text': 'Which of your pieces needs protection?'}
        self.app.coach_client = client
        self.hint()
        before = self.app.snapshot()['game']['fen']
        self.cmd('coach_chat', text='Can you guide me?')
        self.app.coach_future.result(2)
        snap = self.app.snapshot()['game']
        self.assertEqual(before, snap['fen'])
        self.assertEqual('assistant', snap['coach']['dialogue'][-1]['role'])
        self.assertFalse(snap['coach']['llm_pending'])
        self.assertEqual([], snap['coach']['arrows'])
        raw = self.app.state['game']['coach']
        self.assertNotIn(raw['move'], '\n'.join(seen))
        self.assertNotIn(raw['before_fen'], '\n'.join(seen))
        self.assertEqual(2, len(self.app.store.load()['game']['coach']['dialogue']))

    def test_failure_preserves_standard_hint(self):
        def fail(*args, **kwargs):
            raise OSError('offline')
        self.app.coach_client = fail
        self.hint()
        before = self.app.snapshot()['game']['coach']['text']
        self.cmd('coach_chat')
        self.app.coach_future.result(2)
        c = self.app.snapshot()['game']['coach']
        self.assertEqual(before, c['text'])
        self.assertTrue(c['llm_error'])
        self.assertFalse(c['llm_pending'])

    def test_stage_change_discards_late_answer(self):
        started, release = threading.Event(), threading.Event()
        def slow(*args, **kwargs):
            started.set()
            release.wait(2)
            return {'text': 'Old answer'}
        self.app.coach_client = slow
        self.hint()
        try:
            self.cmd('coach_chat')
            self.assertTrue(started.wait(1))
            self.cmd('next')
        finally:
            release.set()
        self.app.coach_future.result(2)
        c = self.app.snapshot()['game']['coach']
        self.assertEqual(1, c['stage'])
        self.assertEqual([], c['dialogue'])
        self.assertFalse(c['llm_pending'])

    def test_skip_discards_late_answer_and_duplicate_requests_are_bounded(self):
        started, release = threading.Event(), threading.Event()
        def slow(*args, **kwargs):
            started.set()
            release.wait(2)
            return {'text': 'Old answer'}
        self.app.coach_client = slow
        self.hint()
        try:
            self.cmd('coach_chat')
            self.assertTrue(started.wait(1))
            with self.assertRaises(ValueError):
                self.cmd('coach_chat')
            self.cmd('skip')
        finally:
            release.set()
        self.app.coach_future.result(2)
        self.assertIsNone(self.app.snapshot()['game']['coach'])
