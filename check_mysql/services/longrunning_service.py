"""Long-running processes service implementation."""

from __future__ import annotations

from typing import Any

from check_mysql.core.logging_config import get_verbose_logger
from check_mysql.core.models import MySQLClientProtocol, ServiceResult

LONG_RUNNING_SECONDS = 60

# Idle or infrastructure threads whose Time column grows forever by design.
_IDLE_COMMANDS = frozenset({"Sleep", "Daemon", "Binlog Dump", "Binlog Dump GTID"})


def _row_time(row: dict[str, Any]) -> int:
    """Read the Time column, tolerating missing or non-numeric values."""
    try:
        return int(row.get("Time") or 0)
    except (TypeError, ValueError):
        return 0


def _is_long_running(row: dict[str, Any]) -> bool:
    """Tell whether a processlist row is an active long-running query."""
    if str(row.get("Command", "")) in _IDLE_COMMANDS:
        return False
    return _row_time(row) > LONG_RUNNING_SECONDS


def _describe(row: dict[str, Any]) -> str:
    """One-line description of a long-running processlist row."""
    return (
        f"id {row.get('Id')}: {row.get('Command')} by {row.get('User')} "
        f"for {_row_time(row)}s"
    )


class LongRunningService:
    """Service counting queries running longer than LONG_RUNNING_SECONDS."""

    def __init__(self, client: MySQLClientProtocol, verbose_level: int = 0) -> None:
        """Initialize with a MySQL client."""
        self.client = client
        self.logger = get_verbose_logger(__name__, verbose_level)

    def get_result(self) -> ServiceResult:
        """Return the number of long-running processes on the server."""
        self.logger.method_entry("get_result")

        processes = self.client.get_processlist()
        long_running = [row for row in processes if _is_long_running(row)]
        count = len(long_running)

        details: list[str] = [
            f"{count} queries running longer than {LONG_RUNNING_SECONDS}s "
            f"({len(processes)} processes total)"
        ]
        details.extend(_describe(row) for row in long_running)
        result: ServiceResult = {"value": count, "details": details}

        self.logger.info(f"Long-running queries: {count}")
        self.logger.method_exit("get_result", result)
        return result
