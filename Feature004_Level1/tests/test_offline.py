"""Offline unit tests for Feature 004 (Add Quiz) - Level 1.

Runs without a browser or live Moodle server to verify:
- Complete 69-case coverage (TC-004-001..TC-004-069, 28 BVA / 24 ECP / 9 DT / 8 UC)
- CSV schema integrity, duplicate/invalid detection
- Local URL safety checks
- XPath escaping & expected-text matching
- Unified results aggregation & CLI --dry-run
"""
from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path
import tempfile
import unittest

import main as cli_main
from core.config import ROOT_DIR, protected_local_url
from core.data_loader import read_group_csv
from core.reporter import create_run_directory, finalize_group_results, finalize_run
from pages.course_page import quiz_link_xpath, xpath_literal
from test_groups.helpers import matches_expected


class TestFeature004Level1Offline(unittest.TestCase):
    def test_all_69_cases_present_unique_and_balanced(self):
        datasets = cli_main.load_all_datasets(list(cli_main.GROUPS))
        all_cases = [c for cases in datasets.values() for c in cases]
        ids = [c.case_id for c in all_cases]
        expected_ids = [f"TC-004-{i:03d}" for i in range(1, 70)]

        self.assertEqual(len(all_cases), 69)
        self.assertEqual(sorted(ids), expected_ids)

        tech_counts = Counter(c["technique"] for c in all_cases)
        self.assertEqual(dict(tech_counts), {"BVA": 28, "ECP": 24, "DT": 9, "UC": 8})

        group_counts = {g: len(cases) for g, cases in datasets.items()}
        self.assertEqual(
            group_counts,
            {
                "Q01_NAME": 9,
                "Q02_DESC": 3,
                "Q03_TIMING": 14,
                "Q04_GRADE_APP": 20,
                "Q05_FEEDBACK": 6,
                "Q06_DECISION": 9,
                "Q07_USECASE": 8,
            },
        )

    def test_special_cases_payloads(self):
        datasets = cli_main.load_all_datasets(list(cli_main.GROUPS))
        by_id = {c.case_id: c for cases in datasets.values() for c in cases}

        # TC-004-006 (1333) and TC-004-007 (1334 + extra 'A')
        self.assertEqual(len(by_id["TC-004-006"]["quiz_name"]), 1333)
        self.assertEqual(len(by_id["TC-004-007"]["quiz_name"]), 1334)
        self.assertEqual(by_id["TC-004-007"]["extra_send_keys"], "A")
        self.assertEqual(len(by_id["TC-004-007"]["expected_present_name"]), 1333)
        self.assertEqual(len(by_id["TC-004-007"]["expected_absent_name"]), 1334)

        # TC-004-050..052 use add_feedback_fields
        for cid in ("TC-004-050", "TC-004-051", "TC-004-052"):
            self.assertEqual(by_id[cid]["click_add_feedbacks"], "yes")

        # TC-004-061 expects two simultaneous error targets
        self.assertEqual(
            by_id["TC-004-061"].json_field("expected_targets_json", []),
            ["timeclose_error", "gradepass_error"],
        )

        # TC-004-065..069 recovery / error-cancel flows
        for cid in ("TC-004-065", "TC-004-066", "TC-004-067", "TC-004-068"):
            self.assertEqual(by_id[cid]["expected_kind"], "recover_then_save")
            self.assertTrue(by_id[cid]["initial_error_target"])
            self.assertEqual(by_id[cid]["second_action"], "save_return")
        self.assertEqual(by_id["TC-004-069"]["expected_kind"], "error_then_cancel")
        self.assertEqual(by_id["TC-004-069"]["second_action"], "cancel")

    def test_duplicate_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "dup.csv"
            src = (ROOT_DIR / "data" / "q01_name.csv").read_text(encoding="utf-8-sig").splitlines()
            p.write_text("\n".join([src[0], src[1], src[1]]) + "\n", encoding="utf-8-sig")
            with self.assertRaisesRegex(ValueError, "Duplicate test_case_id"):
                read_group_csv(p, "Q01_NAME")

    def test_protected_local_url(self):
        self.assertEqual(protected_local_url("http://127.0.0.1:9502/"), "http://127.0.0.1:9502")
        self.assertEqual(protected_local_url("http://localhost:9502"), "http://localhost:9502")
        with self.assertRaises(ValueError):
            protected_local_url("https://moodle.example.com", allow_remote=False)
        self.assertEqual(
            protected_local_url("https://moodle.example.com/", allow_remote=True),
            "https://moodle.example.com",
        )

    def test_xpath_and_matching_helpers(self):
        self.assertEqual(xpath_literal("simple"), "'simple'")
        self.assertEqual(xpath_literal("it's"), '"it\'s"')
        self.assertIn("/mod/quiz/view.php", quiz_link_xpath("f4_004_R01"))
        self.assertTrue(matches_expected(r"regexp:\S", "You must supply a value here."))
        self.assertFalse(matches_expected(r"regexp:\S", "   "))
        self.assertTrue(matches_expected("Exact", "Exact"))

    def test_dry_run_cli_succeeds(self):
        code = cli_main.main(["--dry-run"])
        self.assertEqual(code, 0)

    def test_unified_results_aggregation(self):
        datasets = cli_main.load_all_datasets(["Q01_NAME"])
        cases = datasets["Q01_NAME"]
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = create_run_directory(Path(tmp), "ut01")
            grp_dir = run_dir / "Q01_NAME"
            grp_dir.mkdir()
            rows = [
                {
                    "test_case_id": cases[0].case_id,
                    "technique": cases[0]["technique"],
                    "focus": cases[0]["focus"],
                    "run_id": "ut01",
                    "status": "PASS",
                    "duration_seconds": "1.234",
                    "expected_kind": cases[0]["expected_kind"],
                    "expected_text": cases[0]["expected_text"],
                    "actual_result_or_error": "OK",
                    "review_tags": "",
                    "attempted_quiz_name": "",
                    "created_cmid": "",
                    "screenshot": "",
                    "traceback_file": "",
                }
            ]
            finalize_group_results(grp_dir, rows, "ut01", "http://127.0.0.1:9502", [(c, "") for c in cases])
            finalize_run(
                run_dir,
                datasets,
                "ut01",
                "http://127.0.0.1:9502",
                "2026-11-25T00:00:00+00:00",
                0,
                course_id=2,
                section_id=2,
            )
            info = json.loads((run_dir / "run_info.json").read_text(encoding="utf-8"))
            self.assertEqual(info["level"], 1)
            self.assertEqual(info["counts"]["PASS"], 1)
            self.assertEqual(info["not_recorded"], len(cases) - 1)
            with (run_dir / "summary.csv").open(encoding="utf-8-sig", newline="") as handle:
                summary_rows = list(csv.DictReader(handle))
            self.assertEqual(summary_rows[-1]["group"], "TOTAL")
            self.assertEqual(int(summary_rows[-1]["total"]), len(cases))


if __name__ == "__main__":
    unittest.main()
