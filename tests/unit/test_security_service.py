"""Unit tests for the account security audit service."""

from typing import Any

from check_mysql.services.security_service import SecurityService
from tests.fixtures.mock_mysql_client import MockMySQLClient


def _row(user: str, host: str, **overrides: Any) -> dict[str, Any]:
    """Build a mysql.user row: password set, no privilege, not locked."""
    row: dict[str, Any] = {
        "User": user,
        "Host": host,
        "Select_priv": "N",
        "Super_priv": "N",
        "Grant_priv": "N",
        "File_priv": "N",
        "Process_priv": "N",
        "Shutdown_priv": "N",
        "plugin": "caching_sha2_password",
        "authentication_string": "$A$005$abcdefghijklmnopqrstuvwxyz012345",
        "account_locked": "N",
    }
    row.update(overrides)
    return row


def _result(rows: list[dict[str, Any]], allowlist: frozenset[str] = frozenset()):
    """Run the service over the given mysql.user rows."""
    client = MockMySQLClient(user_accounts=rows)
    return SecurityService(client, allowlist=allowlist).get_result()


class TestSecurityServiceFixture:
    """Behaviour on the shared hardened-server fixture."""

    def test_default_fixture_is_clean(self):
        """The fixture (local root, locked sys accounts, nagios) is clean."""
        result = SecurityService(MockMySQLClient()).get_result()
        assert result["value"] == 0
        assert result["details"][0] == "0 risky accounts out of 2 audited"

    def test_empty_account_table(self):
        """No account means nothing to flag."""
        result = _result([])
        assert result["value"] == 0
        assert result["details"] == ["0 risky accounts out of 0 audited"]


class TestCredentialFindings:
    """Anonymous and passwordless account detection."""

    def test_anonymous_account_is_flagged(self):
        """An empty user name is the classic anonymous account."""
        result = _result([_row("", "localhost")])
        assert result["value"] == 1
        assert "anonymous account" in result["details"][1]

    def test_empty_credentials_are_flagged(self):
        """Empty Password and authentication_string mean no password."""
        rows = [_row("app", "localhost", authentication_string="", Password="")]
        result = _result(rows)
        assert result["value"] == 1
        assert "no password" in result["details"][1]

    def test_mariadb_password_column_counts_as_credential(self):
        """A hash in the legacy Password column is a password."""
        rows = [_row("app", "localhost", authentication_string="")]
        rows[0]["Password"] = "*2470C0C06DEE42FD1618BB99005ADCA2EC9D1E19"
        assert _result(rows)["value"] == 0

    def test_socket_authentication_is_not_passwordless(self):
        """unix_socket authenticates via the OS: no credential expected."""
        rows = [
            _row("root", "localhost", plugin="unix_socket", authentication_string="")
        ]
        assert _result(rows)["value"] == 0

    def test_pam_authentication_is_not_passwordless(self):
        """External PAM authentication carries no stored credential."""
        rows = [_row("ops", "localhost", plugin="pam", authentication_string="")]
        assert _result(rows)["value"] == 0


class TestHostFindings:
    """Wildcard host and remote root detection."""

    def test_pure_wildcard_host_is_flagged(self):
        """A % host exposes the account to any client address."""
        result = _result([_row("app", "%")])
        assert result["value"] == 1
        assert "wildcard host" in result["details"][1]

    def test_empty_host_is_flagged_as_wildcard(self):
        """MySQL treats an empty host like %."""
        assert _result([_row("app", "")])["value"] == 1

    def test_scoped_wildcard_host_is_not_flagged(self):
        """A scoped pattern such as 10.0.% stays below the radar."""
        assert _result([_row("app", "10.0.%")])["value"] == 0

    def test_remote_root_is_flagged(self):
        """Root reachable from the network is reported by name."""
        result = _result([_row("root", "10.0.0.5")])
        assert result["value"] == 1
        assert "root reachable remotely" in result["details"][1]

    def test_local_root_is_not_flagged(self):
        """root bound to localhost, 127.0.0.1 or ::1 is expected."""
        rows = [
            _row("root", "localhost", Super_priv="Y", Grant_priv="Y"),
            _row("root", "127.0.0.1", Super_priv="Y"),
            _row("root", "::1", Super_priv="Y"),
        ]
        assert _result(rows)["value"] == 0


class TestPrivilegeFindings:
    """Dangerous global privileges on remotely reachable accounts."""

    def test_remote_super_is_flagged(self):
        """SUPER on a remote host is reported with the privilege name."""
        result = _result([_row("dba", "10.0.0.5", Super_priv="Y")])
        assert result["value"] == 1
        assert "remote privileges (SUPER)" in result["details"][1]

    def test_multiple_privileges_are_listed(self):
        """Each dangerous privilege shows up in the account line."""
        rows = [_row("dba", "10.0.0.5", Grant_priv="Y", File_priv="Y")]
        result = _result(rows)
        assert "GRANT OPTION" in result["details"][1]
        assert "FILE" in result["details"][1]

    def test_all_privileges_is_reported_as_such(self):
        """Every *_priv column at Y collapses into ALL PRIVILEGES."""
        columns = (
            "Select_priv",
            "Super_priv",
            "Grant_priv",
            "File_priv",
            "Process_priv",
            "Shutdown_priv",
        )
        rows = [_row("admin", "10.0.0.5", **{column: "Y" for column in columns})]
        result = _result(rows)
        assert "remote privileges (ALL PRIVILEGES)" in result["details"][1]

    def test_local_privileges_are_not_flagged(self):
        """Powerful accounts restricted to localhost are expected."""
        rows = [_row("debian-sys-maint", "localhost", Super_priv="Y", Grant_priv="Y")]
        assert _result(rows)["value"] == 0


