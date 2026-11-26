"""Shared verification and input-application helpers for Feature 004 Level 2."""
from __future__ import annotations

import re
from typing import Any

from core.data_loader import Case
from core.runner import CaseOutcome
from pages import locators as L
from pages.add_quiz_page import AddQuizPage
from pages.course_page import CoursePage


def matches_expected(expected: str, actual: str) -> bool:
    if expected.startswith("regexp:"):
        return re.search(expected[7:], actual) is not None
    return actual == expected


def verify_field_errors(quiz_page: AddQuizPage, targets: list[str], expected_text: str) -> str:
    if not targets:
        raise AssertionError("No error targets configured for field_error case")
    observed: list[str] = []
    for target in targets:
        text = quiz_page.wait_for_field_error(target)
        if expected_text and not matches_expected(expected_text, text):
            raise AssertionError(
                f"Validation error at {target} did not match {expected_text!r}; got {text!r}"
            )
        observed.append(f"{target}={text!r}")
    if not quiz_page.is_on_quiz_form():
        raise AssertionError("Expected to remain on Add Quiz form after validation error")
    return "Validation error observed: " + "; ".join(observed)


def verify_reopen_checks(quiz_page: AddQuizPage, cmid: str, checks: list[dict[str, Any]]) -> str:
    if not cmid:
        raise AssertionError("Cannot reopen quiz for persistence check: missing cmid")
    quiz_page.open_edit_form(cmid)
    quiz_page.expand_all_sections()
    verified: list[str] = []
    for chk in checks:
        field = chk["field"]
        mode = chk["mode"]
        expected = chk.get("expected", "")
        if mode == "value":
            actual = quiz_page.read_field_value(field)
            if actual != str(expected):
                raise AssertionError(f"Reopen check {field} expected {expected!r}, got {actual!r}")
            verified.append(f"{field}={actual}")
        elif mode == "regex_value":
            actual = quiz_page.read_field_value(field)
            if not re.search(str(expected), actual):
                raise AssertionError(f"Reopen check {field} did not match /{expected}/, got {actual!r}")
            verified.append(f"{field}={actual}")
        elif mode == "checked":
            if not quiz_page.is_checked(field):
                raise AssertionError(f"Reopen check {field} expected checked, got unchecked")
            verified.append(f"{field}=checked")
        elif mode == "unchecked":
            if quiz_page.is_checked(field):
                raise AssertionError(f"Reopen check {field} expected unchecked, got checked")
            verified.append(f"{field}=unchecked")
        elif mode == "selected_label":
            actual = quiz_page.read_selected_label(field)
            if actual != str(expected):
                raise AssertionError(f"Reopen check {field} label expected {expected!r}, got {actual!r}")
            verified.append(f"{field}={actual}")
        elif mode == "duration_seconds":
            actual = quiz_page.read_duration_seconds(field)
            if actual != int(expected):
                raise AssertionError(f"Reopen check {field} duration expected {expected}s, got {actual}s")
            verified.append(f"{field}={actual}s")
        elif mode == "rich_text":
            actual = quiz_page.get_description_text()
            if actual != str(expected):
                raise AssertionError(f"Reopen check description expected {expected!r}, got {actual!r}")
            verified.append(f"description={actual!r}")
        else:
            raise ValueError(f"Unsupported reopen check mode: {mode!r}")
    return f"Reopen cmid={cmid} OK ({len(verified)} checks)"


def wait_course_or_validation_error(
    browser,
    quiz_page: AddQuizPage,
    course_page: CoursePage,
    timeout: int,
) -> tuple[str, str]:
    from selenium.common.exceptions import StaleElementReferenceException
    from selenium.webdriver.support.ui import WebDriverWait

    course_loc = L.item("VERIFICATION.course_page_body")
    error_locs = {key: L.error_locator(key) for key in L.ERROR_ITEM_KEYS}

    def probe(driver):
        if driver.find_elements(*course_loc):
            return ("course", "")
        for key, loc in error_locs.items():
            for el in driver.find_elements(*loc):
                try:
                    txt = (el.text or "").strip()
                    if txt:
                        return ("error", f"{key}: {txt}")
                except StaleElementReferenceException:
                    continue
        return False

    return WebDriverWait(browser, timeout, poll_frequency=0.25).until(
        probe,
        message="Timed out waiting for course page redirect or form validation error",
    )


