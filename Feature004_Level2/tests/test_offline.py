"""Offline unit tests for Feature 004 (Add Quiz) - Level 2 (core + reporting)."""
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
from core.testing_items import TESTING_ITEMS_RELPATH, TESTING_ITEMS_SHA256
from pages.course_page import quiz_link_locator, xpath_literal
from test_groups.helpers import matches_expected


class TestFeature004Level2Offline(unittest.TestCase):
    def test_all_69_cases_present_unique_and_balanced(self):
        datasets = cli_main.load_all_datasets(list(cli_main.GROUPS))
        all_cases = [c for cases in datasets.values() for c in cases]
        ids = [c.case_id for c in all_cases]
        expected_ids = [f"TC-004-{i:03d}" for i in range(1, 70)]

        self.assertEqual(len(all_cases), 69)
        self.assertEqual(sorted(ids), expected_ids)
        self.assertEqual(dict(Counter(c["technique"] for c in all_cases)), {"BVA": 28, "ECP": 24, "DT": 9, "UC": 8})

    def test_duplicate_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "dup.csv"
            src = (ROOT_DIR / "data" / "q01_name.csv").read_text(encoding="utf-8-sig").splitlines()
            p.write_text("\n".join([src[0], src[1], src[1]]) + "\n", encoding="utf-8-sig")
            with self.assertRaisesRegex(ValueError, "Duplicate test_case_id"):
                read_group_csv(p, "Q01_NAME")

    def test_protected_local_url(self):
        self.assertEqual(protected_local_url("http://127.0.0.1:9502/"), "http://127.0.0.1:9502")
        with self.assertRaises(ValueError):
            protected_local_url("https://moodle.example.com", allow_remote=False)

    def test_locator_template_and_matching(self):
        by, xp = quiz_link_locator("f4_004_R01")
        self.assertEqual(by, "xpath")
        self.assertIn("/mod/quiz/view.php", xp)
        self.assertIn("'f4_004_R01'", xp)
        self.assertEqual(xpath_literal("it's"), '"it\'s"')
        self.assertTrue(matches_expected(r"regexp:\S", "Maximum of 1333 characters"))

    def test_dry_run_cli_succeeds(self):
        self.assertEqual(cli_main.main(["--dry-run"]), 0)

    def test_unified_results_records_level2_metadata(self):
        datasets = cli_main.load_all_datasets(["Q01_NAME"])
        cases = datasets["Q01_NAME"]
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = create_run_directory(Path(tmp), "ut02")
            grp_dir = run_dir / "Q01_NAME"
            grp_dir.mkdir()
            rows = [
                {
                    "test_case_id": cases[0].case_id,
                    "technique": cases[0]["technique"],
                    "focus": cases[0]["focus"],
                    "run_id": "ut02",
                    "status": "PASS",
                    "duration_seconds": "1.000",
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
            finalize_group_results(grp_dir, rows, "ut02", "http://127.0.0.1:9502", [(c, "") for c in cases])
            finalize_run(
                run_dir,
                datasets,
                "ut02",
                "http://127.0.0.1:9502",
                "2026-11-26T00:00:00+00:00",
                0,
                course_id=2,
                section_id=2,
            )
            info = json.loads((run_dir / "run_info.json").read_text(encoding="utf-8"))
            self.assertEqual(info["level"], 2)
            self.assertEqual(info["testing_items_file"], TESTING_ITEMS_RELPATH)
            self.assertEqual(info["testing_items_sha256"], TESTING_ITEMS_SHA256)
            self.assertEqual(len(info["testing_items_sha256"]), 64)
            with (run_dir / "summary.csv").open(encoding="utf-8-sig", newline="") as handle:
                summary_rows = list(csv.DictReader(handle))
            self.assertEqual(summary_rows[-1]["group"], "TOTAL")


if __name__ == "__main__":
    unittest.main()
