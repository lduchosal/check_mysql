"""
CLI integration tests using Click's CliRunner.

The MySQLClient query methods are patched at class level, so the whole CLI stack (click parsing,
config loading, service, Nagios runner) runs for real without any MySQL server.
"""

import pytest
from click.testing import CliRunner

from check_mysql.cli import main
from check_mysql.core.config import get_ssh_config, load_config
from check_mysql.core.exceptions import MySQLConnectionError
from check_mysql.core.mysql_client import MySQLClient
from check_mysql.services.counter_service import COUNTER_SPECS
from check_mysql.services.ratio_service import RATIO_SPECS
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


class TestPingCommand:
    """End-to-end runs of the ping command."""

    def test_ok_reports_versions(self, config_file, monkeypatch):
        """A reachable server exits 0 with both versions in the headline."""
        _patch_client(
            monkeypatch,
            ping=1.23,
            get_versions={"client": "1.1.1", "server": "8.4.0-MariaDB"},
        )
        result = CliRunner().invoke(main, ["ping", "-c", config_file])
        assert result.exit_code == 0
        assert "client PyMySQL 1.1.1, server 8.4.0-MariaDB" in result.output
        assert "ping=1.23ms" in result.output

    def test_unreachable_server_is_critical(self, config_file, monkeypatch):
        """A connection failure exits 2 (CRITICAL), not 3 (UNKNOWN)."""

        def refuse(self):
            """Raise like the connector on a refused connection."""
            raise MySQLConnectionError(
                "Cannot connect to MySQL at 127.0.0.1:3306: refused"
            )

        monkeypatch.setattr(MySQLClient, "ping", refuse)
        result = CliRunner().invoke(main, ["ping", "-c", config_file])
        assert result.exit_code == 2
        assert "MYSQL CRITICAL" in result.output
        assert "Cannot connect" in result.output


class TestInitYes:
    """End-to-end runs of init --yes (non-interactive)."""

    def test_creates_a_default_config(self, tmp_path):
        """Init writes the template, prints the SQL and the next steps."""
        target = tmp_path / "check_mysql.ini"
        result = CliRunner().invoke(main, ["init", "-c", str(target), "--yes"])
        assert result.exit_code == 0
        assert "Created" in result.output
        assert "CREATE USER IF NOT EXISTS 'nagios'@'%'" in result.output
        assert target.stat().st_mode & 0o777 == 0o600
        assert "[mysql]" in target.read_text()

    def test_refuses_to_overwrite(self, tmp_path):
        """Init exits 1 and keeps the existing file intact."""
        target = tmp_path / "check_mysql.ini"
        target.write_text("[mysql]\nhost = keep-me\n")
        result = CliRunner().invoke(main, ["init", "-c", str(target), "--yes"])
        assert result.exit_code == 1
        assert "keep-me" in target.read_text()

    def test_force_overwrites(self, tmp_path):
        """Init --force replaces the existing file."""
        target = tmp_path / "check_mysql.ini"
        target.write_text("[mysql]\nhost = old\n")
        result = CliRunner().invoke(
            main, ["init", "-c", str(target), "--yes", "--force"]
        )
        assert result.exit_code == 0
        assert "change-me" in target.read_text()

    def test_generated_config_feeds_the_checks(self, tmp_path, monkeypatch):
        """A check command runs against the generated configuration."""
        target = tmp_path / "check_mysql.ini"
        CliRunner().invoke(main, ["init", "-c", str(target), "--yes"])
        _patch_client(monkeypatch, get_global_status={"Uptime": "864000"})
        result = CliRunner().invoke(main, ["uptime", "-c", str(target)])
        assert result.exit_code == 0
        assert "MYSQL OK" in result.output


