"""Result files, screenshots and review-only cleanup candidates."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

STATUSES = ("PASS", "FAIL", "ERROR", "SKIP")
RESULT_FIELDS = [
    "test_case_id", "technique", "focus", "run_id", "status", "duration_seconds",
    "expected_kind", "expected_text", "actual_result_or_error", "review_tags",
    "source_has_submit", "fixture_required", "attempted_username", "attempted_email",
    "screenshot", "traceback_file",
]


def safe_screenshot(browser, folder: Path, case_id: str) -> str:
    path = folder / f"{case_id}.png"
    try:
        if browser.save_screenshot(str(path)):
            return str(path)
    except Exception:
        pass
    return ""


def output_results(path: Path, results: list[dict[str, str]]) -> None:
    write_csv(path, RESULT_FIELDS, results)


def write_csv(path: Path, fields, rows) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def create_run_directory(results_dir: Path, run_id: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # Separate execution identity from the optional stable test-data run ID.
    folder = results_dir / f"run_{stamp}_{run_id}_{uuid4().hex[:8]}"
    folder.mkdir(parents=True, exist_ok=False)
    return folder


def finalize_run(output_dir: Path, datasets, run_id: str, base_url: str,
                 started_utc: str, exit_code: int | None) -> None:
    """Aggregate only the files belonging to this invocation, including partial runs."""
    summaries = []
    all_rows = []
    for group, cases in datasets.items():
        if not cases:
            continue
        path = output_dir / group / "results.csv"
        rows = []
        if path.is_file():
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
        all_rows.extend({"group": group, **row} for row in rows)
        counts = {status: sum(row["status"] == status for row in rows) for status in STATUSES}
        summaries.append({"group": group, "total": len(cases), **counts,
                          "not_recorded": len(cases) - len(rows)})

    fields = ["group", "total", *STATUSES, "not_recorded"]
    totals = {field: sum(row[field] for row in summaries) for field in fields[1:]}
    write_csv(output_dir / "summary.csv", fields, [*summaries, {"group": "TOTAL", **totals}])
    write_csv(output_dir / "all_results.csv", ["group", *RESULT_FIELDS], all_rows)
    meta = {
        "run_id": run_id,
        "base_url": base_url,
        "started_utc": started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "groups": [row["group"] for row in summaries],
        "total": totals["total"],
        "counts": {status: totals[status] for status in STATUSES},
        "not_recorded": totals["not_recorded"],
        "complete": exit_code is not None and totals["not_recorded"] == 0,
        "exit_code": exit_code,
    }
    (output_dir / "run_info.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Run results: {output_dir}")
    print(f"Summary: {output_dir / 'summary.csv'}")
    print(f"All results: {output_dir / 'all_results.csv'}")
    print(" | ".join(f"{key}={value}" for key, value in totals.items()))


def finalize_results(output_dir: Path, results: list[dict[str, str]], run_id: str, base_url: str, planned, *, started_utc: str | None = None):
    output_results(output_dir / "results.csv", results)
    # A review-only list; never delete accounts automatically.
    with (output_dir / "cleanup_candidates.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        cleanup = csv.DictWriter(handle, fieldnames=["test_case_id", "attempted_username", "attempted_email", "status", "note"])
        cleanup.writeheader()
        for row in results:
            if row["attempted_username"]:
                cleanup.writerow({"test_case_id":row["test_case_id"],
                                  "attempted_username":row["attempted_username"],
                                  "attempted_email":row["attempted_email"],
                                  "status":row["status"],
                                  "note":"Check account existence in Moodle before deleting; NOT proof of creation"})
        # Recovery creates a second account; include it for manual review even
        # if final verification failed. Never infer that an account was created.
        cases = {case.case_id: case for case, _ in planned}
        for row in results:
            case = cases[row['test_case_id']]
            if row['status'] != 'SKIP' and case.values.get('recovery_username'):
                from core.data_loader import resolve_data
                cleanup.writerow({'test_case_id': row['test_case_id'],
                                  'attempted_username': case['recovery_username'],
                                  'attempted_email': resolve_data(case['second_email'], run_id),
                                  'status': row['status'],
                                  'note': 'Recovery candidate; verify exact account before deleting'})
    meta = {
        "run_id": run_id, "base_url": base_url, "started_utc": started_utc or datetime.now(timezone.utc).isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "total": len(planned),
        "counts": {label: sum(r["status"] == label for r in results) for label in ("PASS", "FAIL", "ERROR", "SKIP")},
        "warning": "Success asserts source toast; account persistence is NOT independently validated.",
    }
    (output_dir / "run_info.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Results: {output_dir / 'results.csv'}")
    print("Important: Reset isolated Moodle test data before a rerun; fixed usernames come from Project #2.")
