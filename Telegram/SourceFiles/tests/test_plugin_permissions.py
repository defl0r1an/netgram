"""Exercise permission wrappers with a mocked native boundary in disposable processes.
The C++ audit hook and GUI still require the GitHub build/client validation.
"""
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

SDK = Path(__file__).resolve().parents[1] / 'netgram/plugins/python'
WORKER = r'''import sys,types,json,pathlib,_imp,base64
sys.dont_write_bytecode=True
sys.path.insert(0,sys.argv[1])
root=pathlib.Path(sys.argv[2]); mode=sys.argv[3]
for folder in ['plugins','settings','files','deps']:(root/folder).mkdir()
native=types.ModuleType('_extera');hooks={};sent=[];owners=[]
native.log=lambda *a:None
native.sbx_secrets=lambda:json.dumps({'codes':['987654'],'phones':['79991234567'],'keys':['ab'*32]})
native.sbx_state=lambda:(None,True,True)
native.sbx_push=lambda owner:owners.append(owner) or len(owners)
native.sbx_pop=lambda token:owners.pop()
native.sbx_owner=lambda:owners[-1] if owners else ''
native.sbx_ticket=lambda:None
native.sbx_thread_entry=lambda *a:None
native.sbx_install=lambda *a:hooks.update(decide=a[0],query=a[2])
native.sbx_create_dynamic=_imp.create_dynamic
native.sbx_create_builtin=_imp.create_builtin
for name in ['send_message','edit_message','send_request','send_raw_request','send_media']:
 setattr(native,name,lambda *a:sent.append(a))
sys.modules['_extera']=native
sys.modules['tl_runtime']=types.SimpleNamespace(_by_id={0x12345678:types.SimpleNamespace(name='messages.deleteMessages')})
import extera_host as host
import exd_sandbox
exd_sandbox.install(host,str(root/'plugins'),str(root/'settings'),str(root/'files'),str(root/'deps'),interactive=False)
assert not hasattr(native,'sbx_secrets') and not hasattr(native,'sbx_push')
with host._plugin_context('permission_test'):
 assert host.owner_now()=='permission_test'
assert not owners
query=hooks['query']
def run_plugin(code):
 exec(compile(code,str(root/'plugins/permission_test.py'),'exec'),{'native':native,'json':json,'base64':base64})
if mode=='context':
 print('PASS');sys.exit()
rule,code={
 'compact':('msg_send',''),
 'send':('msg_send','native.send_message(1,"hello")'),
 'edit':('msg_edit','native.edit_message(1,2,"changed")'),
 'delete':('msg_delete','native.send_raw_request(base64.b64encode(bytes.fromhex("78563412")).decode())'),
 'upload':('files_read','native.send_media(1,2,str_path)'),
 'leak':(None,'native.send_message(1,"login code 987654")'),
 'allow':(None,'native.send_message(1,"hello")'),
}[mode]
if mode=='compact':code='native.send_request(json.dumps({"_":"messages.sendMessage","message":"hello"},separators=(",",":")))'
if mode=='upload':code='native.send_media(1,2,'+repr(str(root/'plugins/.data/permission_test/file.txt'))+')'
if rule:query('set_rule','permission_test','extra',rule+'=deny',[])
# Historical always-allow rules must not permit login codes after the fix.
if mode=='leak':query('set_rule','permission_test','net','leak:code|Telegram=allow',[])
try:run_plugin(code)
except PermissionError:
 assert mode!='allow'
 assert not sent
else:
 assert mode=='allow',mode
 assert len(sent)==1
print('PASS')
'''

@unittest.skipUnless(sys.version_info[:2] == (3,11), 'embedded runtime is Python 3.11')
class PluginPermissionTests(unittest.TestCase):
    def test_permissions_and_hidden_native_helpers(self):
        for mode in ['context','compact','send','edit','delete','upload','leak','allow']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as folder:
                worker=Path(folder)/'worker.py'
                worker.write_text(WORKER,encoding='utf-8')
                result=subprocess.run([sys.executable,str(worker),str(SDK),folder,mode],capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertIn('PASS',result.stdout)

if __name__ == '__main__':
    unittest.main()
