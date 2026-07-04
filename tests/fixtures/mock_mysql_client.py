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

    def get_global_status(self) -> dict[str, str]:
        """Return the fixture global status."""
        return self.status

    def get_global_variables(self) -> dict[str, str]:
        """Return the fixture global variables."""
        return self.variables

    def get_replica_status(self) -> Optional[dict[str, Any]]:
        """Return the fixture replication status."""
        return self.replica_status

    def ping(self) -> float:
        """Return the fixture latency."""
        return self.ping_ms
