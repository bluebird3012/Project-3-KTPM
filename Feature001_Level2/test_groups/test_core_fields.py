"""F01_CORE assertions and test workflow."""
from __future__ import annotations

import json
import re

from core.data_loader import Case
from pages.add_user_page import AddUserPage
from pages.locators import locator_tuple, resolve_target


def matching_text(actual: str, expected: str) -> bool:
    actual = actual.strip()
    if expected.startswith("regexp:"):
        return re.search(expected[len("regexp:"):], actual, re.DOTALL) is not None
    return actual == expected.strip()


def verify_pre_submit(browser, checks: list[dict[str, str]]):
    for check in checks:
        raw_locator = resolve_target(check["target"])
        element = browser.find_element(*locator_tuple(raw_locator))

        actual = element.get_attribute("value") or ""
        expected = check["expected"]

        if actual == expected:
            continue

        maxlength = element.get_dom_attribute("maxlength")

        if (
                check.get("allow_maxlength_truncation") is True
                and maxlength is not None
                and maxlength.isdigit()
        ):
            limit = int(maxlength)

            if (
                    len(expected) > limit
                    and len(actual) == limit
                    and actual == expected[:limit]
            ):
                print(
                    f"[INPUT RESTRICTION] {raw_locator}: "
                    f"attempted={len(expected)}, "
                    f"accepted={len(actual)}, "
                    f"maxlength={limit}"
                )
                continue

        raise AssertionError(
            f"Pre-submit value mismatch for {raw_locator}: "
            f"expected {len(expected)} chars, "
            f"got {len(actual)} chars"
        )

def verify_expected(browser, case: Case, timeout: int) -> str:
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.common.exceptions import TimeoutException
    raw_locator = resolve_target(case["expected_target"])
    locator = locator_tuple(raw_locator)
    expected_text = case["expected_text"]
    observed = {"text": ""}

    def condition(d):
        for element in d.find_elements(*locator):
            try:
                if element.is_displayed():
                    text = element.text.strip()
                    observed["text"] = text
                    if matching_text(text, expected_text):
                        return text or "<matched empty>"
            except Exception:
                continue
        return False

    try:
        actual = WebDriverWait(browser, timeout, poll_frequency=0.25).until(condition)
    except TimeoutException as e:
        raise AssertionError(
            f"{case['expected_kind']} not matched. "
            f"Locator={raw_locator}, expected={expected_text!r}, "
            f"last observed={observed['text'][:240]!r}"
        ) from e
    return str(actual)


def run_case(browser, base_url: str, case: Case, run_id: str, timeout: int) -> str:
    """One shared Add New User flow for all F01_CORE CSV rows."""
    page = AddUserPage(browser, base_url, timeout)
    page.open(case)
    page.fill_core_fields(case, run_id)
    verify_pre_submit(browser, json.loads(case["pre_submit_checks_json"] or "[]"))
    page.submit()
    return verify_expected(browser, case, timeout)
