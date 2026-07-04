"""Hitrate and ratio commands backported from check_mysql_health."""

# pyright: reportUnusedFunction=false

from typing import Any, Optional

from check_mysql.cli.decorators import common_options
from check_mysql.cli.handlers import run_check
from check_mysql.core.models import MySQLClientProtocol
from check_mysql.services.ratio_service import RATIO_SPECS, RatioService, RatioSpec


def _register_ratio_command(main_group: Any, spec: RatioSpec) -> None:
    """Register one ratio command from its spec."""

    @main_group.command(spec.command, help=spec.help_text)
    @common_options
    def ratio_cmd(
        config: str,
        verbose: int,
        hostname: Optional[str],
        port: Optional[int],
        warning: Optional[str],
        critical: Optional[str],
    ) -> None:
        """Run the ratio check described by the enclosing spec."""

        def factory(
            client: MySQLClientProtocol, verbose_level: int = 0
        ) -> RatioService:
            """Build the ratio service for this command."""
            return RatioService(spec, client, verbose_level)

        run_check(
            factory,
            spec.command,
            config=config,
            verbose=verbose,
            hostname=hostname,
            port=port,
            warning=warning if warning is not None else spec.default_warning,
            critical=critical if critical is not None else spec.default_critical,
        )


def register_ratio_commands(main_group: Any) -> None:
    """Register all ratio commands with the main CLI group."""
    for spec in RATIO_SPECS:
        _register_ratio_command(main_group, spec)
