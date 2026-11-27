"""Windows-safe Docker PHP CLI bridge for Moodle Quiz DB auditing & cleanup."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

from .config import settings

PHP_SOURCE = Path(__file__).with_name("audit.php").read_text(encoding="utf-8")


def bridge(op: str, **params) -> dict:
    cfg = settings()
    payload = {
        "op": op,
        "base": cfg["base"],
        "config": cfg["config_path"],
        "course_id": cfg["course_id"],
        **params,
    }
    proc = subprocess.run(
        ["docker", "exec", "-i", cfg["container"], "php", "-r", PHP_SOURCE],
        input=json.dumps(payload),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=300,
    )
    if proc.returncode != 0 or "NFR4_JSON:" not in proc.stdout:
        raise RuntimeError(
            "Moodle CLI audit bridge failed. Verify Docker container, config path, and wwwroot.\n"
            + (proc.stderr or proc.stdout)[-800:]
        )
    raw_json = proc.stdout.rsplit("NFR4_JSON:", 1)[1].splitlines()[0]
    result = json.loads(raw_json)
    if not result.get("ok"):
        raise RuntimeError(f"Moodle CLI audit returned non-ok response: {result}")
    return result


def audit_quizzes(prefix: str, names: list[str]) -> dict[str, list[dict]]:
    if not names:
        return {}
    result = bridge("audit", prefix=prefix, names=list(names))["quizzes"]
    return result if isinstance(result, dict) else {}


def exact_quiz(observed: dict[str, list[dict]], name: str) -> bool:
    entries = observed.get(name, [])
    return len(entries) == 1 and int(entries[0].get("cmid", 0)) > 0
