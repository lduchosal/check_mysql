"""Latency command for CLI."""

# pyright: reportUnusedFunction=false

from typing import Any, Optional

from check_mysql.cli.decorators import common_options
from check_mysql.cli.handlers import run_check
from check_mysql.services.latency_service import LatencyService


def register_latency_commands(main_group: Any) -> None:
    """Register the latency command with the main CLI group."""

    @main_group.command("latency")
    @common_options
    def latency_cmd(
        config: str,
        verbose: int,
        hostname: Optional[str],
        port: Optional[int],
        warning: Optional[str],
        critical: Optional[str],
    ) -> None:
        """Check SELECT 1 round-trip latency in milliseconds."""
        warning = warning if warning is not None else "100"
        critical = critical if critical is not None else "500"

        run_check(
            LatencyService,
            "latency",
            config=config,
            verbose=verbose,
            hostname=hostname,
            port=port,
            warning=warning,
            critical=critical,
        )
