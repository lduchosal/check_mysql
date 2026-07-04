"""CLI module for check_mysql."""

import click

from check_mysql import __version__
from check_mysql.cli.commands import register_all_commands


@click.group()
@click.version_option(version=__version__, prog_name="check_mysql")
def main() -> None:
    """Check MySQL server health and validate values against Nagios thresholds."""


# Register all commands
register_all_commands(main)
