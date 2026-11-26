"""Interactions for the remaining Moodle Add New User widgets."""
from __future__ import annotations

from core.browser import click_visible, safe_type
from core.preconditions import PreconditionMissing
from pages import locators as L


class ExtraFields:
    def __init__(self, browser, timeout):
        self.browser = browser
        self.timeout = timeout

    def wait(self):
        from selenium.webdriver.support.ui import WebDriverWait
        return WebDriverWait(self.browser, self.timeout, poll_frequency=0.25)

    def visible(self, locator):
        return [e for e in self.browser.find_elements(*locator) if e.is_displayed()]

    def click(self, locator, name):
        click_visible(self.browser, *locator, self.timeout, name)

    def check(self, field):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        locator = (By.ID, L.FLAG_IDS[field])
        if field == 'delete_picture' and not self.browser.find_elements(*locator):
            raise PreconditionMissing('Delete picture is not rendered on the new user form; cannot exercise recorded checkbox.')
        element = self.wait().until(EC.presence_of_element_located(locator))
        if not element.is_selected():
            self.click(locator, field)
        self.wait().until(EC.element_located_to_be_selected(locator))

    def select(self, field, value, verify=False):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import Select
        locator = (By.ID, L.AUTH_ID if field == 'authentication' else L.SELECT_IDS[field])
        element = self.wait().until(lambda d: d.find_element(*locator))
        Select(element).select_by_value(value)
        if verify and Select(self.browser.find_element(*locator)).first_selected_option.get_attribute('value') != value:
            raise AssertionError(f'{field}: expected selected value {value!r}')

    def set_description(self, html, require_bold):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException
        self.wait().until(EC.frame_to_be_available_and_switch_to_it((By.ID, L.RICH_FRAME)))
        try:
            body = self.wait().until(EC.presence_of_element_located((By.CSS_SELECTOR, L.RICH_BODY)))
            # Katalon editContent sets HTML, not literal keystrokes. TinyMCE
            # setContent + save synchronizes the underlying Moodle textarea.
            # Pass data as an argument rather than interpolating into JS.
            self.browser.execute_script('''
                const body = arguments[0], html = arguments[1];
                const editor = window.parent.tinymce && window.parent.tinymce.get(body.ownerDocument.defaultView.frameElement.id.replace(/_ifr$/, ''));
                if (!editor) throw new Error('TinyMCE editor instance not found');
                editor.setContent(html); editor.fire('change'); editor.save();
            ''', body, html)
            if require_bold:
                try:
                    self.wait().until(EC.presence_of_element_located((By.CSS_SELECTOR, L.RICH_BOLD)))
                except TimeoutException as e:
                    raise AssertionError('Recorded rich text strong element missing') from e
        finally:
            self.browser.switch_to.default_content()

    def set_tags(self, tags, expected_count):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.common.exceptions import TimeoutException
        locator = (By.CSS_SELECTOR, L.TAG_INPUT)
        if not self.visible(locator):
            self.click((By.CSS_SELECTOR, L.INTERESTS_TOGGLE), 'Interests section')
        self.wait().until(lambda d: self.visible(locator))
        seen = set()
        for tag in tags:
            safe_type(self.browser, *locator, tag, self.timeout)
            self.browser.find_element(*locator).send_keys(Keys.ENTER)
            seen.add(tag)
            try:
                self.wait().until(lambda d: len(d.find_elements(By.CSS_SELECTOR, L.TAG_SELECTED)) >= len(seen))
            except TimeoutException as e:
                raise AssertionError(f'Tag not added: {tag!r}') from e
        try:
            self.wait().until(lambda d: len(d.find_elements(By.CSS_SELECTOR, L.TAG_SELECTED)) == expected_count)
        except TimeoutException as e:
            raise AssertionError(f'Expected {expected_count} selected tags') from e

    def cancel(self):
        from selenium.webdriver.common.by import By
        self.click((By.ID, L.CANCEL_ID), 'Cancel')
