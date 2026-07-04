"""
End-to-end tests running the real CLI against the local MySQL server.

No mocks: every test drives the installed ``check_mysql`` binary as a subprocess with the
repository's ``check_mysql.ini`` — real config loading, real PyMySQL connection, real SQL, real
Nagios output and exit codes. Threshold ranges are chosen so the expected state is deterministic
whatever the server reports: ``1:`` accepts any live server, ``@0:HUGE`` alerts on any value,
``HUGE`` never alerts.

Excluded from the default pytest run (``-m "not e2e"`` in pytest.ini); ``pdm run test-e2e`` runs the
suite and gates ``pdm run publish`` and the publish.sh pipeline — a down server blocks the release,
by design.
"""

import subprocess
import sys

import pytest

from tests.e2e.conftest import CLI_BINARY, INI_PATH

pytestmark = pytest.mark.e2e

HUGE = "99999999999"


class TestEnvironment:
    """Preconditions for the E2E run."""

    def test_local_configuration_exists(self):
        """The local configuration must exist — create it with check_mysql init."""
        assert INI_PATH.exists(), f"{INI_PATH} missing — run `check_mysql init`"

    def test_cli_binary_is_installed(self):
        """The console script must be installed in the venv (pdm install)."""
        assert CLI_BINARY.exists(), f"{CLI_BINARY} missing — run `pdm install`"


