"""Open files command for CLI."""

# pyright: reportUnusedFunction=false

from typing import Any, Optional

from check_mysql.cli.decorators import common_options
from check_mysql.cli.handlers import run_check
from check_mysql.services.openfiles_service import OpenFilesService


def register_openfiles_commands(main_group: Any) -> None:
    """Register the openfiles command with the main CLI group."""

    @main_group.command("openfiles")
    @common_options
    def openfiles_cmd(
        config: str,
        verbose: int,
        hostname: Optional[str],
        port: Optional[int],
        warning: Optional[str],
        critical: Optional[str],
    ) -> None:
        """Check Open_files as a percentage of open_files_limit."""
        warning = warning if warning is not None else "80"
        critical = critical if critical is not None else "95"

        run_check(
            OpenFilesService,
            "openfiles",
            config=config,
            verbose=verbose,
            hostname=hostname,
            port=port,
            warning=warning,
            critical=critical,
        )
