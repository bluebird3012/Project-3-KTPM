"""Offline F02 coverage and dispatch checks (no browser or Moodle required)."""
import contextlib
import io
import json
from collections import Counter
from pathlib import Path
import sys
import unittest
import tempfile
from unittest.mock import Mock, call, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main as cli
from core.data_loader import read_cases
from pages.locators import TEXT_FIELD_IDS, resolve_target
from test_groups import test_text_fields as text_group


class TextOfflineChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = text_group.read_text_cases(cli.GROUPS['F02_TEXT'][0])
        cls.by_id = {c.case_id: c for c in cls.cases}

    def test_exact_source_ids_and_techniques(self):
        self.assertEqual(set(self.by_id), {f'TC-001-{n:03}' for n in [*range(30, 90), *range(142, 146)]})
        self.assertEqual(Counter(c['technique'] for c in self.cases), {'BVA': 60, 'ECP': 4})

    def test_unique_usernames_across_groups(self):
        f01 = read_cases(cli.DATA_FILE)
        self.assertEqual(len({c['username'] for c in self.cases}), 64)
        self.assertFalse({c['username'] for c in f01} & {c['username'] for c in self.cases})

    def test_targets_and_oracles(self):
        self.assertEqual({c['text_field'] for c in self.cases}, set(TEXT_FIELD_IDS))
        self.assertEqual(Counter(c['expected_kind'] for c in self.cases), {'success': 63, 'system_error': 1})
        self.assertEqual(sum(len(json.loads(c['pre_submit_checks_json'])) for c in self.cases), 12)
        for c in self.cases:
            self.assertTrue(resolve_target(c['expected_target']))
            for check in json.loads(c['pre_submit_checks_json']):
                self.assertEqual(resolve_target(check['target']), 'id=' + TEXT_FIELD_IDS[c['text_field']])

    def test_source_anomalies_preserved(self):
        for n, input_len, expected_len in [(34,121,121),(39,197,197),(44,101,101),(49,101,100),(64,256,255),(84,21,20)]:
            c = self.by_id[f'TC-001-{n:03}']
            self.assertEqual(len(c['text_value']), input_len)
            self.assertEqual(len(json.loads(c['pre_submit_checks_json'])[0]['expected']), expected_len)
        self.assertEqual(self.by_id['TC-001-034']['expected_text'], 'Error writing to database')
        self.assertEqual(self.by_id['TC-001-145']['text_value'], 'Thành phố Hồ Chí Minh')

    def test_all_cases_use_shared_workflow(self):
        browser = Mock()
        for c in self.cases:
            with self.subTest(case=c.case_id), \
                 patch.object(text_group, 'AddUserPage') as page_cls, \
                 patch.object(text_group, 'verify_pre_submit') as pre, \
                 patch.object(text_group, 'verify_expected', return_value='mock result') as final:
                sequence = Mock()
                page = page_cls.return_value
                sequence.attach_mock(page, 'page')
                sequence.attach_mock(pre, 'pre')
                sequence.attach_mock(final, 'final')
                self.assertEqual(text_group.run_case(browser, 'http://localhost', c, 'abc', 15), 'mock result')
                self.assertEqual(sequence.mock_calls, [
                    call.page.open(c), call.page.fill_core_fields(c, 'abc'),
                    call.page.fill_additional_text(c['text_field'], c['text_value'], c['section']),
                    call.pre(browser, json.loads(c['pre_submit_checks_json'])),
                    call.page.submit(), call.final(browser, c, 15),
                ])

    def test_cli_dispatch(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(cli, 'run_suite', return_value=0) as suite, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['--results-dir', temp, '--case','TC-001-001','--case','TC-001-145']), 0)
            self.assertEqual(suite.call_count, 2)
            for invocation, cid, prefix in zip(suite.call_args_list, ['TC-001-001','TC-001-145'], ['f01','f02']):
                self.assertEqual(invocation.args[0][0][0].case_id, cid)
                self.assertEqual(invocation.args[-1], prefix)

    def test_dry_run_does_not_launch_browser(self):
        output = io.StringIO()
        with patch.object(cli, 'run_suite') as suite, contextlib.redirect_stdout(output):
            self.assertEqual(cli.main(['--dry-run']), 0)
            suite.assert_not_called()
        self.assertIn('F01_CORE: 48 CSV cases, runnable=45, blocked=3', output.getvalue())
        self.assertIn('F02_TEXT: 64 CSV cases, runnable=64, blocked=0', output.getvalue())


if __name__ == '__main__':
    unittest.main()
