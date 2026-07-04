"""CLI integration tests using Click's CliRunner.

The MySQLClient query methods are patched at class level, so the whole
CLI stack (click parsing, config loading, service, Nagios runner) runs
for real without any MySQL server.
"""

import pytest
from click.testing import CliRunner

from check_mysql.cli import main
from check_mysql.core.mysql_client import MySQLClient
from tests.fixtures.mock_mysql_client import load_fixture_data

_DATA = load_fixture_data()

_INI = """[mysql]
host = 127.0.0.1
user = monitoring
password = secret
"""


@pytest.fixture
def config_file(tmp_path):
    """Write a minimal config file and return its path."""
    ini = tmp_path / "check_mysql.ini"
    ini.write_text(_INI)
    return str(ini)


def _patch_client(monkeypatch, **methods):
    """Patch MySQLClient query methods so no server is needed."""
    for name, value in methods.items():
        monkeypatch.setattr(MySQLClient, name, lambda self, _value=value: _value)


class TestUptimeCommand:
    """End-to-end runs of the uptime command."""

    def test_ok(self, config_file, monkeypatch):
        """A long-running server exits 0 with perfdata."""
        _patch_client(monkeypatch, get_global_status={"Uptime": "864000"})
        result = CliRunner().invoke(main, ["uptime", "-c", config_file])
        assert result.exit_code == 0
        assert "MYSQL OK" in result.output
        assert "uptime=864000" in result.output

    def test_recent_restart_is_critical(self, config_file, monkeypatch):
        """An uptime below the default 300: range exits 2."""
        _patch_client(monkeypatch, get_global_status={"Uptime": "60"})
        result = CliRunner().invoke(main, ["uptime", "-c", config_file])
        assert result.exit_code == 2
        assert "MYSQL CRITICAL" in result.output

    def test_threshold_override(self, config_file, monkeypatch):
        """Explicit -W/-C ranges replace the defaults."""
        _patch_client(monkeypatch, get_global_status={"Uptime": "60"})
        result = CliRunner().invoke(
            main, ["uptime", "-c", config_file, "-W", "100:", "-C", "10:"]
        )
        assert result.exit_code == 1
        assert "MYSQL WARNING" in result.output


class TestConnectionsCommand:
    """End-to-end runs of the connections command."""

    def test_warning_above_80_percent(self, config_file, monkeypatch):
        """130 of 151 connections (86%) trips the default warning."""
        _patch_client(
            monkeypatch,
            get_global_status={"Threads_connected": "130"},
            get_global_variables={"max_connections": "151"},
        )
        result = CliRunner().invoke(main, ["connections", "-c", config_file])
        assert result.exit_code == 1
        assert "130/151" in result.output


class TestReplicationCommand:
    """End-to-end runs of the replication command."""

    def test_not_a_replica_is_unknown(self, config_file, monkeypatch):
        """A server without replication status exits 3."""
        _patch_client(monkeypatch, get_replica_status=None)
        result = CliRunner().invoke(main, ["replication", "-c", config_file])
        assert result.exit_code == 3
        assert "UNKNOWN" in result.output

    def test_stopped_threads_are_critical(self, config_file, monkeypatch):
        """Stopped replication threads exit 2 regardless of thresholds."""
        _patch_client(monkeypatch, get_replica_status=_DATA["replica_status_broken"])
        result = CliRunner().invoke(main, ["replication", "-c", config_file])
        assert result.exit_code == 2
        assert "Replication threads stopped" in result.output

    def test_healthy_replica_is_ok(self, config_file, monkeypatch):
        """A healthy replica with low lag exits 0."""
        _patch_client(monkeypatch, get_replica_status=_DATA["replica_status_healthy"])
        result = CliRunner().invoke(main, ["replication", "-c", config_file])
        assert result.exit_code == 0
        assert "replication=3" in result.output


class TestSlowQueriesCommand:
    """End-to-end runs of the slowqueries command."""

    def test_ok(self, config_file, monkeypatch):
        """A low counter exits 0 with perfdata."""
        _patch_client(
            monkeypatch,
            get_global_status={"Slow_queries": "12", "Uptime": "864000"},
        )
        result = CliRunner().invoke(main, ["slowqueries", "-c", config_file])
        assert result.exit_code == 0
        assert "slowqueries=12" in result.output


class TestLatencyCommand:
    """End-to-end runs of the latency command."""

    def test_ok(self, config_file, monkeypatch):
        """A fast ping exits 0 with a ms perfdata unit."""
        _patch_client(monkeypatch, ping=3.42)
        result = CliRunner().invoke(main, ["latency", "-c", config_file])
        assert result.exit_code == 0
        assert "latency=3.42ms" in result.output


class TestCliSurface:
    """Cross-command CLI behaviour."""

    def test_missing_config_is_unknown(self):
        """A missing configuration file exits 3, never a traceback."""
        result = CliRunner().invoke(main, ["uptime", "-c", "/nonexistent/x.ini"])
        assert result.exit_code == 3
        assert "UNKNOWN" in result.output

    def test_version(self):
        """--version prints the program name and version."""
        result = CliRunner().invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "check_mysql" in result.output

    def test_help_lists_all_commands(self):
        """--help lists the five check commands."""
        result = CliRunner().invoke(main, ["--help"])
        assert result.exit_code == 0
        for command in (
            "uptime",
            "connections",
            "replication",
            "slowqueries",
            "latency",
        ):
            assert command in result.output
