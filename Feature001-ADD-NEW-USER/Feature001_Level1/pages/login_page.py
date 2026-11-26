"""Moodle authentication page object."""
from __future__ import annotations

import os
from urllib.parse import urlsplit

from core.browser import click_visible, safe_type
from pages.locators import (
    CREATE_USER_PATH, FIELD_IDS, LOGIN_PATH, LOGIN_LINK, LOGIN_USERNAME_ID,
    LOGIN_PASSWORD_ID, LOGIN_BUTTON_ID, LOGIN_ERROR_SELECTOR,
)


def login_redirect_complete(current_url: str) -> bool:
    """True once Moodle leaves its login endpoint after submitting credentials.

    URL checks are stable across DOM replacement. Final authentication is
    confirmed separately by checking the Add New User form after navigation.
    """
    return urlsplit(current_url).path.rstrip("/") != LOGIN_PATH


class LoginPage:
    def __init__(self, browser, base_url: str, timeout: int):
        self.browser = browser
        self.base_url = base_url
        self.timeout = timeout

    def prepare_admin_session(self, login_mode: str):
        """Prepare an authenticated Moodle Admin session before running tests.

        Uses the home page's Log in link when present, then the exact input/button
        IDs from the provided Moodle screenshots. Sign-in is only test setup.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.common.exceptions import TimeoutException

        browser, base_url, timeout = self.browser, self.base_url, self.timeout
        wait = WebDriverWait(browser, timeout)
        browser.get(base_url + "/")
        login_links = browser.find_elements(By.CSS_SELECTOR, LOGIN_LINK)
        if login_links:
            try:
                click_visible(browser, By.CSS_SELECTOR, LOGIN_LINK, timeout, "Log in link")
            except RuntimeError:
                # Navigating to the link's public destination is equivalent, and
                # more robust if the site's navigation overlays intercept clicks.
                browser.get(base_url + LOGIN_PATH)
        else:
            browser.get(base_url + LOGIN_PATH)

        if login_mode == "manual":
            print("Log in to the opened Moodle page as Admin, then press Enter here.")
            input()
        else:
            username = os.environ.get("MOODLE_ADMIN_USERNAME", "").strip()
            password = os.environ.get("MOODLE_ADMIN_PASSWORD", "")
            if not username or not password:
                raise RuntimeError(
                    "Missing Moodle Admin credentials: set MOODLE_ADMIN_USERNAME and "
                    "MOODLE_ADMIN_PASSWORD in a local .env file or environment variables. "
                    "Alternatively use --manual-login."
                )

            # Resolve each login field only when interacting with it. A form
            # re-render between finding the username and password can invalidate
            # a previously cached WebElement.
            try:
                safe_type(browser, By.ID, LOGIN_USERNAME_ID, username, timeout)
                safe_type(browser, By.ID, LOGIN_PASSWORD_ID, password, timeout)
            except TimeoutException as error:
                raise RuntimeError(
                    "Cannot enter Moodle login credentials; check login page and field visibility"
                ) from error
            print("Submitting Moodle Admin login...")
            click_visible(browser, By.ID, LOGIN_BUTTON_ID, timeout, "Log in button")

            # Moodle replaces the login form during the POST/redirect. Never call
            # is_displayed() on #loginbtn here: its WebElement can become stale
            # between find_elements() and is_displayed() while navigation happens.
            # Wait for navigation away from the login URL instead. We still verify
            # the authenticated Add New User form below before running any tests.
            try:
                wait.until(lambda d: login_redirect_complete(d.current_url))
            except TimeoutException as error:
                from selenium.common.exceptions import StaleElementReferenceException

                # Error widgets may also rerender; read only fresh elements and
                # tolerate a race rather than replacing the useful timeout error.
                message = ""
                for el in browser.find_elements(
                        By.CSS_SELECTOR, LOGIN_ERROR_SELECTOR
                ):
                    try:
                        if el.is_displayed() and el.text.strip():
                            message = el.text.strip()
                            break
                    except StaleElementReferenceException:
                        continue
                suffix = f" Moodle says: {message[:180]}" if message else ""
                raise RuntimeError(
                    "Moodle Admin login did not complete; verify credentials and account status." + suffix
                ) from error

        browser.get(base_url + CREATE_USER_PATH)
        try:
            wait.until(EC.visibility_of_element_located((By.ID, FIELD_IDS["username"])))
        except TimeoutException as error:
            current_path = urlsplit(browser.current_url).path
            if current_path.startswith("/login"):
                raise RuntimeError("Not logged in: Moodle redirected back to the login page") from error
            raise RuntimeError(
                "Cannot open Add New User as Admin; check user permissions and Moodle URL "
                f"(current path: {current_path})"
            ) from error
        print("Moodle Admin session ready; Add New User form opened.")


def prepare_admin_session(browser, base_url: str, login_mode: str, timeout: int):
    return LoginPage(browser, base_url, timeout).prepare_admin_session(login_mode)
