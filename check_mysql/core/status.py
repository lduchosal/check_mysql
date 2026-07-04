"""Helpers reading SHOW GLOBAL STATUS / VARIABLES mappings."""

from __future__ import annotations

from check_mysql.core.exceptions import ValidationError


def read_int(mapping: dict[str, str], key: str, hint: str = "") -> int:
    """
    Read an integer entry from a SHOW output mapping.

    The optional hint is appended to the missing-key error, e.g. to point
    at a feature removed from recent server versions.

    Raises:
        ValidationError: If the entry is missing or not an integer.
    """
    raw = mapping.get(key)
    if raw is None:
        raise ValidationError(f"No {key} reported by the server{hint}")
    try:
        return int(raw)
    except ValueError as exc:
        raise ValidationError(f"Invalid {key} value: {raw!r}") from exc


def sum_counters(mapping: dict[str, str], keys: tuple[str, ...], hint: str = "") -> int:
    """Sum several integer counters from a SHOW output mapping."""
    return sum(read_int(mapping, key, hint) for key in keys)
