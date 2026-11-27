"""Group 3 - who may add an assignment (UC-08, TC-003-055).

One row per check: log in as the given user, open a page and check which elements are
present / absent and which text is shown. The CTRL row runs the same check as the
teacher, to show that the locators used for the 'absent' checks really find the elements.
Data: data/tc_permission.csv
"""
import unittest

from base_test import DataDrivenTest
from data_loader import any_of, split_list
from moodle_ui import contains_any, loc

PAGES = {"course": "COURSE_PAGE", "add_form": "ADD_ASSIGNMENT_PAGE"}


class TestPermission(DataDrivenTest):
    DATA_FILE = "tc_permission.csv"
    KEY = "check_id"

    def test_permission(self):
        self.run_rows(self.rows, self.run_case)

    def run_case(self, r):
        ui = self.ui
        ui.ensure_user(r["login_as"])
        ui.go(PAGES[r["page"]])
        problems = []
        for key in split_list(r["expect_present"]):
            if not ui.exists(loc(key)):
                problems.append(f"'{key}' should be shown but is not")
        for key in split_list(r["expect_absent"]):
            if ui.is_displayed(loc(key)):
                problems.append(f"'{key}' should NOT be shown for {r['login_as']}")
        if r["expect_text"] and not contains_any(ui.page_text(), any_of(r["expect_text"])):
            problems.append(f"text '{r['expect_text']}' not shown on {ui.current_url()}")
        if r["expect_url_contains"] and r["expect_url_contains"] not in ui.current_url():
            problems.append(f"URL is {ui.current_url()}, expected it to contain '{r['expect_url_contains']}'")
        self.assertFalse(problems, "; ".join(problems))


if __name__ == "__main__":
    unittest.main(verbosity=2)
