"""Uptime command for CLI."""

# pyright: reportUnusedFunction=false

from typing import Any

from check_mysql.cli.decorators import common_options
from check_mysql.cli.handlers import run_check
from check_mysql.services.uptime_service import UptimeService


def register_uptime_commands(main_group: Any) -> None:
    """Register the uptime command with the main CLI group."""

    @main_group.command("uptime")
    @common_options
    def uptime_cmd(
        config: str,
        verbose: int,
        hostname: str | None,
        port: int | None,
        warning: str | None,
        critical: str | None,
    ) -> None:
        """Check seconds elapsed since the MySQL server started."""
        warning = warning if warning is not None else "3600:"
        critical = critical if critical is not None else "300:"

        run_check(
            UptimeService,
            "uptime",
            config=config,
            verbose=verbose,
            hostname=hostname,
            port=port,
            warning=warning,
            critical=critical,
        )
