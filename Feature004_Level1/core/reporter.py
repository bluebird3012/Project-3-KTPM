"""Unified result reporting, screenshots, tracebacks, and cleanup candidates."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

STATUSES = ("PASS", "FAIL", "ERROR", "SKIP")
RESULT_FIELDS = [
    "test_case_id",
    "technique",
    "focus",
    "run_id",
    "status",
    "duration_seconds",
    "expected_kind",
    "expected_text",
    "actual_result_or_error",
    "review_tags",
    "attempted_quiz_name",
    "created_cmid",
    "screenshot",
    "traceback_file",
]


def safe_screenshot(browser, folder: Path, case_id: str) -> str:
    path = folder / f"{case_id}.png"
    try:
        if browser.save_screenshot(str(path)):
            return str(path)
    except Exception:
        pass
    return ""


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def create_run_directory(results_dir: Path, run_id: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = results_dir / f"run_{stamp}_{run_id}_{uuid4().hex[:8]}"
    folder.mkdir(parents=True, exist_ok=False)
    return folder


def finalize_group_results(
    output_dir: Path,
    results: list[dict[str, str]],
    run_id: str,
    base_url: str,
    planned,
    *,
    started_utc: str | None = None,
) -> None:
    write_csv(output_dir / "results.csv", RESULT_FIELDS, results)

    cleanup_rows = []
    for row in results:
        if row["status"] != "SKIP" and (row["created_cmid"] or row["attempted_quiz_name"]):
            cleanup_rows.append(
                {
                    "test_case_id": row["test_case_id"],
                    "attempted_quiz_name": row["attempted_quiz_name"],
                    "created_cmid": row["created_cmid"],
                    "status": row["status"],
                    "note": (
                        "Recorded cmid from Add Quiz run; clean via cleanup.py"
                        if row["created_cmid"]
                        else "No cmid recorded (error/cancel/not created); verify before deleting"
                    ),
                }
            )
    write_csv(
        output_dir / "cleanup_candidates.csv",
        ["test_case_id", "attempted_quiz_name", "created_cmid", "status", "note"],
        cleanup_rows,
    )

    meta = {
        "feature": "Feature 004 - Add Quiz",
        "level": 1,
        "run_id": run_id,
        "base_url": base_url,
        "started_utc": started_utc or datetime.now(timezone.utc).isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "total": len(planned),
        "counts": {label: sum(r["status"] == label for r in results) for label in STATUSES},
    }
    (output_dir / "run_info.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def finalize_run(
    output_dir: Path,
    datasets: dict,
    run_id: str,
    base_url: str,
    started_utc: str,
    exit_code: int | None,
    *,
    course_id: int,
    section_id: int,
) -> None:
    """Aggregate group CSVs into run-level summary.csv, all_results.csv, and run_info.json."""
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
        summaries.append(
            {
                "group": group,
                "total": len(cases),
                **counts,
                "not_recorded": len(cases) - len(rows),
            }
        )

    fields = ["group", "total", *STATUSES, "not_recorded"]
    totals = {field: sum(row[field] for row in summaries) for field in fields[1:]}
    write_csv(output_dir / "summary.csv", fields, [*summaries, {"group": "TOTAL", **totals}])
    write_csv(output_dir / "all_results.csv", ["group", *RESULT_FIELDS], all_rows)

    meta = {
        "feature": "Feature 004 - Add Quiz",
        "level": 1,
        "run_id": run_id,
        "base_url": base_url,
        "course_id": course_id,
        "section_id": section_id,
        "started_utc": started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "groups": [row["group"] for row in summaries],
        "total": totals["total"],
        "counts": {status: totals[status] for status in STATUSES},
        "not_recorded": totals["not_recorded"],
        "complete": exit_code is not None and totals["not_recorded"] == 0,
        "exit_code": exit_code,
    }
    (output_dir / "run_info.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Run results: {output_dir}")
    print(f"Summary: {output_dir / 'summary.csv'}")
    print(f"All results: {output_dir / 'all_results.csv'}")
    print(" | ".join(f"{key}={value}" for key, value in totals.items()))
