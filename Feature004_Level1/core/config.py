"""Local configuration and target safety checks for Feature 004 Level 1."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

ROOT_DIR = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:9502"
DEFAULT_COURSE_ID = 2
DEFAULT_SECTION_ID = 2
DEFAULT_TIMEOUT = 30

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
    """Load optional local Moodle settings without third-party dependencies.

    Existing environment variables take precedence. Credentials are never
    printed or written to result logs.
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in ALLOWED_ENV_KEYS:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def get_course_id() -> int:
    return int(os.environ.get("MOODLE_COURSE_ID", str(DEFAULT_COURSE_ID)))


def get_section_id() -> int:
    return int(os.environ.get("MOODLE_SECTION_ID", str(DEFAULT_SECTION_ID)))