class TestExemptions:
    """Locked accounts, no-login plugins and the allowlist."""

    def test_locked_accounts_are_skipped(self):
        """A locked account carries no attack surface."""
        rows = [_row("root", "%", Super_priv="Y", account_locked="Y")]
        result = _result(rows)
        assert result["value"] == 0
        assert "0 audited" in result["details"][0]

    def test_no_login_plugin_is_skipped(self):
        """mysql_no_login refuses every connection."""
        rows = [_row("definer", "%", plugin="mysql_no_login")]
        assert _result(rows)["value"] == 0

    def test_allowlisted_account_is_exempt(self):
        """An allowlisted user@host is excluded from every check."""
        rows = [_row("backup", "10.0.0.5", Super_priv="Y")]
        assert _result(rows, frozenset({"backup@10.0.0.5"}))["value"] == 0

    def test_allowlist_matches_exact_host_only(self):
        """The allowlist entry must match the stored host exactly."""
        rows = [_row("backup", "10.0.0.5", Super_priv="Y")]
        assert _result(rows, frozenset({"backup@localhost"}))["value"] == 1


class TestMonitoringUserExemption:
    """The plugin's own account is exempt from the wildcard criterion only."""

    def _monitored(self, rows):
        """Run the service with nagios declared as the monitoring user."""
        client = MockMySQLClient(user_accounts=rows)
        return SecurityService(client, monitoring_user="nagios").get_result()

    def test_monitoring_user_wildcard_host_is_not_flagged(self):
        """The account init creates (nagios@%) must not warn by itself."""
        assert self._monitored([_row("nagios", "%")])["value"] == 0

    def test_monitoring_user_stays_subject_to_other_checks(self):
        """Passwordless or over-privileged, the monitoring user still warns."""
        rows = [_row("nagios", "%", Super_priv="Y", authentication_string="")]
        result = self._monitored(rows)
        assert result["value"] == 1
        assert "no password" in result["details"][1]
        assert "remote privileges (SUPER)" in result["details"][1]
        assert "wildcard host" not in result["details"][1]

    def test_other_wildcard_accounts_are_still_flagged(self):
        """The exemption is scoped to the monitoring user name."""
        assert self._monitored([_row("app", "%")])["value"] == 1

    def test_anonymous_account_never_inherits_the_exemption(self):
        """An empty user never matches an unset monitoring user."""
        result = _result([_row("", "%")])
        assert "anonymous account" in result["details"][1]
        assert "wildcard host" in result["details"][1]


class TestVerboseLogging:
    """Per-criterion tracing at -vvv, verdicts and exemptions at -vv."""

    def test_trace_details_every_criterion(self, capsys):
        """-vvv logs each of the five criteria with its verdict per account."""
        client = MockMySQLClient(user_accounts=[_row("app", "%")])
        SecurityService(client, verbose_level=3).get_result()
        err = capsys.readouterr().err
        assert "'app'@'%': anonymous: ok" in err
        assert "'app'@'%': no password: ok" in err
        assert "'app'@'%': wildcard host: FLAGGED" in err
        assert "'app'@'%': remote root: ok" in err
        assert "'app'@'%': remote privileges: ok" in err

    def test_debug_reports_skips_exemptions_and_verdicts(self, capsys):
        """-vv explains skipped, exempted and clean accounts."""
        rows = [
            _row("locked", "%", account_locked="Y"),
            _row("nagios", "%"),
            _row("backup", "10.0.0.5", Super_priv="Y"),
        ]
        client = MockMySQLClient(user_accounts=rows)
        SecurityService(
            client,
            verbose_level=2,
            allowlist=frozenset({"backup@10.0.0.5"}),
            monitoring_user="nagios",
        ).get_result()
        err = capsys.readouterr().err
        assert "'locked'@'%': locked or no-login plugin, not audited" in err
        assert "'nagios'@'%': wildcard host exempted (monitoring user)" in err
        assert "'nagios'@'%': clean" in err
        assert "'backup'@'10.0.0.5': allowlisted, exempt from every check" in err

    def test_debug_summarises_flagged_accounts(self, capsys):
        """-vv prints one FLAGGED line per risky account with its findings."""
        rows = [_row("root", "10.0.0.5", Super_priv="Y")]
        SecurityService(
            MockMySQLClient(user_accounts=rows), verbose_level=2
        ).get_result()
        err = capsys.readouterr().err
        assert (
            "'root'@'10.0.0.5': FLAGGED — root reachable remotely, "
            "remote privileges (SUPER)" in err
        )

    def test_silent_without_verbose(self, capsys):
        """Level 0 emits nothing on stderr."""
        SecurityService(MockMySQLClient()).get_result()
        assert capsys.readouterr().err == ""


class TestReporting:
    """Headline and per-account detail lines."""

    def test_value_counts_accounts_not_issues(self):
        """One account with several findings counts once."""
        result = _result([_row("root", "%", Super_priv="Y", authentication_string="")])
        assert result["value"] == 1

    def test_headline_breaks_down_categories(self):
        """The headline lists per-category counts for the flagged accounts."""
        rows = [_row("app", "%"), _row("root", "10.0.0.5")]
        headline = _result(rows)["details"][0]
        assert headline.startswith("2 risky accounts out of 2 audited")
        assert "wildcard host: 1" in headline
        assert "remote root: 1" in headline

    def test_detail_line_names_the_account(self):
        """Each flagged account gets one 'user'@'host' line."""
        result = _result([_row("app", "%")])
        assert result["details"][1].startswith("'app'@'%': ")
