"""CSV loading, schema validation, and case dataclass for Feature 004 Level 1."""
from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from pathlib import Path
import re

VALID_TECHNIQUES = {"BVA", "ECP", "DT", "UC"}
VALID_SUBMIT_ACTIONS = {"save_return", "save_display", "cancel"}
VALID_EXPECTED_KINDS = {
    "course_quiz_present",
    "course_quiz_present_and_reopen",
    "quiz_view_page",
    "course_quiz_absent",
    "field_error",
    "recover_then_save",
    "error_then_cancel",
}

COMMON_REQUIRED_COLUMNS = {
    "test_case_id",
    "technique",
    "focus",
    "quiz_name",
    "submit_action",
    "expected_kind",
    "expected_targets_json",
    "expected_text",
    "reopen_checks_json",
    "review_tags",
}

GROUP_EXTRA_COLUMNS = {
    "Q01_NAME": {"extra_send_keys", "expected_present_name", "expected_absent_name"},
    "Q02_DESC": {"description_text", "show_description", "course_desc_expectation"},
    "Q03_TIMING": {
        "timeopen_json",
        "timeclose_json",
        "timelimit_json",
        "overduehandling",
        "graceperiod_json",
    },
    "Q04_GRADE_APP": {"gradecat", "gradepass", "attempts", "grademethod", "decimalpoints"},
    "Q05_FEEDBACK": {"click_add_feedbacks", "boundary_0", "boundary_1"},
    "Q06_DECISION": {
        "dt_rule",
        "timeopen_json",
        "timeclose_json",
        "timelimit_json",
        "attempts",
        "gradepass",
    },
    "Q07_USECASE": {
        "uc_path",
        "initial_inputs_json",
        "initial_error_target",
        "recovery_inputs_json",
        "second_action",
    },
}


@dataclass(frozen=True)
class Case:
    values: dict[str, str]

    @property
    def case_id(self) -> str:
        return self.values["test_case_id"]

    def __getitem__(self, key: str) -> str:
        return self.values[key]

    def get(self, key: str, default: str = "") -> str:
        return self.values.get(key, default)

    def json_field(self, key: str, default):
        raw = self.values.get(key, "").strip()
        if not raw:
            return default
        return json.loads(raw)


def read_group_csv(path: Path, group_name: str) -> list[Case]:
    if group_name not in GROUP_EXTRA_COLUMNS:
        raise ValueError(f"Unknown group: {group_name}")
    required = COMMON_REQUIRED_COLUMNS | GROUP_EXTRA_COLUMNS[group_name]
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing = required - fieldnames
        if missing:
            raise ValueError(f"{path.name} missing required CSV columns: {sorted(missing)}")
        rows: list[Case] = []
        for idx, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"Malformed CSV row {idx} in {path.name}")
            rows.append(Case(dict(row)))

    ids = [c.case_id for c in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate test_case_id in {path.name}")

    for case in rows:
        if not re.fullmatch(r"TC-004-\d{3}", case.case_id):
            raise ValueError(f"Invalid test_case_id: {case.case_id}")
        if case["technique"] not in VALID_TECHNIQUES:
            raise ValueError(f"Invalid technique in {case.case_id}: {case['technique']!r}")
        if case["submit_action"] not in VALID_SUBMIT_ACTIONS:
            raise ValueError(f"Invalid submit_action in {case.case_id}: {case['submit_action']!r}")
        if case["expected_kind"] not in VALID_EXPECTED_KINDS:
            raise ValueError(f"Invalid expected_kind in {case.case_id}: {case['expected_kind']!r}")

        targets = case.json_field("expected_targets_json", [])
        if not isinstance(targets, list) or not all(isinstance(t, str) for t in targets):
            raise ValueError(f"Invalid expected_targets_json in {case.case_id}")

        reopen_checks = case.json_field("reopen_checks_json", [])
        if not isinstance(reopen_checks, list) or any(
            not isinstance(item, dict) or not {"field", "mode"} <= set(item.keys())
            for item in reopen_checks
        ):
            raise ValueError(f"Invalid reopen_checks_json in {case.case_id}")

        # Validate any additional *_json columns parse cleanly as JSON objects
        for col in GROUP_EXTRA_COLUMNS[group_name]:
            if col.endswith("_json") and case[col].strip():
                parsed = json.loads(case[col])
                if not isinstance(parsed, dict):
                    raise ValueError(f"{col} must be a JSON object in {case.case_id}")

    return rows
