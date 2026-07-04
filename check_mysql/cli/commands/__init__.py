"""Commands package for CLI."""

from typing import Any

from check_mysql.cli.commands.connections import register_connections_commands
from check_mysql.cli.commands.latency import register_latency_commands
from check_mysql.cli.commands.replication import register_replication_commands
from check_mysql.cli.commands.slowqueries import register_slowqueries_commands
from check_mysql.cli.commands.uptime import register_uptime_commands


def register_all_commands(main_group: Any) -> None:
    """Register all commands with the main CLI group."""
    register_uptime_commands(main_group)
    register_connections_commands(main_group)
    register_replication_commands(main_group)
    register_slowqueries_commands(main_group)
    register_latency_commands(main_group)
