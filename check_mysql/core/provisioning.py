"""Provisioning of the MySQL monitoring user."""

from __future__ import annotations

from typing import List, Tuple

from check_mysql.core.connection import MySQLConnector
from check_mysql.core.logging_config import get_verbose_logger

MONITORING_HOST_SCOPE = "%"


def _quote_account(user: str, host_scope: str) -> str:
    """Return the quoted ``'user'@'host'`` account literal, quotes escaped."""
    user_escaped = user.replace("'", "''")
    host_escaped = host_scope.replace("'", "''")
    return f"'{user_escaped}'@'{host_escaped}'"


def monitoring_user_statements(
    user: str, host_scope: str = MONITORING_HOST_SCOPE
) -> List[Tuple[str, bool]]:
    """
    Statements creating the monitoring user and its grants.

    Returns (query, needs_password) pairs; the password is bound as a query parameter at execution
    time, never interpolated.
    """
    account = _quote_account(user, host_scope)
    # PyMySQL renders parameterized queries with Python's % operator: literal
    # percent signs (the '%' host scope) must be doubled there — and only there.
    account_parameterized = account.replace("%", "%%")
    return [
        (f"CREATE USER IF NOT EXISTS {account_parameterized} IDENTIFIED BY %s", True),
        (f"GRANT USAGE, REPLICATION CLIENT ON *.* TO {account}", False),
        (f"GRANT SELECT ON mysql.user TO {account}", False),
    ]


def monitoring_user_sql(
    user: str, password: str, host_scope: str = MONITORING_HOST_SCOPE
) -> str:
    """Copy-pasteable SQL block creating the monitoring user."""
    account = _quote_account(user, host_scope)
    password_escaped = password.replace("'", "''")
    return (
        f"    CREATE USER IF NOT EXISTS {account} IDENTIFIED BY '{password_escaped}';\n"
        f"    GRANT USAGE, REPLICATION CLIENT ON *.* TO {account};\n"
        f"    GRANT SELECT ON mysql.user TO {account};"
    )


def create_monitoring_user(
    connector: MySQLConnector,
    user: str,
    password: str,
    host_scope: str = MONITORING_HOST_SCOPE,
    verbose_level: int = 0,
) -> None:
    """
    Create the monitoring user and its grants through the given connector.

    The connection (and the SSH tunnel, when the connector carries one) is always released, even
    when a statement fails.
    """
    logger = get_verbose_logger(__name__, verbose_level)
    connection = connector.open()
    try:
        with connection.cursor() as cursor:
            for query, needs_password in monitoring_user_statements(user, host_scope):
                logger.sql_query(query)
                cursor.execute(query, (password,) if needs_password else None)
        connection.commit()
    finally:
        connection.close()
        connector.close()
