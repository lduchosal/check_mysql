"""Account security audit service implementation."""

from __future__ import annotations

import hashlib
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

# Global privileges dangerous enough to flag on remotely reachable accounts:
# administrative control (SUPER, SHUTDOWN, RELOAD, CREATE USER), privilege
# escalation (GRANT OPTION, FILE, PROCESS) and code execution (routines,
# events, triggers).
_DANGEROUS_PRIV_COLUMNS = (
    ("Super_priv", "SUPER"),
    ("Grant_priv", "GRANT OPTION"),
    ("File_priv", "FILE"),
    ("Process_priv", "PROCESS"),
    ("Shutdown_priv", "SHUTDOWN"),
    ("Create_user_priv", "CREATE USER"),
    ("Reload_priv", "RELOAD"),
    ("Create_routine_priv", "CREATE ROUTINE"),
    ("Alter_routine_priv", "ALTER ROUTINE"),
    ("Event_priv", "EVENT"),
    ("Trigger_priv", "TRIGGER"),
)

# Common passwords tested offline against mysql_native_password hashes only
# (the salted caching_sha2_password hashes cannot be tested without a login).
_WEAK_PASSWORDS = frozenset(
    {
        "123456",
        "12345678",
        "123456789",
        "password",
        "password1",
        "root",
        "toor",
        "admin",
        "mysql",
        "changeme",
        "change-me",
        "secret",
        "letmein",
        "welcome",
        "qwerty",
        "abc123",
        "test",
        "guest",
        "oracle",
        "master",
        "monitor",
        "nagios",
    }
)


def _text(row: dict[str, Any], column: str) -> str:
    """Read a column as a stripped string, tolerating missing or null values."""
    return str(row.get(column) or "").strip()


def _account(row: dict[str, Any]) -> str:
    """Render the row as the usual ``'user'@'host'`` account literal."""
    return f"'{_text(row, 'User')}'@'{_text(row, 'Host')}'"


def _entry(row: dict[str, Any]) -> str:
    """Render the row as the ``user@host`` key used by the allow/admins lists."""
    return f"{_text(row, 'User')}@{_text(row, 'Host')}"


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


def _native_password_hash(password: str) -> str:
    """Return the mysql_native_password hash: ``*`` + UPPER(SHA1(SHA1(password)))."""
    first = hashlib.sha1(password.encode(), usedforsecurity=False).digest()
    second = hashlib.sha1(first, usedforsecurity=False).hexdigest().upper()
    return "*" + second


def _weak_password(row: dict[str, Any]) -> bool:
    """
    Tell whether a native-auth account uses a well-known weak password.

    Only ``mysql_native_password`` stores an unsalted, offline-comparable hash;
    every other plugin (salted or external) is skipped, never a false positive.
    """
    if _text(row, "plugin").lower() != "mysql_native_password":
        return False
    stored = (_text(row, "authentication_string") or _text(row, "Password")).upper()
    if not stored:
        return False
    return any(
        _native_password_hash(password) == stored for password in _WEAK_PASSWORDS
    )


def _dangerous_privileges(row: dict[str, Any]) -> list[str]:
    """Names of the dangerous global privileges held by the account."""
    priv_columns = [column for column in row if column.endswith("_priv")]
    if priv_columns and all(_is_granted(row, column) for column in priv_columns):
        return ["ALL PRIVILEGES"]
    return [
        label for column, label in _DANGEROUS_PRIV_COLUMNS if _is_granted(row, column)
    ]


def _account_checks(
    row: dict[str, Any],
    monitoring_user: str = "",
    admins: frozenset[str] = frozenset(),
) -> list[tuple[str, bool, str]]:
    """
    Evaluate every audit criterion for one mysql.user row.

    Returns one (category, triggered, description) triple per criterion, so callers can log negative
    results too. The monitoring account (the user the plugin authenticates as) is exempted from the
    wildcard-host criterion only; accounts listed as expected admins are exempted from the
    remote-privileges criterion only. Both stay subject to every other check.
    """
    user = _text(row, "User")
    wildcard_exempt = bool(monitoring_user) and user == monitoring_user
    admin_exempt = _entry(row) in admins
    privileges = [] if _is_local(row) else _dangerous_privileges(row)
    return [
        ("anonymous", not user, "anonymous account"),
        ("no password", _lacks_password(row), "no password"),
        ("weak password", _weak_password(row), "weak password"),
        ("password expired", _is_granted(row, "password_expired"), "password expired"),
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
            bool(privileges) and not admin_exempt,
            f"remote privileges ({', '.join(privileges)})",
        ),
    ]


class SecurityService:
    """
    Service counting over-privileged or insecure MySQL accounts.

    Locked accounts and login-refusing plugins are skipped (they carry no attack surface); accounts
    listed in the allowlist (``user@host``, as stored in mysql.user) are exempted from every check;
    the monitoring user is exempted from the wildcard-host finding only; accounts listed as expected
    admins are exempted from the remote-privileges finding only.
    """

    def __init__(
        self,
        client: MySQLClientProtocol,
        verbose_level: int = 0,
        allowlist: frozenset[str] = frozenset(),
        monitoring_user: str = "",
        admins: frozenset[str] = frozenset(),
    ) -> None:
        """Initialize with a MySQL client and the exempted accounts."""
        self.client = client
        self.allowlist = allowlist
        self.monitoring_user = monitoring_user
        self.admins = admins
        self.logger = get_verbose_logger(__name__, verbose_level)

    def _log_exemptions(self, row: dict[str, Any], account: str) -> None:
        """Trace the wildcard-host and admin exemptions applied to an account."""
        if (
            _text(row, "Host") in _WILDCARD_HOSTS
            and self.monitoring_user
            and _text(row, "User") == self.monitoring_user
        ):
            self.logger.debug(f"{account}: wildcard host exempted (monitoring user)")
        if (
            not _is_local(row)
            and _entry(row) in self.admins
            and _dangerous_privileges(row)
        ):
            self.logger.debug(f"{account}: privileges exempted (expected admin)")

    def _audit_row(self, row: dict[str, Any]) -> list[tuple[str, str]]:
        """
        Evaluate one account, logging each criterion and its verdict.

        Trace (-vvv) shows every criterion with its result; debug (-vv) shows the exemptions applied
        and the per-account verdict. Returns the triggered (category, description) findings — empty
        for exempt or clean accounts.
        """
        account = _account(row)
        if _entry(row) in self.allowlist:
            self.logger.debug(f"{account}: allowlisted, exempt from every check")
            return []
        self._log_exemptions(row, account)
        checks = _account_checks(row, self.monitoring_user, self.admins)
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
