"""Execution workflows for Q01_NAME (9 cases) and Q02_DESC (3 cases)."""
from __future__ import annotations

from core.data_loader import Case
from core.runner import CaseOutcome
from pages.add_quiz_page import AddQuizPage
from pages.course_page import CoursePage
from test_groups.helpers import (
    verify_reopen_checks,
    verify_standard_outcome,
    wait_course_or_validation_error,
)


def run_name_case(browser, base_url: str, case: Case, run_id: str, timeout: int) -> CaseOutcome:
    quiz_page = AddQuizPage(browser, base_url, timeout)
    course_page = CoursePage(browser, base_url, timeout)

    quiz_page.open_add_form()
    quiz_page.set_name(case["quiz_name"], extra_send_keys=case["extra_send_keys"])
    quiz_page.submit(case["submit_action"])

    present_name = case["expected_present_name"] or case["quiz_name"]
    absent_name = case["expected_absent_name"] or None
    return verify_standard_outcome(
        browser,
        quiz_page,
        course_page,
        case,
        timeout,
        present_name=present_name,
        absent_name=absent_name,
    )


def run_desc_case(browser, base_url: str, case: Case, run_id: str, timeout: int) -> CaseOutcome:
    quiz_page = AddQuizPage(browser, base_url, timeout)
    course_page = CoursePage(browser, base_url, timeout)

    quiz_page.open_add_form()
    quiz_page.expand_all_sections()
    quiz_page.set_name(case["quiz_name"])

    desc_text = case["description_text"]
    if desc_text:
        quiz_page.set_description(desc_text)

    show_flag = case["show_description"].strip().lower()
    if show_flag == "check":
        quiz_page.set_show_description(True)
    elif show_flag == "uncheck":
        quiz_page.set_show_description(False)

    quiz_page.submit(case["submit_action"])

    state, err_detail = wait_course_or_validation_error(browser, quiz_page, course_page, timeout)
    if state == "error":
        raise AssertionError(f"Expected quiz creation with description, got validation error: {err_detail}")

    cmid = course_page.wait_quiz_link_and_cmid(case["quiz_name"])
    course_desc_expect = case["course_desc_expectation"].strip().lower()
    if course_desc_expect == "present":
        if not course_page.has_visible_text(desc_text):
            raise AssertionError(f"Expected description {desc_text!r} visible on course page, but not found")
    elif course_desc_expect == "absent":
        if course_page.has_visible_text(desc_text):
            raise AssertionError(f"Expected description {desc_text!r} hidden on course page, but visible")

    reopen_checks = case.json_field("reopen_checks_json", [])
    reopen_msg = verify_reopen_checks(quiz_page, cmid, reopen_checks)
    return CaseOutcome(
        actual=f"Created quiz (cmid={cmid}); course_desc={course_desc_expect}; {reopen_msg}",
        attempted_quiz_name=case["quiz_name"],
        created_cmid=cmid,
    )
