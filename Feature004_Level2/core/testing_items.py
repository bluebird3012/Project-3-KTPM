"""Strict Level 2 external testing-items loader; zero fallback to hardcoded locators."""
from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path
from types import MappingProxyType
from urllib.parse import urlsplit

TESTING_ITEMS_FILE = Path(__file__).resolve().parents[1] / "config" / "testing_items.csv"
TESTING_ITEMS_RELPATH = "config/testing_items.csv"

STRATEGIES = MappingProxyType(
    {
        "id": "id",
        "css": "css selector",
        "xpath": "xpath",
        "name": "name",
        "class": "class name",
        "tag": "tag name",
        "link_text": "link text",
        "partial_link_text": "partial link text",
    }
)
ALLOWED_TYPES = frozenset({*STRATEGIES.keys(), "url", "path", "token"})


def load_items(path: Path, *, raw: bytes | None = None) -> MappingProxyType:
    """Parse and strictly validate testing_items.csv into an immutable MappingProxyType."""
    data_bytes = path.read_bytes() if raw is None else raw
    items: dict[str, tuple[str, str]] = {}
    with io.StringIO(data_bytes.decode("utf-8-sig"), newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["item_name", "item_type", "item_value"]:
            raise ValueError(f"Invalid testing-items header in {path}: {reader.fieldnames!r}")
        for line_no, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"Malformed testing-items row {line_no} in {path}")
            name, kind, val = (row["item_name"], row["item_type"], row["item_value"])
            if not name or name != name.strip():
                raise ValueError(f"Invalid or padded item_name at row {line_no}: {name!r}")
            if not val or not val.strip():
                raise ValueError(f"Empty item_value at row {line_no} for {name!r}")
            if kind not in ALLOWED_TYPES:
                raise ValueError(f"Unsupported item_type {kind!r} at row {line_no} for {name!r}")
            if name in items:
                raise ValueError(f"Duplicate testing item at row {line_no}: {name!r}")
            if kind == "path":
                parsed = urlsplit(val)
                if not val.startswith("/") or val.startswith("//") or parsed.netloc:
                    raise ValueError(f"Expected site-relative path for {name!r}, got {val!r}")
            if kind == "url":
                parsed = urlsplit(val)
                if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                    raise ValueError(f"Expected absolute HTTP(S) URL for {name!r}, got {val!r}")
            items[name] = (kind, val)
    if not items:
        raise ValueError(f"No testing items defined in {path}")
    return MappingProxyType(items)


_CONFIG_BYTES = TESTING_ITEMS_FILE.read_bytes()
ITEMS = load_items(TESTING_ITEMS_FILE, raw=_CONFIG_BYTES)
TESTING_ITEMS_SHA256 = hashlib.sha256(_CONFIG_BYTES).hexdigest()


def get_item(name: str, *expected_kinds: str, items_map=None) -> tuple[str, str]:
    store = ITEMS if items_map is None else items_map
    try:
        kind, val = store[name]
    except KeyError as error:
        raise ValueError(f"Missing testing item {name!r} in {TESTING_ITEMS_FILE}") from error
    if expected_kinds and kind not in expected_kinds:
        raise ValueError(
            f"Unexpected item_type {kind!r} for {name!r}; expected one of {', '.join(expected_kinds)}"
        )
    return kind, val


def value(name: str, *expected_kinds: str, items_map=None) -> str:
    return get_item(name, *expected_kinds, items_map=items_map)[1]


def item(name: str, key: str | None = None, *, items_map=None) -> tuple[str, str]:
    """Return a Selenium (by, value) tuple from an externalized testing item."""
    full_name = name if key is None else f"{name}.{key}"
    kind, selector = get_item(full_name, *STRATEGIES.keys(), items_map=items_map)
    return STRATEGIES[kind], selector


def item_template(name: str, *, items_map=None, **kwargs: str) -> tuple[str, str]:
    """Return a Selenium (by, formatted_value) tuple from a parameterized locator template."""
    by, raw_selector = item(name, items_map=items_map)
    return by, raw_selector.format(**kwargs)


def item_type_summary(items_map=None) -> dict[str, int]:
    store = ITEMS if items_map is None else items_map
    counts: dict[str, int] = {}
    for kind, _ in store.values():
        counts[kind] = counts.get(kind, 0) + 1
    return counts
