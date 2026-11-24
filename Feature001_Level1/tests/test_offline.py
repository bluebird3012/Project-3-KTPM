"""Offline checks for configuration and the 48-source-row input dataset."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_core_fields as app


class OfflineChecks(unittest.TestCase):
    def test_all_48_cases_exist(self):
        cases = app.read_cases(app.DATA_FILE)
        self.assertEqual(len(cases), 48)
        self.assertEqual(len({case.case_id for case in cases}), 48)

    def test_missing_env_file_is_allowed(self):
        with tempfile.TemporaryDirectory() as folder:
            app.load_local_env(Path(folder) / 'missing.env')

    def test_env_file_values_loaded(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            path = Path(folder) / '.env'
            path.write_text('MOODLE_ADMIN_USERNAME=admin\nMOODLE_ADMIN_PASSWORD="test_only"\n')
            app.load_local_env(path)
            self.assertEqual(os.environ['MOODLE_ADMIN_USERNAME'], 'admin')
            self.assertEqual(os.environ['MOODLE_ADMIN_PASSWORD'], 'test_only')

    def test_exported_env_overrides_file(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'MOODLE_ADMIN_USERNAME': 'other'}, clear=True):
            path = Path(folder) / '.env'
            path.write_text('MOODLE_ADMIN_USERNAME=admin\nOTHER_SECRET=ignored\n')
            app.load_local_env(path)
            self.assertEqual(os.environ['MOODLE_ADMIN_USERNAME'], 'other')
            self.assertNotIn('OTHER_SECRET', os.environ)


if __name__ == '__main__':
    unittest.main()
