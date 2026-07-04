"""Ping service implementation."""

from __future__ import annotations

from check_mysql.core.exceptions import (
    CriticalError,
    MySQLConnectionError,
    SSHTunnelError,
)
from check_mysql.core.logging_config import get_verbose_logger
from check_mysql.core.models import MySQLClientProtocol, ServiceResult


class PingService:
    """Service checking connectivity and reporting client and server versions."""

    def __init__(self, client: MySQLClientProtocol, verbose_level: int = 0) -> None:
        """Initialize with a MySQL client."""
        self.client = client
        self.logger = get_verbose_logger(__name__, verbose_level)

    def get_result(self) -> ServiceResult:
        """
        Return the ping round-trip time with the client and server versions.

        Raises:
            CriticalError: If the server cannot be reached — for a ping check
                an unreachable server is CRITICAL, not UNKNOWN.
        """
        self.logger.method_entry("get_result")

        try:
            elapsed_ms = round(self.client.ping(), 2)
            versions = self.client.get_versions()
        except (MySQLConnectionError, SSHTunnelError) as exc:
            raise CriticalError(str(exc)) from exc

        details: list[str] = [
            f"client PyMySQL {versions['client']}, server {versions['server']}"
        ]
        result: ServiceResult = {"value": elapsed_ms, "details": details, "uom": "ms"}

        self.logger.info(f"{details[0]}; ping {elapsed_ms} ms")
        self.logger.method_exit("get_result", result)
        return result
