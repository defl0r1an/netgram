"""Exercise batch generation without running any dependency build."""
import ast
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TREE = ast.parse((ROOT / 'build/prepare/prepare.py').read_text(encoding='utf-8'))
FUNCTION = next(n for n in TREE.body
    if isinstance(n, ast.FunctionDef) and n.name == 'winFailOnEach')
SCOPE = {'re': re}
exec(compile(ast.Module(body=[FUNCTION], type_ignores=[]), '<batch helper>', 'exec'), SCOPE)
generate = SCOPE['winFailOnEach']


class WindowsBatchTests(unittest.TestCase):
    def test_control_blocks_are_preserved(self):
        result = generate('for %%i in (one two) do (\nver >nul\n'
            'if errorlevel 1 (\necho failed\nexit /b 1\n)\n)\necho reached')
        self.assertNotIn('call )', result)
        self.assertNotIn('%errorlevel%', result)
        self.assertIn('\r\nver >nul\r\n', result)
        self.assertIn('call echo reached', result)

    @unittest.skipUnless(sys.platform == 'win32', 'Windows command processor')
    def test_success_and_failure_inside_loop(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'smoke.cmd'
            for command, status, marker in [
                ('ver >nul', 0, 'REACHED_END'), ('verify invalid', 1, '')
            ]:
                source = ('for %%i in (one two) do (\n' + command
                    + '\nif errorlevel 1 (\necho failed\nexit /b 1\n)\n)\necho REACHED_END')
                path.write_bytes(('@echo off\r\n' + generate(source)).encode())
                result = subprocess.run(['cmd', '/c', str(path)], capture_output=True, text=True)
                self.assertEqual(result.returncode, status)
                self.assertEqual('REACHED_END' in result.stdout, bool(marker))


if __name__ == '__main__':
    unittest.main()
