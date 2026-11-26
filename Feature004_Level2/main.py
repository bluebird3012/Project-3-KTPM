"""Entry point for Project #3 Feature 004 (Add Quiz) - Level 2 (all 69 test cases)."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import sys
from uuid import uuid4

from core.config import (
    BASE_URL,
    DEFAULT_TIMEOUT,
    ROOT_DIR,
    get_course_id,
    get_section_id,
    load_local_env,
    protected_local_url,
)
from core.data_loader import read_group_csv
from core.reporter import create_run_directory, finalize_run
from core.runner import run_suite
from core.testing_items import ITEMS, TESTING_ITEMS_RELPATH, TESTING_ITEMS_SHA256
from test_groups.test_decision_usecase import run_decision_case, run_usecase_case
from test_groups.test_name_and_desc import run_desc_case, run_name_case
from test_groups.test_timing_and_grade import (
    run_feedback_case,
    run_grade_app_case,
    run_timing_case,
)

GROUPS = {
    "Q01_NAME": (ROOT_DIR / "data" / "q01_name.csv", run_name_case, "q01"),
    "Q02_DESC": (ROOT_DIR / "data" / "q02_desc.csv", run_desc_case, "q02"),
    "Q03_TIMING": (ROOT_DIR / "data" / "q03_timing.csv", run_timing_case, "q03"),
    "Q04_GRADE_APP": (ROOT_DIR / "data" / "q04_grade_app.csv", run_grade_app_case, "q04"),
    "Q05_FEEDBACK": (ROOT_DIR / "data" / "q05_feedback.csv", run_feedback_case, "q05"),
    "Q06_DECISION": (ROOT_DIR / "data" / "q06_decision.csv", run_decision_case, "q06"),
    "Q07_USECASE": (ROOT_DIR / "data" / "q07_usecase.csv", run_usecase_case, "q07"),
}


def load_all_datasets(selected_groups: list[str], data_override: Path | None = None) -> dict:
    datasets = {}
    seen_ids: set[str] = set()
    for group in selected_groups:
        csv_path = data_override if data_override is not None else GROUPS[group][0]
        cases = read_group_csv(csv_path, group)
        for case in cases:
            if case.case_id in seen_ids:
                raise ValueError(f"Duplicate test_case_id across groups: {case.case_id}")
            seen_ids.add(case.case_id)
        datasets[group] = cases
    return datasets


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_local_env(ROOT_DIR / ".env")

    parser = argparse.ArgumentParser(description="Project #3 Feature 004 (Add Quiz) - Level 2")
    parser.add_argument("--group", action="append", choices=list(GROUPS))
    parser.add_argument("--data", type=Path)
    parser.add_argument("--base-url", default=os.environ.get("MOODLE_BASE_URL", BASE_URL))
    parser.add_argument("--case", action="append", metavar="TC-004-NNN")
    parser.add_argument("--run-id")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--manual-login", action="store_true")
    parser.add_argument("--allow-remote-target", action="store_true")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--results-dir", type=Path, default=ROOT_DIR / "results")
    parser.add_argument("--output-dir", type=Path, help="Optional explicit run output directory")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    groups = list(dict.fromkeys(args.group or list(GROUPS)))
    if args.data and len(groups) != 1:
        parser.error("--data requires a single --group")

    datasets = load_all_datasets(groups, args.data)

    if args.case:
        selected = set(args.case)
        all_known = {c.case_id for cases in datasets.values() for c in cases}
        unknown = selected - all_known
        if unknown:
            parser.error(f"Unknown Test Case IDs: {', '.join(sorted(unknown))}")
        datasets = {
            group: [c for c in cases if c.case_id in selected]
            for group, cases in datasets.items()
        }

    try:
        base_url = protected_local_url(args.base_url, args.allow_remote_target)
    except ValueError as exc:
        parser.error(str(exc))

    if args.timeout < 1:
        parser.error("--timeout must be >= 1")
    if args.manual_login and args.headless and not args.dry_run:
        parser.error("--manual-login requires an interactive browser window")

    run_id = args.run_id or (datetime.now(timezone.utc).strftime("%m%d%H%M") + uuid4().hex[:4])
    if not re.fullmatch(r"[a-z0-9_-]{1,16}", run_id):
        parser.error("--run-id must be 1-16 lowercase letters, digits, _ or -")

    exit_code = 0
    started_utc = datetime.now(timezone.utc).isoformat()
    if args.dry_run:
        output_dir = None
    elif args.output_dir is not None:
        output_dir = args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = create_run_directory(args.results_dir, run_id)

    completed = False
    shared_browser = None

    try:
        total_cases = sum(len(v) for v in datasets.values())
        if args.dry_run:
            print(
                f"Feature 004 Level 2 Dry-Run: {total_cases} cases across "
                f"{sum(bool(v) for v in datasets.values())} groups | "
                f"{len(ITEMS)} testing items ({TESTING_ITEMS_RELPATH}, sha256={TESTING_ITEMS_SHA256[:12]}...)"
            )
        elif total_cases > 0:
            from core.browser import build_browser
            from pages.login_page import prepare_admin_session

            shared_browser = build_browser(args.headless)
            prepare_admin_session(
                shared_browser,
                base_url,
                "manual" if args.manual_login else "auto",
                args.timeout,
            )
        for group, cases in datasets.items():
            if not cases:
                continue
            planned = [(case, "") for case in cases]
            print(f"Feature 004 L2 / {group}: {len(planned)} CSV cases, runnable={len(planned)}, blocked=0", flush=True)
            if args.dry_run:
                for case, _ in planned:
                    print(f"  {case.case_id}: READY [{case['technique']}] {case['focus']} ({case['expected_kind']})")
            else:
                _, execute_case, prefix = GROUPS[group]
                exit_code = max(
                    exit_code,
                    run_suite(
                        planned,
                        args,
                        base_url,
                        run_id,
                        execute_case,
                        prefix,
                        output_dir=output_dir / group,
                        shared_browser=shared_browser,
                    ),
                )
        completed = True
    finally:
        if shared_browser is not None:
            try:
                shared_browser.quit()
            except Exception as quit_error:
                print(f"Warning: WebDriver cleanup: {quit_error}", file=sys.stderr)
        if output_dir is not None:
            finalize_run(
                output_dir,
                datasets,
                run_id,
                base_url,
                started_utc,
                exit_code if completed else None,
                course_id=get_course_id(),
                section_id=get_section_id(),
            )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
