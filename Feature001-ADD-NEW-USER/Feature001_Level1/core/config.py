"""Local configuration and target safety checks."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

ROOT_DIR = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:9502"
DATA_FILE = ROOT_DIR / "data" / "f01_core.csv"


def protected_local_url(base_url: str, allow_remote: bool) -> str:
    base_url = base_url.rstrip("/")
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("MOODLE_BASE_URL must be an absolute HTTP(S) URL")
    if not allow_remote and parsed.hostname.lower() not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("This test creates users. Non-local target blocked. See --allow-remote-target.")
    return base_url


def load_local_env(path: Path) -> None:
    """Load optional local Moodle settings without a third-party dependency.

    Existing environment variables have precedence. The file is never copied
    into test output or printed, and should not be committed to source control.
    """
    if not path.is_file():
        return
    allowed = {"MOODLE_BASE_URL", "MOODLE_ADMIN_USERNAME", "MOODLE_ADMIN_PASSWORD", "MOODLE_RESTRICTED_USERNAME", "MOODLE_RESTRICTED_PASSWORD", "MOODLE_IMAGE_MAX_BYTES"}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in allowed:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key, value)
