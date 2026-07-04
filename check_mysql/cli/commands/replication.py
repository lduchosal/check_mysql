"""Replication command for CLI."""

# pyright: reportUnusedFunction=false

from typing import Any, Optional

from check_mysql.cli.decorators import common_options
from check_mysql.cli.handlers import run_check
from check_mysql.services.replication_service import ReplicationService


def register_replication_commands(main_group: Any) -> None:
    """Register the replication command with the main CLI group."""

    @main_group.command("replication")
    @common_options
    def replication_cmd(
        config: str,
        verbose: int,
        hostname: Optional[str],
        port: Optional[int],
        warning: Optional[str],
        critical: Optional[str],
    ) -> None:
        """Check replication lag and replication thread state."""
        warning = warning if warning is not None else "60"
        critical = critical if critical is not None else "300"

        run_check(
            ReplicationService,
            "replication",
            config=config,
            verbose=verbose,
            hostname=hostname,
            port=port,
            warning=warning,
            critical=critical,
        )
