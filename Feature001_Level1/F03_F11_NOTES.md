# Feature 001 – Level 1: remaining groups

## Coverage

| Group | Test case IDs (TC-001-XXX) | Count |
|---|---|---:|
| F03_RICH | 090–094, 136 | 6 |
| F04_IMAGE | 095–100, 137–140 | 10 |
| F05_TAG | 101–103, 141 | 4 |
| F06_FLAGS | 124–128, 146–156 | 16 |
| F07_SELECT | 129–135 | 7 |
| F08_DUP | 108 | 1 |
| F09_CANCEL | 157, 160 | 2 |
| F10_RECOVER | 158 | 1 |
| F11_DENY | 159 | 1 |
| Total new | | 48 |

All IDs are unique; 160 across 11 groups (103 BVA, 42 ECP, 8 DT, 7 UC). F01/F02 datasets and test group scripts are byte-identical to the previous package. Shared runner gains precondition status, optional restricted-session setup and expanded cleanup candidates. New workflow functions live in `test_groups/remaining.py`, with one CSV per group, `pages/extra_fields.py` and `pages/picture_picker.py`. Browser paths/selectors remain Python code, as in Level 1.

## Source traceability and limitations

- Primary source: Feature1-Add-New-User(1).krecorder. Report Project #2, tab t.urt78fzh0es2, provides additional intended inputs for manual upload steps and rich text. See `data/review_f03_f11.csv` for explicit differences. The source has no actual uploaded binary attachments; supplied images are synthetic fixtures, not claimed to be originals.
- TC-001-091–094 HTML from nested XHTML cells: `<p>a</p>` (8 serialized chars) and 49999/50000/50001 total HTML chars. The source retains a description field error for 094. TC-001-136 export has only plain text `Kiểm thử MoodleDòng mới`, but Project #2 explicitly says bold first phrase and newline; CSV preserves original plain text and separately reconstructs HTML with strong/br. The script checks the recorded bold element before submission. It does not independently verify post-save formatting.
- Source TC-001-139 requires file present and thumbnail absent (no submit), while the report allows rejection or no updated avatar. This implementation keeps the narrower recorded oracle; a rejected file may be a FAIL against Katalon, not necessarily an application defect.
- TC-001-095, 096, 097, 137 and 140 verify draft state and source success toast; no independent post-save avatar verification. TC-001-140 may be SKIP at runtime if Delete picture is not rendered for a new user. A report claim of persistence or default avatar must be verified separately.
- TC-001-100, 138, 139, 157, 159 intentionally have no Create user submission. They are not treated as missing-submit defects. Rejection cases require actual picker rejection (not just absence of a file before upload settles). Cancellation checks return link, not independent DB inspection.
- TC-001-108 and 158 use a seed username with dynamic run ID and a distinct second email. TC-001-158 then corrects username and re-enters password. Both seed and recovery username are cleanup candidates; verify actual account before deleting.
- TC-001-150/151 and 125 preserve original password-related expected errors even when local configuration may allow them. No password policy setting is changed.
- New UI selectors based on Katalon and supplied screenshots are not live-verified; if a selector differs on your local Moodle build, collect screenshot and DOM rather than changing Expected Result. TinyMCE uses setContent/save because Katalon editContent supplies HTML. No JavaScript forced form submission.

## F04 – file upload

The workflow clicks the Add (+) control and the `Upload a file` repository; uses Selenium `send_keys(absolute_path)` on the native file input rather than clicking Browse and manipulating the operating-system dialog; clicks `Upload this file`; waits for filepicker close/draft file or explicit rejection. For the second file case it attempts upload if the Add control remains available, otherwise verifies the one-file cap. A file rejection which cannot be detected is an ERROR, not a fabricated PASS.

Included under `fixtures/images/`: valid PNG x2, valid JPEG, plain text TXT and broken PNG (plain text deliberately named `.png`). `python main.py --case TC-001-096` is the recommended first live check. `--timeout 30` can be useful during file operations.

### Size boundary cases (098,099,100)

The screenshot shows Maximum file size: Unlimited. These three cases require a real finite limit M; they are blocked by default. Configure the test environment to a known finite limit (site/course/PHP/repository settings as applicable), confirm the actual widget limit, and set `MOODLE_IMAGE_MAX_BYTES` in `.env` to that same value in bytes. Example only, for M=1 MiB:

```bash
python fixtures/make_size_fixtures.py 1048576
# .env: MOODLE_IMAGE_MAX_BYTES=1048576
python main.py --group F04_IMAGE --dry-run
python main.py --case TC-001-098 --case TC-001-099 --case TC-001-100 --timeout 30
```

Generator uses a valid PNG ancillary chunk to produce exact M−1/M/M+1 bytes; it does not configure Moodle. Verify actual limit separately; an Unlimited banner still causes SKIP at runtime. Exact files can alternatively be placed in `fixtures/images/boundary_minus1.png`, `boundary_max.png`, `boundary_plus1.png`. Generated files may be large; do not include large test assets in submission directly (provide shared location if necessary). Generator supports up to 64 MiB; for larger use independently prepared fixtures.

## F11 – access control

Create a dedicated authenticated ordinary Moodle user on your test instance, with no `moodle/user:create` permission. Do not use an admin, guest or the same account as admin. Add to `.env`:

```
MOODLE_RESTRICTED_USERNAME=restricted_test_user
MOODLE_RESTRICTED_PASSWORD=<local test password>
```

`python main.py --group F11_DENY` opens a new separate browser and logs in with those credentials, then navigates to Add New User. It checks explicit permission-denial feedback and absence of Create user; anonymous redirect does not count as PASS. It does not independently query Admin user list for unexpected accounts. Missing credentials are SKIP. `--manual-login` does not replace restricted credentials for this group.

## Offline validation

21 unittest checks passed including original 11 checks; 160 unique IDs, exact group/technique totals, original source oracles, representative mocked flows, file size generation and restricted login dispatch. Compilation passed. Padded PNGs at 4095/4096/4097 bytes independently decoded using Pillow in the authoring environment; Pillow is not required by runtime. No Selenium browser was run against local Moodle. Default dry-run: 153 runnable, 7 blocked (3 F01 existing, 3 finite-M, 1 restricted account). Runtime preconditions can add SKIP (e.g. Delete picture absent). Historical results retained, not proof of new execution.
