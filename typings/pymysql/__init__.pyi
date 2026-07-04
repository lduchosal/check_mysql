"""Type stubs for pymysql (only the surface used by check_mysql)."""

from typing import Any

from pymysql import connections as connections
from pymysql import cursors as cursors
from pymysql.connections import Connection as Connection

__version__: str

class MySQLError(Exception): ...
class Warning(MySQLError): ...
class Error(MySQLError): ...
class InterfaceError(Error): ...
class DatabaseError(Error): ...
class OperationalError(DatabaseError): ...
class ProgrammingError(DatabaseError): ...

def connect(
    *,
    host: str = ...,
    port: int = ...,
    user: str | None = ...,
    password: str = ...,
    database: str | None = ...,
    connect_timeout: int | None = ...,
    **kwargs: Any,
) -> Connection: ...
