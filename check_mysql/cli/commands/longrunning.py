"""Long-running processes command for CLI."""

# pyright: reportUnusedFunction=false

from typing import Any, Optional

from check_mysql.cli.decorators import common_options
from check_mysql.cli.handlers import run_check
from check_mysql.services.longrunning_service import LongRunningService


def register_longrunning_commands(main_group: Any) -> None:
    """Register the longrunning command with the main CLI group."""

    @main_group.command("longrunning")
    @common_options
    def longrunning_cmd(
        config: str,
        verbose: int,
        hostname: Optional[str],
        port: Optional[int],
        warning: Optional[str],
        critical: Optional[str],
    ) -> None:
        """Check the number of queries running longer than 60 seconds."""
        warning = warning if warning is not None else "10"
        critical = critical if critical is not None else "20"

        run_check(
            LongRunningService,
            "longrunning",
            config=config,
            verbose=verbose,
            hostname=hostname,
            port=port,
            warning=warning,
            critical=critical,
        )
