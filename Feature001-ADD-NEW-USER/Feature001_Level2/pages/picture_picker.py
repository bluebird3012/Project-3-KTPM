"""Moodle file picker: Add -> Upload a file -> local path -> Upload this file."""
from __future__ import annotations
from pathlib import Path
from core.preconditions import PreconditionMissing
from pages import locators as L
from pages.extra_fields import ExtraFields


class PicturePicker(ExtraFields):
    def open_section(self):
        toggle = L.item('PICTURE_SECTION')
        if not self.visible(L.item('PICTURE_ADD')) and self.visible(toggle):
            self.click(toggle, 'User picture section')

    def count(self):
        return len(self.browser.find_elements(*L.item('PICTURE_FILES')))

    def check_count(self, count):
        from selenium.common.exceptions import TimeoutException
        try:
            self.wait().until(lambda d: self.count() == count)
        except TimeoutException as e:
            raise AssertionError(f'Expected {count} draft picture(s); actual {self.count()}') from e

    def require_finite_limit(self):
        self.open_section()
        if self.visible(L.item('PICTURE_UNLIMITED')):
            raise PreconditionMissing('Moodle displays Maximum file size: Unlimited; finite M boundary is not applicable.')

    def visible(self, locator):
        from selenium.common.exceptions import StaleElementReferenceException
        result = []
        for element in self.browser.find_elements(*locator):
            try:
                if element.is_displayed():
                    result.append(element)
            except StaleElementReferenceException:
                continue
        return result

    def rejection_message(self):
        """Read explicit UI rejection, including Moodle notification dialogs."""
        from selenium.common.exceptions import StaleElementReferenceException
        messages = []
        for element in self.visible(L.item('PICKER_ERROR')):
            try:
                if element.text.strip():
                    messages.append(element.text.strip())
            except StaleElementReferenceException:
                continue
        for dialog in self.visible(L.item('PICKER_DIALOG')):
            try:
                titles = dialog.find_elements(*L.item('PICKER_DIALOG_TITLE'))
                title = ' '.join(e.text.strip() for e in titles if e.is_displayed()).lower()
                if title in {'error', 'file type not accepted', 'invalid file type', 'upload error'}:
                    bodies = dialog.find_elements(*L.item('PICKER_DIALOG_BODY'))
                    body = ' '.join(e.text.strip() for e in bodies if e.is_displayed())
                    if body:
                        messages.append(f'{title}: {body}')
            except StaleElementReferenceException:
                continue
        return ' | '.join(dict.fromkeys(messages))

    def selected_file(self, element):
        """Check the actual browser file selection, not the filename label."""
        return self.browser.execute_script(
            'return arguments[0].files.length ? arguments[0].files[0].name : "";', element)

    def select_file(self, path):
        from selenium.common.exceptions import StaleElementReferenceException
        locator = L.item('PICKER_UPLOAD_INPUT')

        def selected(d):
            try:
                for element in self.visible(locator):
                    if self.selected_file(element) != path.name:
                        element.send_keys(str(path.resolve()))
                    if self.selected_file(element) == path.name:
                        return True
            except StaleElementReferenceException:
                return False
            return False

        self.wait().until(selected, message=f'Could not confirm selection of {path.name}')

    def click_upload(self, before, path):
        """Reacquire a replaced button; do not blindly repeat a submitted upload."""
        from selenium.common.exceptions import StaleElementReferenceException, ElementClickInterceptedException
        from selenium.webdriver.common.action_chains import ActionChains
        inputs = L.item('PICKER_UPLOAD_INPUT')
        buttons = (L.item('PICKER_UPLOAD_BUTTON'), L.item('PICKER_UPLOAD_TEXT'))

        def attempt(d):
            try:
                if self.rejection_message() or self.count() > before:
                    return True
                selected = [e for e in self.visible(inputs) if self.selected_file(e) == path.name]
                if not selected:
                    # Picker might be rebuilding after selection, or processing a click.
                    # Never click with an empty file input.
                    return False
                for locator in buttons:
                    for button in self.visible(locator):
                        if not button.is_enabled():
                            continue
                        try:
                            button.click()
                        except ElementClickInterceptedException:
                            ActionChains(d).move_to_element(button).click().perform()
                        return True
            except StaleElementReferenceException:
                return False
            return False

        self.wait().until(attempt, message=f'Could not click Upload this file for {path.name}')

    def assert_no_real_thumbnail(self):
        """Distinguish Moodle's file-type icon from a generated draft preview.

        A generic icon is positive evidence, whereas an absent/unknown DOM
        representation is inconclusive. The original Katalon img assertion
        is recorded in the actual result for traceability.
        """
        from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
        def sources(d):
            try:
                return [e.get_attribute('src') for e in self.visible(L.item('PICTURE_FILE_ICONS')) if e.get_attribute('src')]
            except StaleElementReferenceException:
                return False
        try:
            urls = self.wait().until(sources)
        except TimeoutException as e:
            raise RuntimeError('Cannot identify draft icon or thumbnail; inspect screenshot.') from e
        classifications = [classify_picture_source(url) for url in urls]
        if 'preview' in classifications:
            raise AssertionError(f'Unexpected generated image preview: {urls}')
        if any(kind != 'icon' for kind in classifications):
            raise RuntimeError(f'Unrecognised draft image source; cannot verify thumbnail absence: {urls}')
        return ('No generated draft thumbnail; generic file icon present. '
                'Original Katalon .fp-file img absence assertion would fail.')

    def upload(self, path: Path, *, expect_rejection=False, second=False):
        from selenium.common.exceptions import TimeoutException
        self.open_section()
        add = L.item('PICTURE_ADD')
        before = self.count()
        if second and not any(e.is_enabled() for e in self.visible(add)):
            return 'Add control unavailable at one-file limit'
        self.click(add, 'Add picture')
        self.click(L.item('PICKER_REPOSITORY'), 'Upload a file')
        self.select_file(path)
        self.click_upload(before, path)

        def settled(d):
            message = self.rejection_message()
            if message:
                return ('rejected', message)
            if not self.visible(L.item('PICKER_UPLOAD_INPUT')):
                if self.count() > before or (second and self.count() == before):
                    return ('accepted', f'{self.count()} draft picture(s)')
            return False
        try:
            outcome, message = self.wait().until(settled)
        except TimeoutException as e:
            raise RuntimeError(f'Upload outcome not observed for {path.name}; no explicit rejection or completed upload. Inspect screenshot.') from e
        if outcome == 'rejected':
            if not (expect_rejection or second):
                raise AssertionError(f'Upload unexpectedly rejected: {message}')
            if not is_expected_rejection(message, second=second):
                raise RuntimeError(f'Upload error is not a recognised file restriction: {message}')
            # Rejection-only cases need no more interaction; keep evidence.
            # For a second-file case, dismiss dialogs before submitting.
            if second:
                for _ in range(3):
                    if not self.visible(L.item('PICKER_UPLOAD_INPUT')) and not self.rejection_message():
                        break
                    closers = self.visible(L.item('PICKER_OK')) or self.visible(L.item('PICKER_CLOSE'))
                    if not closers:
                        break
                    closers[-1].click()
                self.wait().until(lambda d: not self.visible(L.item('PICKER_UPLOAD_INPUT')))
            return message
        if expect_rejection:
            raise AssertionError(f'Invalid file unexpectedly accepted: {path.name}')
        return message


