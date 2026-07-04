"""Arbitrary SQL scalar service implementation."""

from __future__ import annotations

from check_mysql.core.logging_config import get_verbose_logger
from check_mysql.core.models import MySQLClientProtocol, ServiceResult


class SqlService:
    """Service checking the scalar result of an arbitrary SQL statement."""

    def __init__(
        self,
        statement: str,
        client: MySQLClientProtocol,
        verbose_level: int = 0,
    ) -> None:
        """Initialize with the SQL statement and a MySQL client."""
        self.statement = statement
        self.client = client
        self.logger = get_verbose_logger(__name__, verbose_level)

    def get_result(self) -> ServiceResult:
        """Return the first column of the statement's first row as the value."""
        self.logger.method_entry("get_result")

        value = self.client.query_scalar(self.statement)
        details: list[str] = [f"SQL result: {value:g} ({self.statement})"]
        result: ServiceResult = {"value": value, "details": details}

        self.logger.info(f"SQL result: {value}")
        self.logger.method_exit("get_result", result)
        return result
