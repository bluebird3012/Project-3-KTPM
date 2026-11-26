"""Entry point for the implemented Feature 001 Level 2 groups."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
import json
from pathlib import Path
import re
import sys
from uuid import uuid4

from core.config import ROOT_DIR, BASE_URL, DATA_FILE, load_local_env, protected_local_url
from core.data_loader import Case, read_cases
from core.runner import run_suite
from core.reporter import create_run_directory, finalize_run
from test_groups.test_core_fields import run_case
from test_groups.test_text_fields import read_text_cases, run_case as run_text_case

from test_groups import remaining as R
from pages.locators import resolve_target

GROUPS = {
    "F01_CORE": (DATA_FILE, read_cases, run_case, "f01"),
    "F02_TEXT": (ROOT_DIR / "data" / "f02_text.csv", read_text_cases, run_text_case, "f02"),
    "F03_RICH": (ROOT_DIR / "data/f03_rich.csv", R.read_remaining, R.run_rich, "f03"),
    "F04_IMAGE": (ROOT_DIR / "data/f04_image.csv", R.read_remaining, R.run_image, "f04"),
    "F05_TAG": (ROOT_DIR / "data/f05_tag.csv", R.read_remaining, R.run_tags, "f05"),
    "F06_FLAGS": (ROOT_DIR / "data/f06_flags.csv", R.read_remaining, R.run_flags, "f06"),
    "F07_SELECT": (ROOT_DIR / "data/f07_select.csv", R.read_remaining, R.run_select, "f07"),
    "F08_DUP": (ROOT_DIR / "data/f08_dup.csv", R.read_remaining, R.run_duplicate, "f08"),
    "F09_CANCEL": (ROOT_DIR / "data/f09_cancel.csv", R.read_remaining, R.run_cancel, "f09"),
    "F10_RECOVER": (ROOT_DIR / "data/f10_recover.csv", R.read_remaining, R.run_recovery, "f10"),
    "F11_DENY": (ROOT_DIR / "data/f11_deny.csv", R.read_remaining, R.run_denial, "f11"),
}


def main(argv: list[str] | None = None, *, default_groups=None) -> int:
    load_local_env(ROOT_DIR / ".env")
    parser = argparse.ArgumentParser(description="Project #3 Feature 001 Level 2")
    parser.add_argument("--group", action="append", choices=list(GROUPS), help="Repeat to select groups; defaults to all implemented groups")
    parser.add_argument("--data", type=Path, help="Override CSV for a single group (defaults to F01_CORE if no group selected)")
    parser.add_argument("--base-url", default=os.environ.get("MOODLE_BASE_URL", BASE_URL))
    parser.add_argument("--case", action="append", metavar="TC-001-NNN", help="May be repeated")
    parser.add_argument("--run-id", help="Stable run ID used only for generated test emails")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--manual-login", action="store_true")
    parser.add_argument("--allow-remote-target", action="store_true")
    parser.add_argument("--include-fixtures", action="store_true", help="Only after preparing duplicate email fixture")
    parser.add_argument("--repair-missing-submit", action="store_true", help="Explicitly repair TC-001-006")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--results-dir", type=Path, default=ROOT_DIR / "results")
    parser.add_argument("--dry-run", action="store_true", help="Validate CSV and list cases, without Selenium")
    args = parser.parse_args(argv)
    groups = list(dict.fromkeys(args.group or (['F01_CORE'] if args.data else default_groups or GROUPS)))
    if args.data and len(groups) != 1:
        parser.error("--data requires a single group")
    datasets = {}
    for group in groups:
        path, loader, _, _ = GROUPS[group]
        try:
            cases = loader(args.data or path)
            for case in cases:
                targets = [case["expected_target"], *(c["target"] for c in json.loads(case["pre_submit_checks_json"] or "[]"))]
                if case.values.get("intermediate_target"):
                    targets.append(case["intermediate_target"])
                for target in targets:
                    try:
                        resolve_target(target)
                    except (KeyError, ValueError) as error:
                        raise ValueError(f"{case.case_id}: invalid testing target {target!r}") from error
            datasets[group] = cases
        except (ValueError, OSError, KeyError) as error:
            parser.error(str(error))
    if args.case:
        selected = set(args.case)
        unknown = selected - {case.case_id for cases in datasets.values() for case in cases}
        if unknown:
            parser.error(f"Unknown Test Case IDs: {', '.join(sorted(unknown))}")
        datasets = {group: [case for case in cases if case.case_id in selected]
                    for group, cases in datasets.items()}
    try:
        base_url = protected_local_url(args.base_url, args.allow_remote_target)
    except ValueError as e:
        parser.error(str(e))
    if args.timeout < 1:
        parser.error("--timeout must be >= 1")
    if args.manual_login and args.headless and not args.dry_run:
        parser.error("Manual login requires an interactive Chrome window")
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%m%d%H%M") + uuid4().hex[:4]
    if not re.fullmatch(r"[a-z0-9_-]{1,16}", run_id):
        parser.error("run-id must be 1-16 lowercase letters, numbers, _ or -")

    def skip_reason(case: Case, group: str) -> str:
        if group == "F01_CORE" and case["source_has_submit"] != "yes" and not args.repair_missing_submit:
            return "Original Katalon has no Create user submit; pass --repair-missing-submit only after review"
        if case["fixture_required"] == "yes" and not args.include_fixtures:
            return "Requires existing f1_existing@example.com account; use --include-fixtures after seeding"
        return R.preflight(case) if group not in {"F01_CORE", "F02_TEXT"} else ""

    exit_code = 0
    started_utc = datetime.now(timezone.utc).isoformat()
    output_dir = None if args.dry_run else create_run_directory(args.results_dir, run_id)
    completed = False
    try:
        for group, cases in datasets.items():
            if not cases:
                continue
            planned = [(case, skip_reason(case, group)) for case in cases]
            print(f"Feature 001 / {group}: {len(planned)} CSV cases, "
                  f"runnable={sum(not x[1] for x in planned)}, blocked={sum(bool(x[1]) for x in planned)}")
            if args.dry_run:
                for case, why in planned:
                    print(f"  {case.case_id}: {'SKIP - ' + why if why else 'READY'}  "
                          f"[{case['focus']}] {case['expected_kind']}")
            else:
                _, _, execute_case, prefix = GROUPS[group]
                kwargs = {"prepare_session": R.prepare_restricted_session} if group == "F11_DENY" else {}
                exit_code = max(exit_code, run_suite(
                    planned, args, base_url, run_id, execute_case, prefix,
                    output_dir=output_dir / group, **kwargs))
        completed = True
    finally:
        if output_dir is not None:
            finalize_run(output_dir, datasets, run_id, base_url, started_utc,
                         exit_code if completed else None)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
