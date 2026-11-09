"""Access-control regression checks in disposable Python 3.11 processes.

The native C++ audit hook is covered by the client build; these tests exercise
the SDK fallback audit hook with a mocked native interface and no account.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SDK = Path(__file__).resolve().parents[1] / 'netgram/plugins/python'
WORKER = r'''
import json, sys, types
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
native = types.ModuleType('_extera')
native.log = lambda *a: None
native.settings_changed = lambda *a: None
native.get_selected_account = lambda: 0
sys.modules['_extera'] = native
import extera_host as host
root = sys.argv[2]
def call(method, **args):
    value = json.loads(host.dispatch(method, json.dumps(args)))
    assert value['ok'], value
    return value.get('result')
call('init', plugins=root+'/plugins', settings=root+'/settings', safe_mode=False,
     unknown_sources=True, sandbox_prompts=False)
value = call('install', path=root+'/input.plugin')
print(json.dumps(value))
'''


@unittest.skipUnless(sys.version_info[:2] == (3, 11), 'embedded runtime is Python 3.11')
class SandboxTests(unittest.TestCase):
    def check_blocked(self, operation):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            marker = root/'outside.txt'
            source = ('__id__="sandbox_test"\n__name__="Sandbox test"\n__version__="1.0"\n'
                'from base_plugin import BasePlugin\n'
                'class Test(BasePlugin):\n    def on_plugin_load(self):\n'
                + ''.join('        '+line+'\n' for line in operation(str(marker)).splitlines()))
            (root/'input.plugin').write_text(source, encoding='utf-8')
            worker = root/'worker.py'
            worker.write_text(WORKER, encoding='utf-8')
            result = subprocess.run([sys.executable, str(worker), str(SDK), folder],
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr+result.stdout)
            self.assertIn('PermissionError', result.stdout)
            self.assertFalse(marker.exists())

    def test_cannot_write_outside_plugin_directory_without_permission(self):
        self.check_blocked(lambda marker: f'open({marker!r}, "w").write("blocked")')

    def test_cannot_connect_to_local_network_without_permission(self):
        self.check_blocked(lambda marker: 'import socket\nsocket.socket().connect(("127.0.0.1", 9))')


if __name__ == '__main__':
    unittest.main()
