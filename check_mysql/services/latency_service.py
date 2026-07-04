"""Latency service implementation."""

from __future__ import annotations

from check_mysql.core.logging_config import get_verbose_logger
from check_mysql.core.models import MySQLClientProtocol, ServiceResult


class LatencyService:
    """Service measuring the SELECT 1 round-trip latency."""

    def __init__(self, client: MySQLClientProtocol, verbose_level: int = 0) -> None:
        """Initialize with a MySQL client."""
        self.client = client
        self.logger = get_verbose_logger(__name__, verbose_level)

    def get_result(self) -> ServiceResult:
        """Return the SELECT 1 round-trip time in milliseconds."""
        self.logger.method_entry("get_result")

        elapsed_ms = round(self.client.ping(), 2)
        details: list[str] = [f"SELECT 1 completed in {elapsed_ms} ms"]
        result: ServiceResult = {"value": elapsed_ms, "details": details, "uom": "ms"}

        self.logger.info(f"Query latency: {elapsed_ms} ms")
        self.logger.method_exit("get_result", result)
        return result
