"""Prove that config changes are consumed by a fresh Level 2 process."""
import csv
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from core.testing_items import ITEMS, TESTING_ITEMS_FILE, load_items
from pages import locators as L

ROOT = Path(__file__).resolve().parents[1]


class TestingItemsChecks(unittest.TestCase):
    def test_all_default_items_are_loaded(self):
        self.assertEqual(len(ITEMS), 82)
        self.assertEqual(L.item('FIELD_IDS', 'username'), ('id', 'id_username'))
        self.assertEqual(L.item('PICKER_UPLOAD_TEXT'), ('xpath', "//button[normalize-space(.)='Upload this file']"))
        self.assertEqual(L.locator_tuple(L.resolve_target('first_name')), L.item('FIELD_IDS', 'first_name'))
        self.assertEqual(L.locator_tuple(L.resolve_target('create_button')), L.item('SUBMIT_ID'))

    def test_loader_rejects_bad_config(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'bad.csv'
            for body in ('x,id,a\nx,id,b\n', 'x,not_a_strategy,a\n', 'x,path,https://other.test/\n', 'x,id,\n', 'x,id\n'):
                with self.subTest(body=body):
                    path.write_text('item_name,item_type,item_value\n' + body)
                    with self.assertRaises(ValueError):
                        load_items(path)

    def test_modified_csv_controls_live_call_arguments(self):
        # Isolated package copy: do not edit the delivered config, use browser mocks only.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'level2'
            for name in ('core', 'pages', 'test_groups', 'config'):
                shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns('__pycache__'))
            path = root / 'config/testing_items.csv'
            with path.open(newline='', encoding='utf-8') as f:
                rows = list(csv.DictReader(f))
            changes = {
                'SUBMIT_ID': ('css', '#new-submit'),
                'FIELD_IDS.first_name': ('xpath', '//input[@name="given"]'),
                'BASE_URL': ('url', 'http://localhost:9999'),
                'LOGIN_PATH': ('path', '/alternate/auth'),
                'PICTURE_FILES': ('css', '.new-file'),
                'VERIFICATION.success_message': ('id', 'new-alert'),
            }
            for row in rows:
                if row['item_name'] in changes:
                    row['item_type'], row['item_value'] = changes[row['item_name']]
            with path.open('w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['item_name','item_type','item_value'])
                writer.writeheader(); writer.writerows(rows)
            code = '''
from unittest.mock import Mock, patch
from core.config import BASE_URL
from pages import locators as L
from pages.add_user_page import AddUserPage, input_field
from pages.login_page import login_redirect_complete
from pages.picture_picker import PicturePicker
from test_groups.test_core_fields import verify_pre_submit
assert BASE_URL == 'http://localhost:9999'
assert not login_redirect_complete(BASE_URL + '/alternate/auth')
browser = Mock()
with patch('pages.add_user_page.click_visible') as click:
    AddUserPage(browser, BASE_URL, 10).submit()
    click.assert_called_once_with(browser, 'css selector', '#new-submit', 10, 'Create user')
with patch('pages.add_user_page.safe_type') as safe:
    input_field(browser, L.item('FIELD_IDS','first_name'), 'An')
    safe.assert_called_once_with(browser, 'xpath', '//input[@name="given"]', 'An', 15)
browser.find_element.return_value.get_attribute.return_value = 'An'
verify_pre_submit(browser, [{'target':'first_name','expected':'An'}])
browser.find_element.assert_called_with('xpath', '//input[@name="given"]')
browser.find_elements.return_value = []
assert PicturePicker(browser, 10).count() == 0
browser.find_elements.assert_called_with('css selector', '.new-file')
assert L.locator_tuple(L.resolve_target('success_message')) == ('id','new-alert')
assert L.locator_tuple(L.resolve_target('create_button')) == ('css selector','#new-submit')
'''
            result = subprocess.run([sys.executable, '-c', code], cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            # Missing a required row must fail rather than silently using hardcoded defaults.
            with path.open('w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['item_name','item_type','item_value'])
                writer.writeheader(); writer.writerows(r for r in rows if r['item_name'] != 'SUBMIT_ID')
            result = subprocess.run([sys.executable, '-c', 'import pages.locators'], cwd=root, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Missing testing item: SUBMIT_ID', result.stderr)
