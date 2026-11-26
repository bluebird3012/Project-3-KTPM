"""CSV loading, F01 validation and test data expansion."""
from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from pathlib import Path
import re


@dataclass(frozen=True)
class Case:
    values: dict[str, str]

    @property
    def case_id(self) -> str:
        return self.values["test_case_id"]

    def __getitem__(self, key: str) -> str:
        return self.values[key]


def read_cases(path: Path, *, extra_kinds=()) -> list[Case]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "test_case_id", "technique", "focus", "authentication", "username",
            "first_name", "last_name", "email", "new_password", "password_entry",
            "first_name_entry", "last_name_entry", "pre_submit_checks_json",
            "expected_kind", "expected_target", "expected_text",
            "source_has_submit", "fixture_required", "review_tags",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Data file is missing CSV columns: {sorted(missing)}")
        rows = [Case(dict(row)) for row in reader]
    ids = [case.case_id for case in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate test_case_id values in CSV")
    for case in rows:
        if not re.fullmatch(r"TC-001-\d{3}", case.case_id):
            raise ValueError(f"Invalid case ID: {case.case_id}")
        if case["expected_kind"] not in {"success", "field_error", "system_error", *extra_kinds}:
            raise ValueError(f"Unexpected result kind in {case.case_id}")
        if case["authentication"] != "manual":
            raise ValueError(f"F01_CORE assumes manual authentication: {case.case_id}")
        for field in ("new_password", "first_name", "last_name"):
            mode_key = "password_entry" if field == "new_password" else field + "_entry"
            if case[mode_key] not in {"omit", "type", "send_keys"}:
                raise ValueError(f"Unsupported entry mode for {case.case_id}: {case[mode_key]}")
        checks = json.loads(case["pre_submit_checks_json"] or "[]")
        if not isinstance(checks, list) or any(
                not isinstance(x, dict) or not {"target", "expected"} <= x.keys()
                for x in checks
        ):
            raise ValueError(f"Invalid pre-submit checks in {case.case_id}")
    return rows


def resolve_data(value: str, run_id: str) -> str:
    """Only expand the single supported test email template."""
    return value.replace("{run_id}", run_id)
