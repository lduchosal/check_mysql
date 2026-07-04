"""Connections command for CLI."""

# pyright: reportUnusedFunction=false

from typing import Any, Optional

from check_mysql.cli.decorators import common_options
from check_mysql.cli.handlers import run_check
from check_mysql.services.connections_service import ConnectionsService


def register_connections_commands(main_group: Any) -> None:
    """Register the connections command with the main CLI group."""

    @main_group.command("connections")
    @common_options
    def connections_cmd(
        config: str,
        verbose: int,
        hostname: Optional[str],
        port: Optional[int],
        warning: Optional[str],
        critical: Optional[str],
    ) -> None:
        """Check current connections as a percentage of max_connections."""
        warning = warning if warning is not None else "80"
        critical = critical if critical is not None else "95"

        run_check(
            ConnectionsService,
            "connections",
            config=config,
            verbose=verbose,
            hostname=hostname,
            port=port,
            warning=warning,
            critical=critical,
        )
