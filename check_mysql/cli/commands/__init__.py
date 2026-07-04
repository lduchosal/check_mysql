"""Commands package for CLI."""

from typing import Any

from check_mysql.cli.commands.connections import register_connections_commands
from check_mysql.cli.commands.counters import register_counter_commands
from check_mysql.cli.commands.init import register_init_commands
from check_mysql.cli.commands.latency import register_latency_commands
from check_mysql.cli.commands.longrunning import register_longrunning_commands
from check_mysql.cli.commands.openfiles import register_openfiles_commands
from check_mysql.cli.commands.ping import register_ping_commands
from check_mysql.cli.commands.ratios import register_ratio_commands
from check_mysql.cli.commands.replication import register_replication_commands
from check_mysql.cli.commands.security import register_security_commands
from check_mysql.cli.commands.slowqueries import register_slowqueries_commands
from check_mysql.cli.commands.sql import register_sql_commands
from check_mysql.cli.commands.uptime import register_uptime_commands


def register_all_commands(main_group: Any) -> None:
    """Register all commands with the main CLI group."""
    register_init_commands(main_group)
    register_ping_commands(main_group)
    register_uptime_commands(main_group)
    register_connections_commands(main_group)
    register_replication_commands(main_group)
    register_slowqueries_commands(main_group)
    register_latency_commands(main_group)
    register_ratio_commands(main_group)
    register_counter_commands(main_group)
    register_openfiles_commands(main_group)
    register_longrunning_commands(main_group)
    register_security_commands(main_group)
    register_sql_commands(main_group)
