"""NFR-2 Security (ISO/IEC 25010 - confidentiality / integrity, OWASP Top 10) of Feature 3.

Data-driven: every row of data/nfr_security.csv is one check; the column 'check' selects the steps:
  xss_name         teacher saves an assignment whose NAME is a script payload, then the course page and
                   the assignment page are opened: no JavaScript alert may run, no injected element may exist
  xss_description  same with the DESCRIPTION (raw HTML put into the editor's textarea, bypassing TinyMCE)
  sql_name         name with SQL characters is stored literally and the course page still works
  csrf             the form is posted with a forged sesskey: it must be refused, nothing is created
  access_add       user 'login_as' (student / guest) opens the Add assignment URL: no form may be shown
  access_edit      the teacher creates an assignment, 'login_as' opens its edit URL: no form may be shown
  access_delete    the teacher creates an assignment, 'login_as' calls its delete URL with his own sesskey:
                   the assignment must still exist
Expected results are columns: expect_text (any of a|b), expect_url_contains, expect_count.
"""
import unittest

from base_test import DataDrivenTest
from data_loader import any_of
from moodle_ui import contains_any, loc

MARK = "f3xss"     # id of the element the XSS payloads try to inject


class TestNfrSecurity(DataDrivenTest):
    DATA_FILE = "nfr_security.csv"
    KEY = "nfr_id"

    def test_nfr_security(self):
        self.run_rows(self.rows, self.run_case)

    def no_script_ran(self, where):
        ui = self.ui
        ui.accept_alerts()
        # dangerous = a <script> or an event-handler attribute that still carries the payload
        injected = self.ui.d.execute_script(
            "var m = arguments[0], n = 0;"
            "document.querySelectorAll('script').forEach(function (e) { if (e.textContent.indexOf(m) >= 0) n++; });"
            "document.querySelectorAll('*').forEach(function (e) { for (var i = 0; i < e.attributes.length; i++) {"
            "  var at = e.attributes[i]; if (at.name.indexOf('on') === 0 && at.value.indexOf(m) >= 0) n++; } });"
            "return n;", MARK)
        self.assertEqual([], ui.alerts, f"JavaScript alert executed on {where}: {ui.alerts}")
        self.assertEqual(0, injected, f"script / event handler with the payload found on {where}")

    def create_as_teacher(self, r, raw_description=False):
        ui = self.ui
        ui.ensure_user("teacher")
        ui.cleanup(self.cleanup_names(r))
        ui.open_add_form()
        ui.fill_assignment_form({"name": r["name"]})
        if raw_description:
            self.ui.d.execute_script(
                "if (window.tinymce && tinymce.get('id_introeditor')) { tinymce.get('id_introeditor').remove(); }"
                "var t = document.querySelector(arguments[0]); t.style.display='block'; t.value = arguments[1];",
                "#" + loc("form.description_textarea")[1], r["payload"])
        ui.click_button("save_display" if raw_description else "save_return")
        prefix = self.cleanup_names(r)[0].rstrip("*")      # Moodle may strip the HTML from the name
        return ui.find_activities(prefix, "startswith")

    def run_case(self, r):
        ui = self.ui
        ui.alerts.clear()
        check = r["check"]
        if check in ("xss_name", "xss_description"):
            cmids = self.create_as_teacher(r, raw_description=(check == "xss_description"))
            self.assertTrue(cmids, "assignment with the payload was not saved (cannot check the output)")
            self.no_script_ran("the course page")
            ui.go(ui.url("ASSIGNMENT_VIEW_PATH") + f"?id={cmids[-1]}")
            self.no_script_ran("the assignment page")
        elif check == "sql_name":
            self.create_as_teacher(r)
            self.assertEqual(1, len(ui.find_activities(r["name"])), "name with SQL characters was not stored literally")
        elif check == "csrf":
            ui.ensure_user("teacher")
            ui.cleanup(self.cleanup_names(r))
            ui.open_add_form()
            ui.fill_assignment_form({"name": r["name"]})
            self.ui.d.execute_script(          # forge the CSRF token of the form
                "var v = arguments[1]; document.querySelectorAll('form ' + arguments[0])"
                ".forEach(function (e) { e.value = v; });", loc("form.sesskey")[1], r["payload"])
            ui.click_button("save_return")
            self.check_expectations(r)
            ui.ensure_user("teacher")
            self.assertEqual(0, ui.count_activities(r["name"]) if ui.on_page("COURSE_PATH") else
                             len(ui.find_activities(r["name"])), "assignment was created with a forged sesskey")
            return
        elif check == "access_add":
            ui.ensure_user(r["login_as"])
            ui.go("ADD_ASSIGNMENT_PAGE")
            self.assertFalse(ui.is_displayed(loc("form.name")), f"{r['login_as']} can open the Add assignment form")
        elif check in ("access_edit", "access_delete"):
            cmids = self.create_as_teacher(r)
            self.assertTrue(cmids, "target assignment was not created")
            ui.ensure_user(r["login_as"])
            if check == "access_edit":
                ui.go("EDIT_ACTIVITY_PAGE", cmid=cmids[-1])
                self.assertFalse(ui.is_displayed(loc("form.name")), f"{r['login_as']} can open the edit form")
            else:
                ui.open_course()
                ui.delete_activity(cmids[-1])
                self.check_expectations(r)
                ui.ensure_user("teacher")
                self.assertEqual(1, len(ui.find_activities(r["name"])), f"{r['login_as']} could delete the assignment")
                return
        else:
            raise ValueError(f"unknown check '{check}'")
        self.check_expectations(r)

    def check_expectations(self, r):
        ui = self.ui
        if r["expect_text"]:
            self.assertTrue(contains_any(ui.page_text(), any_of(r["expect_text"])),
                            f"text '{r['expect_text']}' not shown on {ui.current_url()}")
        if r["expect_url_contains"]:
            self.assertIn(r["expect_url_contains"], ui.current_url(), "unexpected page")


if __name__ == "__main__":
    unittest.main(verbosity=2)
