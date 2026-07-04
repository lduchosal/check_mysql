"""Shared execution path for the check commands."""

import sys
from typing import Optional, Protocol

from check_mysql.core.config import get_mysql_config, get_ssh_config, load_config
from check_mysql.core.connection import MySQLConnector
from check_mysql.core.models import CheckServiceProtocol, MySQLClientProtocol
from check_mysql.core.mysql_client import MySQLClient
from check_mysql.core.nagios import NagiosPlugin


class ServiceFactory(Protocol):
    """Callable building a check service from a client and a verbosity level."""

    def __call__(
        self, client: MySQLClientProtocol, verbose_level: int = 0
    ) -> CheckServiceProtocol:
        """Return a configured check service."""
        ...


def run_check(
    service_class: ServiceFactory,
    command_name: str,
    config: str,
    verbose: int,
    hostname: Optional[str],
    port: Optional[int],
    warning: Optional[str],
    critical: Optional[str],
) -> None:
    """
    Run a check command end to end and exit with the Nagios code.

    Loads the configuration, opens the connection (direct or through the SSH tunnel), executes the
    service through the Nagios runner and exits with codes 0/1/2, or 3 (UNKNOWN) on any setup
    failure.
    """
    try:
        cfg = load_config(config)
        mysql_config = get_mysql_config(cfg, hostname, port)
        ssh_config = get_ssh_config(cfg)
        connector = MySQLConnector(mysql_config, ssh_config, verbose_level=verbose)

        with MySQLClient(connector, verbose_level=verbose) as client:
            service = service_class(client, verbose_level=verbose)
            plugin = NagiosPlugin(service, command_name)
            result = plugin.check(warning=warning, critical=critical, verbose=verbose)

        sys.exit(result)

    except Exception as e:
        print(f"UNKNOWN: {e}")
        sys.exit(3)
