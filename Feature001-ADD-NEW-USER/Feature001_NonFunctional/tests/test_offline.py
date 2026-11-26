import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from bs4 import BeautifulSoup
from core.config import local_url
from core.moodle_client import form_values, override, checked_url, prepare, sesskey, success, denial
from core.audit import exact_user
from core.reporter import new_name, append_json, read_jsonl
from performance.run_performance import metrics
from security.test_security import execute


def response(html, code=200, url='http://127.0.0.1:9502/user/editadvanced.php?id=-1'):
    r=MagicMock(); r.text=html; r.url=url; r.status_code=code; return r

FORM='''<form action="/user/editadvanced.php?id=-1"><input name="username"><input name="firstname">
<input name="sesskey" value="realkey"><input name="_qf__user_editadvanced_form" value="1">
<input name="id" value="-1"><input name="createpassword" type="checkbox" checked>
<select name="auth"><option value="manual">Manual</option></select><textarea name="description_editor[text]"></textarea>
<input type="submit" name="submitbutton" value="Create user"></form>'''
PREFIX='nfr0123456789ab_'; NAME=PREFIX+'0123456789abcdef'

class TestParsing(unittest.TestCase):
    def test_local_only(self):
        self.assertEqual(local_url('http://127.0.0.1:9502/'),'http://127.0.0.1:9502')
        for s in ['https://example.org','http://localhost@example.org','http://127.0.0.1:9502/?a=b']:
            with self.assertRaises(ValueError): local_url(s)
    def test_same_origin(self):
        with self.assertRaises(ValueError): checked_url('http://localhost','https://example.com/a')
    def test_successful_controls(self):
        f=BeautifulSoup('''<form><input name="x" value="1"><input name="x" value="2"><input disabled name="d">
        <input type="checkbox" name="off"><input type="checkbox" checked name="on" value="1">
        <select name="s"><option value="a">A</option><option selected value="b">B</option></select>
        <textarea name="t">hello</textarea><input type="file" name="file"><button name="b">b</button></form>''','html.parser').form
        self.assertEqual(form_values(f),[('x','1'),('x','2'),('on','1'),('s','b'),('t','hello')])
    def test_override(self): self.assertEqual(override([('k','a'),('k','b'),('x','z')],k='c',x=None),[('k','c')])
    def test_prepare(self):
        c=MagicMock(); c.get.return_value=response(FORM)
        url,data=prepare(c,'http://127.0.0.1:9502',NAME); d=dict(data)
        self.assertEqual(d['username'],NAME); self.assertEqual(d['email'],NAME+'@example.invalid')
        self.assertEqual(d['sesskey'],'realkey'); self.assertEqual(d['_qf__user_editadvanced_form'],'1')
        self.assertNotIn('createpassword',d); self.assertEqual(d['submitbutton'],'Create user')
    def test_missing_form(self):
        c=MagicMock(); c.get.return_value=response('login')
        with self.assertRaises(RuntimeError): prepare(c,'http://127.0.0.1:9502',NAME)
    def test_sesskey(self): self.assertEqual(sesskey(response('<script>M.cfg={"sesskey":"abc"};</script>')),'abc')
    def test_success(self):
        self.assertTrue(success(response('<div class="alert-success" role="alert">Changes saved<button>Dismiss</button></div>')))
        self.assertFalse(success(response('<div>Changes saved</div>')))
    def test_denial(self): self.assertTrue(denial(response('<input name="logintoken">')))
    def test_unique_names_and_manifest(self):
        self.assertNotEqual(new_name(PREFIX),new_name(PREFIX))
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'manifest.jsonl'; append_json(f,{'event':'attempt','username':NAME}); self.assertEqual(read_jsonl(f)[0]['username'],NAME)

class TestMetrics(unittest.TestCase):
    def setUp(self):
        self.events=[{'event':'attempt','username':NAME},{'event':'result','username':NAME,'http_ok':True,'response_ms':1800}]
        self.observed={NAME:[{'id':42,'email':NAME+'@example.invalid'}]}
    def test_exact(self): self.assertTrue(exact_user(self.observed,NAME)); self.assertFalse(exact_user({},NAME))
    def test_pass(self): self.assertEqual(metrics(self.events,1,60,1,60,0,self.observed)['verdict'],'PASS')
    def test_missing_db_fail(self): self.assertEqual(metrics(self.events,1,60,1,60,0,{})['verdict'],'FAIL')
    def test_slow_fail(self):
        self.events[1]['response_ms']=5001; self.assertEqual(metrics(self.events,1,60,1,60,0,self.observed)['verdict'],'FAIL')
    def test_duplicate_fail(self):
        self.observed[NAME]*=2; self.assertEqual(metrics(self.events,1,60,1,60,0,self.observed)['verdict'],'FAIL')
    def test_unfinished_inconclusive(self): self.assertEqual(metrics(self.events[:1],1,60,1,60,0,self.observed)['verdict'],'INCONCLUSIVE')
    def test_audit_failure_inconclusive(self): self.assertEqual(metrics(self.events,1,60,1,60,0,{},'audit failed')['verdict'],'INCONCLUSIVE')
    def test_setup_error(self):
        self.events.append({'event':'setup_error'}); self.assertEqual(metrics(self.events,1,60,1,60,0,self.observed)['error_rate_pct'],50)

class TestSecurity(unittest.TestCase):
    def test_anonymous_get_denied(self):
        c=MagicMock(); c.get.return_value=response('<input name="logintoken">')
        with patch('security.test_security.session',return_value=c):
            row=execute({'case_id':'SEC-01'},'http://127.0.0.1:9502','admin','test',PREFIX,Path('/unused'))
        self.assertEqual(row['verdict'],'PASS')
    def test_form_exposed_fails(self):
        c=MagicMock(); c.get.return_value=response(FORM)
        with patch('security.test_security.session',return_value=c):
            row=execute({'case_id':'SEC-01'},'http://127.0.0.1:9502','admin','test',PREFIX,Path('/unused'))
        self.assertEqual(row['verdict'],'FAIL')
    def test_missing_csrf_audit(self):
        c=MagicMock(); c.post.return_value=response('<div class="alert-danger">Invalid session key</div>')
        with tempfile.TemporaryDirectory() as d, patch('security.test_security.session',return_value=c), patch('security.test_security.login'), patch('security.test_security.prepare',return_value=('http://127.0.0.1:9502/user/editadvanced.php',[('sesskey','real')])), patch('security.test_security.audit',side_effect=[{},{}]):
            row=execute({'case_id':'SEC-06'},'http://127.0.0.1:9502','admin','test',PREFIX,Path(d)/'attempts.jsonl')
            self.assertEqual(row['verdict'],'PASS'); self.assertNotIn('sesskey',dict(c.post.call_args.kwargs['data']))
    def test_unauthorized_record_fails(self):
        c=MagicMock(); c.post.return_value=response('<div class="alert-danger">Denied</div>')
        with tempfile.TemporaryDirectory() as d, patch('security.test_security.session',return_value=c), patch('security.test_security.login'), patch('security.test_security.prepare',return_value=('http://127.0.0.1:9502/user/editadvanced.php',[('sesskey','real')])), patch('security.test_security.new_name',return_value=NAME), patch('security.test_security.audit',side_effect=[{},{NAME:[{'id':1,'email':NAME+'@example.invalid'}]}]):
            row=execute({'case_id':'SEC-06'},'http://127.0.0.1:9502','admin','test',PREFIX,Path(d)/'attempts.jsonl')
        self.assertEqual(row['verdict'],'FAIL')

if __name__=='__main__': unittest.main()
