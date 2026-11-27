"""Group 2 - exception flows: submit with an error, correct the field, submit again.

Covers TC-003-051 (name empty), TC-003-052 (due date before allow submissions from),
TC-003-053 (grade to pass greater than maximum grade). One data row per attempt:
attempt 1 fills the whole form (baseline), the next attempts only change the
non-empty cells. Every attempt has its own expected result.
Data: data/tc_fix_and_retry.csv
"""
import unittest
from collections import OrderedDict

from base_test import DataDrivenTest


class TestFixAndRetry(DataDrivenTest):
    DATA_FILE = "tc_fix_and_retry.csv"

    def test_fix_and_retry(self):
        cases = OrderedDict()
        for r in self.rows:
            cases.setdefault(r["tc_id"], []).append(r)
        self.run_rows([dict(attempts[0], attempts=attempts) for attempts in cases.values()], self.run_case)

    def run_case(self, case):
        ui = self.ui
        attempts = sorted(case["attempts"], key=lambda a: int(a["attempt"]))
        final_name = next((a["name"] for a in reversed(attempts) if a["name"]), "")
        ui.ensure_user(case["login_as"] or "teacher")
        ui.cleanup(self.cleanup_names(case) or [final_name])
        ui.open_add_form()
        name = ""
        for a in attempts:
            name = a["name"] or name
            ui.fill_assignment_form(a, baseline=(a["attempt"] == "1"))
            ui.click_button(a["button"] or "save_return")
            try:
                self.check_result(a, name=name)
            except AssertionError as e:
                raise AssertionError(f"attempt {a['attempt']}: {e}") from None
        self.check_saved(attempts[-1], name=final_name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
