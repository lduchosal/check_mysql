"""Counter-rate services backported from check_mysql_health."""

from __future__ import annotations

from dataclasses import dataclass

from check_mysql.core.exceptions import ValidationError
from check_mysql.core.logging_config import get_verbose_logger
from check_mysql.core.models import MySQLClientProtocol, ServiceResult
from check_mysql.core.status import read_int

_QCACHE_HINT = " (query cache removed in MySQL 8.0)"


@dataclass(frozen=True)
class CounterSpec:
    """Status counter reported as an average rate per second."""

    command: str
    label: str
    counter: str
    default_warning: str
    default_critical: str
    help_text: str
    hint: str = ""


COUNTER_SPECS: tuple[CounterSpec, ...] = (
    CounterSpec(
        command="querycacheprunes",
        label="Query cache lowmem prunes",
        counter="Qcache_lowmem_prunes",
        default_warning="1",
        default_critical="10",
        help_text="Check query cache prunes per second (MariaDB only).",
        hint=_QCACHE_HINT,
    ),
    CounterSpec(
        command="bufferpoolwaits",
        label="InnoDB buffer pool waits",
        counter="Innodb_buffer_pool_wait_free",
        default_warning="1",
        default_critical="10",
        help_text="Check InnoDB buffer pool wait-free stalls per second.",
    ),
    CounterSpec(
        command="logwaits",
        label="InnoDB log waits",
        counter="Innodb_log_waits",
        default_warning="1",
        default_critical="10",
        help_text="Check InnoDB log buffer waits per second.",
    ),
)


class CounterRateService:
    """Service reporting a status counter as an average rate per second.

    check_mysql_health computes these rates as deltas between two runs
    persisted in a state file; here the rate is averaged since server
    start instead, which needs no local state.
    """

    def __init__(
        self,
        spec: CounterSpec,
        client: MySQLClientProtocol,
        verbose_level: int = 0,
    ) -> None:
        """Initialize with a counter spec and a MySQL client."""
        self.spec = spec
        self.client = client
        self.logger = get_verbose_logger(__name__, verbose_level)

    def get_result(self) -> ServiceResult:
        """
        Return the average per-second rate of the counter since server start.

        Raises:
            ValidationError: If the server does not report a positive Uptime.
        """
        self.logger.method_entry("get_result")

        status = self.client.get_global_status()
        count = read_int(status, self.spec.counter, self.spec.hint)
        uptime = read_int(status, "Uptime")
        if uptime <= 0:
            raise ValidationError(f"Invalid Uptime value: {uptime}")

        rate = round(count / uptime, 4)
        details: list[str] = [
            f"{self.spec.label}: {count} since server start "
            f"({rate}/s over {uptime} seconds)"
        ]
        result: ServiceResult = {"value": rate, "details": details}

        self.logger.info(f"{self.spec.label}: {rate}/s")
        self.logger.method_exit("get_result", result)
        return result
