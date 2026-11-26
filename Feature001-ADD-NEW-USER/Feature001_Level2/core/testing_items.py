"""Load Level 2 testing items once per process; no fallback to embedded locators."""
from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path
from urllib.parse import urlsplit
from types import MappingProxyType

TESTING_ITEMS_FILE = Path(__file__).resolve().parents[1] / "config" / "testing_items.csv"
STRATEGIES = {"id": "id", "css": "css selector", "xpath": "xpath", "name": "name", "class": "class name", "tag": "tag name", "link_text": "link text", "partial_link_text": "partial link text"}


def load_items(path: Path, *, raw: bytes | None = None):
    items = {}
    with io.StringIO((path.read_bytes() if raw is None else raw).decode("utf-8-sig"), newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["item_name", "item_type", "item_value"]:
            raise ValueError(f"Invalid testing-items header: {path}")
        for line, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"Invalid testing-items row {line}")
            name, kind, value = (row[k] for k in reader.fieldnames)
            if not name or name != name.strip() or not value.strip() or kind not in {*STRATEGIES, "path", "url", "token"}:
                raise ValueError(f"Invalid testing item at row {line}: {name!r}")
            if name in items:
                raise ValueError(f"Duplicate testing item: {name}")
            if kind == "path" and (not value.startswith("/") or value.startswith("//") or urlsplit(value).netloc):
                raise ValueError(f"Expected site-relative path for {name}")
            if kind == "url" and (urlsplit(value).scheme not in {"http", "https"} or not urlsplit(value).hostname):
                raise ValueError(f"Expected absolute HTTP(S) URL for {name}")
            items[name] = (kind, value)
    return MappingProxyType(items)


_CONFIG_BYTES = TESTING_ITEMS_FILE.read_bytes()
ITEMS = load_items(TESTING_ITEMS_FILE, raw=_CONFIG_BYTES)
TESTING_ITEMS_SHA256 = hashlib.sha256(_CONFIG_BYTES).hexdigest()


def get_item(name, *kinds):
    try:
        kind, value = ITEMS[name]
    except KeyError as error:
        raise ValueError(f"Missing testing item: {name} in {TESTING_ITEMS_FILE}") from error
    if kind not in kinds:
        raise ValueError(f"Unexpected item type {kind!r} for {name}; expected {', '.join(kinds)}")
    return kind, value


def value(name, *kinds):
    return get_item(name, *kinds)[1]


def item(name, key=None):
    """Return a Selenium (by, value) tuple from an external testing item."""
    name = name if key is None else f"{name}.{key}"
    kind, selector = get_item(name, *STRATEGIES)
    return STRATEGIES[kind], selector


def encoded_locator(name):
    kind, selector = get_item(name, *STRATEGIES)
    return f"{kind}={selector}"


def locator_tuple(locator):
    kind, sep, selector = locator.partition("=")
    if not sep or kind not in STRATEGIES or not selector:
        raise ValueError(f"Unsupported locator format: {locator!r}")
    return STRATEGIES[kind], selector
