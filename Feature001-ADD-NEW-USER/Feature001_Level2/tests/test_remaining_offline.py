"""Offline verification of all added datasets and representative workflow behavior."""
import contextlib
import io
import json
import os
import sys
import unittest
import tempfile
from collections import Counter
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main as cli
from core.data_loader import resolve_data
from fixtures.make_size_fixtures import padded_png
from test_groups import remaining as R


class RemainingOfflineChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.groups = {g: loader(p) for g, (p, loader, _, _) in cli.GROUPS.items()}
        cls.cases = {int(c.case_id[-3:]): c for cases in cls.groups.values() for c in cases}

    def test_exact_coverage(self):
        self.assertEqual(set(self.cases), set(range(1, 161)))
        self.assertEqual(sum(map(len, self.groups.values())), 160)
        self.assertEqual([len(v) for v in self.groups.values()], [48, 64, 6, 10, 4, 16, 7, 1, 2, 1, 1])
        self.assertEqual(Counter(c['technique'] for c in self.cases.values()), {'BVA':103,'ECP':42,'DT':8,'UC':7})

    def test_rich_boundary_html(self):
        self.assertEqual([len(self.cases[n]['description_html']) for n in (91,92,93,94)], [8,49999,50000,50001])
        self.assertEqual(self.cases[136]['source_editor_value'], 'Kiểm thử MoodleDòng mới')
        self.assertIn('<strong>Kiểm thử Moodle</strong><br>',self.cases[136]['description_html'])
        self.assertEqual(self.cases[94]['expected_target'], 'description_error')

    def test_image_fixtures_and_limit(self):
        for filename, signature in [('f1_avatar.png', b'\x89PNG'),('f1_avatar_second.png',b'\x89PNG'),('f1_avatar.jpg',b'\xff\xd8'),('f1_note.txt',b'Synthetic'),('f1_broken.png',b'Synthetic')]:
            self.assertTrue(R.image_path(filename).read_bytes().startswith(signature))
        source = R.image_path('f1_avatar.png').read_bytes()
        for n in (4095,4096,4097):
            self.assertEqual(len(padded_png(source,n)), n)
        with patch.dict(os.environ, {'MOODLE_IMAGE_MAX_BYTES':'4096'}):
            self.assertEqual([R.boundary_size(self.cases[n]) for n in (98,99,100)], [4095,4096,4097])
        for n in (100,138,139):
            self.assertEqual(self.cases[n]['source_has_submit'], 'no')

    def test_default_preconditions(self):
        with patch.dict(os.environ, {}, clear=True):
            blocked = {n for n in range(90,161) if n in self.cases and any(self.cases[n] in cs for g,cs in self.groups.items() if g not in ('F01_CORE','F02_TEXT')) and R.preflight(self.cases[n])}
        self.assertEqual(blocked, {98,99,100,159})

    def test_tags_and_flags_source_values(self):
        self.assertEqual(json.loads(self.cases[141]['tags_json']), ['testing','testing'])
        self.assertEqual(self.cases[141]['expected_tag_count'], '1')
        self.assertEqual(self.cases[124]['final_authentication'], 'nologin')
        self.assertEqual(self.cases[125]['password_entry'], 'omit')
        self.assertEqual(json.loads(self.cases[153]['flags_json']), ['suspended','generate_password'])
        self.assertEqual(self.cases[153]['expected_target'],'suspended_error')
        self.assertEqual(self.cases[134]['select_value'],'Asia/Ho_Chi_Minh')

    def test_multi_step_data(self):
        for n in (108,158):
            c=self.cases[n]
            self.assertEqual(resolve_data(c['username'],'abc'),f'username{n}_abc')
            self.assertNotEqual(c['email'],c['second_email'])
        self.assertEqual(self.cases[158]['recovery_username'],'username158')
        self.assertEqual(self.cases[160]['intermediate_target'],'suspended_error')

    def test_image_workflows_mock(self):
        for n in (95,96,97,137,138,139,140):
            c=self.cases[n]; page=Mock(); extra=Mock(); picker=Mock(spec=R.PicturePicker); picker.upload.return_value='uploaded/rejected'; picker.assert_no_real_thumbnail.return_value='generic icon'
            with self.subTest(case=n), patch.object(R,'begin',return_value=(page,extra)), patch.object(R,'PicturePicker',return_value=picker), patch.object(R,'assert_outcome',return_value='verified'):
                R.run_image(Mock(),'http://localhost',c,'abc',15)
                self.assertEqual(page.submit.call_count,int(c['source_has_submit']=='yes'))
                self.assertEqual(picker.upload.call_count, int(bool(c['file_name']))+int(bool(c['second_file_name'])))
                picker.check_count.assert_called_once_with(int(c['expected_file_count']))
                if n==138: self.assertTrue(picker.upload.call_args.kwargs['expect_rejection'])

    def test_rich_tags_flags_select_cancel_mock(self):
        for group,method in [('F03_RICH',R.run_rich),('F05_TAG',R.run_tags),('F06_FLAGS',R.run_flags),('F07_SELECT',R.run_select),('F09_CANCEL',R.run_cancel)]:
            for c in self.groups[group]:
                page,extra=Mock(),Mock()
                with self.subTest(case=c.case_id), patch.object(R,'begin',return_value=(page,extra)), patch.object(R,'assert_outcome',return_value='verified') as assertion:
                    self.assertEqual(method(Mock(),'http://localhost',c,'abc',15),'verified')
                    self.assertEqual(page.submit.call_count,int(c['source_has_submit']=='yes'))
                    if group=='F09_CANCEL':
                        extra.cancel.assert_called_once()
                        self.assertEqual(assertion.call_count,2 if c['intermediate_target'] else 1)

    def test_duplicate_sequence_mock(self):
        c=self.cases[108]; page=Mock()
        with patch.object(R,'begin',return_value=(page,Mock())) as begin, patch.object(R,'assert_outcome',return_value='verified') as assertion:
            self.assertEqual(R.run_duplicate(Mock(),'http://localhost',c,'abc',15),'verified')
            self.assertEqual(page.submit.call_count,2)
            first,second=[x.args[2] for x in begin.call_args_list]
            self.assertEqual(first['username'],second['username'])
            self.assertNotEqual(first['email'],second['email'])
            self.assertEqual(assertion.call_args_list[0].args[1]['expected_kind'],'success')

    def test_deny_dispatch_uses_restricted_login(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'MOODLE_RESTRICTED_USERNAME':'student_test','MOODLE_RESTRICTED_PASSWORD':'local_test'},clear=True),patch.object(cli,'run_suite',return_value=0) as suite,contextlib.redirect_stdout(io.StringIO()):
            cli.main(['--results-dir', temp, '--case','TC-001-159'])
            self.assertIs(suite.call_args.kwargs['prepare_session'],R.prepare_restricted_session)
            self.assertEqual(suite.call_args.args[0][0][1],'')
        with patch.dict(os.environ, {'MOODLE_RESTRICTED_USERNAME':'admin','MOODLE_RESTRICTED_PASSWORD':'local_test'},clear=True):
            self.assertTrue(R.preflight(self.cases[159]))

if __name__=='__main__':
    unittest.main()
