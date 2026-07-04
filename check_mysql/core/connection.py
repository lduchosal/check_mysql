"""MySQL connectivity — direct or through an SSH tunnel."""

from __future__ import annotations

from typing import Optional

import pymysql
import sshtunnel

from check_mysql.core.exceptions import MySQLConnectionError, SSHTunnelError
from check_mysql.core.logging_config import get_verbose_logger
from check_mysql.core.models import MySQLConfig, SSHConfig


class MySQLConnector:
    """
    Open PyMySQL connections, directly or through an SSH tunnel.

    When an SSH configuration is provided, an SSH tunnel is established to the bastion first and
    MySQL is reached through the tunnel's local endpoint; otherwise PyMySQL connects straight to the
    configured host and port.
    """

    def __init__(
        self,
        mysql_config: MySQLConfig,
        ssh_config: Optional[SSHConfig] = None,
        verbose_level: int = 0,
    ) -> None:
        """Initialize with MySQL settings and optional SSH tunnel settings."""
        self.mysql_config = mysql_config
        self.ssh_config = ssh_config
        self.logger = get_verbose_logger(__name__, verbose_level)
        self._tunnel: Optional[sshtunnel.SSHTunnelForwarder] = None

    def open(self) -> pymysql.connections.Connection:
        """
        Open and return a live PyMySQL connection.

        A tunnel failure surfaces as the SSHTunnelError raised by
        :meth:`_start_tunnel`.

        Raises:
            MySQLConnectionError: If the MySQL connection fails.
        """
        host, port = self.mysql_config.host, self.mysql_config.port
        if self.ssh_config is not None:
            host, port = "127.0.0.1", self._start_tunnel(self.ssh_config)

        try:
            self.logger.info(f"Connecting to MySQL at {host}:{port}")
            return pymysql.connect(
                host=host,
                port=port,
                user=self.mysql_config.user,
                password=self.mysql_config.password,
                database=self.mysql_config.database,
                connect_timeout=self.mysql_config.timeout,
            )
        except pymysql.MySQLError as exc:
            self.close()
            raise MySQLConnectionError(
                f"Cannot connect to MySQL at {host}:{port}: {exc}"
            ) from exc

    def _start_tunnel(self, ssh: SSHConfig) -> int:
        """
        Start the SSH tunnel towards the MySQL server and return the local port.

        Raises:
            SSHTunnelError: If the tunnel cannot be established.
        """
        try:
            self.logger.info(f"Opening SSH tunnel via {ssh.user}@{ssh.host}:{ssh.port}")
            tunnel = sshtunnel.SSHTunnelForwarder(
                (ssh.host, ssh.port),
                ssh_username=ssh.user,
                ssh_password=ssh.password,
                ssh_pkey=ssh.private_key,
                remote_bind_address=(self.mysql_config.host, self.mysql_config.port),
                local_bind_address=("127.0.0.1", 0),
            )
            tunnel.start()
        except Exception as exc:
            raise SSHTunnelError(
                f"Cannot open SSH tunnel via {ssh.user}@{ssh.host}:{ssh.port}: {exc}"
            ) from exc

        self._tunnel = tunnel
        self.logger.debug(
            f"SSH tunnel established on local port {tunnel.local_bind_port}"
        )
        return int(tunnel.local_bind_port)

    def close(self) -> None:
        """Stop the SSH tunnel if one is open."""
        if self._tunnel is not None:
            self._tunnel.stop()
            self._tunnel = None
