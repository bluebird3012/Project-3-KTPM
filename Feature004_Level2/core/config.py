"""Local configuration and target safety checks for Feature 004 Level 2."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

from core.testing_items import value as item_value

ROOT_DIR = Path(__file__).resolve().parents[1]
BASE_URL = item_value("BASE_URL", "url")
DEFAULT_COURSE_ID = 2
DEFAULT_SECTION_ID = 2
DEFAULT_TIMEOUT = 45

ALLOWED_ENV_KEYS = {
    "MOODLE_BASE_URL",
    "MOODLE_ADMIN_USERNAME",
    "MOODLE_ADMIN_PASSWORD",
    "MOODLE_COURSE_ID",
    "MOODLE_SECTION_ID",
    "MOODLE_WEB_CONTAINER",
    "MOODLE_CONFIG_PATH",
}


def protected_local_url(base_url: str, allow_remote: bool = False) -> str:
    base_url = base_url.rstrip("/")
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("MOODLE_BASE_URL must be an absolute HTTP(S) URL")
    if not allow_remote and parsed.hostname.lower() not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError(
            "This test creates quizzes in Moodle. Non-local target blocked. "
            "Pass --allow-remote-target only if explicitly intended."
        )
    return base_url


def load_local_env(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        if key not in ALLOWED_ENV_KEYS:
            continue
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        os.environ.setdefault(key, val)


def get_course_id() -> int:
    return int(os.environ.get("MOODLE_COURSE_ID", str(DEFAULT_COURSE_ID)))


def get_section_id() -> int:
    return int(os.environ.get("MOODLE_SECTION_ID", str(DEFAULT_SECTION_ID)))
