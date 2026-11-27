# Project 3 – Feature 003 Add Assignment

Data-driven automation (Level 1 and Level 2) and non-functional testing for the
Project 2 test cases of **Moodle 5.1.8 (mutms/demo Docker) – Course › Add an activity › Assignment**.
Tester: Mạnh Dũng. Language: Python + Selenium WebDriver + unittest. Data: CSV.

All **55** Project 2 test cases (TC-003-001 … TC-003-055) are automated.

```
setup/           setup_moodle_data.php - creates the course, teacher and student (preconditions)
Level1/          data-driven: test data + expected results in data/*.csv,
                 site URL, pages and element locators hard-coded in moodle_ui.py
Level2/          data-driven: test data in data/*.csv + site URL/pages in config/site.csv
                 + every element locator in config/locators.csv (no site details in the code)
NonFunctional/   performance + security tests (use the Level 2 helper and config)
REPORT_SECTION.md   text for the team report (approach, NFR description, results, AI usage declaration)
```

## 1. Setup (once)

1. Install Python 3.10+ and Google Chrome, then `pip install -r requirements.txt`
   (Selenium 4 downloads the matching ChromeDriver automatically).
2. Start Moodle: `bin/start` in the mutms/demo folder – site at `http://127.0.0.1:9502`.
3. Create the test course and accounts (run in the mutms/demo folder):
   ```bash
   docker compose exec -T -u www-data webserver php < ../Project3_AddAssignment/setup/setup_moodle_data.php
   ```
   It creates course **Software Testing F3** (id printed as `COURSE_ID`, normally 2),
   `teacher/teacher` (editing teacher) and `student/student` (student).
   If the id is not 2, change `COURSE_ID` in `data/variables.csv` of every folder.
4. Other values (accounts, section, error messages, long names) are in `data/variables.csv`;
   for Level 2 the site URL and pages are in `config/site.csv`, the elements in `config/locators.csv`.

### Environment problems found and fixed on the demo site (26 Nov 2026)
* The database contained only `admin` (no course / teacher / student) → step 3.
* An upgrade was pending and the installation was not finished (`adminsetuppending`, 1047 default
  settings missing, e.g. *Maximum number of uploaded files* had no options) → `php admin/cli/upgrade.php`,
  site name set, `admin_apply_default_settings()` run as admin.
* `dataroot/sessions` points to `/tmp/moodle-sessions` inside the container; after the container is
  recreated create it again: `docker compose exec webserver sh -c "mkdir -p /tmp/moodle-sessions && chmod 777 /tmp/moodle-sessions"`.
* **Speed:** `site/moodle/config.php` sets `$CFG->debug = (E_ALL | 2048)` (developer mode). In developer
  mode Moodle rebuilds its class cache on every request, which takes 30–45 s per page on Docker
  for Windows. The line was commented out (backup `config.php.bak-before-f3`); pages then load in ~1.5 s.
  The opcache settings of the container were also raised (`/usr/local/etc/php/conf.d/99-f3-speed.ini`,
  lost when the container is recreated – not required).

## 2. Run

```bash
cd Level1        && python run_all.py     # 55 test cases (+1 control check)
cd Level2        && python run_all.py     # same test cases, locators/site from config/*.csv
cd NonFunctional && python run_all.py     # 4 performance + 9 security checks
python run_all.py test_fix_and_retry.py   # a single script
```
Options (environment variables): `BROWSER=chrome|firefox|edge`, `HEADLESS=1`,
`ONLY=TC-003-001,TC-003-016` (only these test cases), `KEEP_DATA=1` (keep the created assignments).
Do not run Level 1 and Level 2 at the same time (they use the same assignment names).
Results: `results/results.csv` (one line per test case: PASS/FAIL/ERROR + message),
`results/screenshots/<tc_id>.png` for every failure,
`NonFunctional/results/performance_measurements.csv` (every timing).

Every test case first deletes the assignments it is going to create (precondition
"no assignment with this name exists"); every script deletes them again at the end (CLEANUP-003).

## 3. Test cases → scripts (both levels)

| Script | Data file | Test cases | Shared steps |
|---|---|---|---|
| `test_add_assignment_form.py` | `tc_add_assignment_form.csv` | 001–050, 054 (51) | open *Add an assignment* → fill the fields of the row → click the button of the row (*Save and return* / *Save and display* / *Cancel*, `repeat` times) → check page, error messages, number of assignments with that name, saved settings |
| `test_fix_and_retry.py` | `tc_fix_and_retry.csv` | 051, 052, 053 (3) | submit with an error → correct the field → submit again (one row per attempt) |
| `test_permission.py` | `tc_permission.csv` | 055 (+ control row) | log in as student → course page has no *Edit mode*; the Add assignment URL shows no form |

Input columns: `name, description, allow_from, due, cutoff, remind` (`YYYY-MM-DD HH:MM`, empty = date disabled –
the Project 2 baseline), `onlinetext, file` (yes/no), `wordlimit, maxfiles, maxsize` (`@smallest`/`@largest`),
`grade, gradepass` (`@empty` clears the field), `button, repeat`.
Expected-result columns: `expected_outcome` (success/error/cancelled), `expected_page`,
`expected_error_fields`, `expected_message` (`;` = all of them, `|` = any one), `expected_count`,
`verify_settings` (e.g. `grade=80;gradepass=40`, read back from the edit form of the saved assignment).
Values such as `{DUE}`, `{MSG_DUE}`, `@padto(f3_TC003_002_|A|255)` are defined in `data/variables.csv`.

## 4. Expected failures – Project 2 expectations that differ from Moodle 5.1.8

The expected results were copied from the Project 2 sheet **without changing them**. The Moodle 5.1.8
source (`public/mod/assign/mod_form.php`, `public/course/moodleform_mod.php`,
`public/mod/assign/submission/onlinetext/locallib.php`) explains the failures below. Each one is either
a defect to report or an expected result to correct in the CSV (change the data, not the script).

| TC | Project 2 expectation | Moodle 5.1.8 behaviour |
|---|---|---|
| TC-003-003 | name of 256 characters is cut or refused (limit 255) | the limit is **1333** characters (`maxlength 1333`), 256 characters are saved |
| TC-003-008 | Grade to pass −1 is refused | only "not a number" and "greater than maximum grade" are checked; −1 is saved |
| TC-003-014 | Word limit 0 is refused | 0 is accepted and silently turns the word limit off |
| TC-003-046 | name error **and** grade-to-pass error shown together | the empty name is caught in the browser (client-side rule), the form is not sent, so the server-side grade-to-pass error cannot appear |

Other notes:
* TC-003-024 (Katalon expected success) follows the Project 2 sheet: Moodle refuses a *Remind me to grade by* date before the due date.
* TC-003-047: Moodle shows two errors (due date; cut-off date – "earlier than the allow submissions from date").
* TC-003-055: the *Add an activity* button only exists in edit mode, so the student check relies mainly on the
  *Edit mode* switch and on opening the Add assignment URL directly; the CTRL-055 row proves the switch locator works for the teacher.
* The Katalon scripts of Project 2 used `sectionid=2`; section ids change with every new course, so the
  scripts use the section **number** (`section=1`).
