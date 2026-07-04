"""Unit tests for the monitoring-user provisioning."""

import pytest

from check_mysql.core.provisioning import (
    create_monitoring_user,
    monitoring_user_sql,
    monitoring_user_statements,
)


class FakeCursor:
    """Cursor recording executed statements."""

    def __init__(self, log, error=None):
        """Initialize with a shared execution log and an optional error."""
        self.log = log
        self.error = error

    def execute(self, query, args=None):
        """Record the statement or raise the canned error."""
        if self.error is not None:
            raise self.error
        self.log.append((query, args))
        return 0

    def __enter__(self):
        """Enter the context manager."""
        return self

    def __exit__(self, *args):
        """Exit the context manager."""


class FakeConnection:
    """Connection recording statements, commits and closes."""

    def __init__(self, error=None):
        """Initialize with an optional error raised on execute."""
        self.executed = []
        self.error = error
        self.committed = False
        self.closed = False

    def cursor(self, cursor_class=None):
        """Return a recording cursor."""
        del cursor_class
        return FakeCursor(self.executed, self.error)

    def commit(self):
        """Record the commit."""
        self.committed = True

    def close(self):
        """Record the close."""
        self.closed = True


class FakeConnector:
    """Connector handing out a prepared FakeConnection."""

    def __init__(self, connection):
        """Initialize with the connection to hand out."""
        self.connection = connection
        self.closed = False

    def open(self):
        """Return the prepared connection."""
        return self.connection

    def close(self):
        """Record the close."""
        self.closed = True


class TestStatements:
    """Tests for monitoring_user_statements."""

    def test_create_then_grant(self):
        """A CREATE USER (parameterized password) precedes the GRANT."""
        statements = monitoring_user_statements("monitoring")
        assert statements[0][0].startswith(
            "CREATE USER IF NOT EXISTS 'monitoring'@'%%'"
        )
        assert statements[0][0].endswith("IDENTIFIED BY %s")
        assert statements[0][1] is True
        assert "GRANT USAGE, REPLICATION CLIENT ON *.*" in statements[1][0]
        assert statements[1][1] is False
        assert "GRANT SELECT ON mysql.user" in statements[2][0]
        assert statements[2][1] is False

    def test_parameterized_statement_survives_pymysql_interpolation(self):
        """
        PyMySQL renders args with %; the literal '%' host scope must survive.

        Regression for the live failure: `unsupported format character '''
        (0x27)` — the single '%' of the host scope was read as a format
        specifier before the query ever reached the server.
        """
        query, needs_password = monitoring_user_statements("nagios")[0]
        assert needs_password is True
        rendered = query % ("'pw'",)
        assert rendered == "CREATE USER IF NOT EXISTS 'nagios'@'%' IDENTIFIED BY 'pw'"

    def test_grants_keep_a_single_percent(self):
        """The GRANTs run without args: no interpolation, single '%'."""
        statements = monitoring_user_statements("nagios")
        for query, _ in statements[1:]:
            assert "'nagios'@'%'" in query
            assert "%%" not in query

    def test_quotes_are_escaped(self):
        """Single quotes in user and host scope are doubled."""
        statements = monitoring_user_statements("mon'itor", "10.0.0.'1")
        assert "'mon''itor'@'10.0.0.''1'" in statements[0][0]


class TestPrintableSql:
    """Tests for monitoring_user_sql."""

    def test_block_is_copy_pasteable(self):
        """The block carries every statement, terminated by semicolons."""
        sql = monitoring_user_sql("monitoring", "s3cret")
        assert (
            "CREATE USER IF NOT EXISTS 'monitoring'@'%' IDENTIFIED BY 's3cret';" in sql
        )
        assert "GRANT USAGE, REPLICATION CLIENT ON *.* TO 'monitoring'@'%';" in sql
        assert "GRANT SELECT ON mysql.user TO 'monitoring'@'%';" in sql

    def test_password_quotes_are_escaped(self):
        """Single quotes in the password are doubled."""
        assert "IDENTIFIED BY 'pa''ss'" in monitoring_user_sql("m", "pa'ss")


class TestCreateMonitoringUser:
    """Tests for create_monitoring_user."""

    def test_executes_commits_and_closes(self):
        """Every statement runs, the password is bound, everything is released."""
        connection = FakeConnection()
        connector = FakeConnector(connection)

        create_monitoring_user(connector, "monitoring", "s3cret")

        queries = [query for query, _ in connection.executed]
        assert queries[0].startswith("CREATE USER IF NOT EXISTS")
        assert queries[1].startswith("GRANT USAGE, REPLICATION CLIENT")
        assert queries[2].startswith("GRANT SELECT ON mysql.user")
        assert connection.executed[0][1] == ("s3cret",)
        assert connection.executed[1][1] is None
        assert connection.executed[2][1] is None
        assert connection.committed is True
        assert connection.closed is True
        assert connector.closed is True

    def test_resources_released_on_failure(self):
        """A failing statement still closes the connection and the tunnel."""
        connection = FakeConnection(error=RuntimeError("access denied"))
        connector = FakeConnector(connection)

        with pytest.raises(RuntimeError, match="access denied"):
            create_monitoring_user(connector, "monitoring", "s3cret")

        assert connection.committed is False
        assert connection.closed is True
        assert connector.closed is True
