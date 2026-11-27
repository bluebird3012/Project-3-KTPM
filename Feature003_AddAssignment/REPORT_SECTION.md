# Feature 003 – Add Assignment (Mạnh Dũng)

## 1. Scope
All Project 2 test cases of feature 003 were re-tested with data-driven automation:
**55 test cases** (BVA 25, ECP 15, decision table 7, use case 8).
Tools: Python 3, Selenium WebDriver 4, unittest, CSV data files. Target: Moodle 5.1.8 (mutms/demo Docker),
account `teacher` (editing teacher of course *Software Testing F3*), `student` for the permission test.

## 2. Level 1 – data-driven testing
Test cases that differ only in their data were grouped; each group became **one** Python script and **one**
CSV data file that contains all inputs **and the expected results**. The script reads every row, runs the
same steps with that row and checks the result against the expected-result columns. Every row is a unittest
sub-test, so a failing row does not stop the others; results are written to `results/results.csv`
with a screenshot per failure.

| Group (script) | Test cases | Data file columns (main) |
|---|---|---|
| Fill the form once (`test_add_assignment_form.py`) | 001–050, 054 (51) | name, description, allow_from, due, cutoff, remind, onlinetext, file, wordlimit, maxfiles, maxsize, grade, gradepass, button, repeat, expected_outcome, expected_page, expected_error_fields, expected_message, expected_count, verify_settings |
| Error, correct, retry (`test_fix_and_retry.py`) | 051, 052, 053 | one row per attempt: changed fields + expected result of that attempt |
| Permission (`test_permission.py`) | 055 (+ control row) | login_as, page, expect_present, expect_absent, expect_text |

The expected results are checked in four ways: the page shown after the click (course / assignment page /
form), the error message next to each field (exact Moodle text), the number of assignments with that name
in the course (proves "saved" / "not saved" / duplicates), and the saved settings read back from the
edit form (`verify_settings`). Shared data (dates, 255/256-character names, Moodle messages) is defined once in
`data/variables.csv`. In Level 1 the site URL, page paths and element locators are written in `moodle_ui.py`.

## 3. Level 2 – data and test items provided to the script
Level 2 uses the same scripts and data files, but **nothing site-specific is in the code**:
* `config/site.csv` – base URL, page paths (course, add-assignment, edit, delete), timeouts;
* `config/locators.csv` – every element used by the scripts (40 entries: text fields, date selectors,
  checkboxes, dropdowns, buttons, error messages, course-page elements) as *element, by (id/css/xpath), value*.
To test another Moodle site or a changed page, only these files are edited.

## 4. Non-functional testing

### NFR-1 Performance (time behaviour)
* **Type:** performance testing – response time of the feature under normal (single-user) load
  (ISO/IEC 25010 *performance efficiency – time behaviour*).
* **Approach:** Selenium measures what the teacher waits for: page load of *Adding a new Assignment* and of
  the course page (browser Navigation Timing API), and the time from clicking *Save and return to course* until
  the course page is loaded, for a minimal and a fully filled form. Each measurement is repeated (5 / 5 / 5 / 3 runs);
  average and slowest run are compared with the limits in `nfr_performance.csv`
  (pages ≤ 3 s average / ≤ 5 s max; saving ≤ 5 s / 8 s – assumed limits, no official requirement exists).
* **Tool:** Python + Selenium WebDriver; every timing is saved in `results/performance_measurements.csv`.

### NFR-2 Security
* **Type:** security testing (ISO/IEC 25010 *security – confidentiality, integrity*; OWASP Top 10:
  A03 injection/XSS, A01 broken access control, CSRF).
* **Approach:** 9 automated, data-driven checks (`nfr_security.csv`): stored XSS payloads in the assignment
  name and in the description (raw HTML, bypassing the editor) – no script may run and no injected element may
  exist on the course and assignment pages; SQL characters in the name are stored literally; the form posted with a
  forged `sesskey` must be refused (CSRF); a student cannot open the add form, cannot open the edit form and cannot
  delete the teacher's assignment; a visitor who is not logged in is sent to the login page.
* **Tool:** Python + Selenium WebDriver (JavaScript alert detection, DOM checks, form tampering with JavaScript).

## 5. Results
<!-- RESULTS START -->

| Part | Checks run | PASS | FAIL | ERROR |
|---|---|---|---|---|
| Level 1 | 56 | 56 | 0 | 0 |
| Level 2 | 56 | 56 | 0 | 0 |
| Non-functional | 13 | 12 | 1 | 0 |

Test cases that did not pass (reason from `results/results.csv`; see README §4 for the analysis):

| Part | ID | Title | Status | Message |
|---|---|---|---|---|
| Non-functional | NFR-SEC-03 | Stored XSS: raw HTML in description | FAIL | 0 != 2 : script / event handler with the payload found on the assignment page |

Performance measurements (seconds):

| NFR | action | average | slowest |
|---|---|---|---|
| NFR-PERF-01 | open_form | 10.82 | 11.63 |
| NFR-PERF-02 | open_course | 6.34 | 6.84 |
| NFR-PERF-03 | save | 13.65 | 15.16 |
| NFR-PERF-04 | save_full | 14.72 | 16.17 |

<!-- RESULTS END -->

## 6. AI Usage Declaration
* **AI tool used:** Claude (Anthropic), model Claude Opus 5.5, used through Claude Code in VS Code.
* **Prompts provided:**
  1. "dựa vào mô tả project 3 sau hãy giúp tôi làm cho feature 3 này luôn và theo form, tham khảo luôn của
     D:\ManhDung\Project3_ImportCalendar_URL" + the Project 3 description and hints (pasted).
  2. "tôi đã bật docker desktop", "expect là một folder giống cái tôi đã gửi nha" *(+ short follow-up questions about progress)*.
* **AI output / review comments:** the Python/Selenium scripts and CSV data files of Level 1, Level 2 and the
  non-functional tests, the setup script, this report section and the README; the grouping of the 55 test cases;
  the reading of the Moodle 5.1.8 source that shows which Project 2 expected results differ from Moodle
  (TC-003-003, 008, 014, 046 – README §4); the diagnosis of the demo-site problems (unfinished installation,
  missing default settings, developer mode making every page take 30–45 s). The AI ran the scripts against
  the local Moodle and reported the results in §5.
  *(Add here what you reviewed, changed and verified yourself before submitting.)*
