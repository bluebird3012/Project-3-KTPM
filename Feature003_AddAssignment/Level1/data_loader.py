"""Reads the CSV test-data files and resolves test-data variables.

A cell may reference a variable from data/variables.csv with {NAME} and may use
these small helpers (useful for very long values):

    @repeat(A|255)            -> 'AAA...A' (255 characters)
    @padto(prefix|a|255)      -> prefix followed by 'a' until the length is 255

An empty cell means "do not use / do not touch this field" (see each script).
"""
import csv
import os
import re

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

_VAR = re.compile(r"\{([A-Z0-9_]+)\}")
_FUNC = re.compile(r"@(repeat|padto)\(([^()]*)\)")


def read_csv(filename, folder=DATA_DIR):
    with open(os.path.join(folder, filename), newline="", encoding="utf-8-sig") as f:
        return [dict(row) for row in csv.DictReader(f)]


def _apply_funcs(text):
    def run(m):
        fn, args = m.group(1), m.group(2).split("|")
        if fn == "repeat":
            return args[0] * int(args[1])
        prefix, ch, n = args[0], args[1], int(args[2])
        return (prefix + ch * n)[:n]
    return _FUNC.sub(run, text)


class Variables:
    def __init__(self, folder=DATA_DIR, filename="variables.csv"):
        self.raw = {r["variable"]: r["value"] for r in read_csv(filename, folder)}
        self._cache = {}

    def get(self, name, default=None):
        if name not in self.raw:
            return default
        if name not in self._cache:
            self._cache[name] = self.resolve(self.raw[name])
        return self._cache[name]

    def resolve(self, text):
        if text is None:
            return ""
        for _ in range(10):  # nested variables
            new = _VAR.sub(lambda m: self.get(m.group(1)) if m.group(1) in self.raw else m.group(0), text)
            if new == text:
                break
            text = new
        return _apply_funcs(text)

    def resolve_row(self, row):
        return {k: self.resolve(v) for k, v in row.items()}


def split_list(text, sep=";"):
    """'a;b;c' -> ['a', 'b', 'c'] (empty parts removed)."""
    return [p for p in (s.strip() for s in (text or "").split(sep)) if p]


def any_of(text):
    """'x|y' -> ['x', 'y'] : alternatives, any one of them is accepted."""
    return [p.strip() for p in (text or "").split("|") if p.strip()]


def parse_pairs(text):
    """'grade=80;maxfiles=20' -> {'grade': '80', 'maxfiles': '20'}"""
    pairs = {}
    for part in split_list(text):
        key, _, value = part.partition("=")
        pairs[key.strip()] = value.strip()
    return pairs


def load_cases(filename, folder=DATA_DIR):
    """Returns the resolved rows of a test-case CSV file and the variables."""
    variables = Variables(folder)
    return [variables.resolve_row(r) for r in read_csv(filename, folder)], variables
