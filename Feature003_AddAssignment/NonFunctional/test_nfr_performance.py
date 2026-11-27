"""NFR-1 Performance (ISO/IEC 25010 - time behaviour) of Feature 3 Add Assignment.

Data-driven: every row of data/nfr_performance.csv is one measurement:
  action      open_form   - page load of 'Adding a new Assignment' (Navigation Timing API)
              open_course - page load of the course page that lists the assignments
              save        - from the click on 'Save and return to course' until the course page is loaded
              save_full   - same, with description, 4 dates, submission types and grades filled
  runs        number of repetitions
  avg_limit_s / max_limit_s   limits for the average and the slowest run (seconds)
Every single timing is written to results/performance_measurements.csv.
"""
import csv
import os
import time
import unittest

from base_test import RESULTS_DIR, DataDrivenTest

FULL_FORM = {"description": "Performance test description", "allow_from": "2026-12-01 09:00",
             "due": "2026-12-08 09:00", "cutoff": "2026-12-10 09:00", "remind": "2026-12-15 09:00",
             "onlinetext": "yes", "file": "yes", "maxfiles": "5", "grade": "80", "gradepass": "40"}


class TestNfrPerformance(DataDrivenTest):
    DATA_FILE = "nfr_performance.csv"
    KEY = "nfr_id"

    def test_nfr_performance(self):
        self.ui.ensure_user("teacher")
        self.ui.cleanup(["f3_PERF_*"])
        self.run_rows(self.rows, self.run_case)

    @classmethod
    def cleanup_names(cls, r):
        return ["f3_PERF_*"]

    def page_load_seconds(self):
        ms = self.ui.d.execute_script(
            "var n = performance.getEntriesByType('navigation')[0];"
            "return n ? n.loadEventEnd - n.startTime : performance.timing.loadEventEnd - performance.timing.navigationStart;")
        return ms / 1000.0

    def measure(self, r, run):
        ui = self.ui
        if r["action"] == "open_form":
            ui.open_add_form()
            return self.page_load_seconds()
        if r["action"] == "open_course":
            ui.open_course()
            return self.page_load_seconds()
        # save / save_full
        ui.open_add_form()
        data = dict(FULL_FORM) if r["action"] == "save_full" else {}
        data["name"] = f"f3_PERF_{r['nfr_id']}_{run}"
        ui.fill_assignment_form(data, baseline=(r["action"] == "save_full"))
        start = time.perf_counter()
        ui.click_button("save_return")
        seconds = time.perf_counter() - start
        self.assertTrue(ui.on_page("COURSE_PATH") and not ui.visible_errors(),
                        f"assignment was not saved: {ui.visible_errors()} {ui.current_url()}")
        return seconds

    def run_case(self, r):
        times = []
        for run in range(1, int(r["runs"]) + 1):
            seconds = self.measure(r, run)
            times.append(seconds)
            self.save_measurement(r, run, seconds)
        avg, worst = sum(times) / len(times), max(times)
        print(f"    {r['nfr_id']}: avg {avg:.2f}s  max {worst:.2f}s  ({len(times)} runs)")
        problems = []
        if avg > float(r["avg_limit_s"]):
            problems.append(f"average {avg:.2f}s > {r['avg_limit_s']}s")
        if worst > float(r["max_limit_s"]):
            problems.append(f"slowest run {worst:.2f}s > {r['max_limit_s']}s")
        self.assertFalse(problems, f"{'; '.join(problems)} (runs: {', '.join(f'{t:.2f}' for t in times)})")

    def save_measurement(self, r, run, seconds):
        os.makedirs(RESULTS_DIR, exist_ok=True)
        path = os.path.join(RESULTS_DIR, "performance_measurements.csv")
        new = not os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["nfr_id", "action", "run", "seconds"])
            w.writerow([r["nfr_id"], r["action"], run, f"{seconds:.3f}"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
