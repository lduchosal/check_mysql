"""Unit tests for the ping service."""

import pytest

from check_mysql.core.exceptions import CriticalError, MySQLConnectionError
from check_mysql.services.ping_service import PingService
from tests.fixtures.mock_mysql_client import MockMySQLClient


class TestPingService:
    """Tests for PingService.get_result."""

    def test_reports_client_and_server_versions(self):
        """The headline carries both versions; the value is the ping RTT."""
        client = MockMySQLClient(
            ping_ms=3.4567, versions={"client": "1.1.1", "server": "8.4.0"}
        )
        result = PingService(client).get_result()
        assert result["value"] == 3.46
        assert result["uom"] == "ms"
        assert result["details"] == ["client PyMySQL 1.1.1, server 8.4.0"]

    def test_defaults_to_the_fixture_server_version(self):
        """Without overrides the mock exposes the fixture server version."""
        result = PingService(MockMySQLClient()).get_result()
        assert "server 8.4.0" in result["details"][0]

    def test_unreachable_server_is_critical(self):
        """A connection failure surfaces as CriticalError, not a generic error."""

        class UnreachableClient(MockMySQLClient):
            """Mock client whose ping fails like a refused connection."""

            def ping(self) -> float:
                """Raise the connector's connection error."""
                raise MySQLConnectionError(
                    "Cannot connect to MySQL at 127.0.0.1:3306: refused"
                )

        with pytest.raises(CriticalError, match="Cannot connect"):
            PingService(UnreachableClient()).get_result()
