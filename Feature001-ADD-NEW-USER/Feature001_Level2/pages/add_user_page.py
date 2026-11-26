"""Add New User page object with shared field interactions."""
from __future__ import annotations

from core.browser import click_visible, safe_type
from pages import locators as L
from core.data_loader import resolve_data


def input_field(browser, locator: tuple[str, str], value: str, mode: str = "type", timeout: int = 15):
    if mode == "omit":
        return
    if mode not in {"type", "send_keys"}:
        raise ValueError(f"Unsupported entry mode: {mode}")
    # Preserve the original effective contents, including empty and boundary
    # values, while resolving a fresh element after any stale reference.
    safe_type(browser, *locator, value, timeout)


class AddUserPage:
    def __init__(self, browser, base_url: str, timeout: int):
        self.browser = browser
        self.base_url = base_url
        self.timeout = timeout

    def open(self, case):
        from selenium.webdriver.support.ui import Select, WebDriverWait

        browser, base_url, timeout = self.browser, self.base_url, self.timeout
        browser.get(base_url + L.CREATE_USER_PATH)
        WebDriverWait(browser, timeout).until(lambda d: d.find_element(*L.item('FIELD_IDS', "username")))
        Select(browser.find_element(*L.item('AUTH_ID'))).select_by_value(case["authentication"])

    def fill_core_fields(self, case, run_id: str):
        browser, timeout = self.browser, self.timeout
        input_field(browser, L.item("FIELD_IDS", "username"), case["username"], timeout=timeout)
        input_field(browser, L.item("FIELD_IDS", "first_name"), case["first_name"], case["first_name_entry"], timeout)
        input_field(browser, L.item("FIELD_IDS", "last_name"), case["last_name"], case["last_name_entry"], timeout)
        input_field(browser, L.item("FIELD_IDS", "email"), resolve_data(case["email"], run_id), timeout=timeout)

        if case["password_entry"] != "omit":
            buttons = browser.find_elements(*L.item('PASSWORD_TOGGLE'))
            if buttons:
                click_visible(browser, *L.item('PASSWORD_TOGGLE'), timeout, "password toggle")
            input_field(browser, L.item("FIELD_IDS", "new_password"), case["new_password"], case["password_entry"], timeout)

    def submit(self):
        click_visible(self.browser, *L.item('SUBMIT_ID'), self.timeout, "Create user")

    def fill_additional_text(self, field: str, value: str, section: str):
        """Open the recorded section if needed, then enter the literal CSV value."""
        from selenium.webdriver.support.ui import WebDriverWait

        browser, timeout = self.browser, self.timeout
        field_locator = L.item("TEXT_FIELD_IDS", field)
        if section != "none":
            toggle = L.item("SECTION_TOGGLES", section)
            WebDriverWait(browser, timeout).until(
                lambda d: d.find_element(*toggle)
            )
            # The page may remember expanded sections across cases. Avoid
            # closing an already visible field before attempting to type.
            if not any(e.is_displayed() for e in browser.find_elements(*field_locator)):
                click_visible(browser, *toggle, timeout, section)
        input_field(browser, field_locator, value, timeout=timeout)
