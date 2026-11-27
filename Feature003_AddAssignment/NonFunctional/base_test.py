"""Base class shared by all test scripts (one browser per script).

Every row of a data file is run as a unittest sub-test, so one failing row does not
stop the others. Results are appended to results/results.csv and a screenshot is
saved for every failed row.

Expected-result columns understood by check_result():
  expected_outcome       success | error | cancelled
  expected_page          course | assignment | form       (page shown after the click)
  expected_error_fields  name;grade;gradepass;due;cutoff;remind;allow_from;wordlimit
  expected_message       messages that must be shown; ';' = all of them, '|' = any one of these
  expected_count         number of assignments with this name in the course afterwards
  verify_settings        values the saved assignment must have, e.g. grade=80;gradepass=40
"""
import csv
import datetime
import os
import sys
import time
import traceback
import unittest

from data_loader import DATA_DIR, any_of, load_cases, parse_pairs, split_list
from moodle_ui import MoodleUI, create_driver, contains_any, norm, same_value

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
PAGES = {"course": "COURSE_PATH", "assignment": "ASSIGNMENT_VIEW_PATH", "form": "FORM_PATH"}
for _stream in (sys.stdout, sys.stderr):        # Vietnamese names on a Windows console
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


class DataDrivenTest(unittest.TestCase):
    DATA_FILE = None            # set by each script
    KEY = "tc_id"

    @classmethod
    def setUpClass(cls):
        cls.rows, cls.vars = load_cases(cls.DATA_FILE, DATA_DIR)
        accounts = {role: (cls.vars.get(f"{role.upper()}_USER"), cls.vars.get(f"{role.upper()}_PASSWORD"))
                    for role in ("teacher", "student", "admin")}
        cls.ui = MoodleUI(create_driver(), accounts, cls.vars.get("COURSE_ID"), cls.vars.get("SECTION", "1"))
        cls.all_cleanup = []
        for r in cls.rows:
            cls.all_cleanup += cls.cleanup_names(r)

    @classmethod
    def tearDownClass(cls):
        try:
            if os.environ.get("KEEP_DATA", "0") != "1" and cls.all_cleanup:
                cls.ui.ensure_user("teacher")
                cls.ui.cleanup(cls.all_cleanup)       # clean-up script (CLEANUP-003)
        finally:
            cls.ui.d.quit()

    @staticmethod
    def cleanup_names(r):
        """Assignments deleted before the test case (precondition) and after the script."""
        names = split_list(r.get("cleanup_names", ""))
        if not names and norm(r.get("name", "")):
            names = [r["name"]]
        return names

    # ------------------------------------------------------------------ runner
    def run_rows(self, rows, run_one):
        only = split_list(os.environ.get("ONLY", ""), ",")
        for row in rows:
            key = row[self.KEY]
            if only and key not in only and row.get("tc_id") not in only:
                continue
            with self.subTest(tc=key, title=row.get("title", "")):
                started = time.time()
                status, message = "PASS", ""
                try:
                    run_one(row)
                except AssertionError as e:
                    status, message = "FAIL", str(e)
                    raise
                except Exception as e:
                    status, message = "ERROR", f"{type(e).__name__}: {e}"
                    traceback.print_exc()
                    raise
                finally:
                    if status != "PASS":
                        self.ui.screenshot(os.path.join(RESULTS_DIR, "screenshots", f"{key}.png"))
                    self.record(key, row.get("title", ""), status, message, time.time() - started)

    def record(self, tc_id, title, status, message, seconds):
        os.makedirs(RESULTS_DIR, exist_ok=True)
        path = os.path.join(RESULTS_DIR, "results.csv")
        new = not os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["time", "script", "tc_id", "title", "status", "seconds", "message"])
            w.writerow([datetime.datetime.now().isoformat(timespec="seconds"), type(self).__name__,
                        tc_id, title, status, f"{seconds:.1f}", message.replace("\n", " ")[:500]])
        print(f"  {tc_id:<12} {status:<5} {seconds:6.1f}s  {title}" + (f"  -> {message[:200]}" if message else ""),
              flush=True)

    # ------------------------------------------------------------------ shared checks
    def check_result(self, r, name=None):
        """Compares the page shown after the click with the expected-result columns of row r."""
        ui = self.ui
        name = r.get("name", "") if name is None else name
        problems = []
        outcome = r.get("expected_outcome", "")
        errors = ui.visible_errors()
        if outcome == "success" and errors:
            problems.append(f"expected success but the form shows errors {errors}")
        if outcome in ("error",) and not errors:
            problems.append(f"expected an error but no error message is shown (page {ui.current_url()})")
        page = r.get("expected_page") or {"success": "course", "error": "form", "cancelled": "course"}.get(outcome)
        if page and not ui.on_page(PAGES[page]):
            problems.append(f"expected the {page} page but the browser shows {ui.current_url()}")
        if page == "assignment" and norm(name) and not any(norm(name) == h for h in ui.heading_texts()):
            problems.append(f"assignment page heading is {ui.heading_texts()[:3]}, expected '{name[:60]}'")
        for field in split_list(r.get("expected_error_fields", "")):
            if not ui.field_error(field):
                problems.append(f"no error message shown next to field '{field}'")
        shown = " ".join(errors) or ui.page_text()
        for message in split_list(r.get("expected_message", "")):
            if not contains_any(shown, any_of(message)):
                problems.append(f"message '{message}' not shown (shown: {errors[:4]})")
        self.assertFalse(problems, "; ".join(problems))

    def check_saved(self, r, name=None):
        """expected_count + verify_settings (opens the course page / the edit form)."""
        name = r.get("name", "") if name is None else name
        if r.get("expected_count", "") != "" and norm(name):
            cmids = self.ui.find_activities(name, reload=not self.ui.on_page("COURSE_PATH"))
            self.assertEqual(int(r["expected_count"]), len(cmids),
                             f"number of assignments named '{name[:60]}' in the course")
        expected = parse_pairs(r.get("verify_settings", ""))
        if expected:
            cmids = self.ui.find_activities(name, reload=not self.ui.on_page("COURSE_PATH"))
            self.assertTrue(cmids, f"assignment '{name[:60]}' not found, cannot verify its settings")
            actual = self.ui.read_settings(cmids[-1], list(expected))
            wrong = {k: f"{actual[k]!r} (expected {v!r})" for k, v in expected.items() if not same_value(v, actual[k])}
            self.assertFalse(wrong, f"saved settings differ: {wrong}")
