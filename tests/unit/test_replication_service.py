"""Unit tests for the replication service."""

import pytest

from check_mysql.core.exceptions import CriticalError, ValidationError
from check_mysql.services.replication_service import ReplicationService
from tests.fixtures.mock_mysql_client import MockMySQLClient, load_fixture_data

_DATA = load_fixture_data()


class TestReplicationService:
    """Tests for ReplicationService.get_result."""

    def test_healthy_replica_returns_lag(self):
        """A healthy replica returns Seconds_Behind_Source."""
        client = MockMySQLClient(replica_status=_DATA["replica_status_healthy"])
        result = ReplicationService(client).get_result()
        assert result["value"] == 3
        assert result["uom"] == "s"
        assert "db-primary.example.com" in result["details"][0]

    def test_legacy_columns_are_supported(self):
        """Old servers reporting Slave_*/Master_* columns work the same."""
        client = MockMySQLClient(replica_status=_DATA["replica_status_legacy"])
        result = ReplicationService(client).get_result()
        assert result["value"] == 7
        assert "db-primary.example.com" in result["details"][0]

    def test_not_a_replica_raises_validation_error(self):
        """A server without replication status raises ValidationError."""
        client = MockMySQLClient(replica_status=None)
        with pytest.raises(ValidationError, match="not a replica"):
            ReplicationService(client).get_result()

    def test_stopped_thread_raises_critical_error(self):
        """A stopped IO thread raises CriticalError with the last error."""
        client = MockMySQLClient(replica_status=_DATA["replica_status_broken"])
        with pytest.raises(CriticalError, match="IO: No"):
            ReplicationService(client).get_result()

    def test_stopped_thread_message_carries_last_error(self):
        """The CRITICAL message includes Last_IO_Error when present."""
        client = MockMySQLClient(replica_status=_DATA["replica_status_broken"])
        with pytest.raises(CriticalError, match="error connecting to source"):
            ReplicationService(client).get_result()

    def test_null_lag_raises_critical_error(self):
        """Running threads with a NULL lag raise CriticalError."""
        client = MockMySQLClient(replica_status=_DATA["replica_status_null_lag"])
        with pytest.raises(CriticalError, match="lag unknown"):
            ReplicationService(client).get_result()
