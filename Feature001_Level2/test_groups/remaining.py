"""Data-driven workflows F03–F11; each group uses one shared execution path."""
from __future__ import annotations
import json
import os
from pathlib import Path

from core.config import ROOT_DIR
from core.data_loader import Case, read_cases, resolve_data
from core.preconditions import PreconditionMissing
from pages.add_user_page import AddUserPage, input_field
from pages.extra_fields import ExtraFields
from pages.picture_picker import PicturePicker
from pages import locators as L
from test_groups.test_core_fields import verify_expected


def read_remaining(path: Path) -> list[Case]:
    cases = read_cases(path, extra_kinds=('presence', 'absence'))
    for case in cases:
        L.resolve_target(case['expected_target'])
    return cases


def updated(case, **fields):
    return Case({**case.values, **fields})


def assert_outcome(browser, case, timeout):
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.common.exceptions import TimeoutException
    kind = case['expected_kind']
    if kind not in ('presence', 'absence'):
        return verify_expected(browser, case, timeout)
    loc = L.locator_tuple(L.resolve_target(case['expected_target']))
    try:
        WebDriverWait(browser, timeout, poll_frequency=0.25).until(
            lambda d: bool(d.find_elements(*loc)) == (kind == 'presence'))
    except TimeoutException as e:
        raise AssertionError(f"Expected {case['expected_target']} {case['expected_text']}") from e
    return f"{case['expected_target']}: {case['expected_text']}"


def begin(browser, base_url, case, run_id, timeout):
    page = AddUserPage(browser, base_url, timeout)
    page.open(case)
    page.fill_core_fields(case, run_id)
    return page, ExtraFields(browser, timeout)


def run_rich(browser, base_url, case, run_id, timeout):
    page, extra = begin(browser, base_url, case, run_id, timeout)
    if case['editor_mode'] == 'html':
        extra.set_description(case['description_html'], case['require_bold'] == 'yes')
    page.submit()
    return assert_outcome(browser, case, timeout)


def image_path(name):
    root = (ROOT_DIR / 'fixtures' / 'images').resolve()
    path = (root / name).resolve()
    if path.parent != root or not path.is_file():
        raise PreconditionMissing(f'Image fixture missing or invalid: {name}')
    return path


def boundary_size(case):
    raw = os.environ.get('MOODLE_IMAGE_MAX_BYTES', '')
    try:
        m = int(raw)
        if m < 1:
            raise ValueError
    except ValueError as e:
        raise PreconditionMissing('Set MOODLE_IMAGE_MAX_BYTES to the actual finite limit M in bytes.') from e
    return m + int(case['size_delta'])


def preflight(case):
    """Offline fixture availability checks; no browser required."""
    try:
        if 'image_action' in case.values:
            if case['image_action'] == 'size_boundary':
                target_size = boundary_size(case)
                if image_path(case['file_name']).stat().st_size != target_size:
                    raise PreconditionMissing(f"Fixture {case['file_name']} must be exactly {target_size} bytes.")
            for field in ('file_name', 'second_file_name'):
                if case[field]:
                    image_path(case[field])
        if case['expected_target'] == 'create_button' and case['expected_kind'] == 'absence':
            restricted_credentials()
    except PreconditionMissing as e:
        return str(e)
    return ''


def run_image(browser, base_url, case, run_id, timeout):
    page, extra = begin(browser, base_url, case, run_id, timeout)
    picker = PicturePicker(browser, timeout)
    action = case['image_action']
    picker.open_section()
    if action == 'size_boundary':
        picker.require_finite_limit()
        expected_size = boundary_size(case)
        if image_path(case['file_name']).stat().st_size != expected_size:
            raise PreconditionMissing(f'Incorrect boundary fixture size: expected {expected_size} bytes')
    upload_note = ''
    if case['file_name']:
        upload_note = picker.upload(image_path(case['file_name']), expect_rejection=case['expected_file_count'] == '0')
    if case['second_file_name']:
        upload_note += '; ' + picker.upload(image_path(case['second_file_name']), second=True)
    if action == 'delete_picture':
        extra.check('delete_picture')
    picker.check_count(int(case['expected_file_count']))
    thumbnail_note = ''
    if case['require_thumbnail_absent'] == 'yes':
        thumbnail_note = picker.assert_no_real_thumbnail()
    if case['source_has_submit'] == 'yes':
        page.submit()
    result = thumbnail_note if case['expected_target'] == 'picture_thumbnail' else assert_outcome(browser, case, timeout)
    return '; '.join(filter(None, (result, upload_note)))


def run_tags(browser, base_url, case, run_id, timeout):
    page, extra = begin(browser, base_url, case, run_id, timeout)
    extra.set_tags(json.loads(case['tags_json']), int(case['expected_tag_count']))
    page.submit()
    return assert_outcome(browser, case, timeout)


def run_flags(browser, base_url, case, run_id, timeout):
    page, extra = begin(browser, base_url, case, run_id, timeout)
    if case['final_authentication'] != case['authentication']:
        extra.select('authentication', case['final_authentication'])
    for flag in json.loads(case['flags_json']):
        extra.check(flag)
    page.submit()
    return assert_outcome(browser, case, timeout)


