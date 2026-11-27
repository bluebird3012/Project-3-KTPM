"""Offline unit tests for Feature 004 Non-Functional Testing (NFR-07 & NFR-08)."""
from __future__ import annotations

import csv
import unittest

from bs4 import BeautifulSoup

from accessibility.evaluation import (
    evaluate_aria_error_result,
    evaluate_axe_result,
    evaluate_keyboard_result,
    overall_verdict,
)
from core.config import ROOT, local_url
from core.moodle_client import form_values, override
from performance.run_performance import compute_metrics


class TestFeature004NonFunctionalOffline(unittest.TestCase):
    def test_local_url_blocks_remote(self):
        self.assertEqual(local_url("http://127.0.0.1:9502/"), "http://127.0.0.1:9502")
        self.assertEqual(local_url("http://localhost:9502"), "http://localhost:9502")
        with self.assertRaises(ValueError):
            local_url("https://example.com")
        with self.assertRaises(ValueError):
            local_url("http://127.0.0.1:9502/extra?x=1")

    def test_form_values_extracts_hidden_and_overrides(self):
        html = """
        <form class="mform" action="/course/modedit.php" method="post">
            <input type="hidden" name="sesskey" value="abc123" />
            <input type="hidden" name="_qf__mod_quiz_mod_form" value="1" />
            <input type="hidden" name="modulename" value="quiz" />
            <input type="text" name="name" value="" />
            <select name="attempts"><option value="0" selected>Unlimited</option><option value="1">1</option></select>
            <input type="submit" name="submitbutton2" value="Save and return to course" />
        </form>
        """
        form = BeautifulSoup(html, "html.parser").select_one("form")
        vals = form_values(form)
        d = dict(vals)
        self.assertEqual(d["sesskey"], "abc123")
        self.assertEqual(d["_qf__mod_quiz_mod_form"], "1")
        self.assertEqual(d["attempts"], "0")
        self.assertNotIn("submitbutton2", d)

        patched = dict(override(vals, name="nfr4test_1", submitbutton2="Save and return to course"))
        self.assertEqual(patched["name"], "nfr4test_1")
        self.assertEqual(patched["submitbutton2"], "Save and return to course")

    def test_performance_config_csv_schema(self):
        with (ROOT / "performance" / "config.csv").open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 4)
        self.assertEqual([int(r["users"]) for r in rows], [1, 5, 10, 20])
        self.assertTrue(all(int(r["duration_seconds"]) == 60 and int(r["repetitions"]) == 3 for r in rows))

    def test_performance_metrics_pass_and_fail_thresholds(self):
        events = [
            {"event": "attempt", "quiz_name": "q1"},
            {"event": "result", "quiz_name": "q1", "http_ok": True, "status": 200, "response_ms": 800.0, "error": ""},
            {"event": "attempt", "quiz_name": "q2"},
            {"event": "result", "quiz_name": "q2", "http_ok": True, "status": 200, "response_ms": 1200.0, "error": ""},
        ]
        observed = {"q1": [{"cmid": 10}], "q2": [{"cmid": 11}]}
        m_pass = compute_metrics(events, 1, 60, 1, 60.0, 0, observed)
        self.assertEqual(m_pass["verdict"], "PASS")
        self.assertEqual(m_pass["mean_ms"], 1000.0)
        self.assertEqual(m_pass["error_rate_pct"], 0.0)
        self.assertEqual(m_pass["duplicate_quizzes"], 0)

        # Exceed Mean > 2000ms -> FAIL
        slow_events = [
            {"event": "attempt", "quiz_name": "q1"},
            {"event": "result", "quiz_name": "q1", "http_ok": True, "status": 200, "response_ms": 12500.0, "error": ""},
        ]
        m_fail = compute_metrics(slow_events, 5, 60, 1, 60.0, 0, {"q1": [{"cmid": 12}]})
        self.assertEqual(m_fail["verdict"], "FAIL")
        self.assertIn("Mean", m_fail["reason"])

        # Duplicate DB record -> FAIL
        dup_obs = {"q1": [{"cmid": 10}, {"cmid": 13}], "q2": [{"cmid": 11}]}
        m_dup = compute_metrics(events, 5, 60, 1, 60.0, 0, dup_obs)
        self.assertEqual(m_dup["verdict"], "FAIL")
        self.assertEqual(m_dup["duplicate_quizzes"], 1)

    def test_accessibility_scenarios_csv_and_evaluator(self):
        with (ROOT / "accessibility" / "scenarios.csv").open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual([r["scenario_id"] for r in rows], ["ACC-01", "ACC-02", "ACC-03", "ACC-04", "ACC-05"])

        axe_clean = {"violations": [], "passes": [{"id": "label"}], "incomplete": []}
        s_pass, v_pass = evaluate_axe_result("ACC-01", "Default", axe_clean)
        self.assertEqual(s_pass["verdict"], "PASS")
        self.assertEqual(v_pass, [])

        axe_serious = {
            "violations": [
                {"id": "color-contrast", "impact": "serious", "help": "Contrast", "helpUrl": "u", "nodes": [{"target": ["#x"]}]}
            ],
            "passes": [],
            "incomplete": [],
        }
        s_fail, v_fail = evaluate_axe_result("ACC-02", "Expanded", axe_serious)
        self.assertEqual(s_fail["verdict"], "FAIL")
        self.assertEqual(s_fail["serious_nodes"], 1)
        self.assertEqual(s_fail["color_contrast_nodes"], 1)
        self.assertEqual(len(v_fail), 1)

        kb_pass = evaluate_keyboard_result("ACC-04", "Tab", ["id_a", "id_b"], {"id_a", "id_b"}, False, 10)
        self.assertEqual(kb_pass["verdict"], "PASS")
        kb_fail = evaluate_keyboard_result("ACC-04", "Tab", ["id_a", "id_b"], {"id_a"}, False, 10)
        self.assertEqual(kb_fail["verdict"], "FAIL")

        aria_pass = evaluate_aria_error_result("ACC-05", "ARIA", [{"field": "id_name", "associated": True}])
        self.assertEqual(aria_pass["verdict"], "PASS")
        self.assertEqual(overall_verdict([s_pass, kb_pass, aria_pass]), "PASS")
        self.assertEqual(overall_verdict([s_pass, s_fail, aria_pass]), "FAIL")


if __name__ == "__main__":
    unittest.main()
