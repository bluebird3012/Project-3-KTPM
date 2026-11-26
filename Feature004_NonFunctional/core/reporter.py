"""Run directory creation, JSONL manifest helpers, and CSV/JSON writers."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from .config import ROOT


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_run(kind: str, base: str, *, extra: dict | None = None) -> tuple[Path, dict]:
    token = uuid.uuid4().hex[:12]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = ROOT / "results" / kind / f"{stamp}_{token}"
    directory.mkdir(parents=True, exist_ok=False)
    info = {
        "feature": "Feature 004 - Add Quiz",
        "kind": kind,
        "base": base,
        "prefix": f"nfr4{token}_",
        "started_at": now(),
        **(extra or {}),
    }
    write_json(directory / "run_info.json", info)
    return directory, info


def new_quiz_name(prefix: str) -> str:
    return prefix + uuid.uuid4().hex[:16]


def append_json(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
