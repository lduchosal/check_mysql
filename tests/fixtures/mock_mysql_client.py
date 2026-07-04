"""Mock MySQL client for service tests."""

import json
from pathlib import Path
from typing import Any, Optional


def load_fixture_data() -> dict[str, Any]:
    """Load the shared fixture data file."""
    with (Path(__file__).parent / "status_data.json").open() as handle:
        return json.load(handle)


class MockMySQLClient:
    """Mock MySQL client backed by fixture data.

    Satisfies MySQLClientProtocol without any server; every dataset can be
    overridden per test.
    """

    def __init__(
        self,
        status: Optional[dict[str, str]] = None,
        variables: Optional[dict[str, str]] = None,
        replica_status: Optional[dict[str, Any]] = None,
        ping_ms: float = 3.42,
        versions: Optional[dict[str, str]] = None,
        processlist: Optional[list[dict[str, Any]]] = None,
        scalar: float = 42.0,
    ):
        """Initialize with fixture data, defaulting to status_data.json."""
        data = load_fixture_data()
        self.status: dict[str, str] = (
            status if status is not None else data["global_status"]
        )
        self.variables: dict[str, str] = (
            variables if variables is not None else data["global_variables"]
        )
        self.replica_status = replica_status
        self.ping_ms = ping_ms
        self.versions: dict[str, str] = (
            versions
            if versions is not None
            else {"client": "1.1.1", "server": self.variables.get("version", "")}
        )
        self.processlist: list[dict[str, Any]] = (
            processlist if processlist is not None else data["processlist"]
        )
        self.scalar = scalar
        self.last_scalar_query: Optional[str] = None

    def get_global_status(self) -> dict[str, str]:
        """Return the fixture global status."""
        return self.status

    def get_global_variables(self) -> dict[str, str]:
        """Return the fixture global variables."""
        return self.variables

    def get_replica_status(self) -> Optional[dict[str, Any]]:
        """Return the fixture replication status."""
        return self.replica_status

    def get_versions(self) -> dict[str, str]:
        """Return the fixture client and server versions."""
        return self.versions

    def get_processlist(self) -> list[dict[str, Any]]:
        """Return the fixture processlist."""
        return self.processlist

    def query_scalar(self, query: str) -> float:
        """Record the query and return the fixture scalar."""
        self.last_scalar_query = query
        return self.scalar

    def ping(self) -> float:
        """Return the fixture latency."""
        return self.ping_ms
