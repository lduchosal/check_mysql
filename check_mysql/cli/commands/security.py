"""Account security audit command for CLI."""

# pyright: reportUnusedFunction=false

from typing import Any, Optional

from check_mysql.cli.decorators import common_options
from check_mysql.cli.handlers import run_check
from check_mysql.core.config import (
    get_mysql_config,
    get_security_admins,
    get_security_allowlist,
    load_config,
)
from check_mysql.core.models import MySQLClientProtocol
from check_mysql.services.security_service import SecurityService


def register_security_commands(main_group: Any) -> None:
    """Register the security command with the main CLI group."""

    @main_group.command("security")
    @common_options
    def security_cmd(
        config: str,
        verbose: int,
        hostname: Optional[str],
        port: Optional[int],
        warning: Optional[str],
        critical: Optional[str],
    ) -> None:
        """Check for over-privileged or insecure MySQL accounts."""
        warning = warning if warning is not None else "0"
        critical = critical if critical is not None else "5"

        def factory(
            client: MySQLClientProtocol, verbose_level: int = 0
        ) -> SecurityService:
            """Build the security service bound to the configured exemptions."""
            cfg = load_config(config)
            return SecurityService(
                client,
                verbose_level,
                allowlist=get_security_allowlist(cfg),
                monitoring_user=get_mysql_config(cfg).user,
                admins=get_security_admins(cfg),
            )

        run_check(
            factory,
            "security",
            config=config,
            verbose=verbose,
            hostname=hostname,
            port=port,
            warning=warning,
            critical=critical,
        )
