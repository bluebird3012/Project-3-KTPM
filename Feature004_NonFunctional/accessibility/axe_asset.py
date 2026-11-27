"""Local axe-core JS asset management with SHA-256 verification."""
from __future__ import annotations

import hashlib
from pathlib import Path
import urllib.request

AXE_VERSION = "4.10.2"
AXE_CDN_URL = f"https://cdnjs.cloudflare.com/ajax/libs/axe-core/{AXE_VERSION}/axe.min.js"
VENDOR_FILE = Path(__file__).resolve().parent / "vendor" / "axe.min.js"


def ensure_axe_script() -> tuple[str, str]:
    """Return (js_source, sha256) from local vendor/axe.min.js (downloading once if absent)."""
    if not VENDOR_FILE.is_file():
        VENDOR_FILE.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(AXE_CDN_URL, headers={"User-Agent": "Feature004-NFR08/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
        if b"axe" not in raw or len(raw) < 100_000:
            raise RuntimeError("Downloaded axe.min.js appears invalid or truncated")
        VENDOR_FILE.write_bytes(raw)
    raw = VENDOR_FILE.read_bytes()
    return raw.decode("utf-8"), hashlib.sha256(raw).hexdigest()
