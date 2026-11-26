"""Moodle authentication page object for Feature 004 Level 1."""
from __future__ import annotations

import os
from urllib.parse import urlsplit

from core.browser import click_visible, safe_type
from pages import locators as L


def login_redirect_complete(current_url: str) -> bool:
    return urlsplit(current_url).path.rstrip("/") != L.LOGIN_PATH


class LoginPage:
    def __init__(self, browser, base_url: str, timeout: int):
        self.browser = browser
        self.base_url = base_url
        self.timeout = timeout

    def prepare_admin_session(self, login_mode: str) -> None:
        from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        browser, base_url, timeout = self.browser, self.base_url, self.timeout
        wait = WebDriverWait(browser, timeout)
        browser.get(base_url + L.LOGIN_PATH)

        if login_mode == "manual":
            print("Log in to the opened Moodle page as Teacher/Admin, then press Enter here.")
            input()
        else:
            username = os.environ.get("MOODLE_ADMIN_USERNAME", "").strip()
            password = os.environ.get("MOODLE_ADMIN_PASSWORD", "")
            if not username or not password:
                raise RuntimeError(
                    "Missing Moodle credentials: set MOODLE_ADMIN_USERNAME and "
                    "MOODLE_ADMIN_PASSWORD in .env or environment variables (or use --manual-login)."
                )
            try:
                safe_type(browser, By.ID, L.LOGIN_USERNAME_ID, username, timeout)
                safe_type(browser, By.ID, L.LOGIN_PASSWORD_ID, password, timeout)
            except TimeoutException as error:
                raise RuntimeError("Cannot enter Moodle login credentials; check login page.") from error

            print("Submitting Moodle login...", flush=True)
            click_visible(browser, By.ID, L.LOGIN_BUTTON_ID, timeout, "Log in button")
            try:
                wait.until(lambda d: login_redirect_complete(d.current_url))
            except TimeoutException as error:
                message = ""
                for el in browser.find_elements(By.CSS_SELECTOR, L.LOGIN_ERROR_SELECTOR):
                    try:
                        if el.is_displayed() and el.text.strip():
                            message = el.text.strip()
                            break
                    except StaleElementReferenceException:
                        continue
                suffix = f" Moodle says: {message[:180]}" if message else ""
                raise RuntimeError("Moodle login did not complete." + suffix) from error

        # Verify authenticated access to Add a new Quiz form directly
        browser.get(base_url + L.add_quiz_path())
        try:
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, L.MFORM_NAME_INPUT)))
        except TimeoutException as error:
            current_path = urlsplit(browser.current_url).path
            if current_path.startswith(L.LOGIN_PREFIX):
                raise RuntimeError("Not logged in: Moodle redirected back to login page.") from error
            raise RuntimeError(
                f"Cannot open Add a new Quiz form at {L.add_quiz_path()} (current path: {current_path})"
            ) from error
        print("Moodle session ready; Add a new Quiz form verified.", flush=True)


def prepare_admin_session(browser, base_url: str, login_mode: str, timeout: int) -> None:
    LoginPage(browser, base_url, timeout).prepare_admin_session(login_mode)
