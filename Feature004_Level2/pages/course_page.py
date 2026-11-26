"""Page Object for Moodle Course Page & Quiz Detail Page - Level 2 (config-driven)."""
from __future__ import annotations

import re

from pages import locators as L


def xpath_literal(text: str) -> str:
    if "'" not in text:
        return f"'{text}'"
    if '"' not in text:
        return f'"{text}"'
    parts = text.split("'")
    return "concat(" + ", \"'\", ".join(f"'{p}'" for p in parts) + ")"


def quiz_link_locator(quiz_name: str) -> tuple[str, str]:
    return L.item_template(
        "VERIFICATION.quiz_link_xpath",
        href_token=xpath_literal(L.QUIZ_LINK_HREF_TOKEN),
        instance_class=xpath_literal(f" {L.QUIZ_INSTANCE_CLASS_TOKEN} "),
        quiz_name=xpath_literal(quiz_name),
    )


class CoursePage:
    def __init__(self, browser, base_url: str, timeout: int):
        self.browser = browser
        self.base_url = base_url
        self.timeout = timeout

    def wait_course_loaded(self) -> None:
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        WebDriverWait(self.browser, self.timeout).until(
            EC.presence_of_element_located(L.item("VERIFICATION.course_page_body"))
        )

    def wait_quiz_link_and_cmid(self, quiz_name: str) -> str:
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        loc = quiz_link_locator(quiz_name)
        WebDriverWait(self.browser, self.timeout).until(EC.presence_of_element_located(loc))
        matches = self.browser.find_elements(*loc)
        href = matches[-1].get_attribute("href") or ""
        m = re.search(r"[?&]id=(\d+)", href)
        return m.group(1) if m else ""

    def has_quiz_link(self, quiz_name: str) -> bool:
        return bool(self.browser.find_elements(*quiz_link_locator(quiz_name)))

    def has_visible_text(self, text: str) -> bool:
        loc = L.item_template("VERIFICATION.visible_text_xpath", text=xpath_literal(text))
        return any(el.is_displayed() for el in self.browser.find_elements(*loc))

    def wait_quiz_view_page(self, expected_quiz_name: str) -> tuple[str, str]:
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        wait = WebDriverWait(self.browser, self.timeout)
        wait.until(EC.presence_of_element_located(L.item("VERIFICATION.quiz_view_body")))
        h1_loc = L.item_template("VERIFICATION.quiz_view_h1_xpath", quiz_name=xpath_literal(expected_quiz_name))
        h1 = wait.until(EC.presence_of_element_located(h1_loc))
        m = re.search(r"[?&]id=(\d+)", self.browser.current_url or "")
        return (h1.text or "").strip(), (m.group(1) if m else "")
