"""MySQL client running the queries used by the check services."""

from __future__ import annotations

import time
from typing import Any, Optional

import pymysql
import pymysql.cursors

from check_mysql.core.connection import MySQLConnector
from check_mysql.core.exceptions import QueryError
from check_mysql.core.logging_config import get_verbose_logger


class MySQLClient:
    """Thin client over PyMySQL for the queries used by the services.

    The connection (and the SSH tunnel, when configured) opens lazily on the
    first query and is released by :meth:`close` — use the client as a context
    manager so failures still clean up the tunnel.
    """

    def __init__(self, connector: MySQLConnector, verbose_level: int = 0) -> None:
        """Initialize with a connector; the connection opens lazily."""
        self.connector = connector
        self.logger = get_verbose_logger(__name__, verbose_level)
        self._connection: Optional[pymysql.connections.Connection] = None

    def __enter__(self) -> "MySQLClient":
        """Return self; the connection opens on first query."""
        return self

    def __exit__(self, *_exc_info: object) -> None:
        """Close the connection and the tunnel."""
        self.close()

    def close(self) -> None:
        """Close the connection and the tunnel."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        self.connector.close()

    def _connection_or_open(self) -> pymysql.connections.Connection:
        """Return the open connection, opening it on first use."""
        if self._connection is None:
            self._connection = self.connector.open()
        return self._connection

    def _fetch_pairs(self, query: str) -> dict[str, str]:
        """Run a two-column SHOW query and return it as a name/value mapping."""
        connection = self._connection_or_open()
        self.logger.sql_query(query)
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
        return {str(row[0]): str(row[1]) for row in rows}

    def get_global_status(self) -> dict[str, str]:
        """Return SHOW GLOBAL STATUS as a name/value mapping."""
        return self._fetch_pairs("SHOW GLOBAL STATUS")

    def get_global_variables(self) -> dict[str, str]:
        """Return SHOW GLOBAL VARIABLES as a name/value mapping."""
        return self._fetch_pairs("SHOW GLOBAL VARIABLES")

    def get_replica_status(self) -> Optional[dict[str, Any]]:
        """
        Return SHOW REPLICA STATUS as a row mapping, or None when not a replica.

        Falls back to SHOW SLAVE STATUS for servers older than MySQL 8.0.22 /
        MariaDB 10.5.1.

        Raises:
            QueryError: If neither statement is accepted by the server.
        """
        connection = self._connection_or_open()
        for query in ("SHOW REPLICA STATUS", "SHOW SLAVE STATUS"):
            self.logger.sql_query(query)
            try:
                with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(query)
                    row: Optional[dict[str, Any]] = cursor.fetchone()
            except pymysql.MySQLError as exc:
                self.logger.debug(f"{query} failed: {exc}")
                continue
            return row
        raise QueryError("Neither SHOW REPLICA STATUS nor SHOW SLAVE STATUS succeeded")

    def get_versions(self) -> dict[str, str]:
        """
        Return the client (PyMySQL) and server version strings.

        Raises:
            QueryError: If SELECT VERSION() returns no row.
        """
        connection = self._connection_or_open()
        query = "SELECT VERSION()"
        self.logger.sql_query(query)
        with connection.cursor() as cursor:
            cursor.execute(query)
            row = cursor.fetchone()
        if row is None:
            raise QueryError("SELECT VERSION() returned no row")
        return {"client": pymysql.__version__, "server": str(row[0])}

    def get_processlist(self) -> list[dict[str, Any]]:
        """Return SHOW FULL PROCESSLIST as a list of row mappings."""
        connection = self._connection_or_open()
        query = "SHOW FULL PROCESSLIST"
        self.logger.sql_query(query)
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def query_scalar(self, query: str) -> float:
        """
        Run a query and return the first column of its first row as a float.

        Raises:
            QueryError: If the query returns no row or a non-numeric value.
        """
        connection = self._connection_or_open()
        self.logger.sql_query(query)
        with connection.cursor() as cursor:
            cursor.execute(query)
            row = cursor.fetchone()
        if not row or row[0] is None:
            raise QueryError(f"Query returned no scalar result: {query}")
        try:
            return float(row[0])
        except (TypeError, ValueError) as exc:
            raise QueryError(f"Query returned a non-numeric value: {row[0]!r}") from exc

    def ping(self) -> float:
        """Execute SELECT 1 and return the round-trip time in milliseconds."""
        connection = self._connection_or_open()
        start = time.perf_counter()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchall()
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self.logger.sql_query("SELECT 1", elapsed_ms / 1000.0)
        return elapsed_ms
