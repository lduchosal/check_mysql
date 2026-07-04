"""Account security audit service implementation."""

from __future__ import annotations

from collections import Counter
from typing import Any

from check_mysql.core.logging_config import get_verbose_logger
from check_mysql.core.models import MySQLClientProtocol, ServiceResult

# Hosts from which a powerful account is expected (root, maintenance users).
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

# Host values matching any client address.
_WILDCARD_HOSTS = frozenset({"", "%"})

# Plugins authenticating outside mysql.user (socket peer, PAM, LDAP, GSSAPI):
# an empty credential column is normal there, not a missing password.
_EXTERNAL_AUTH_PLUGINS = frozenset(
    {
        "auth_pam_compat",
        "auth_socket",
        "authentication_kerberos",
        "authentication_ldap_sasl",
        "authentication_ldap_simple",
        "authentication_pam",
        "authentication_windows",
        "gssapi",
        "pam",
        "unix_socket",
    }
)

# Global privileges dangerous enough to flag on remotely reachable accounts.
_DANGEROUS_PRIV_COLUMNS = (
    ("Super_priv", "SUPER"),
    ("Grant_priv", "GRANT OPTION"),
    ("File_priv", "FILE"),
    ("Process_priv", "PROCESS"),
    ("Shutdown_priv", "SHUTDOWN"),
)


def _text(row: dict[str, Any], column: str) -> str:
    """Read a column as a stripped string, tolerating missing or null values."""
    return str(row.get(column) or "").strip()


def _account(row: dict[str, Any]) -> str:
    """Render the row as the usual ``'user'@'host'`` account literal."""
    return f"'{_text(row, 'User')}'@'{_text(row, 'Host')}'"


def _is_granted(row: dict[str, Any], column: str) -> bool:
    """Tell whether a privilege column holds Y."""
    return _text(row, column).upper() == "Y"


def _is_local(row: dict[str, Any]) -> bool:
    """Tell whether the account is only reachable from the server itself."""
    return _text(row, "Host").lower() in _LOCAL_HOSTS


def _cannot_log_in(row: dict[str, Any]) -> bool:
    """Tell whether the account is locked or uses a login-refusing plugin."""
    if _is_granted(row, "account_locked"):
        return True
    return _text(row, "plugin").lower() == "mysql_no_login"


def _lacks_password(row: dict[str, Any]) -> bool:
    """Tell whether a password-authenticated account has an empty credential."""
    if _text(row, "plugin").lower() in _EXTERNAL_AUTH_PLUGINS:
        return False
    return not (_text(row, "Password") or _text(row, "authentication_string"))


def _dangerous_privileges(row: dict[str, Any]) -> list[str]:
    """Names of the dangerous global privileges held by the account."""
    priv_columns = [column for column in row if column.endswith("_priv")]
    if priv_columns and all(_is_granted(row, column) for column in priv_columns):
        return ["ALL PRIVILEGES"]
    return [
        label for column, label in _DANGEROUS_PRIV_COLUMNS if _is_granted(row, column)
    ]


def _account_checks(
    row: dict[str, Any], monitoring_user: str = ""
) -> list[tuple[str, bool, str]]:
    """
    Evaluate every audit criterion for one mysql.user row.

    Returns one (category, triggered, description) triple per criterion, so callers can log
    negative results too. The monitoring account (the user the plugin authenticates as) is
    exempted from the wildcard-host criterion only — it must be remotely reachable to do its
    job — and stays subject to every other check.
    """
    user = _text(row, "User")
    wildcard_exempt = bool(monitoring_user) and user == monitoring_user
    privileges = [] if _is_local(row) else _dangerous_privileges(row)
    return [
        ("anonymous", not user, "anonymous account"),
        ("no password", _lacks_password(row), "no password"),
        (
            "wildcard host",
            _text(row, "Host") in _WILDCARD_HOSTS and not wildcard_exempt,
            "wildcard host",
        ),
        (
            "remote root",
            user == "root" and not _is_local(row),
            "root reachable remotely",
        ),
        (
            "remote privileges",
            bool(privileges),
            f"remote privileges ({', '.join(privileges)})",
        ),
    ]


class SecurityService:
    """
    Service counting over-privileged or insecure MySQL accounts.

    Locked accounts and login-refusing plugins are skipped (they carry no attack surface); accounts
    listed in the allowlist (``user@host``, as stored in mysql.user) are exempted from every check;
    the monitoring user is exempted from the wildcard-host finding only.
    """

    def __init__(
        self,
        client: MySQLClientProtocol,
        verbose_level: int = 0,
        allowlist: frozenset[str] = frozenset(),
        monitoring_user: str = "",
    ) -> None:
        """Initialize with a MySQL client and the exempted accounts."""
        self.client = client
        self.allowlist = allowlist
        self.monitoring_user = monitoring_user
        self.logger = get_verbose_logger(__name__, verbose_level)

    def _audit_row(self, row: dict[str, Any]) -> list[tuple[str, str]]:
        """
        Evaluate one account, logging each criterion and its verdict.

        Trace (-vvv) shows every criterion with its result; debug (-vv) shows the exemptions
        applied and the per-account verdict. Returns the triggered (category, description)
        findings — empty for exempt or clean accounts.
        """
        account = _account(row)
        if f"{_text(row, 'User')}@{_text(row, 'Host')}" in self.allowlist:
            self.logger.debug(f"{account}: allowlisted, exempt from every check")
            return []
        if (
            _text(row, "Host") in _WILDCARD_HOSTS
            and self.monitoring_user
            and _text(row, "User") == self.monitoring_user
        ):
            self.logger.debug(f"{account}: wildcard host exempted (monitoring user)")
        checks = _account_checks(row, self.monitoring_user)
        for category, triggered, _ in checks:
            verdict = "FLAGGED" if triggered else "ok"
            self.logger.trace(f"{account}: {category}: {verdict}")
        issues = [
            (category, description)
            for category, triggered, description in checks
            if triggered
        ]
        if issues:
            findings = ", ".join(description for _, description in issues)
            self.logger.debug(f"{account}: FLAGGED — {findings}")
        else:
            self.logger.debug(f"{account}: clean")
        return issues

    def get_result(self) -> ServiceResult:
        """Return the number of risky accounts with one detail line each."""
        self.logger.method_entry("get_result")

        accounts = self.client.get_user_accounts()
        audited: list[dict[str, Any]] = []
        for row in accounts:
            if _cannot_log_in(row):
                self.logger.debug(
                    f"{_account(row)}: locked or no-login plugin, not audited"
                )
            else:
                audited.append(row)
        self.logger.info(f"Auditing {len(audited)} of {len(accounts)} accounts")

        flagged: list[tuple[str, list[tuple[str, str]]]] = []
        for row in audited:
            issues = self._audit_row(row)
            if issues:
                flagged.append((_account(row), issues))

        count = len(flagged)
        headline = f"{count} risky accounts out of {len(audited)} audited"
        categories = Counter(
            category for _, issues in flagged for category, _ in issues
        )
        if categories:
            breakdown = ", ".join(
                f"{category}: {total}" for category, total in sorted(categories.items())
            )
            headline += f" ({breakdown})"

        details: list[str] = [headline]
        details.extend(
            f"{account}: {', '.join(description for _, description in issues)}"
            for account, issues in flagged
        )
        result: ServiceResult = {"value": count, "details": details}

        self.logger.info(f"Risky accounts: {count}")
        self.logger.method_exit("get_result", result)
        return result
