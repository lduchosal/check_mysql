"""Unit tests for the MySQL client."""

import pymysql
import pytest

from check_mysql.core.exceptions import QueryError
from check_mysql.core.mysql_client import MySQLClient


class FakeCursor:
    """Cursor returning canned rows per query."""

    def __init__(self, rows_by_query, executed):
        """Initialize with a query→rows mapping and a shared execution log."""
        self.rows_by_query = rows_by_query
        self.executed = executed
        self.rows = []

    def execute(self, query, args=None):
        """Record the query and select the canned rows."""
        del args
        self.executed.append(query)
        result = self.rows_by_query.get(query)
        if isinstance(result, Exception):
            raise result
        self.rows = result if result is not None else []
        return len(self.rows)

    def fetchall(self):
        """Return the canned rows."""
        return self.rows

    def fetchone(self):
        """Return the first canned row, if any."""
        return self.rows[0] if self.rows else None

    def __enter__(self):
        """Enter the context manager."""
        return self

    def __exit__(self, *args):
        """Exit the context manager."""


class FakeConnection:
    """Connection handing out FakeCursors."""

    def __init__(self, rows_by_query):
        """Initialize with a query→rows mapping."""
        self.rows_by_query = rows_by_query
        self.executed = []
        self.closed = False

    def cursor(self, cursor_class=None):
        """Return a FakeCursor (cursor class is irrelevant here)."""
        del cursor_class
        return FakeCursor(self.rows_by_query, self.executed)

    def close(self):
        """Mark the connection as closed."""
        self.closed = True


class FakeConnector:
    """Connector returning a prepared FakeConnection."""

    def __init__(self, connection):
        """Initialize with the connection to hand out."""
        self.connection = connection
        self.opened = 0
        self.closed = False

    def open(self):
        """Return the prepared connection."""
        self.opened += 1
        return self.connection

    def close(self):
        """Mark the connector as closed."""
        self.closed = True


def _client(rows_by_query):
    """Build a MySQLClient over a fake connection with canned rows."""
    connection = FakeConnection(rows_by_query)
    connector = FakeConnector(connection)
    return MySQLClient(connector), connection, connector


class TestFetchPairs:
    """Tests for the SHOW ... name/value queries."""

    def test_get_global_status(self):
        """Tuple rows become a name/value mapping."""
        client, connection, _ = _client(
            {"SHOW GLOBAL STATUS": [("Uptime", "864000"), ("Threads_connected", "42")]}
        )
        status = client.get_global_status()
        assert status == {"Uptime": "864000", "Threads_connected": "42"}
        assert connection.executed == ["SHOW GLOBAL STATUS"]

    def test_get_global_variables(self):
        """Variables go through the same two-column path."""
        client, _, _ = _client({"SHOW GLOBAL VARIABLES": [("max_connections", "151")]})
        assert client.get_global_variables() == {"max_connections": "151"}

    def test_connection_opens_once(self):
        """The lazy connection is reused across queries."""
        client, _, connector = _client(
            {
                "SHOW GLOBAL STATUS": [("Uptime", "1")],
                "SHOW GLOBAL VARIABLES": [("max_connections", "10")],
            }
        )
        client.get_global_status()
        client.get_global_variables()
        assert connector.opened == 1


class TestReplicaStatus:
    """Tests for the replica status query and its legacy fallback."""

    def test_returns_the_row(self):
        """The modern statement returns its row mapping."""
        row = {"Replica_IO_Running": "Yes"}
        client, _, _ = _client({"SHOW REPLICA STATUS": [row]})
        assert client.get_replica_status() == row

    def test_returns_none_when_not_a_replica(self):
        """An empty result means the server is not a replica."""
        client, _, _ = _client({"SHOW REPLICA STATUS": []})
        assert client.get_replica_status() is None

    def test_falls_back_to_show_slave_status(self):
        """Old servers rejecting REPLICA fall back to SLAVE."""
        row = {"Slave_IO_Running": "Yes"}
        client, connection, _ = _client(
            {
                "SHOW REPLICA STATUS": pymysql.ProgrammingError("syntax error"),
                "SHOW SLAVE STATUS": [row],
            }
        )
        assert client.get_replica_status() == row
        assert connection.executed == ["SHOW REPLICA STATUS", "SHOW SLAVE STATUS"]

    def test_both_statements_failing_raises(self):
        """A server accepting neither statement raises QueryError."""
        client, _, _ = _client(
            {
                "SHOW REPLICA STATUS": pymysql.ProgrammingError("syntax error"),
                "SHOW SLAVE STATUS": pymysql.ProgrammingError("syntax error"),
            }
        )
        with pytest.raises(QueryError, match="Neither"):
            client.get_replica_status()


class TestPing:
    """Tests for the latency probe."""

    def test_ping_measures_select_1(self):
        """Ping executes SELECT 1 and returns a positive duration."""
        client, connection, _ = _client({"SELECT 1": [(1,)]})
        elapsed = client.ping()
        assert elapsed > 0
        assert connection.executed == ["SELECT 1"]


class TestClose:
    """Tests for resource cleanup."""

    def test_close_shuts_everything_down(self):
        """Close closes the connection and the connector."""
        client, connection, connector = _client({"SELECT 1": [(1,)]})
        client.ping()
        client.close()
        assert connection.closed is True
        assert connector.closed is True

    def test_close_without_connection_is_safe(self):
        """Close before any query only closes the connector."""
        client, connection, connector = _client({})
        client.close()
        assert connection.closed is False
        assert connector.closed is True

    def test_context_manager_closes(self):
        """The context manager closes on exit."""
        client, connection, _ = _client({"SELECT 1": [(1,)]})
        with client:
            client.ping()
        assert connection.closed is True
