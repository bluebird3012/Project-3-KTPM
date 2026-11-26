"""Shared sequential execution and status classification."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import time
import traceback

from core.browser import build_browser
from core.data_loader import resolve_data
from core.reporter import safe_screenshot, finalize_results
from pages.login_page import prepare_admin_session
from core.preconditions import PreconditionMissing


def run_suite(planned, args, base_url: str, run_id: str, execute_case, group_prefix: str, *, prepare_session=prepare_admin_session, output_dir: Path | None = None):
    started_utc = datetime.now(timezone.utc).isoformat()
    if output_dir is None:
        output_dir = args.results_dir / (group_prefix + "_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + run_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir = output_dir / "screenshots"
    screenshot_dir.mkdir(exist_ok=True)
    trace_dir = output_dir / "tracebacks"
    trace_dir.mkdir(exist_ok=True)
    results: list[dict[str, str]] = []
    browser = None
    failures = 0
    try:
        if any(not why for _, why in planned):
            browser = build_browser(args.headless)
            prepare_session(browser, base_url, "manual" if args.manual_login else "auto", args.timeout)
        for case, why in planned:
            start = time.monotonic()
            status, actual, screenshot, traceback_file = "SKIP", why, "", ""
            if not why:
                try:
                    actual = execute_case(browser, base_url, case, run_id, args.timeout)
                    status = "PASS"
                except PreconditionMissing as e:
                    status, actual = "SKIP", str(e)
                except AssertionError as e:
                    status, actual = "FAIL", f"{type(e).__name__}: {e}"
                    traceback_file = str(trace_dir / f"{case.case_id}.txt")
                    Path(traceback_file).write_text(traceback.format_exc(), encoding="utf-8")
                except Exception as e:
                    status, actual = "ERROR", f"{type(e).__name__}: {e}"
                    traceback_file = str(trace_dir / f"{case.case_id}.txt")
                    Path(traceback_file).write_text(traceback.format_exc(), encoding="utf-8")
                if status in {"FAIL", "ERROR"}:
                    failures += 1
                    screenshot = safe_screenshot(browser, screenshot_dir, case.case_id)
            elapsed = time.monotonic() - start
            results.append({
                "test_case_id": case.case_id,
                "technique": case["technique"], "focus": case["focus"], "run_id": run_id,
                "status": status, "duration_seconds": f"{elapsed:.3f}",
                "expected_kind": case["expected_kind"], "expected_text": case["expected_text"],
                "actual_result_or_error": actual[:600], "review_tags": case["review_tags"],
                "source_has_submit": case["source_has_submit"],
                "fixture_required": case["fixture_required"],
                "attempted_username": resolve_data(case["username"], run_id) if not why and status != "SKIP" else "",
                "attempted_email": resolve_data(case["email"], run_id) if not why and status != "SKIP" else "",
                "screenshot": screenshot, "traceback_file": traceback_file,
            })
            print(f"{case.case_id}: {status} ({elapsed:.2f}s)" + (f" - {actual[:150]}" if status != "PASS" else ""))
    finally:
        if browser is not None:
            try:
                browser.quit()  # Closes WebDriver session. Does not delete Moodle users.
            except Exception as quit_error:
                print(f"Warning: WebDriver cleanup: {quit_error}", file=sys.stderr)
        finalize_results(output_dir, results, run_id, base_url, planned, started_utc=started_utc)
    return 1 if failures else 0
