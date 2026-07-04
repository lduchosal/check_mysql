"""Replication service implementation."""

from __future__ import annotations

from typing import Any

from check_mysql.core.exceptions import CriticalError, ValidationError
from check_mysql.core.logging_config import get_verbose_logger
from check_mysql.core.models import MySQLClientProtocol, ServiceResult


class ReplicationService:
    """Service checking replication lag and replication thread state.

    Handles both the modern (``Replica_*`` / ``Source_*``, MySQL >= 8.0.22)
    and the legacy (``Slave_*`` / ``Master_*``) column names.
    """

    def __init__(self, client: MySQLClientProtocol, verbose_level: int = 0) -> None:
        """Initialize with a MySQL client."""
        self.client = client
        self.logger = get_verbose_logger(__name__, verbose_level)

    def get_result(self) -> ServiceResult:
        """
        Return the replication lag in seconds behind the source.

        Raises:
            ValidationError: If the server is not configured as a replica.
            CriticalError: If a replication thread is stopped or the lag is
                unknown (NULL) — an immediate CRITICAL regardless of thresholds.
        """
        self.logger.method_entry("get_result")

        replica = self.client.get_replica_status()
        if not replica:
            raise ValidationError("Server is not a replica (no replication status)")

        io_running = str(self._pick(replica, "Replica_IO_Running", "Slave_IO_Running"))
        sql_running = str(
            self._pick(replica, "Replica_SQL_Running", "Slave_SQL_Running")
        )
        if io_running != "Yes" or sql_running != "Yes":
            raise CriticalError(self._stopped_message(replica, io_running, sql_running))

        behind = self._pick(replica, "Seconds_Behind_Source", "Seconds_Behind_Master")
        if behind is None:
            raise CriticalError(
                "Replication lag unknown (Seconds_Behind_Source is NULL)"
            )

        lag = int(behind)
        source = str(self._pick(replica, "Source_Host", "Master_Host") or "unknown")
        details: list[str] = [
            f"Replica of {source} - {lag} seconds behind, IO/SQL threads running"
        ]
        result: ServiceResult = {"value": lag, "details": details, "uom": "s"}

        self.logger.info(f"Replication lag: {lag} seconds behind {source}")
        self.logger.method_exit("get_result", result)
        return result

    @staticmethod
    def _pick(replica: dict[str, Any], modern: str, legacy: str) -> Any:
        """Read a column trying the modern name first, then the legacy one."""
        if modern in replica:
            return replica[modern]
        return replica.get(legacy)

    @staticmethod
    def _stopped_message(
        replica: dict[str, Any], io_running: str, sql_running: str
    ) -> str:
        """Build the CRITICAL message for stopped replication threads."""
        last_error = str(
            replica.get("Last_IO_Error")
            or replica.get("Last_SQL_Error")
            or replica.get("Last_Error")
            or ""
        ).strip()
        suffix = f": {last_error}" if last_error else ""
        return (
            f"Replication threads stopped "
            f"(IO: {io_running}, SQL: {sql_running}){suffix}"
        )
