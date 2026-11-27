"""Group 1 - fill the 'Adding a new Assignment' form once and check the result.

Covers 51 test cases (BVA 001-025, ECP 026-040, Decision table 041-047, UC 048-050, 054)
that share the same steps and differ only in their data:
  1. log in as teacher, open Add an activity > Assignment in the course
  2. fill the fields given by the row (name, description, 4 dates, submission types,
     word limit, max files, max size, maximum grade, grade to pass)
  3. click the button of the row (Save and return to course / Save and display / Cancel)
     - 'repeat' times (TC-003-054 creates the same assignment twice)
  4. check the page, the error messages next to the fields, the number of assignments
     with that name in the course and the saved settings
Data: data/tc_add_assignment_form.csv
"""
import unittest

from base_test import DataDrivenTest


class TestAddAssignmentForm(DataDrivenTest):
    DATA_FILE = "tc_add_assignment_form.csv"

    def test_add_assignment_form(self):
        self.run_rows(self.rows, self.run_case)

    def run_case(self, r):
        ui = self.ui
        ui.ensure_user(r["login_as"] or "teacher")
        ui.cleanup(self.cleanup_names(r))            # precondition: no assignment with this name
        repeat = int(r["repeat"] or 1)
        for attempt in range(1, repeat + 1):
            # Step 1-2: open the form and fill it with the data of the row
            ui.open_add_form()
            ui.fill_assignment_form(r)
            # Step 3: click the button
            ui.click_button(r["button"] or "save_return")
            if attempt < repeat:                     # earlier copies must be saved normally
                self.assertFalse(ui.visible_errors(), f"copy {attempt} was not saved: {ui.visible_errors()}")
        # Step 4: check the result against the expected-result columns
        self.check_result(r)
        self.check_saved(r)


if __name__ == "__main__":
    unittest.main(verbosity=2)
