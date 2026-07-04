"""Uptime service implementation."""

from __future__ import annotations

import datetime

from check_mysql.core.exceptions import ValidationError
from check_mysql.core.logging_config import get_verbose_logger
from check_mysql.core.models import MySQLClientProtocol, ServiceResult


class UptimeService:
    """Service checking the seconds elapsed since the MySQL server started."""

    def __init__(self, client: MySQLClientProtocol, verbose_level: int = 0) -> None:
        """Initialize with a MySQL client."""
        self.client = client
        self.logger = get_verbose_logger(__name__, verbose_level)

    def get_result(self) -> ServiceResult:
        """
        Return the server uptime in seconds with a human-readable detail line.

        Raises:
            ValidationError: If the server does not report a numeric Uptime.
        """
        self.logger.method_entry("get_result")

        raw = self.client.get_global_status().get("Uptime")
        if raw is None:
            raise ValidationError("No Uptime in SHOW GLOBAL STATUS")
        try:
            uptime = int(raw)
        except ValueError as exc:
            raise ValidationError(f"Invalid Uptime value: {raw!r}") from exc

        human = str(datetime.timedelta(seconds=uptime))
        details: list[str] = [f"Server up for {human} ({uptime} seconds)"]
        result: ServiceResult = {"value": uptime, "details": details, "uom": "s"}

        self.logger.info(f"Server uptime: {uptime} seconds")
        self.logger.method_exit("get_result", result)
        return result
