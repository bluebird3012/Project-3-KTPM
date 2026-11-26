# Refactor scope and verification

Structural refactor only: shared modules, page objects, Python locator mapping,
semantic CSV targets, common CLI and reporting. The original F01_CORE execution
order, expected results, input values, skip conditions, timeout handling, click
fallback, credential handling and output format are unchanged for the supplied
48 cases. The original command remains available as a compatibility entry point;
custom CSV files must use the new target-based schema. F02–F11 and Level 2 are not
implemented; no automatic user deletion is added.

Offline verification performed on this refactor:
- Python compilation and the 4 existing offline tests passed.
- Reversing the new semantic targets restores all 48 original CSV rows and all
  original pre-submit check values/locators.
- Dry-run output matched the original for 5 CLI flag/selection combinations.
- Mocked Selenium calls and verification outcomes matched the original across
  144 scenarios (48 rows x 3 simulated conditions). The input and click helpers
  were mocked for this comparison; this is not a browser integration test.
- All 57 historical result files were preserved byte-for-byte. These are prior
  runs, not evidence of live execution of the refactored script.

Live Selenium execution on the user's local Moodle is still required. No actual
PASS/FAIL result is asserted for the refactored version. The `.env`, virtual
environment, IDE metadata and Python caches are excluded from the archive.

AI assistance: ChatGPT performed structural refactoring and offline comparison
of the existing implementation. The user should declare this accurately.