class TestUptimeE2E:
    """The uptime command against the real server."""

    def test_ok(self, run_cli, ini_path):
        """Any live server satisfies an uptime of at least one second."""
        result = run_cli("uptime", "-c", ini_path, "-W", "1:", "-C", "1:")
        assert result.returncode == 0, result.stdout + result.stderr
        assert "MYSQL OK" in result.stdout
        assert "uptime=" in result.stdout

    def test_forced_warning(self, run_cli, ini_path):
        """An unreachable warning floor flags any real uptime."""
        result = run_cli("uptime", "-c", ini_path, "-W", f"{HUGE}:", "-C", "1:")
        assert result.returncode == 1
        assert "MYSQL WARNING" in result.stdout

    def test_forced_critical(self, run_cli, ini_path):
        """An unreachable critical floor flags any real uptime."""
        result = run_cli("uptime", "-c", ini_path, "-C", f"{HUGE}:")
        assert result.returncode == 2
        assert "MYSQL CRITICAL" in result.stdout

    def test_hostname_and_port_override(self, run_cli, ini_path, mysql_settings):
        """-H/-P overrides reach the same server explicitly."""
        result = run_cli(
            "uptime",
            "-c",
            ini_path,
            "-H",
            mysql_settings.get("host", "localhost"),
            "-P",
            mysql_settings.get("port", "3306"),
            "-W",
            "1:",
            "-C",
            "1:",
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "MYSQL OK" in result.stdout


class TestConnectionsE2E:
    """The connections command against the real server."""

    def test_ok_with_default_thresholds(self, run_cli, ini_path):
        """The test connection alone stays far below the 80% warning."""
        result = run_cli("connections", "-c", ini_path)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "MYSQL OK" in result.stdout
        assert "Connections:" in result.stdout
        assert "connections=" in result.stdout
        assert "%" in result.stdout

    def test_forced_critical(self, run_cli, ini_path):
        """An inside range over 0-100% flags any real usage."""
        result = run_cli("connections", "-c", ini_path, "-C", "@0:100")
        assert result.returncode == 2
        assert "MYSQL CRITICAL" in result.stdout


class TestLatencyE2E:
    """The latency command against the real server."""

    def test_ok_with_default_thresholds(self, run_cli, ini_path):
        """A local SELECT 1 answers well under the default 100 ms."""
        result = run_cli("latency", "-c", ini_path)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "MYSQL OK" in result.stdout
        assert "latency=" in result.stdout
        assert "ms" in result.stdout

    def test_forced_warning(self, run_cli, ini_path):
        """An inside warning range flags any real round-trip time."""
        result = run_cli("latency", "-c", ini_path, "-W", f"@0:{HUGE}", "-C", HUGE)
        assert result.returncode == 1
        assert "MYSQL WARNING" in result.stdout


class TestSlowqueriesE2E:
    """The slowqueries command against the real server."""

    def test_ok(self, run_cli, ini_path):
        """A huge ceiling accepts any real slow-query counter."""
        result = run_cli("slowqueries", "-c", ini_path, "-W", HUGE, "-C", HUGE)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "MYSQL OK" in result.stdout
        assert "slowqueries=" in result.stdout

    def test_forced_critical(self, run_cli, ini_path):
        """An inside critical range flags any real counter, including 0."""
        result = run_cli("slowqueries", "-c", ini_path, "-C", f"@0:{HUGE}")
        assert result.returncode == 2
        assert "MYSQL CRITICAL" in result.stdout


class TestReplicationE2E:
    """The replication command against the real server."""

    def test_standalone_or_replica(self, run_cli, ini_path):
        """A standalone server is UNKNOWN with a clear message; a replica is judged by the
        thresholds (any code but a crash).
        """
        result = run_cli("replication", "-c", ini_path)
        assert result.returncode in (0, 1, 2, 3), result.stdout + result.stderr
        if result.returncode == 3:
            assert "UNKNOWN" in result.stdout
            assert "not a replica" in result.stdout
        else:
            assert "replication=" in result.stdout


class TestSecurityE2E:
    """The security command against the real server."""

    def test_audits_or_unknown_without_grant(self, run_cli, ini_path):
        """A huge ceiling accepts any audit result; a monitoring user without SELECT on mysql.user
        yields UNKNOWN with the server's denial.
        """
        result = run_cli("security", "-c", ini_path, "-W", HUGE, "-C", HUGE)
        assert result.returncode in (0, 3), result.stdout + result.stderr
        if result.returncode == 0:
            assert "security=" in result.stdout
            assert "audited" in result.stdout
        else:
            assert "UNKNOWN" in result.stdout

    def test_forced_critical(self, run_cli, ini_path):
        """An inside range over any count flags the audit when it runs at all."""
        result = run_cli("security", "-c", ini_path, "-C", f"@0:{HUGE}")
        assert result.returncode in (2, 3), result.stdout + result.stderr
        if result.returncode == 2:
            assert "MYSQL CRITICAL" in result.stdout


class TestInitE2E:
    """The init command as a real subprocess."""

    def test_yes_writes_the_default_config(self, run_cli, tmp_path):
        """Init --yes writes the template with mode 600."""
        target = tmp_path / "generated.ini"
        result = run_cli("init", "-c", str(target), "--yes")
        assert result.returncode == 0, result.stdout + result.stderr
        assert "Created" in result.stdout
        assert target.stat().st_mode & 0o777 == 0o600
        assert "[mysql]" in target.read_text()

    def test_refuses_to_overwrite(self, run_cli, tmp_path):
        """Init exits 1 and keeps the existing file intact."""
        target = tmp_path / "generated.ini"
        target.write_text("[mysql]\nhost = keep-me\n")
        result = run_cli("init", "-c", str(target), "--yes")
        assert result.returncode == 1
        assert "keep-me" in target.read_text()

    def test_guided_init_connects_then_checks(self, run_cli, tmp_path, mysql_settings):
        """Full journey: guided init probes the real server, then a check runs against the
        configuration it generated.
        """
        target = tmp_path / "generated.ini"
        answers = (
            "\n".join(
                [
                    mysql_settings.get("host", "localhost"),
                    mysql_settings.get("port", "3306"),
                    mysql_settings.get("user", "nagios"),
                    mysql_settings["password"],
                    "n",  # no SSH bastion
                    "n",  # the monitoring user already exists
                    "y",  # probe the connection for real
                ]
            )
            + "\n"
        )
        result = run_cli("init", "-c", str(target), stdin=answers)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "Connection OK" in result.stdout

        check = run_cli("uptime", "-c", str(target), "-W", "1:", "-C", "1:")
        assert check.returncode == 0, check.stdout + check.stderr
        assert "MYSQL OK" in check.stdout


class TestErrorPathsE2E:
    """Real connection failures map to UNKNOWN, never a traceback."""

    def test_unreachable_port_is_unknown(self, run_cli, ini_path):
        """A closed port yields exit 3 with the connection error."""
        result = run_cli("uptime", "-c", ini_path, "-P", "1")
        assert result.returncode == 3
        assert "UNKNOWN" in result.stdout
        assert "Cannot connect" in result.stdout

    def test_wrong_password_is_unknown(self, run_cli, tmp_path, mysql_settings):
        """The server's real authentication rejection yields exit 3."""
        bad = tmp_path / "bad.ini"
        bad.write_text(
            "[mysql]\n"
            f"host = {mysql_settings.get('host', 'localhost')}\n"
            f"port = {mysql_settings.get('port', '3306')}\n"
            f"user = {mysql_settings.get('user', 'nagios')}\n"
            "password = not-the-password\n"
        )
        result = run_cli("uptime", "-c", str(bad))
        assert result.returncode == 3
        assert "UNKNOWN" in result.stdout
        assert "Access denied" in result.stdout

    def test_missing_config_is_unknown(self, run_cli):
        """A missing configuration file yields exit 3 (lookup runs from a neutral directory, away
        from the repo-root configuration).
        """
        result = run_cli("uptime", "-c", "does-not-exist.ini")
        assert result.returncode == 3
        assert "UNKNOWN" in result.stdout


class TestCliSurfaceE2E:
    """Cross-command behaviour of the real executable."""

    def test_version(self, run_cli):
        """--version prints the program name."""
        result = run_cli("--version")
        assert result.returncode == 0
        assert "check_mysql" in result.stdout

    def test_help_lists_all_commands(self, run_cli):
        """--help lists init and the five check commands."""
        result = run_cli("--help")
        assert result.returncode == 0
        for command in (
            "init",
            "uptime",
            "connections",
            "replication",
            "slowqueries",
            "latency",
        ):
            assert command in result.stdout

    def test_module_entrypoint(self, ini_path):
        """Python -m check_mysql drives the same real check."""
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "check_mysql",
                "uptime",
                "-c",
                ini_path,
                "-W",
                "1:",
                "-C",
                "1:",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "MYSQL OK" in proc.stdout

    def test_verbose_traces_the_sql_on_stderr(self, run_cli, ini_path):
        """-vv logs the real SQL round trip on stderr, keeping stdout clean."""
        result = run_cli("uptime", "-c", ini_path, "-vv", "-W", "1:", "-C", "1:")
        assert result.returncode == 0
        assert "SHOW GLOBAL STATUS" in result.stderr
        assert "MYSQL OK" in result.stdout