class TestInitGuided:
    """End-to-end runs of the guided (interactive) init."""

    def test_defaults_direct_connection(self, tmp_path):
        """Enter-through defaults produce a direct-connection config."""
        target = tmp_path / "check_mysql.ini"
        answers = "\n\n\nS3cret\nn\nn\nn\n"
        result = CliRunner().invoke(main, ["init", "-c", str(target)], input=answers)
        assert result.exit_code == 0
        content = target.read_text()
        assert "host = localhost" in content
        assert "password = S3cret" in content
        assert "#[ssh]" in content
        assert "CREATE USER IF NOT EXISTS 'nagios'@'%'" in result.output
        assert "Setup complete" in result.output

    def test_ssh_tunnel_settings(self, tmp_path):
        """Answering yes to the bastion writes an active [ssh] section."""
        target = tmp_path / "check_mysql.ini"
        answers = "\n".join(
            [
                "10.0.0.12",  # MySQL host (seen from the bastion)
                "",  # port 3306
                "",  # monitoring user
                "pw",  # monitoring password
                "y",  # SSH tunnel?
                "bastion.example.com",
                "",  # SSH port 22
                "tunnel",  # SSH user
                "",  # private key default
                "n",  # create user?
                "n",  # test connection?
            ]
        )
        result = CliRunner().invoke(
            main, ["init", "-c", str(target)], input=answers + "\n"
        )
        assert result.exit_code == 0

        config = load_config(str(target))
        ssh = get_ssh_config(config)
        assert ssh is not None
        assert ssh.host == "bastion.example.com"
        assert ssh.port == 22
        assert ssh.user == "tunnel"
        assert ssh.private_key is not None
        assert ssh.private_key.endswith(".ssh/id_ed25519")

    def test_creates_the_monitoring_user(self, tmp_path, monkeypatch):
        """Saying yes provisions the user through the (faked) connector."""
        connections = []

        class FakeConnection:
            """Connection recording the provisioning statements."""

            def __init__(self):
                self.executed = []
                self.committed = False
                connections.append(self)

            def cursor(self, cursor_class=None):
                """Return self as a naive cursor."""
                del cursor_class
                return self

            def execute(self, query, args=None):
                """Record the statement."""
                self.executed.append((query, args))
                return 0

            def commit(self):
                """Record the commit."""
                self.committed = True

            def close(self):
                """Do nothing."""

            def __enter__(self):
                """Enter the cursor context."""
                return self

            def __exit__(self, *args):
                """Exit the cursor context."""

        class FakeConnector:
            """Connector recording the admin credentials used."""

            instances = []

            def __init__(self, mysql_config, ssh_config=None, verbose_level=0):
                self.mysql_config = mysql_config
                self.ssh_config = ssh_config
                FakeConnector.instances.append(self)

            def open(self):
                """Return a recording connection."""
                return FakeConnection()

            def close(self):
                """Do nothing."""

        monkeypatch.setattr(
            "check_mysql.cli.commands.init.MySQLConnector", FakeConnector
        )
        target = tmp_path / "check_mysql.ini"
        answers = "\n\n\npw\nn\ny\n\nadminpw\nn\n"
        result = CliRunner().invoke(main, ["init", "-c", str(target)], input=answers)

        assert result.exit_code == 0
        assert "Monitoring user 'nagios' created and granted." in result.output
        admin = FakeConnector.instances[0].mysql_config
        assert admin.user == "root"
        assert admin.password == "adminpw"
        queries = [query for query, _ in connections[0].executed]
        assert queries[0].startswith("CREATE USER IF NOT EXISTS 'nagios'@'%%'")
        assert connections[0].executed[0][1] == ("pw",)
        assert connections[0].committed is True

    def test_tests_the_connection(self, tmp_path, monkeypatch):
        """Saying yes to the test probes the server and reports latency."""
        _patch_client(monkeypatch, ping=3.42, get_global_status={"Uptime": "864000"})
        target = tmp_path / "check_mysql.ini"
        answers = "\n\n\npw\nn\nn\ny\n"
        result = CliRunner().invoke(main, ["init", "-c", str(target)], input=answers)
        assert result.exit_code == 0
        assert "Connection OK" in result.output
        assert "3.42 ms" in result.output
        assert "864000 seconds" in result.output

    def test_failed_user_creation_exits_1(self, tmp_path, monkeypatch):
        """A provisioning failure is reported and flips the exit code."""

        class FailingConnector:
            """Connector whose open always fails."""

            def __init__(self, mysql_config, ssh_config=None, verbose_level=0):
                pass

            def open(self):
                """Refuse the connection."""
                raise RuntimeError("access denied for admin")

            def close(self):
                """Do nothing."""

        monkeypatch.setattr(
            "check_mysql.cli.commands.init.MySQLConnector", FailingConnector
        )
        target = tmp_path / "check_mysql.ini"
        answers = "\n\n\npw\nn\ny\n\nadminpw\nn\n"
        result = CliRunner().invoke(main, ["init", "-c", str(target)], input=answers)
        assert result.exit_code == 1
        assert "Setup finished with errors" in result.output


