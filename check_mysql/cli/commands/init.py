"""Init command for CLI — guided setup of the monitoring configuration."""

# pyright: reportUnusedFunction=false

import secrets
import sys
from typing import Any, List, Optional, Tuple

import click

from check_mysql.core.config import render_config, write_config, write_default_config
from check_mysql.core.connection import MySQLConnector
from check_mysql.core.models import MySQLConfig, SSHConfig
from check_mysql.core.mysql_client import MySQLClient
from check_mysql.core.provisioning import create_monitoring_user, monitoring_user_sql


def register_init_commands(main_group: Any) -> None:
    """Register the init command with the main CLI group."""

    @main_group.command("init")
    @click.option(
        "-c",
        "--config",
        default="check_mysql.ini",
        help="Configuration file path to create",
    )
    @click.option("--force", is_flag=True, help="Overwrite an existing file")
    @click.option(
        "-y",
        "--yes",
        is_flag=True,
        help="Non-interactive: write the default template and exit",
    )
    def init_cmd(config: str, force: bool, yes: bool) -> None:
        """Guided setup: config file, monitoring user, connection test."""
        try:
            runner = _run_default_init if yes else _run_guided_init
            failures = runner(config, force)
        except Exception as e:
            click.echo(f"ERROR: {e}", err=True)
            sys.exit(1)

        if failures:
            sys.exit(1)


def _run_default_init(config: str, force: bool) -> List[str]:
    """Write the default template and print the SQL to run manually."""
    path = write_default_config(config, force)
    click.echo(f"Created {path} (mode 600)")
    click.echo("\nSQL to create the monitoring user (password from the file):\n")
    click.echo(monitoring_user_sql("nagios", "change-me"))
    click.echo("\nEdit the [mysql] credentials, then try: check_mysql uptime")
    return []


def _run_guided_init(config: str, force: bool) -> List[str]:
    """Interactive flow: prompts, config write, user creation, connection test."""
    failures: List[str] = []
    mysql, ssh = _prompt_settings()

    path = write_config(config, render_config(mysql, ssh), force)
    click.echo(f"\nCreated {path} (mode 600)")

    click.echo("\nSQL to create the monitoring user:\n")
    click.echo(monitoring_user_sql(mysql.user, mysql.password))
    click.echo()

    created = False
    if click.confirm("Create the monitoring user on the server now?", default=False):
        errors = _create_user(mysql, ssh)
        failures += errors
        created = not errors

    if click.confirm("Test the monitoring connection now?", default=created):
        failures += _test_connection(mysql, ssh)

    if failures:
        click.echo("\nSetup finished with errors — run the SQL above manually, then")
        click.echo("retry with: check_mysql uptime")
    else:
        click.echo("\nSetup complete — try: check_mysql uptime")
    return failures


def _prompt_settings() -> Tuple[MySQLConfig, Optional[SSHConfig]]:
    """Prompt for the MySQL and optional SSH tunnel settings."""
    mysql = MySQLConfig(
        host=click.prompt("MySQL host", default="localhost"),
        port=click.prompt("MySQL port", default=3306, type=int),
        user=click.prompt("Monitoring user", default="nagios"),
        password=click.prompt("Monitoring password", default=secrets.token_urlsafe(12)),
    )

    ssh: Optional[SSHConfig] = None
    if click.confirm("Reach MySQL through an SSH bastion (tunnel)?", default=False):
        ssh = SSHConfig(
            host=click.prompt("SSH bastion host"),
            port=click.prompt("SSH bastion port", default=22, type=int),
            user=click.prompt("SSH user", default="nagios"),
            private_key=click.prompt("SSH private key", default="~/.ssh/id_ed25519"),
        )
    return mysql, ssh


def _create_user(mysql: MySQLConfig, ssh: Optional[SSHConfig]) -> List[str]:
    """Create the monitoring user with admin credentials; reports, never raises."""
    admin = MySQLConfig(
        host=mysql.host,
        port=mysql.port,
        user=click.prompt("Admin user", default="root"),
        password=click.prompt(
            "Admin password", hide_input=True, default="", show_default=False
        ),
        timeout=mysql.timeout,
    )
    try:
        create_monitoring_user(MySQLConnector(admin, ssh), mysql.user, mysql.password)
    except Exception as e:
        click.echo(f"ERROR: could not create the monitoring user: {e}", err=True)
        return [f"user creation failed: {e}"]

    click.echo(f"Monitoring user '{mysql.user}' created and granted.")
    return []


def _test_connection(mysql: MySQLConfig, ssh: Optional[SSHConfig]) -> List[str]:
    """Probe the monitoring connection (SELECT 1 + uptime); reports, never raises."""
    try:
        with MySQLClient(MySQLConnector(mysql, ssh)) as client:
            elapsed_ms = round(client.ping(), 2)
            uptime = client.get_global_status().get("Uptime", "?")
    except Exception as e:
        click.echo(f"ERROR: connection test failed: {e}", err=True)
        return [f"connection test failed: {e}"]

    click.echo(
        f"Connection OK — SELECT 1 in {elapsed_ms} ms, server up for {uptime} seconds."
    )
    return []
