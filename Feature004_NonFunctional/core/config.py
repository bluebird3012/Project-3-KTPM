"""Local-only configuration and safety checks for Feature 004 Non-Functional Testing."""
from __future__ import annotations

import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def local_url(raw: str) -> str:
    cleaned = raw.rstrip("/")
    parsed = urlsplit(cleaned)
    if (
        parsed.scheme not in ("http", "https")
        or (parsed.hostname or "").lower() not in ("localhost", "127.0.0.1", "::1")
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Only a local Moodle HTTP(S) target is allowed for non-functional tests.")
    return cleaned


def settings() -> dict:
    base = local_url(os.getenv("MOODLE_BASE_URL", "http://127.0.0.1:9502"))
    username = os.getenv("MOODLE_ADMIN_USERNAME", "admin").strip()
    password = os.getenv("MOODLE_ADMIN_PASSWORD", "")
    container = os.getenv("MOODLE_WEB_CONTAINER", "").strip()
    config_path = os.getenv("MOODLE_CONFIG_PATH", "/var/www/site/moodle/config.php").strip()
    course_id = int(os.getenv("MOODLE_COURSE_ID", "2"))
    section_id = int(os.getenv("MOODLE_SECTION_ID", "2"))

    if not username or not password or password.startswith("REPLACE"):
        raise ValueError("Set MOODLE_ADMIN_USERNAME and MOODLE_ADMIN_PASSWORD in .env.")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", container):
        raise ValueError("Set MOODLE_WEB_CONTAINER to the actual local Moodle webserver container name.")

    return {
        "base": base,
        "username": username,
        "password": password,
        "container": container,
        "config_path": config_path,
        "course_id": course_id,
        "section_id": section_id,
    }
