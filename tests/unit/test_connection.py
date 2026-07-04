"""Unit tests for the MySQL connector (direct and SSH tunnel)."""

import pymysql
import pytest

from check_mysql.core.connection import MySQLConnector
from check_mysql.core.exceptions import MySQLConnectionError, SSHTunnelError
from check_mysql.core.models import MySQLConfig, SSHConfig

_MYSQL = MySQLConfig(
    host="db.example.com",
    port=3307,
    user="monitoring",
    password="secret",
    database="appdb",
    timeout=5,
)
_SSH = SSHConfig(
    host="bastion.example.com",
    port=2222,
    user="tunnel",
    private_key="/home/x/.ssh/id_test",
)


class FakeConnection:
    """Minimal stand-in for a PyMySQL connection."""

    def close(self):
        """Do nothing."""


class FakeTunnel:
    """Minimal stand-in for sshtunnel.SSHTunnelForwarder."""

    instances = []

    def __init__(self, ssh_address_or_host, **kwargs):
        """Record constructor arguments."""
        self.ssh_address_or_host = ssh_address_or_host
        self.kwargs = kwargs
        self.local_bind_port = 12345
        self.started = False
        self.stopped = False
        FakeTunnel.instances.append(self)

    def start(self):
        """Mark the tunnel as started."""
        self.started = True

    def stop(self):
        """Mark the tunnel as stopped."""
        self.stopped = True


class FailingTunnel(FakeTunnel):
    """Tunnel whose start always fails."""

    def start(self):
        """Fail to start."""
        raise RuntimeError("ssh handshake failed")


@pytest.fixture(autouse=True)
def _reset_tunnels():
    """Reset the recorded FakeTunnel instances between tests."""
    FakeTunnel.instances = []


def _capture_connect(monkeypatch, captured, connection=None):
    """Patch pymysql.connect to record kwargs and return a fake connection."""

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return connection if connection is not None else FakeConnection()

    monkeypatch.setattr("check_mysql.core.connection.pymysql.connect", fake_connect)


class TestDirectConnection:
    """Tests for the direct (no tunnel) path."""

    def test_connects_with_configured_settings(self, monkeypatch):
        """PyMySQL receives the settings from the [mysql] section."""
        captured = {}
        _capture_connect(monkeypatch, captured)

        connection = MySQLConnector(_MYSQL).open()

        assert isinstance(connection, FakeConnection)
        assert captured["host"] == "db.example.com"
        assert captured["port"] == 3307
        assert captured["user"] == "monitoring"
        assert captured["password"] == "secret"
        assert captured["database"] == "appdb"
        assert captured["connect_timeout"] == 5

    def test_connect_failure_raises_connection_error(self, monkeypatch):
        """A PyMySQL error is wrapped in MySQLConnectionError."""

        def failing_connect(**kwargs):
            raise pymysql.MySQLError("access denied")

        monkeypatch.setattr(
            "check_mysql.core.connection.pymysql.connect", failing_connect
        )
        connector = MySQLConnector(_MYSQL)

        with pytest.raises(MySQLConnectionError, match="db.example.com:3307"):
            connector.open()


class TestTunnelConnection:
    """Tests for the SSH tunnel path."""

    def test_connects_through_the_tunnel(self, monkeypatch):
        """The tunnel targets the MySQL host and PyMySQL uses the local port."""
        monkeypatch.setattr(
            "check_mysql.core.connection.sshtunnel.SSHTunnelForwarder", FakeTunnel
        )
        captured = {}
        _capture_connect(monkeypatch, captured)
        connector = MySQLConnector(_MYSQL, _SSH)

        connector.open()

        tunnel = FakeTunnel.instances[0]
        assert tunnel.started is True
        assert tunnel.ssh_address_or_host == ("bastion.example.com", 2222)
        assert tunnel.kwargs["ssh_username"] == "tunnel"
        assert tunnel.kwargs["ssh_pkey"] == "/home/x/.ssh/id_test"
        assert tunnel.kwargs["remote_bind_address"] == ("db.example.com", 3307)
        assert captured["host"] == "127.0.0.1"
        assert captured["port"] == 12345

    def test_close_stops_the_tunnel(self, monkeypatch):
        """Closing the connector stops the tunnel exactly once."""
        monkeypatch.setattr(
            "check_mysql.core.connection.sshtunnel.SSHTunnelForwarder", FakeTunnel
        )
        _capture_connect(monkeypatch, {})
        connector = MySQLConnector(_MYSQL, _SSH)
        connector.open()

        connector.close()
        connector.close()

        tunnel = FakeTunnel.instances[0]
        assert tunnel.stopped is True

    def test_tunnel_failure_raises_ssh_tunnel_error(self, monkeypatch):
        """A tunnel start failure is wrapped in SSHTunnelError."""
        monkeypatch.setattr(
            "check_mysql.core.connection.sshtunnel.SSHTunnelForwarder", FailingTunnel
        )
        connector = MySQLConnector(_MYSQL, _SSH)

        with pytest.raises(SSHTunnelError, match="bastion.example.com"):
            connector.open()

    def test_mysql_failure_through_tunnel_stops_the_tunnel(self, monkeypatch):
        """When MySQL refuses the tunneled connection, the tunnel is torn down."""
        monkeypatch.setattr(
            "check_mysql.core.connection.sshtunnel.SSHTunnelForwarder", FakeTunnel
        )

        def failing_connect(**kwargs):
            raise pymysql.MySQLError("access denied")

        monkeypatch.setattr(
            "check_mysql.core.connection.pymysql.connect", failing_connect
        )
        connector = MySQLConnector(_MYSQL, _SSH)

        with pytest.raises(MySQLConnectionError):
            connector.open()

        assert FakeTunnel.instances[0].stopped is True
