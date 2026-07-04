"""Data models for check_mysql."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol, TypedDict

# ---------------------------------------------------------------------------
# Configuration dataclasses
# ---------------------------------------------------------------------------


@dataclass
class MySQLConfig:
    """MySQL connection settings read from the ``[mysql]`` section."""

    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: Optional[str] = None
    timeout: int = 10


@dataclass
class SSHConfig:
    """SSH tunnel settings read from the optional ``[ssh]`` section."""

    host: str
    port: int = 22
    user: str = ""
    password: Optional[str] = None
    private_key: Optional[str] = None


# ---------------------------------------------------------------------------
# Service result TypedDict
# ---------------------------------------------------------------------------


class _ServiceResultBase(TypedDict):
    """Required part of a service result: the probed value."""

    value: float


class ServiceResult(_ServiceResultBase, total=False):
    """Common service result shape."""

    details: list[str]
    uom: str


# ---------------------------------------------------------------------------
# Protocols (used by services and the Nagios runner instead of Any)
# ---------------------------------------------------------------------------


class MySQLClientProtocol(Protocol):
    """Protocol describing the MySQL client methods used by services."""

    def get_global_status(self) -> dict[str, str]:
        """Return SHOW GLOBAL STATUS as a name/value mapping."""
        ...

    def get_global_variables(self) -> dict[str, str]:
        """Return SHOW GLOBAL VARIABLES as a name/value mapping."""
        ...

    def get_replica_status(self) -> Optional[dict[str, Any]]:
        """Return SHOW REPLICA STATUS as a row mapping, or None when not a replica."""
        ...

    def get_versions(self) -> dict[str, str]:
        """Return the client (PyMySQL) and server version strings."""
        ...

    def get_processlist(self) -> list[dict[str, Any]]:
        """Return SHOW FULL PROCESSLIST as a list of row mappings."""
        ...

    def get_user_accounts(self) -> list[dict[str, Any]]:
        """Return the mysql.user rows (one per account) as a list of row mappings."""
        ...

    def query_scalar(self, query: str) -> float:
        """Run a query and return the first column of its first row as a float."""
        ...

    def ping(self) -> float:
        """Execute SELECT 1 and return the round-trip time in milliseconds."""
        ...


class CheckServiceProtocol(Protocol):
    """Protocol describing a check service consumed by the Nagios runner."""

    def get_result(self) -> ServiceResult:
        """Return the probed value with its detail lines."""
        ...
