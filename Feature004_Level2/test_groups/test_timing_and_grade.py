"""Execution workflows for Q03_TIMING (14 cases), Q04_GRADE_APP (20 cases), and Q05_FEEDBACK (6 cases)."""
from __future__ import annotations

from core.data_loader import Case
from core.runner import CaseOutcome
from pages.add_quiz_page import AddQuizPage
from pages.course_page import CoursePage
from test_groups.helpers import verify_standard_outcome


def run_timing_case(browser, base_url: str, case: Case, run_id: str, timeout: int) -> CaseOutcome:
    quiz_page = AddQuizPage(browser, base_url, timeout)
    course_page = CoursePage(browser, base_url, timeout)

    quiz_page.open_add_form()
    quiz_page.expand_all_sections()
    quiz_page.set_name(case["quiz_name"])

    quiz_page.configure_datetime("timeopen", case.json_field("timeopen_json", {}))
    quiz_page.configure_datetime("timeclose", case.json_field("timeclose_json", {}))
    quiz_page.configure_duration("timelimit", case.json_field("timelimit_json", {}))
    if case["overduehandling"].strip():
        quiz_page.set_overduehandling(case["overduehandling"].strip())
    quiz_page.configure_duration("graceperiod", case.json_field("graceperiod_json", {}))

    quiz_page.submit(case["submit_action"])
    return verify_standard_outcome(browser, quiz_page, course_page, case, timeout)


def run_grade_app_case(browser, base_url: str, case: Case, run_id: str, timeout: int) -> CaseOutcome:
    quiz_page = AddQuizPage(browser, base_url, timeout)
    course_page = CoursePage(browser, base_url, timeout)

    quiz_page.open_add_form()
    quiz_page.expand_all_sections()
    quiz_page.set_name(case["quiz_name"])

    if case["gradecat"].strip():
        quiz_page.set_select_field("gradecat", case["gradecat"].strip())
    if case["gradepass"] != "" or case["focus"] == "gradepass_empty":
        quiz_page.set_gradepass(case["gradepass"])
    if case["attempts"].strip():
        quiz_page.set_select_field("attempts", case["attempts"].strip())
    if case["grademethod"].strip():
        quiz_page.set_select_field("grademethod", case["grademethod"].strip())
    if case["decimalpoints"].strip():
        quiz_page.set_select_field("decimalpoints", case["decimalpoints"].strip())

    quiz_page.submit(case["submit_action"])
    return verify_standard_outcome(browser, quiz_page, course_page, case, timeout)


def run_feedback_case(browser, base_url: str, case: Case, run_id: str, timeout: int) -> CaseOutcome:
    quiz_page = AddQuizPage(browser, base_url, timeout)
    course_page = CoursePage(browser, base_url, timeout)

    quiz_page.open_add_form()
    quiz_page.expand_all_sections()
    quiz_page.set_name(case["quiz_name"])

    if case["click_add_feedbacks"].strip().lower() == "yes":
        quiz_page.click_add_feedback_fields()

    if case["boundary_0"] != "":
        quiz_page.set_feedback_boundary(0, case["boundary_0"])
    if case["boundary_1"] != "":
        quiz_page.set_feedback_boundary(1, case["boundary_1"])

    quiz_page.submit(case["submit_action"])
    return verify_standard_outcome(browser, quiz_page, course_page, case, timeout)
