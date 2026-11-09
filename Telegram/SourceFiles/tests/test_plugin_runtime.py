"""Exercise the plugin host with temporary plugins and a fake native boundary."""
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
import zipfile

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
        # These tests mock the native boundary. The production C++ audit hook
        # and the separate sandbox tests exercise access control instead.
        self.call('init', plugins=str(self.root/'plugins'), settings=str(self.root/'settings'),
                  safe_mode=False, unknown_sources=True, sandbox_off=True)
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

    def test_java_collections_and_android_send_hook(self):
        from hook_utils import find_class
        collection = find_class('java.util.ArrayList')()
        collection.add('one')
        collection.add('two')
        self.assertEqual(collection.size(), 2)
        self.assertEqual(collection.get(1), 'two')
        plugin = '''
__id__ = "test_virtual"
__name__ = "Android hook test"
__version__ = "1.0"
from base_plugin import BasePlugin
from hook_utils import find_class
class Virtual(BasePlugin):
    def on_plugin_load(self):
        self.hook_all_methods(find_class("org.telegram.messenger.SendMessagesHelper"),
                              "sendMessage", before=self.modify)
    def modify(self, param):
        param.args[0].message = "android:" + param.args[0].message
'''
        self.path.write_text(plugin, encoding='utf-8')
        self.call('install', path=str(self.path))
        self.assertEqual(self.call('send_hook', peer=123, text='hello')['text'], 'android:hello')
        self.call('set_enabled', id='test_virtual', enabled=False)
        self.assertEqual(self.call('send_hook', peer=123, text='hello')['strategy'], 'default')

    def test_elyx_metadata_and_archive_path_traversal(self):
        import exd_elyx
        path = self.root/'test.elyx'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('refmap.json', json.dumps({'main': 'main.py', 'metainfo': 'meta.json'}))
            archive.writestr('meta.json', json.dumps({'id': 'test_elyx', 'name': 'Elyx test', 'version': '1.0'}))
            archive.writestr('main.py', PLUGIN)
            archive.writestr('../escape.txt', 'must stay inside')
        self.assertEqual(exd_elyx.read_meta(str(path))['id'], 'test_elyx')
        with self.assertRaises(exd_elyx.ElyxError):
            exd_elyx.extract(str(path), 'test_elyx')
        self.assertFalse((Path(exd_elyx.plugins_root())/'escape.txt').exists())
        self.assertFalse((self.root/'escape.txt').exists())

    def test_guard_detects_code_that_tries_to_disable_protection(self):
        import plugin_guard
        self.path.write_text(PLUGIN + '\nimport ctypes\nctypes.CDLL("payload.dll")\n', encoding='utf-8')
        report = plugin_guard.scan(str(self.path))
        self.assertTrue(report['findings'])
        self.assertTrue(any('NATIVE' in entry['rule'] or 'CTYPES' in entry['rule']
                            for entry in report['findings']))

if __name__ == '__main__':
    unittest.main()
