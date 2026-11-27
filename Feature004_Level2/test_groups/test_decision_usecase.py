"""Execution workflows for Q06_DECISION (9 cases) and Q07_USECASE (8 cases)."""
from __future__ import annotations

from core.data_loader import Case
from core.runner import CaseOutcome
from pages.add_quiz_page import AddQuizPage
from pages.course_page import CoursePage
from test_groups.helpers import (
    apply_input_dict,
    verify_field_errors,
    verify_standard_outcome,
    wait_course_or_validation_error,
)


def run_decision_case(browser, base_url: str, case: Case, run_id: str, timeout: int) -> CaseOutcome:
    quiz_page = AddQuizPage(browser, base_url, timeout)
    course_page = CoursePage(browser, base_url, timeout)

    quiz_page.open_add_form()
    quiz_page.expand_all_sections()
    quiz_page.set_name(case["quiz_name"])

    quiz_page.configure_datetime("timeopen", case.json_field("timeopen_json", {}))
    quiz_page.configure_datetime("timeclose", case.json_field("timeclose_json", {}))
    quiz_page.configure_duration("timelimit", case.json_field("timelimit_json", {}))
    if case["attempts"].strip():
        quiz_page.set_select_field("attempts", case["attempts"].strip())
    if case["gradepass"] != "":
        quiz_page.set_gradepass(case["gradepass"])

    quiz_page.submit(case["submit_action"])
    return verify_standard_outcome(browser, quiz_page, course_page, case, timeout)


def run_usecase_case(browser, base_url: str, case: Case, run_id: str, timeout: int) -> CaseOutcome:
    quiz_page = AddQuizPage(browser, base_url, timeout)
    course_page = CoursePage(browser, base_url, timeout)
    kind = case["expected_kind"]

    quiz_page.open_add_form()
    quiz_page.expand_all_sections()

    initial_inputs = case.json_field("initial_inputs_json", {})
    if initial_inputs:
        apply_input_dict(quiz_page, initial_inputs)
    else:
        quiz_page.set_name(case["quiz_name"])

    quiz_page.submit(case["submit_action"])

    if kind in {"course_quiz_present", "quiz_view_page", "course_quiz_absent"}:
        return verify_standard_outcome(browser, quiz_page, course_page, case, timeout)

    if kind in {"recover_then_save", "error_then_cancel"}:
        err_target = case["initial_error_target"].strip()
        err_summary = verify_field_errors(quiz_page, [err_target], case["expected_text"])
        # Re-expand sections in case server-side validation reload collapsed them
        quiz_page.expand_all_sections()

        recovery_inputs = case.json_field("recovery_inputs_json", {})
        if recovery_inputs:
            apply_input_dict(quiz_page, recovery_inputs)

        second_action = case["second_action"].strip()
        quiz_page.submit(second_action)

        if kind == "recover_then_save":
            state, err2 = wait_course_or_validation_error(browser, quiz_page, course_page, timeout)
            if state == "error":
                raise AssertionError(f"Recovery submission still failed with validation error: {err2}")
            cmid = course_page.wait_quiz_link_and_cmid(case["quiz_name"])
            return CaseOutcome(
                actual=f"{err_summary} -> Recovered & saved quiz (cmid={cmid})",
                attempted_quiz_name=case["quiz_name"],
                created_cmid=cmid,
            )

        # error_then_cancel
        course_page.wait_course_loaded()
        if course_page.has_quiz_link(case["quiz_name"]):
            raise AssertionError(
                f"Expected quiz {case['quiz_name']!r} absent after error+Cancel, but link exists"
            )
        return CaseOutcome(
            actual=f"{err_summary} -> Cancelled cleanly; quiz {case['quiz_name']!r} absent",
            attempted_quiz_name=case["quiz_name"],
            created_cmid="",
        )

    raise ValueError(f"Unsupported expected_kind in Q07_USECASE: {kind!r}")