def verify_standard_outcome(
    browser,
    quiz_page: AddQuizPage,
    course_page: CoursePage,
    case: Case,
    timeout: int,
    *,
    present_name: str | None = None,
    absent_name: str | None = None,
) -> CaseOutcome:
    kind = case["expected_kind"]
    quiz_name = present_name if present_name is not None else case["quiz_name"]

    if kind == "field_error":
        targets = case.json_field("expected_targets_json", [])
        detail = verify_field_errors(quiz_page, targets, case["expected_text"])
        return CaseOutcome(actual=detail, attempted_quiz_name=case["quiz_name"], created_cmid="")

    if kind in {"course_quiz_present", "course_quiz_present_and_reopen"}:
        state, err_detail = wait_course_or_validation_error(browser, quiz_page, course_page, timeout)
        if state == "error":
            raise AssertionError(
                f"Expected quiz creation on course page, but Moodle rejected submission with {err_detail}"
            )
        cmid = course_page.wait_quiz_link_and_cmid(quiz_name)
        if absent_name and course_page.has_quiz_link(absent_name):
            raise AssertionError(f"Unexpected quiz link found for absent_name (len={len(absent_name)})")
        summary = f"Created quiz on course page (cmid={cmid})"
        if kind == "course_quiz_present_and_reopen":
            reopen_checks = case.json_field("reopen_checks_json", [])
            reopen_msg = verify_reopen_checks(quiz_page, cmid, reopen_checks)
            summary = f"{summary}; {reopen_msg}"
        return CaseOutcome(actual=summary, attempted_quiz_name=quiz_name, created_cmid=cmid)

    if kind == "quiz_view_page":
        heading, cmid = course_page.wait_quiz_view_page(quiz_name)
        return CaseOutcome(
            actual=f"Opened quiz detail page h1={heading!r} (cmid={cmid})",
            attempted_quiz_name=quiz_name,
            created_cmid=cmid,
        )

    if kind == "course_quiz_absent":
        course_page.wait_course_loaded()
        if course_page.has_quiz_link(quiz_name):
            raise AssertionError(f"Expected quiz {quiz_name!r} NOT to exist after Cancel, but link is present")
        return CaseOutcome(
            actual=f"Returned to course page; quiz {quiz_name!r} absent as expected",
            attempted_quiz_name=quiz_name,
            created_cmid="",
        )

    raise ValueError(f"Unhandled expected_kind in standard verifier: {kind!r}")


def apply_input_dict(quiz_page: AddQuizPage, payload: dict[str, Any]) -> None:
    if "name" in payload:
        quiz_page.set_name(str(payload["name"]))
    if "timeopen" in payload:
        quiz_page.configure_datetime("timeopen", payload["timeopen"])
    if "timeclose" in payload:
        quiz_page.configure_datetime("timeclose", payload["timeclose"])
    if "timelimit" in payload:
        quiz_page.configure_duration("timelimit", payload["timelimit"])
    if "overduehandling" in payload:
        quiz_page.set_overduehandling(str(payload["overduehandling"]))
    if "graceperiod" in payload:
        quiz_page.configure_duration("graceperiod", payload["graceperiod"])
    if "gradepass" in payload:
        quiz_page.set_gradepass(str(payload["gradepass"]))
    if "attempts" in payload:
        quiz_page.set_select_field("attempts", str(payload["attempts"]))
    if "grademethod" in payload:
        quiz_page.set_select_field("grademethod", str(payload["grademethod"]))
    if "decimalpoints" in payload:
        quiz_page.set_select_field("decimalpoints", str(payload["decimalpoints"]))
    if "feedbackboundaries[0]" in payload:
        quiz_page.set_feedback_boundary(0, str(payload["feedbackboundaries[0]"]))
    if "feedbackboundaries[1]" in payload:
        quiz_page.set_feedback_boundary(1, str(payload["feedbackboundaries[1]"]))
