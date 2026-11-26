"""Page Object for Moodle Course Page & Quiz Detail Page verification."""
from __future__ import annotations

import re

from pages import locators as L


def xpath_literal(text: str) -> str:
    """Safely quote an arbitrary string as an XPath 1.0 string literal."""
    if "'" not in text:
        return f"'{text}'"
    if '"' not in text:
        return f'"{text}"'
    parts = text.split("'")
    return "concat(" + ", \"'\", ".join(f"'{p}'" for p in parts) + ")"


def quiz_link_xpath(quiz_name: str) -> str:
    lit = xpath_literal(quiz_name)
    return (
        f"//a[contains(@href,{xpath_literal(L.QUIZ_LINK_HREF_TOKEN)})]"
        f"[normalize-space(.)={lit} or "
        f".//span[contains(concat(' ',normalize-space(@class),' '),' instancename ') "
        f"and normalize-space(text()[1])={lit}]]"
    )


class CoursePage:
    def __init__(self, browser, base_url: str, timeout: int):
        self.browser = browser
        self.base_url = base_url
        self.timeout = timeout

    def wait_course_loaded(self) -> None:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        WebDriverWait(self.browser, self.timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, L.COURSE_PAGE_BODY))
        )

    def wait_quiz_link_and_cmid(self, quiz_name: str) -> str:
        """Wait for the created Quiz link on course page and return its Moodle cmid."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        xp = quiz_link_xpath(quiz_name)
        WebDriverWait(self.browser, self.timeout).until(
            EC.presence_of_element_located((By.XPATH, xp))
        )
        matches = self.browser.find_elements(By.XPATH, xp)
        # Prefer the most recently appended activity link if duplicates exist
        href = matches[-1].get_attribute("href") or ""
        m = re.search(r"[?&]id=(\d+)", href)
        return m.group(1) if m else ""

    def has_quiz_link(self, quiz_name: str) -> bool:
        from selenium.webdriver.common.by import By

        return bool(self.browser.find_elements(By.XPATH, quiz_link_xpath(quiz_name)))

    def has_visible_text(self, text: str) -> bool:
        from selenium.webdriver.common.by import By

        xp = f"//*[normalize-space(text())={xpath_literal(text)}]"
        return any(el.is_displayed() for el in self.browser.find_elements(By.XPATH, xp))

    def wait_quiz_view_page(self, expected_quiz_name: str) -> tuple[str, str]:
        """Wait for Save-and-display destination (`body#page-mod-quiz-view`) and return (heading, cmid)."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        wait = WebDriverWait(self.browser, self.timeout)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, L.QUIZ_VIEW_BODY)))
        xp_h1 = f"//h1[normalize-space(.)={xpath_literal(expected_quiz_name)}]"
        h1 = wait.until(EC.presence_of_element_located((By.XPATH, xp_h1)))
        m = re.search(r"[?&]id=(\d+)", self.browser.current_url or "")
        return (h1.text or "").strip(), (m.group(1) if m else "")
