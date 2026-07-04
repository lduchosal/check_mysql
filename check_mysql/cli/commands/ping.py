"""Ping command for CLI."""

# pyright: reportUnusedFunction=false

from typing import Any, Optional

from check_mysql.cli.decorators import common_options
from check_mysql.cli.handlers import run_check
from check_mysql.services.ping_service import PingService


def register_ping_commands(main_group: Any) -> None:
    """Register the ping command with the main CLI group."""

    @main_group.command("ping")
    @common_options
    def ping_cmd(
        config: str,
        verbose: int,
        hostname: Optional[str],
        port: Optional[int],
        warning: Optional[str],
        critical: Optional[str],
    ) -> None:
        """Check connectivity and report the client and server versions."""
        run_check(
            PingService,
            "ping",
            config=config,
            verbose=verbose,
            hostname=hostname,
            port=port,
            warning=warning,
            critical=critical,
        )
