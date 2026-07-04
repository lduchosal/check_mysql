"""Connections service implementation."""

from __future__ import annotations

from check_mysql.core.exceptions import ValidationError
from check_mysql.core.logging_config import get_verbose_logger
from check_mysql.core.models import MySQLClientProtocol, ServiceResult


class ConnectionsService:
    """Service checking current connections against max_connections."""

    def __init__(self, client: MySQLClientProtocol, verbose_level: int = 0) -> None:
        """Initialize with a MySQL client."""
        self.client = client
        self.logger = get_verbose_logger(__name__, verbose_level)

    def get_result(self) -> ServiceResult:
        """
        Return the connection usage as a percentage of max_connections.

        Raises:
            ValidationError: If the server does not report the needed counters.
        """
        self.logger.method_entry("get_result")

        status = self.client.get_global_status()
        variables = self.client.get_global_variables()

        threads = self._read_int(status, "Threads_connected")
        maximum = self._read_int(variables, "max_connections")
        if maximum <= 0:
            raise ValidationError(f"Invalid max_connections value: {maximum}")

        percent = round(threads * 100.0 / maximum, 2)
        details: list[str] = [
            f"Connections: {threads}/{maximum} ({percent}% of max_connections)"
        ]
        result: ServiceResult = {"value": percent, "details": details, "uom": "%"}

        self.logger.info(f"Connection usage: {threads}/{maximum} ({percent}%)")
        self.logger.method_exit("get_result", result)
        return result

    @staticmethod
    def _read_int(mapping: dict[str, str], key: str) -> int:
        """
        Read an integer entry from a SHOW output mapping.

        Raises:
            ValidationError: If the entry is missing or not an integer.
        """
        raw = mapping.get(key)
        if raw is None:
            raise ValidationError(f"No {key} reported by the server")
        try:
            return int(raw)
        except ValueError as exc:
            raise ValidationError(f"Invalid {key} value: {raw!r}") from exc
