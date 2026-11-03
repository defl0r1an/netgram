"""Exercise the plugin host with temporary plugins and a fake native boundary."""
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest

RUNTIME = Path(__file__).resolve().parents[1] / 'netgram/plugins/python'
sys.dont_write_bytecode = True
sys.path.insert(0, str(RUNTIME))
native = types.ModuleType('_extera')
native.log = lambda *args: None
native.settings_changed = lambda *args: None
native.get_selected_account = lambda: 0
native.self_id = lambda: 123
native.current_peer = lambda: 123
sys.modules['_extera'] = native
import extera_host as host

PLUGIN = '''
__id__ = "test_echo"
__name__ = "Temporary test plugin"
__version__ = "1.0"
from base_plugin import BasePlugin, HookResult, HookStrategy, MenuItemData

class Echo(BasePlugin):
    def on_plugin_load(self):
        self.add_on_send_message_hook()
        self.add_menu_item(MenuItemData("MESSAGE_CONTEXT_MENU", "Test action", lambda context: None))
    def on_send_message_hook(self, account, params):
        if params.message == "cancel":
            return HookResult(HookStrategy.CANCEL)
        params.message = params.message.upper()
        return HookResult(HookStrategy.MODIFY, params=params)
'''

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.call('init', plugins=str(self.root/'plugins'), settings=str(self.root/'settings'),
                  safe_mode=False, unknown_sources=True)
        self.path = self.root/'input.plugin'
        self.path.write_text(PLUGIN, encoding='utf-8')

    def tearDown(self):
        self.call('shutdown')
        host._records.clear()
        host._trusted_cache = None
        self.tmp.cleanup()

    def call(self, method, **args):
        response = json.loads(host.dispatch(method, json.dumps(args)))
        self.assertTrue(response['ok'], response)
        return response.get('result')

    def test_install_modify_cancel_and_disable(self):
        self.call('install', path=str(self.path))
        self.assertEqual(self.call('send_hook', peer=123, text='hello')['text'], 'HELLO')
        self.assertEqual(self.call('send_hook', peer=123, text='cancel')['strategy'], 'cancel')
        self.assertTrue(self.call('menu_list', type='message_context_menu'))
        self.call('set_enabled', id='test_echo', enabled=False)
        self.assertEqual(self.call('send_hook', peer=123, text='hello')['strategy'], 'default')

    def test_safe_mode_prevents_execution_and_reenable(self):
        self.call('safe_mode', enabled=True)
        self.call('install', path=str(self.path))
        self.assertEqual(self.call('send_hook', peer=123, text='hello')['strategy'], 'default')
        self.assertTrue(self.call('set_enabled', id='test_echo', enabled=True)['blocked'])

    def test_metadata_does_not_execute_code_and_rejects_path_traversal(self):
        marker = self.root/'executed.txt'
        self.path.write_text(PLUGIN + f'\nopen({str(marker)!r}, "w").write("bad")\n', encoding='utf-8')
        self.call('metadata', path=str(self.path))
        self.assertFalse(marker.exists())
        self.path.write_text(PLUGIN.replace('"test_echo"', '"../escape"'), encoding='utf-8')
        response = json.loads(host.dispatch('install', json.dumps({'path': str(self.path)})))
        self.assertFalse(response['ok'])
        self.assertFalse((self.root/'escape.plugin').exists())

    def test_unknown_source_block_is_enforced_by_host(self):
        self.call('unknown_sources', enabled=False)
        self.call('install', path=str(self.path))
        self.assertEqual(self.call('send_hook', peer=123, text='hello')['strategy'], 'default')

    def test_bundled_api_schema_serializes_and_reads_peer(self):
        import tl_runtime
        peer = tl_runtime.TLRPC.TL_peerUser(user_id=123456789)
        restored = tl_runtime.deserialize(tl_runtime.serialize(peer))
        self.assertEqual(restored.user_id, 123456789)
        request = tl_runtime.TLRPC.TL_account_updateStatus(offline=True)
        self.assertTrue(tl_runtime.is_request(request))
        self.assertTrue(tl_runtime.serialize(request))

if __name__ == '__main__':
    unittest.main()
