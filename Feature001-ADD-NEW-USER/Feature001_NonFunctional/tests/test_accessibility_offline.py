import base64
import hashlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from accessibility.axe_asset import VERSION, verify_archive, extract_asset, load_asset, sha256
from accessibility.evaluation import evaluate_scan, evaluate_keyboard, evaluate_validation, overall
from accessibility.run_accessibility import redact, same_origin


def rule(id='label', impact='critical', tags=None):
    return {'id':id, 'impact':impact, 'tags':tags or ['wcag2a'], 'nodes': [{'impact':impact, 'target':['#example']}]}


def result(violations=None, incomplete=None):
    return {'violations': violations or [], 'incomplete': incomplete or [], 'passes':[rule('html-has-lang','serious')], 'inapplicable':[]}


class EvaluationTests(unittest.TestCase):
    def test_clean_pass(self):
        self.assertEqual(evaluate_scan(result())['status'], 'PASS')

    def test_critical(self):
        self.assertEqual(evaluate_scan(result([rule()]))['status'], 'FAIL')

    def test_moderate_label_blocks(self):
        self.assertEqual(evaluate_scan(result([rule(impact='moderate')]))['status'], 'FAIL')

    def test_contrast_blocks(self):
        self.assertEqual(evaluate_scan(result([rule('color-contrast','moderate')]))['status'], 'FAIL')

    def test_best_practice_informational(self):
        e = evaluate_scan(result([rule('heading-order','serious',['best-practice'])]))
        self.assertEqual(e['status'], 'PASS')
        self.assertEqual(e['node_counts']['violations_best_practice'], 1)

    def test_incomplete_not_pass(self):
        self.assertEqual(evaluate_scan(result(incomplete=[rule()]))['status'], 'INCONCLUSIVE')

    def test_frame_warning_not_pass(self):
        self.assertEqual(evaluate_scan(result(), ['frame warning'])['status'], 'INCONCLUSIVE')

    def test_fail_precedence(self):
        self.assertEqual(evaluate_scan(result([rule()], [rule()]), ['warning'])['status'], 'FAIL')

    def test_malformed_result(self):
        with self.assertRaises(ValueError):
            evaluate_scan({'violations': []})

    def test_no_applicable_rule(self):
        with self.assertRaises(ValueError):
            evaluate_scan({k: [] for k in ('violations','incomplete','passes','inapplicable')})

    def test_keyboard(self):
        self.assertEqual(evaluate_keyboard(['a','b'], ['a','b'], 4, 10)['status'],'PASS')
        self.assertEqual(evaluate_keyboard(['a','b'], ['a'], 10, 10)['status'],'FAIL')
        self.assertEqual(evaluate_keyboard(['a','b'], ['a'], 4, 10, True)['status'],'FAIL')
        self.assertEqual(evaluate_keyboard(['a','b'], ['a'], 4, 10)['status'],'INCONCLUSIVE')

    def test_validation_association(self):
        item = {'field':'email','message':'Required','native':False,'associated':True}
        self.assertEqual(evaluate_validation([item])['status'],'PASS')
        self.assertEqual(evaluate_validation([{**item,'associated':False}])['status'],'FAIL')
        self.assertEqual(evaluate_validation([{**item,'associated':False,'native':True}])['status'],'PASS')
        self.assertEqual(evaluate_validation([{**item,'message':''}])['status'],'INCONCLUSIVE')

    def test_overall(self):
        self.assertEqual(overall(['PASS']*5, 5),'PASS')
        self.assertEqual(overall(['PASS']*4, 5),'INCONCLUSIVE')
        self.assertEqual(overall(['FAIL','INCONCLUSIVE'],5),'FAIL')

    def test_redaction(self):
        self.assertEqual(redact({'x':'secret123; sesskey=abc&foo=bar'}, ['secret123'])['x'], '[REDACTED]; sesskey=[REDACTED]&foo=bar')

    def test_origin(self):
        self.assertTrue(same_origin('http://127.0.0.1:9502/login','http://127.0.0.1:9502'))
        self.assertFalse(same_origin('http://127.0.0.1:9503/login','http://127.0.0.1:9502'))


class AssetTests(unittest.TestCase):
    def test_integrity(self):
        payload = b'fixture'
        integrity = 'sha512-' + base64.b64encode(hashlib.sha512(payload).digest()).decode()
        verify_archive(payload, integrity)
        with self.assertRaises(ValueError):
            verify_archive(b'changed', integrity)

    def test_extract(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode='w:gz') as tar:
            for path, data in [('package/axe.min.js',b'x'*100001), ('package/package.json',json.dumps({'name':'axe-core','version':VERSION}).encode()), ('package/LICENSE',b'license')]:
                member=tarfile.TarInfo(path); member.size=len(data); tar.addfile(member,io.BytesIO(data))
        script, license_data = extract_asset(buf.getvalue())
        self.assertEqual(len(script),100001); self.assertEqual(license_data,b'license')

    def test_cached_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            data = b'x'*100001
            (folder/'axe.min.js').write_bytes(data)
            (folder/'asset.json').write_text(json.dumps({'version':VERSION,'sha256':sha256(data)}))
            self.assertEqual(load_asset(cache=folder)[1],sha256(data))
            (folder/'axe.min.js').write_bytes(b'tampered')
            with self.assertRaises(ValueError): load_asset(cache=folder)


if __name__ == '__main__':
    unittest.main()
