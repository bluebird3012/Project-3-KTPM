# F04 image upload fixes

Based on the 24 November results and screenshots supplied by the tester. No CSV or fixtures changed; other groups retain their original implementation.

- TC-001-137: reacquire visible upload button on stale DOM references; confirm selected local filename via FileList before clicking. Avoid clicking an empty replacement input.
- TC-001-138: inspect visible Moodle error/notification dialogs and explicit file restrictions. Empty selection or timeout alone is not evidence of rejection. If the actual response is not detected, keep ERROR and capture evidence.
- TC-001-139: the original Katalon checks for absence of any `.fp-file img`, but Moodle renders a generic file-type icon for the invalid PNG. The refined semantic oracle distinguishes the generic file icon from a generated draft preview by URL. The actual result records that the original structural assertion would fail. This is an explicit verification correction, not a change to the CSV expectation. Unknown image URLs yield ERROR, generated preview yields FAIL. The original test has no Create user step; no claim is made about the saved account or avatar. A separate post-submit test would be needed for that.

Moodle source reference: https://github.com/moodle/moodle/blob/main/public/lib/filelib.php (file_get_drafarea_files, generic thumbnail vs realthumbnail). Moodle 5.1.7 repository Behat test reference: https://fossies.org/linux/moodle/public/repository/tests/behat/upload_file_type.feature (wrong file type error dialogue).

Retest TC-001-137, TC-001-138, TC-001-139 on the actual Moodle installation. Check for a preexisting username137 before retesting; do not delete unrelated accounts. Then retest successful PNG and one-file limit cases if their test accounts have been cleaned up. No live Selenium execution was performed in the assistant environment.