_HEALTH_COMMANDS = (
    [spec.command for spec in RATIO_SPECS]
    + [spec.command for spec in COUNTER_SPECS]
    + ["openfiles"]
)


class TestHealthCommands:
    """End-to-end runs of the commands backported from check_mysql_health."""

    @pytest.mark.parametrize("command", _HEALTH_COMMANDS)
    def test_healthy_fixture_is_ok(self, config_file, monkeypatch, command):
        """Every counter-based command exits 0 on the healthy fixture."""
        _patch_client(
            monkeypatch,
            get_global_status=_DATA["global_status"],
            get_global_variables=_DATA["global_variables"],
        )
        result = CliRunner().invoke(main, [command, "-c", config_file])
        assert result.exit_code == 0, result.output
        assert f"{command}=" in result.output

    def test_querycache_missing_on_mysql8_is_unknown(self, config_file, monkeypatch):
        """MySQL 8 (no query cache counters) exits 3 with a hint."""
        _patch_client(monkeypatch, get_global_status={"Com_select": "10"})
        result = CliRunner().invoke(main, ["querycache", "-c", config_file])
        assert result.exit_code == 3
        assert "query cache removed in MySQL 8.0" in result.output

    def test_low_keycache_hitrate_is_critical(self, config_file, monkeypatch):
        """A 90% key cache hitrate breaches the default 95: critical."""
        _patch_client(
            monkeypatch,
            get_global_status={"Key_reads": "100", "Key_read_requests": "1000"},
        )
        result = CliRunner().invoke(main, ["keycache", "-c", config_file])
        assert result.exit_code == 2
        assert "MYSQL CRITICAL" in result.output

    def test_threadcache_warning_between_thresholds(self, config_file, monkeypatch):
        """An 85% thread cache hitrate sits between 90: and 80:."""
        _patch_client(
            monkeypatch,
            get_global_status={"Threads_created": "1500", "Connections": "10000"},
        )
        result = CliRunner().invoke(main, ["threadcache", "-c", config_file])
        assert result.exit_code == 1
        assert "MYSQL WARNING" in result.output

    def test_high_logwaits_rate_is_critical(self, config_file, monkeypatch):
        """20 log waits per second breach the default critical of 10."""
        _patch_client(
            monkeypatch,
            get_global_status={"Innodb_log_waits": "2000", "Uptime": "100"},
        )
        result = CliRunner().invoke(main, ["logwaits", "-c", config_file])
        assert result.exit_code == 2
        assert "logwaits=20" in result.output


class TestLongRunningCommand:
    """End-to-end runs of the longrunning command."""

    def test_ok(self, config_file, monkeypatch):
        """One long-running query stays under the default thresholds."""
        _patch_client(monkeypatch, get_processlist=_DATA["processlist"])
        result = CliRunner().invoke(main, ["longrunning", "-c", config_file])
        assert result.exit_code == 0
        assert "longrunning=1" in result.output

    def test_many_long_queries_are_critical(self, config_file, monkeypatch):
        """25 long-running queries breach the default critical of 20."""
        rows = [{"Id": i, "Command": "Query", "Time": 300} for i in range(25)]
        _patch_client(monkeypatch, get_processlist=rows)
        result = CliRunner().invoke(main, ["longrunning", "-c", config_file])
        assert result.exit_code == 2
        assert "longrunning=25" in result.output


