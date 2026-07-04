"""Slow queries service implementation."""

from __future__ import annotations

from check_mysql.core.exceptions import ValidationError
from check_mysql.core.logging_config import get_verbose_logger
from check_mysql.core.models import MySQLClientProtocol, ServiceResult


class SlowQueriesService:
    """Service checking the Slow_queries counter since server start."""

    def __init__(self, client: MySQLClientProtocol, verbose_level: int = 0) -> None:
        """Initialize with a MySQL client."""
        self.client = client
        self.logger = get_verbose_logger(__name__, verbose_level)

    def get_result(self) -> ServiceResult:
        """
        Return the number of slow queries recorded since server start.

        Raises:
            ValidationError: If the server does not report a numeric counter.
        """
        self.logger.method_entry("get_result")

        status = self.client.get_global_status()
        raw = status.get("Slow_queries")
        if raw is None:
            raise ValidationError("No Slow_queries in SHOW GLOBAL STATUS")
        try:
            slow = int(raw)
        except ValueError as exc:
            raise ValidationError(f"Invalid Slow_queries value: {raw!r}") from exc

        uptime = self._read_uptime(status)
        detail = f"{slow} slow queries since server start"
        if uptime > 0:
            rate = slow * 3600.0 / uptime
            detail = f"{detail} ({rate:.2f}/hour over {uptime} seconds)"
        details: list[str] = [detail]
        result: ServiceResult = {"value": slow, "details": details, "uom": "c"}

        self.logger.info(f"Slow queries: {slow}")
        self.logger.method_exit("get_result", result)
        return result

    @staticmethod
    def _read_uptime(status: dict[str, str]) -> int:
        """Read the Uptime counter, tolerating a missing or invalid value."""
        try:
            return int(status.get("Uptime", "0"))
        except ValueError:
            return 0
