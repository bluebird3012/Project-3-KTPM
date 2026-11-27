"""Page Object for Moodle Add / Edit Quiz form - Level 2 (100% config-driven locators)."""
from __future__ import annotations

import time
from typing import Any

from core.browser import click_visible, safe_select, safe_set_checkbox, safe_type
from pages import locators as L


class AddQuizPage:
    def __init__(self, browser, base_url: str, timeout: int):
        self.browser = browser
        self.base_url = base_url
        self.timeout = timeout

    def open_add_form(self) -> None:
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        self.browser.get(self.base_url + L.add_quiz_path())
        WebDriverWait(self.browser, self.timeout).until(
            EC.visibility_of_element_located(L.field_locator("name"))
        )

    def open_edit_form(self, cmid: str) -> None:
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        self.browser.get(self.base_url + L.edit_quiz_path(cmid))
        WebDriverWait(self.browser, self.timeout).until(
            EC.visibility_of_element_located(L.field_locator("name"))
        )

    def expand_all_sections(self) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        expand_loc = L.item("EXPAND_ALL_LINK")
        show_more_loc = L.item("SHOW_MORE_LINKS")

        def try_expand(driver):
            links = driver.find_elements(*expand_loc)
            if not links:
                return True
            link = links[0]
            if not link.is_displayed():
                return True
            if link.get_attribute("aria-expanded") == "true":
                return True
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", link)
                link.click()
            except Exception:
                return False
            return driver.find_element(*expand_loc).get_attribute("aria-expanded") == "true"

        WebDriverWait(self.browser, self.timeout, poll_frequency=0.5).until(
            try_expand,
            message="Could not expand Moodle Add Quiz form sections (Expand all)",
        )
        time.sleep(0.25)

        for _ in range(2):
            clicked_any = False
            for el in self.browser.find_elements(*show_more_loc):
                try:
                    if el.is_displayed() and "show more" in (el.text or "").strip().lower():
                        self.browser.execute_script(
                            "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", el
                        )
                        el.click()
                        clicked_any = True
                except Exception:
                    continue
            if not clicked_any:
                break
            time.sleep(0.25)

    def set_name(self, value: str, *, extra_send_keys: str = "") -> None:
        safe_type(self.browser, *L.field_locator("name"), value, self.timeout, clear_first=True)
        if extra_send_keys:
            safe_type(
                self.browser,
                *L.field_locator("name"),
                extra_send_keys,
                self.timeout,
                clear_first=False,
            )

    def _wait_tinymce_ready(self):
        from selenium.webdriver.support.ui import WebDriverWait

        iframe_loc = L.item("INTRO_EDITOR_IFRAME")
        editor_timeout = max(self.timeout, 240)
        wait = WebDriverWait(self.browser, editor_timeout, poll_frequency=0.5)

        def iframe_visible(driver):
            frames = driver.find_elements(*iframe_loc)
            if not frames:
                return False
            frame = frames[0]
            try:
                ready = driver.execute_script(
                    """
                    const f = arguments[0];
                    const style = window.getComputedStyle(f);
                    const rect = f.getBoundingClientRect();
                    const tox = f.closest('.tox-tinymce');
                    const toxStyle = tox ? window.getComputedStyle(tox) : null;
                    return style.visibility !== 'hidden' && style.display !== 'none'
                        && rect.width > 50 && rect.height > 40
                        && (!toxStyle || (toxStyle.visibility !== 'hidden' && toxStyle.display !== 'none'));
                    """,
                    frame,
                )
                return frame if ready else False
            except Exception:
                return False

        iframe = wait.until(iframe_visible, message="TinyMCE iframe did not become visible in time")
        self.browser.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", iframe)
        return wait

    def set_description(self, text: str) -> None:
        from selenium.common.exceptions import ElementClickInterceptedException, StaleElementReferenceException
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support import expected_conditions as EC

        iframe_loc = L.item("INTRO_EDITOR_IFRAME")
        body_loc = L.item("INTRO_EDITOR_BODY")
        wait = self._wait_tinymce_ready()

        def type_in_editor(driver):
            driver.switch_to.default_content()
            wait.until(EC.frame_to_be_available_and_switch_to_it(iframe_loc))
            try:
                body = wait.until(EC.element_to_be_clickable(body_loc))
                body.click()
                body.send_keys(Keys.CONTROL, "a")
                body.send_keys(Keys.BACKSPACE)
                if text:
                    body.send_keys(text)
                return True
            except (ElementClickInterceptedException, StaleElementReferenceException):
                return False
            finally:
                driver.switch_to.default_content()

        wait.until(type_in_editor, message="Could not focus and type into TinyMCE description editor")

    def get_description_text(self) -> str:
        from selenium.webdriver.support import expected_conditions as EC

        iframe_loc = L.item("INTRO_EDITOR_IFRAME")
        read_loc = L.item("INTRO_EDITOR_BODY_READ")
        wait = self._wait_tinymce_ready()
        wait.until(EC.frame_to_be_available_and_switch_to_it(iframe_loc))
        try:
            body = wait.until(EC.presence_of_element_located(read_loc))
            return (body.text or "").strip()
        finally:
            self.browser.switch_to.default_content()

    def set_show_description(self, checked: bool) -> None:
        safe_set_checkbox(
            self.browser,
            *L.field_locator("showdescription"),
            checked,
            self.timeout,
            "Display description on course page",
        )

    def configure_datetime(self, prefix: str, spec: dict[str, Any]) -> None:
        if not spec:
            return
        enabled = bool(spec.get("enabled", False))
        safe_set_checkbox(
            self.browser,
            *L.field_locator(f"{prefix}[enabled]"),
            enabled,
            self.timeout,
            f"{prefix}[enabled]",
        )
        if not enabled:
            return
        for part in ("year", "month", "day", "hour", "minute"):
            if part in spec and spec[part] is not None and str(spec[part]) != "":
                safe_select(
                    self.browser,
                    *L.field_locator(f"{prefix}[{part}]"),
                    value=str(spec[part]),
                    timeout=self.timeout,
                )

    def configure_duration(self, prefix: str, spec: dict[str, Any]) -> None:
        if not spec:
            return
        enabled = bool(spec.get("enabled", False))
        safe_set_checkbox(
            self.browser,
            *L.field_locator(f"{prefix}[enabled]"),
            enabled,
            self.timeout,
            f"{prefix}[enabled]",
        )
        if not enabled:
            return
        if "number" in spec and spec["number"] is not None:
            safe_type(
                self.browser,
                *L.field_locator(f"{prefix}[number]"),
                str(spec["number"]),
                self.timeout,
                clear_first=True,
            )
        if "timeunit" in spec and spec["timeunit"] is not None and str(spec["timeunit"]) != "":
            safe_select(
                self.browser,
                *L.field_locator(f"{prefix}[timeunit]"),
                value=str(spec["timeunit"]),
                timeout=self.timeout,
            )

    def set_overduehandling(self, value: str) -> None:
        if value:
            safe_select(self.browser, *L.field_locator("overduehandling"), value=value, timeout=self.timeout)

    def set_select_field(self, field_key: str, raw_spec: str) -> None:
        if not raw_spec:
            return
        loc = L.field_locator(field_key)
        if raw_spec.startswith("label="):
            safe_select(self.browser, *loc, label=raw_spec[6:], timeout=self.timeout)
        elif raw_spec.startswith("value="):
            safe_select(self.browser, *loc, value=raw_spec[6:], timeout=self.timeout)
        else:
            safe_select(self.browser, *loc, value=raw_spec, timeout=self.timeout)

    def set_gradepass(self, value: str) -> None:
        safe_type(self.browser, *L.field_locator("gradepass"), value, self.timeout, clear_first=True)

    def click_add_feedback_fields(self) -> None:
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        add_btn_loc = L.item("ADD_FEEDBACK_FIELDS_BUTTON")
        old_btn = WebDriverWait(self.browser, self.timeout).until(
            EC.presence_of_element_located(add_btn_loc)
        )
        click_visible(
            self.browser,
            *add_btn_loc,
            self.timeout,
            "Add 3 more feedback fields",
        )
        WebDriverWait(self.browser, self.timeout).until(EC.staleness_of(old_btn))
        WebDriverWait(self.browser, self.timeout).until(
            EC.presence_of_element_located(L.field_locator("feedbackboundaries[1]"))
        )
        self.expand_all_sections()

    def set_feedback_boundary(self, index: int, value: str) -> None:
        field_key = "feedbackboundaries[0]" if index == 0 else "feedbackboundaries[1]"
        safe_type(self.browser, *L.field_locator(field_key), value, self.timeout, clear_first=True)

    def submit(self, action: str) -> None:
        if action == "save_return":
            click_visible(self.browser, *L.item("SUBMIT_RETURN_BUTTON"), self.timeout, "Save and return to course")
        elif action == "save_display":
            click_visible(self.browser, *L.item("SUBMIT_DISPLAY_BUTTON"), self.timeout, "Save and display")
        elif action == "cancel":
            click_visible(self.browser, *L.item("CANCEL_BUTTON"), self.timeout, "Cancel")
        else:
            raise ValueError(f"Unsupported submit action: {action!r}")

    def wait_for_field_error(self, target_key: str) -> str:
        from selenium.common.exceptions import StaleElementReferenceException
        from selenium.webdriver.support.ui import WebDriverWait

        err_loc = L.error_locator(target_key)

        def read_non_empty(driver):
            for el in driver.find_elements(*err_loc):
                try:
                    txt = (el.text or "").strip()
                    if txt:
                        return txt
                except StaleElementReferenceException:
                    continue
            return False

        return WebDriverWait(self.browser, self.timeout, poll_frequency=0.25).until(
            read_non_empty,
            message=f"Expected non-empty validation error at {target_key} ({err_loc})",
        )

    def is_on_quiz_form(self) -> bool:
        return bool(self.browser.find_elements(*L.field_locator("name")))

    def read_field_value(self, field_key: str) -> str:
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        el = WebDriverWait(self.browser, self.timeout).until(
            EC.presence_of_element_located(L.field_locator(field_key))
        )
        return (el.get_attribute("value") or "").strip()

    def read_selected_label(self, field_key: str) -> str:
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import Select, WebDriverWait

        el = WebDriverWait(self.browser, self.timeout).until(
            EC.presence_of_element_located(L.field_locator(field_key))
        )
        return Select(el).first_selected_option.text.strip()

    def is_checked(self, field_key: str) -> bool:
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        el = WebDriverWait(self.browser, self.timeout).until(
            EC.presence_of_element_located(L.field_locator(field_key))
        )
        return el.is_selected()

    def read_duration_seconds(self, prefix: str) -> int:
        num = float(self.read_field_value(f"{prefix}[number]"))
        unit = float(self.read_field_value(f"{prefix}[timeunit]"))
        return int(round(num * unit))
