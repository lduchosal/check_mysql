"""Custom exceptions for check_mysql."""


class CheckMySQLError(Exception):
    """Base exception for check_mysql."""


class ConfigurationError(CheckMySQLError):
    """Raised when there's a configuration error."""


class MySQLConnectionError(CheckMySQLError):
    """Raised when the MySQL connection cannot be established."""


class SSHTunnelError(CheckMySQLError):
    """Raised when the SSH tunnel cannot be established."""


class QueryError(CheckMySQLError):
    """Raised when a query fails on the server."""


class ValidationError(CheckMySQLError):
    """Raised when the server response cannot be interpreted."""


class CriticalError(CheckMySQLError):
    """Raised when a check must report a CRITICAL state immediately."""
