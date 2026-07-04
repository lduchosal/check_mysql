"""Unit tests for the connections service."""

import pytest

from check_mysql.core.exceptions import ValidationError
from check_mysql.services.connections_service import ConnectionsService
from tests.fixtures.mock_mysql_client import MockMySQLClient


class TestConnectionsService:
    """Tests for ConnectionsService.get_result."""

    def test_returns_percentage_of_max(self):
        """42 of 151 connections is 27.81 percent."""
        result = ConnectionsService(MockMySQLClient()).get_result()
        assert result["value"] == 27.81
        assert result["uom"] == "%"
        assert "42/151" in result["details"][0]

    def test_full_server_reads_100_percent(self):
        """Threads_connected equal to max_connections is 100 percent."""
        client = MockMySQLClient(
            status={"Threads_connected": "151"}, variables={"max_connections": "151"}
        )
        assert ConnectionsService(client).get_result()["value"] == 100.0

    def test_missing_threads_connected_raises(self):
        """A server not reporting Threads_connected raises ValidationError."""
        service = ConnectionsService(MockMySQLClient(status={}))
        with pytest.raises(ValidationError, match="No Threads_connected"):
            service.get_result()

    def test_missing_max_connections_raises(self):
        """A server not reporting max_connections raises ValidationError."""
        service = ConnectionsService(MockMySQLClient(variables={}))
        with pytest.raises(ValidationError, match="No max_connections"):
            service.get_result()

    def test_invalid_max_connections_raises(self):
        """A zero max_connections raises ValidationError."""
        client = MockMySQLClient(variables={"max_connections": "0"})
        with pytest.raises(ValidationError, match="Invalid max_connections"):
            ConnectionsService(client).get_result()

    def test_non_numeric_counter_raises(self):
        """A non-numeric Threads_connected raises ValidationError."""
        client = MockMySQLClient(status={"Threads_connected": "many"})
        with pytest.raises(ValidationError, match="Invalid Threads_connected"):
            ConnectionsService(client).get_result()
