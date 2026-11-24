"""Add New User page object with shared field interactions."""
from __future__ import annotations

from core.browser import click_visible, safe_type
from core.data_loader import resolve_data
from pages.locators import CREATE_USER_PATH, FIELD_IDS, PASSWORD_TOGGLE, AUTH_ID, SUBMIT_ID


def input_field(browser, field_id: str, value: str, mode: str = "type", timeout: int = 15):
    from selenium.webdriver.common.by import By
    if mode == "omit":
        return
    if mode not in {"type", "send_keys"}:
        raise ValueError(f"Unsupported entry mode: {mode}")
    # Preserve the original effective contents, including empty and boundary
    # values, while resolving a fresh element after any stale reference.
    safe_type(browser, By.ID, field_id, value, timeout)


class AddUserPage:
    def __init__(self, browser, base_url: str, timeout: int):
        self.browser = browser
        self.base_url = base_url
        self.timeout = timeout

    def open(self, case):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import Select, WebDriverWait

        browser, base_url, timeout = self.browser, self.base_url, self.timeout
        browser.get(base_url + CREATE_USER_PATH)
        WebDriverWait(browser, timeout).until(lambda d: d.find_element(By.ID, FIELD_IDS["username"]))
        Select(browser.find_element(By.ID, AUTH_ID)).select_by_value(case["authentication"])

    def fill_core_fields(self, case, run_id: str):
        from selenium.webdriver.common.by import By

        browser, timeout = self.browser, self.timeout
        input_field(browser, FIELD_IDS["username"], case["username"], timeout=timeout)
        input_field(browser, FIELD_IDS["first_name"], case["first_name"], case["first_name_entry"], timeout)
        input_field(browser, FIELD_IDS["last_name"], case["last_name"], case["last_name_entry"], timeout)
        input_field(browser, FIELD_IDS["email"], resolve_data(case["email"], run_id), timeout=timeout)

        if case["password_entry"] != "omit":
            buttons = browser.find_elements(By.CSS_SELECTOR, PASSWORD_TOGGLE)
            if buttons:
                click_visible(browser, By.CSS_SELECTOR, PASSWORD_TOGGLE, timeout, "password toggle")
            input_field(browser, FIELD_IDS["new_password"], case["new_password"], case["password_entry"], timeout)

    def submit(self):
        from selenium.webdriver.common.by import By

        click_visible(self.browser, By.ID, SUBMIT_ID, self.timeout, "Create user")

    def fill_additional_text(self, field: str, value: str, section: str):
        """Open the recorded section if needed, then enter the literal CSV value."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from pages.locators import SECTION_TOGGLES, TEXT_FIELD_IDS

        browser, timeout = self.browser, self.timeout
        field_id = TEXT_FIELD_IDS[field]
        if section != "none":
            toggle = SECTION_TOGGLES[section]
            WebDriverWait(browser, timeout).until(
                lambda d: d.find_element(By.CSS_SELECTOR, toggle)
            )
            # The page may remember expanded sections across cases. Avoid
            # closing an already visible field before attempting to type.
            if not any(e.is_displayed() for e in browser.find_elements(By.ID, field_id)):
                click_visible(browser, By.CSS_SELECTOR, toggle, timeout, section)
        input_field(browser, field_id, value, timeout=timeout)
