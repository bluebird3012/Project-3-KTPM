"""Offline checks for the unified reporting layout; no live Moodle connection."""
import contextlib
import csv
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import main as cli
from core.reporter import create_run_directory


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


class ReportingChecks(unittest.TestCase):
    def test_all_groups_aggregate_real_runner_with_mocked_execution(self):
        def execute(browser, base_url, case, run_id, timeout):
            if case.case_id == 'TC-001-001':
                raise AssertionError('mock assertion failure')
            if case.case_id == 'TC-001-030':
                raise RuntimeError('mock execution error')
            return 'mock result'

        groups = {g: (p, loader, execute, prefix)
                  for g, (p, loader, _, prefix) in cli.GROUPS.items()}
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {}, clear=True), \
                patch.object(cli, 'load_local_env'), patch.object(cli, 'GROUPS', groups), \
                patch('core.runner.build_browser', return_value=Mock()), \
                contextlib.redirect_stdout(io.StringIO()):
            # run_suite binds its default session preparer at definition time.
            original = cli.run_suite
            def run(*args, **kwargs):
                kwargs['prepare_session'] = Mock()
                return original(*args, **kwargs)
            with patch.object(cli, 'run_suite', side_effect=run):
                self.assertEqual(cli.main(['--results-dir', temp, '--run-id', 'offline']), 1)
            folders = list(Path(temp).iterdir())
            self.assertEqual(len(folders), 1)
            folder = folders[0]
            summary = rows(folder / 'summary.csv')
            self.assertEqual(len(summary), 12)
            self.assertEqual(summary[-1], {'group':'TOTAL', 'total':'160', 'PASS':'151', 'FAIL':'1', 'ERROR':'1', 'SKIP':'7', 'not_recorded':'0'})
            results = rows(folder / 'all_results.csv')
            self.assertEqual(len(results), 160)
            self.assertEqual(len({r['test_case_id'] for r in results}), 160)
            for group in groups:
                per_group = rows(folder / group / 'results.csv')
                self.assertEqual(per_group, [{k:v for k,v in r.items() if k != 'group'} for r in results if r['group']==group])
                self.assertTrue((folder / group / 'cleanup_candidates.csv').is_file())
            self.assertTrue((folder / 'F01_CORE/tracebacks/TC-001-001.txt').is_file())
            self.assertTrue(json.loads((folder / 'run_info.json').read_text())['complete'])

    def test_interruption_does_not_mark_unrecorded_as_skip(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(cli, 'load_local_env'), \
                patch('core.runner.build_browser', side_effect=RuntimeError('mock startup error')), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'mock startup error'):
                cli.main(['--results-dir', temp, '--case','TC-001-001','--case','TC-001-030'])
            folder = next(Path(temp).iterdir())
            self.assertEqual(rows(folder / 'summary.csv')[-1]['not_recorded'], '2')
            self.assertEqual(rows(folder / 'summary.csv')[-1]['SKIP'], '0')
            self.assertFalse(json.loads((folder / 'run_info.json').read_text())['complete'])

    def test_dry_run_creates_no_output(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['--results-dir', temp, '--dry-run']), 0)
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_repeated_run_id_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            first = create_run_directory(Path(temp), 'same')
            second = create_run_directory(Path(temp), 'same')
            self.assertNotEqual(first, second)


if __name__ == '__main__':
    unittest.main()
