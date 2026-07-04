"""Slow queries command for CLI."""

# pyright: reportUnusedFunction=false

from typing import Any, Optional

from check_mysql.cli.decorators import common_options
from check_mysql.cli.handlers import run_check
from check_mysql.services.slowqueries_service import SlowQueriesService


def register_slowqueries_commands(main_group: Any) -> None:
    """Register the slowqueries command with the main CLI group."""

    @main_group.command("slowqueries")
    @common_options
    def slowqueries_cmd(
        config: str,
        verbose: int,
        hostname: Optional[str],
        port: Optional[int],
        warning: Optional[str],
        critical: Optional[str],
    ) -> None:
        """Check the Slow_queries counter since server start."""
        warning = warning if warning is not None else "100"
        critical = critical if critical is not None else "1000"

        run_check(
            SlowQueriesService,
            "slowqueries",
            config=config,
            verbose=verbose,
            hostname=hostname,
            port=port,
            warning=warning,
            critical=critical,
        )
