"""Safe Moodle Quiz cleanup for Feature 004 NFR-07 (dry-run by default).

Deletes ONLY recorded `nfr4<12hex>_<16hex>` synthetic quizzes from the given
results directory via Moodle's official `course_delete_module()` API inside
the configured local Moodle web container.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from core.audit import audit_quizzes, bridge
from core.config import ROOT, settings
from core.reporter import read_jsonl, write_json


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Clean up synthetic NFR-07 quizzes for a run directory")
    parser.add_argument("run_directory", type=Path, help="Path under results/performance/<run_dir>")
    parser.add_argument("--apply", action="store_true", help="Actually delete matched quizzes (default: dry-run)")
    args = parser.parse_args(argv)

    run_dir = args.run_directory.resolve()
    if not run_dir.is_relative_to((ROOT / "results").resolve()):
        raise ValueError("Run directory must be inside Feature004_NonFunctional/results/")

    info = json.loads((run_dir / "run_info.json").read_text(encoding="utf-8"))
    cfg = settings()
    if info["base"] != cfg["base"]:
        raise ValueError("Run target base URL does not match configured Moodle site")

    names = sorted(
        {
            e["quiz_name"]
            for f in run_dir.rglob("*.jsonl")
            for e in read_jsonl(f)
            if e.get("event") == "attempt" and e.get("quiz_name")
        }
    )
    observed = audit_quizzes(info["prefix"], names)
    existing_count = sum(len(v) for v in observed.values())
    print(f"Run {run_dir.name}: {len(names)} recorded quiz attempts; {existing_count} currently exist in DB.")

    if not args.apply:
        print("Dry-run only. Repeat with --apply to delete only these synthetic quizzes.")
        return 0

    result = bridge("cleanup", prefix=info["prefix"], names=names) if names else {"deleted": []}
    remaining = audit_quizzes(info["prefix"], names)
    write_json(
        run_dir / "cleanup.json",
        {
            "recorded_attempts": len(names),
            "deleted_count": len(result.get("deleted", [])),
            "deleted": result.get("deleted", []),
            "remaining": remaining,
        },
    )
    print(f"Deleted {len(result.get('deleted', []))} quizzes; remaining={sum(len(v) for v in remaining.values())}.")
    if remaining:
        raise RuntimeError(f"Some synthetic quizzes still remain after cleanup: {len(remaining)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
