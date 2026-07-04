"""Counter-rate commands backported from check_mysql_health."""

# pyright: reportUnusedFunction=false

from typing import Any, Optional

from check_mysql.cli.decorators import common_options
from check_mysql.cli.handlers import run_check
from check_mysql.core.models import MySQLClientProtocol
from check_mysql.services.counter_service import (
    COUNTER_SPECS,
    CounterRateService,
    CounterSpec,
)


def _register_counter_command(main_group: Any, spec: CounterSpec) -> None:
    """Register one counter-rate command from its spec."""

    @main_group.command(spec.command, help=spec.help_text)
    @common_options
    def counter_cmd(
        config: str,
        verbose: int,
        hostname: Optional[str],
        port: Optional[int],
        warning: Optional[str],
        critical: Optional[str],
    ) -> None:
        """Run the counter-rate check described by the enclosing spec."""

        def factory(
            client: MySQLClientProtocol, verbose_level: int = 0
        ) -> CounterRateService:
            """Build the counter-rate service for this command."""
            return CounterRateService(spec, client, verbose_level)

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


def register_counter_commands(main_group: Any) -> None:
    """Register all counter-rate commands with the main CLI group."""
    for spec in COUNTER_SPECS:
        _register_counter_command(main_group, spec)
