import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from game import find_stockfish
from profile_lock import acquire_profile_lock


class PortabilityTests(unittest.TestCase):
    def test_windows_discovers_nested_executable_not_mac_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / 'engine' / 'stockfish'
            folder.mkdir(parents=True)
            (folder / 'stockfish-macos-universal').touch()
            executable = folder / 'stockfish-windows-x86-64-universal.exe'
            executable.touch()
            with patch.dict(os.environ, {'STOCKFISH_PATH': ''}), patch('game.shutil.which', return_value=None):
                self.assertEqual(str(executable), find_stockfish(root=root, windows=True))

    def test_explicit_engine_path_wins(self):
        self.assertEqual('custom engine.exe', find_stockfish('custom engine.exe'))

    def test_profile_lock_blocks_another_process_and_releases(self):
        code = '''
import sys
from profile_lock import acquire_profile_lock, ProfileInUse
try:
    handle = acquire_profile_lock(sys.argv[1])
except ProfileInUse:
    print('blocked')
else:
    handle.close()
    print('acquired')
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'profile.lock'
            lock = acquire_profile_lock(path)
            def attempt():
                return subprocess.run([sys.executable, '-c', code, str(path)],
                                      cwd=Path(__file__).resolve().parents[1],
                                      capture_output=True, text=True, check=True, timeout=10).stdout.strip()
            try:
                self.assertEqual('blocked', attempt())
            finally:
                lock.close()
            self.assertEqual('acquired', attempt())
