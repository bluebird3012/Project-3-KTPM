"""Shared sequential execution engine and status classification."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sys
import time
import traceback

from core.browser import build_browser
from core.preconditions import PreconditionMissing
from core.reporter import finalize_group_results, safe_screenshot
from pages.login_page import prepare_admin_session


@dataclass(frozen=True)
class CaseOutcome:
    actual: str
    attempted_quiz_name: str = ""
    created_cmid: str = ""


def run_suite(
    planned,
    args,
    base_url: str,
    run_id: str,
    execute_case,
    group_prefix: str,
    *,
    prepare_session=prepare_admin_session,
    output_dir: Path | None = None,
    shared_browser=None,
) -> int:
    started_utc = datetime.now(timezone.utc).isoformat()
    if output_dir is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_dir = args.results_dir / f"{group_prefix}_{stamp}_{run_id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir = output_dir / "screenshots"
    screenshot_dir.mkdir(exist_ok=True)
    trace_dir = output_dir / "tracebacks"
    trace_dir.mkdir(exist_ok=True)

    results: list[dict[str, str]] = []
    owns_browser = shared_browser is None
    browser = shared_browser
    failures = 0

    try:
        if any(not why for _, why in planned) and browser is None:
            browser = build_browser(args.headless)
            prepare_session(
                browser,
                base_url,
                "manual" if args.manual_login else "auto",
                args.timeout,
            )
        for case, why in planned:
            start = time.monotonic()
            status, actual, screenshot, traceback_file = "SKIP", why, "", ""
            attempted_name = case.get("quiz_name", "") if not why else ""
            created_cmid = ""
            if not why:
                try:
                    outcome = execute_case(browser, base_url, case, run_id, args.timeout)
                    if isinstance(outcome, CaseOutcome):
                        actual = outcome.actual
                        attempted_name = outcome.attempted_quiz_name or attempted_name
                        created_cmid = outcome.created_cmid
                    else:
                        actual = str(outcome)
                    status = "PASS"
                except PreconditionMissing as exc:
                    status, actual = "SKIP", str(exc)
                except AssertionError as exc:
                    status, actual = "FAIL", f"{type(exc).__name__}: {exc}"
                    traceback_file = str(trace_dir / f"{case.case_id}.txt")
                    Path(traceback_file).write_text(traceback.format_exc(), encoding="utf-8")
                except Exception as exc:
                    status, actual = "ERROR", f"{type(exc).__name__}: {exc}"
                    traceback_file = str(trace_dir / f"{case.case_id}.txt")
                    Path(traceback_file).write_text(traceback.format_exc(), encoding="utf-8")

                if status in {"FAIL", "ERROR"}:
                    failures += 1
                    screenshot = safe_screenshot(browser, screenshot_dir, case.case_id)

            elapsed = time.monotonic() - start
            display_name = (
                attempted_name
                if len(attempted_name) <= 120
                else f"{attempted_name[:80]}... (len={len(attempted_name)})"
            )
            results.append(
                {
                    "test_case_id": case.case_id,
                    "technique": case["technique"],
                    "focus": case["focus"],
                    "run_id": run_id,
                    "status": status,
                    "duration_seconds": f"{elapsed:.3f}",
                    "expected_kind": case["expected_kind"],
                    "expected_text": case["expected_text"],
                    "actual_result_or_error": actual[:600],
                    "review_tags": case["review_tags"],
                    "attempted_quiz_name": display_name,
                    "created_cmid": created_cmid,
                    "screenshot": screenshot,
                    "traceback_file": traceback_file,
                }
            )
            suffix = f" - {actual[:160]}" if status != "PASS" else (f" [cmid={created_cmid}]" if created_cmid else "")
            print(f"{case.case_id}: {status} ({elapsed:.2f}s){suffix}", flush=True)
    finally:
        if owns_browser and browser is not None:
            try:
                browser.quit()
            except Exception as quit_error:
                print(f"Warning: WebDriver cleanup: {quit_error}", file=sys.stderr)
        finalize_group_results(output_dir, results, run_id, base_url, planned, started_utc=started_utc)

    return 1 if failures else 0
