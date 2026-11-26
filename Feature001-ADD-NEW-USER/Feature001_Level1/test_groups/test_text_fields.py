"""F02_TEXT: one data-driven workflow for the 12 additional text fields."""
from __future__ import annotations

import json
from pathlib import Path

from core.data_loader import Case, read_cases
from pages.add_user_page import AddUserPage
from pages.locators import TEXT_FIELD_IDS
from test_groups.test_core_fields import verify_expected, verify_pre_submit

# These logical sections describe the recorded workflow, not HTML locators.
FIELD_SECTIONS = {
    "city": "none", "image_alt": "none",
    "first_name_phonetic": "additional_names",
    "last_name_phonetic": "additional_names",
    "middle_name": "additional_names", "alternate_name": "additional_names",
    "id_number": "optional", "institution": "optional", "department": "optional",
    "address": "optional", "phone": "optional", "mobile_phone": "optional",
}


def read_text_cases(path: Path) -> list[Case]:
    """Validate shared data and the three additional F02 columns."""
    cases = read_cases(path)
    for case in cases:
        if not {"section", "text_field", "text_value"} <= case.values.keys():
            raise ValueError(f"Missing additional text columns in {case.case_id}")
        field = case["text_field"]
        if field not in TEXT_FIELD_IDS or case["section"] != FIELD_SECTIONS[field]:
            raise ValueError(f"Invalid text field or section in {case.case_id}")
        if not isinstance(case["text_value"], str):
            raise ValueError(f"Missing text value in {case.case_id}")
        for check in json.loads(case["pre_submit_checks_json"] or "[]"):
            if check["target"] != field or not isinstance(check["expected"], str):
                raise ValueError(f"Invalid additional field check in {case.case_id}")
        if (case["expected_kind"], case["expected_target"]) not in {
            ("success", "success_message"), ("system_error", "system_error")
        }:
            raise ValueError(f"Invalid final verification in {case.case_id}")
    return cases


def run_case(browser, base_url: str, case: Case, run_id: str, timeout: int) -> str:
    page = AddUserPage(browser, base_url, timeout)
    page.open(case)
    page.fill_core_fields(case, run_id)
    page.fill_additional_text(case["text_field"], case["text_value"], case["section"])
    verify_pre_submit(browser, json.loads(case["pre_submit_checks_json"] or "[]"))
    page.submit()
    return verify_expected(browser, case, timeout)