def classify_picture_source(url):
    from urllib.parse import urlsplit, parse_qs, unquote
    parsed = urlsplit(url)
    path = unquote(parsed.path).lower()
    query = parse_qs(parsed.query)
    if L.DRAFT_FILE_TOKEN in path and any(v in ('thumb', 'tinyicon') for v in query.get('preview', [])):
        return 'preview'
    # Moodle's theme image endpoint supplies generic file-type icons.
    if (L.THEME_IMAGE_PATH in path or L.THEME_IMAGE_PATH in url.lower()) and (
        L.THEME_FILE_PATH in path or any(v.startswith(L.THEME_FILE_QUERY_PREFIX) for v in query.get('image', []))
    ):
        return 'icon'
    if L.PIX_FILE_PATH in path:
        return 'icon'
    return 'unknown'


def is_expected_rejection(message, *, second=False):
    text = message.lower()
    restrictions = ('filetype cannot be accepted', 'file type not accepted', 'file type is not accepted',
                    'file type is not allowed', 'filetype is not allowed', 'invalid file type',
                    'file is too large', 'file size exceeds', 'maximum file size', 'exceeds the maximum',
                    'larger than the maximum', 'too big', 'exceeds the upload', 'file too large')
    if second:
        restrictions += ('maximum number of files', 'too many files', 'maximum number of uploaded files')
    return any(token in text for token in restrictions)
