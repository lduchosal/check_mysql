"""CLI decorators for check_mysql."""

from typing import Any, Callable

import click


def common_options(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator applying the options shared by every check command."""
    func = click.option(
        "-c", "--config", default="check_mysql.ini", help="Configuration file path"
    )(func)
    func = click.option("-v", "--verbose", count=True, help="Increase verbosity")(func)
    func = click.option(
        "-H", "--hostname", help="MySQL host (overrides the [mysql] section)"
    )(func)
    func = click.option(
        "-P", "--port", type=int, help="MySQL port (overrides the [mysql] section)"
    )(func)
    func = click.option(
        "-W", "--warning", help="Warning threshold (Nagios range, e.g. 80 or 300:)"
    )(func)
    func = click.option(
        "-C", "--critical", help="Critical threshold (Nagios range, e.g. 95 or 60:)"
    )(func)

    return func
