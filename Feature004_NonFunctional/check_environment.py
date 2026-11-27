"""Read-only readiness check for Feature 004 Non-Functional Testing (NFR-07 & NFR-08)."""
from __future__ import annotations

import importlib.metadata
import sys

from accessibility.axe_asset import AXE_VERSION, ensure_axe_script
from core.audit import bridge
from core.config import settings
from core.moodle_client import TIMEOUT, add_quiz_form, add_quiz_path, login, session


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = settings()
    print(f"Target    : {cfg['base']}")
    print(f"Container : {cfg['container']}")
    print(f"Course/Sec: course={cfg['course_id']}, sectionid={cfg['section_id']}")

    for pkg in ("requests", "beautifulsoup4", "python-dotenv", "locust", "selenium"):
        print(f"  {pkg}: {importlib.metadata.version(pkg)}")

    cap = bridge("capability", username=cfg["username"])
    print(f"Moodle CLI: release={cap.get('release')} | course={cap.get('course')} | can_add_quiz={cap.get('can_add_quiz')}")
    if not cap.get("can_add_quiz") or cap.get("suspended"):
        raise RuntimeError("Configured account lacks active Add Quiz capability on target course")

    with session() as client:
        login(client, cfg["base"], cfg["username"], cfg["password"])
        r = client.get(cfg["base"] + add_quiz_path(cfg["course_id"], cfg["section_id"]), timeout=TIMEOUT)
        r.raise_for_status()
        if not add_quiz_form(r):
            raise RuntimeError("Add a new Quiz form unavailable via HTTP")
    print("HTTP Check: PASS (login + Add Quiz form + sesskey/_qf__mod_quiz_mod_form verified)")

    axe_js, axe_sha = ensure_axe_script()
    print(f"axe-core  : PASS (v{AXE_VERSION}, {len(axe_js)} chars, sha256={axe_sha[:16]}...)")
    print("OVERALL ENVIRONMENT READINESS: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