class TestSecurityCommand:
    """End-to-end runs of the security command."""

    def test_clean_accounts_are_ok(self, config_file, monkeypatch):
        """The hardened fixture reports zero risky accounts."""
        _patch_client(monkeypatch, get_user_accounts=_DATA["user_accounts"])
        result = CliRunner().invoke(main, ["security", "-c", config_file])
        assert result.exit_code == 0
        assert "security=0" in result.output
        assert "0 risky accounts" in result.output

    def test_one_risky_account_is_warning(self, config_file, monkeypatch):
        """A single finding breaches the default warning of 0."""
        rows = _DATA["user_accounts"] + [
            {
                "User": "root",
                "Host": "10.0.0.5",
                "Super_priv": "Y",
                "plugin": "caching_sha2_password",
                "authentication_string": "$A$005$hash",
                "account_locked": "N",
            }
        ]
        _patch_client(monkeypatch, get_user_accounts=rows)
        result = CliRunner().invoke(main, ["security", "-c", config_file])
        assert result.exit_code == 1
        assert "security=1" in result.output
        assert "'root'@'10.0.0.5'" in result.output

    def test_many_risky_accounts_are_critical(self, config_file, monkeypatch):
        """Six risky accounts breach the default critical of 5."""
        rows = [
            {
                "User": f"app{i}",
                "Host": "%",
                "plugin": "caching_sha2_password",
                "authentication_string": "$A$005$hash",
                "account_locked": "N",
            }
            for i in range(6)
        ]
        _patch_client(monkeypatch, get_user_accounts=rows)
        result = CliRunner().invoke(main, ["security", "-c", config_file])
        assert result.exit_code == 2
        assert "security=6" in result.output

    def test_monitoring_user_wildcard_is_exempt(self, config_file, monkeypatch):
        """The [mysql] user itself is not flagged for its % host scope."""
        rows = [
            {
                "User": "monitoring",
                "Host": "%",
                "plugin": "caching_sha2_password",
                "authentication_string": "$A$005$hash",
                "account_locked": "N",
            }
        ]
        _patch_client(monkeypatch, get_user_accounts=rows)
        result = CliRunner().invoke(main, ["security", "-c", config_file])
        assert result.exit_code == 0
        assert "security=0" in result.output

    def test_allowlist_from_the_ini_exempts_accounts(self, tmp_path, monkeypatch):
        """[security] allow silences a known account without escaping the %."""
        ini = tmp_path / "check_mysql.ini"
        ini.write_text(_INI + "\n[security]\nallow = app@%\n")
        rows = [
            {
                "User": "app",
                "Host": "%",
                "plugin": "caching_sha2_password",
                "authentication_string": "$A$005$hash",
                "account_locked": "N",
            }
        ]
        _patch_client(monkeypatch, get_user_accounts=rows)
        result = CliRunner().invoke(main, ["security", "-c", str(ini)])
        assert result.exit_code == 0
        assert "security=0" in result.output


class TestSqlCommand:
    """End-to-end runs of the sql command."""

    def test_ok_without_thresholds(self, config_file, monkeypatch):
        """Without -W/-C even a negative scalar reports OK."""
        monkeypatch.setattr(MySQLClient, "query_scalar", lambda self, query: -7.0)
        result = CliRunner().invoke(
            main, ["sql", "-c", config_file, "--sql", "SELECT -7"]
        )
        assert result.exit_code == 0
        assert "MYSQL OK" in result.output

    def test_thresholds_apply(self, config_file, monkeypatch):
        """An explicit warning range flags the result."""
        monkeypatch.setattr(MySQLClient, "query_scalar", lambda self, query: 42.0)
        result = CliRunner().invoke(
            main,
            ["sql", "-c", config_file, "--sql", "SELECT 42", "-W", "10", "-C", "100"],
        )
        assert result.exit_code == 1
        assert "sql=42" in result.output

    def test_sql_option_is_required(self, config_file):
        """Omitting --sql is a usage error."""
        result = CliRunner().invoke(main, ["sql", "-c", config_file])
        assert result.exit_code == 2
        assert "Missing option" in result.output


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
        """--help lists every check command."""
        result = CliRunner().invoke(main, ["--help"])
        assert result.exit_code == 0
        for command in (
            "ping",
            "uptime",
            "connections",
            "replication",
            "slowqueries",
            "latency",
            *_HEALTH_COMMANDS,
            "longrunning",
            "security",
            "sql",
        ):
            assert command in result.output
