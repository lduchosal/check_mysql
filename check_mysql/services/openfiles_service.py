"""Open files service implementation."""

from __future__ import annotations

from check_mysql.core.exceptions import ValidationError
from check_mysql.core.logging_config import get_verbose_logger
from check_mysql.core.models import MySQLClientProtocol, ServiceResult
from check_mysql.core.status import read_int


class OpenFilesService:
    """Service checking Open_files against open_files_limit."""

    def __init__(self, client: MySQLClientProtocol, verbose_level: int = 0) -> None:
        """Initialize with a MySQL client."""
        self.client = client
        self.logger = get_verbose_logger(__name__, verbose_level)

    def get_result(self) -> ServiceResult:
        """
        Return the open files usage as a percentage of open_files_limit.

        Raises:
            ValidationError: If the server does not report a positive limit.
        """
        self.logger.method_entry("get_result")

        status = self.client.get_global_status()
        variables = self.client.get_global_variables()

        used = read_int(status, "Open_files")
        limit = read_int(variables, "open_files_limit")
        if limit <= 0:
            raise ValidationError(f"Invalid open_files_limit value: {limit}")

        percent = round(used * 100.0 / limit, 2)
        details: list[str] = [
            f"Open files: {used}/{limit} ({percent}% of open_files_limit)"
        ]
        result: ServiceResult = {"value": percent, "details": details, "uom": "%"}

        self.logger.info(f"Open files usage: {used}/{limit} ({percent}%)")
        self.logger.method_exit("get_result", result)
        return result