def run_select(browser, base_url, case, run_id, timeout):
    page, extra = begin(browser, base_url, case, run_id, timeout)
    extra.select(case['select_field'], case['select_value'], case['verify_selection'] == 'yes')
    page.submit()
    return assert_outcome(browser, case, timeout)


def seed_and_repeat(browser, base_url, case, run_id, timeout):
    seed = updated(case, username=resolve_data(case['username'], run_id))
    page, _ = begin(browser, base_url, seed, run_id, timeout)
    page.submit()
    assert_outcome(browser, updated(seed, expected_kind='success', expected_target='success_message', expected_text=case['seed_expected_text']), timeout)
    repeat = updated(seed, email=case['second_email'])
    page, _ = begin(browser, base_url, repeat, run_id, timeout)
    page.submit()
    return page, seed


def run_duplicate(browser, base_url, case, run_id, timeout):
    seed_and_repeat(browser, base_url, case, run_id, timeout)
    return assert_outcome(browser, case, timeout)


def run_cancel(browser, base_url, case, run_id, timeout):
    page, extra = begin(browser, base_url, case, run_id, timeout)
    for flag in json.loads(case['flags_json']):
        extra.check(flag)
    if case['intermediate_target']:
        page.submit()
        assert_outcome(browser, updated(case, expected_kind='field_error', expected_target=case['intermediate_target'], expected_text=case['intermediate_expected_text']), timeout)
    extra.cancel()
    return assert_outcome(browser, case, timeout)


def run_recovery(browser, base_url, case, run_id, timeout):
    page, seed = seed_and_repeat(browser, base_url, case, run_id, timeout)
    assert_outcome(browser, updated(case, expected_kind='field_error', expected_target='username_error', expected_text=case['duplicate_expected_text']), timeout)
    input_field(browser, L.item("FIELD_IDS", 'username'), case['recovery_username'], timeout=timeout)
    # Password can be cleared by failed validation. Re-enter as recorded.
    password = L.item('FIELD_IDS', 'new_password')
    if not ExtraFields(browser, timeout).visible(password) or not any(e.is_enabled() for e in browser.find_elements(*password)):
        ExtraFields(browser, timeout).click(L.item('PASSWORD_TOGGLE'), 'password toggle')
    input_field(browser, L.item("FIELD_IDS", 'new_password'), case['recovery_password'], timeout=timeout)
    page.submit()
    result = assert_outcome(browser, case, timeout)
    return f"{result}; seed username={seed['username']}; recovery username={case['recovery_username']}"


def restricted_credentials():
    username = os.environ.get('MOODLE_RESTRICTED_USERNAME', '').strip()
    password = os.environ.get('MOODLE_RESTRICTED_PASSWORD', '')
    admin = os.environ.get('MOODLE_ADMIN_USERNAME', 'admin').strip()
    if not username or not password or username.casefold() in {admin.casefold(), 'admin', 'guest'}:
        raise PreconditionMissing('Provide a dedicated non-admin, non-guest account without moodle/user:create in .env.')
    return username, password


def prepare_restricted_session(browser, base_url, login_mode, timeout):
    """Always authenticate a dedicated restricted account, never Admin."""
    from selenium.webdriver.support.ui import WebDriverWait
    from core.browser import safe_type, click_visible
    from pages.login_page import login_redirect_complete
    username, password = restricted_credentials()
    browser.get(base_url + L.LOGIN_PATH)
    safe_type(browser, *L.item('LOGIN_USERNAME_ID'), username, timeout)
    safe_type(browser, *L.item('LOGIN_PASSWORD_ID'), password, timeout)
    click_visible(browser, *L.item('LOGIN_BUTTON_ID'), timeout, 'Restricted user login')
    WebDriverWait(browser, timeout).until(lambda d: login_redirect_complete(d.current_url))
    WebDriverWait(browser, timeout).until(lambda d: ExtraFields(d, timeout).visible(L.item('USER_MENU')))


def run_denial(browser, base_url, case, run_id, timeout):
    from urllib.parse import urlsplit
    from selenium.webdriver.support.ui import WebDriverWait
    browser.get(base_url + L.CREATE_USER_PATH)
    if urlsplit(browser.current_url).path.startswith(L.LOGIN_PREFIX):
        raise PreconditionMissing('Restricted account session not authenticated; anonymous access is not the test.')
    # Check explicit denial before accepting absent submit button; a loading
    # or unrelated page is not evidence that access control works.
    extra = ExtraFields(browser, timeout)
    def outcome(d):
        if d.find_elements(*L.item('SUBMIT_ID')):
            raise AssertionError('Restricted user can access Create user button')
        errors = [e.text.strip() for e in extra.visible(L.item('DENIAL_ERROR')) if e.text.strip()]
        return ' | '.join(errors) or False
    from selenium.common.exceptions import TimeoutException
    try:
        denial = WebDriverWait(browser, timeout).until(outcome)
    except TimeoutException as e:
        raise AssertionError('No explicit access denial observed; inspect actual page') from e
    if not any(term in denial.casefold() for term in ('permission', 'not allowed', 'capability', 'access denied', 'not have', 'not authorised', 'not authorized')):
        raise AssertionError(f'Unexpected error instead of permission denial: {denial}')
    return assert_outcome(browser, case, timeout) + '; ' + denial
