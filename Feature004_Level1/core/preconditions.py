"""Precondition exception and helper checks for Feature 004."""
from __future__ import annotations


class PreconditionMissing(Exception):
    """Raised when a test case precondition is not met and must be recorded as SKIP."""
