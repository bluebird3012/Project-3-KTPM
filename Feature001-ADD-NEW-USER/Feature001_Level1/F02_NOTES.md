# F02_TEXT — Level 1 implementation notes

## Scope

64 cases from the supplied `Feature1-Add-New-User(1).krecorder`: TC-001-030–089 (60 BVA), TC-001-142–145 (4 ECP). The exact source text, including empty values, Unicode, boundary strings, usernames, pre-submit verifyValue expectations and final verifyText expectations, is retained. As in F01, the Katalon email template `${run}` is replaced by `{run_id}`. No HTML locator appears in the execution CSV; semantic targets resolve inside Python.

## Implementation

- `data/f02_text.csv`: shared core columns plus `section`, `text_field`, `text_value`. `none` means no section click was recorded; additional_names and optional represent collapsed section toggles.
- `pages/locators.py`: 12 text input IDs, 2 recorded section selectors and semantic verification targets.
- `pages/add_user_page.py`: `fill_additional_text()` opens the section when the target is not visible, then reuses existing `input_field()` and explicit waits. The City/town and Picture description flows do not record a toggle; if the target is hidden in your actual environment, inspect the DOM and report the traceback before adjusting the selector.
- `test_groups/test_text_fields.py`: one shared workflow, uses F01 pre-submit and final verification helpers. Like F01, a failed pre-submit assertion stops that case before submitting.
- `main.py`: dispatches groups, supports `--case` across groups, `--group` selection, and separate group result folders. A single browser is opened per group when running both groups. `--data` overrides one group only.
- `data/review_f02.csv`: review notes, not changes to the oracle.

## Review flags

TC-001-034 expects all 121 characters before submission and a database error after it. TC-001-039 uses 197 characters (not an assumed 101) and a 197-character verification. TC-001-044 expects 101 characters before submission. These source expectations must not be silently repaired. Other verifyValue cases may expect truncation. There are 12 pre-submit checks in total, 63 expected success toasts and 1 expected database error; these are expected outcomes, not execution statistics.

## Validation

- Python compilation and 11 offline unittest checks (4 inherited, 7 new).
- Mocked workflow for every F02 case verifies correct ordering and exact data passed to page and assertion functions; this is not a real UI test.
- Dry-run: F01 48 rows, 45 runnable / 3 blocked; F02 64 rows, 64 runnable / 0 blocked. No shared usernames between the two groups and all 64 F02 usernames are distinct.
- No live Selenium execution against the user's Moodle. All historical results are from the previous supplied package, not from this version.

## Data repeatability

Fixed usernames are retained. Before rerunning, use a clean isolated Moodle test environment or manually remove only accounts confirmed to have been created by your tests. Do not delete Admin, guest or unrelated accounts. The script still does not perform automated DB cleanup. If upgrading a locally modified version, preserve your .env and latest results separately and merge only the changed/new source files.
