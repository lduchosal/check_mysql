"""Arbitrary SQL scalar command for CLI."""

# pyright: reportUnusedFunction=false

from typing import Any, Optional

import click

from check_mysql.cli.decorators import common_options
from check_mysql.cli.handlers import run_check
from check_mysql.core.models import MySQLClientProtocol
from check_mysql.services.sql_service import SqlService


def register_sql_commands(main_group: Any) -> None:
    """Register the sql command with the main CLI group."""

    @main_group.command("sql")
    @common_options
    @click.option(
        "--sql",
        "statement",
        required=True,
        help="SQL statement whose first row / first column is the checked value",
    )
    def sql_cmd(
        config: str,
        verbose: int,
        hostname: Optional[str],
        port: Optional[int],
        warning: Optional[str],
        critical: Optional[str],
        statement: str,
    ) -> None:
        """Check the scalar result of an arbitrary SQL statement."""
        # Without explicit thresholds the check only reports the value ("~:"
        # is the always-true Nagios range; "" would alert on negatives).
        warning = warning if warning is not None else "~:"
        critical = critical if critical is not None else "~:"

        def factory(client: MySQLClientProtocol, verbose_level: int = 0) -> SqlService:
            """Build the SQL service bound to the statement."""
            return SqlService(statement, client, verbose_level)

        run_check(
            factory,
            "sql",
            config=config,
            verbose=verbose,
            hostname=hostname,
            port=port,
            warning=warning,
            critical=critical,
        )
