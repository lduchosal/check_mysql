"""Counter-ratio services backported from check_mysql_health."""

from __future__ import annotations

from dataclasses import dataclass

from check_mysql.core.logging_config import get_verbose_logger
from check_mysql.core.models import MySQLClientProtocol, ServiceResult
from check_mysql.core.status import sum_counters

_QCACHE_HINT = " (query cache removed in MySQL 8.0)"


@dataclass(frozen=True)
class RatioSpec:
    """
    Percentage computed from SHOW GLOBAL STATUS counter sets.

    With ``invert`` the reported value is ``100 - numerator/denominator``
    (a hitrate derived from a miss counter), otherwise the direct share.
    ``empty_value`` is reported when the denominator is zero (idle server).
    """

    command: str
    label: str
    numerator: tuple[str, ...]
    denominator: tuple[str, ...]
    invert: bool
    empty_value: float
    default_warning: str
    default_critical: str
    help_text: str
    hint: str = ""


RATIO_SPECS: tuple[RatioSpec, ...] = (
    RatioSpec(
        command="threadcache",
        label="Thread cache hitrate",
        numerator=("Threads_created",),
        denominator=("Connections",),
        invert=True,
        empty_value=100.0,
        default_warning="90:",
        default_critical="80:",
        help_text="Check the thread cache hitrate (Threads_created vs Connections).",
    ),
    RatioSpec(
        command="querycache",
        label="Query cache hitrate",
        numerator=("Qcache_hits",),
        denominator=("Qcache_hits", "Com_select"),
        invert=False,
        empty_value=100.0,
        default_warning="90:",
        default_critical="80:",
        help_text="Check the query cache hitrate (MariaDB; removed in MySQL 8.0).",
        hint=_QCACHE_HINT,
    ),
    RatioSpec(
        command="keycache",
        label="MyISAM key cache hitrate",
        numerator=("Key_reads",),
        denominator=("Key_read_requests",),
        invert=True,
        empty_value=100.0,
        default_warning="99:",
        default_critical="95:",
        help_text="Check the MyISAM key cache hitrate (Key_reads vs requests).",
    ),
    RatioSpec(
        command="tablecache",
        label="Table cache hitrate",
        numerator=("Open_tables",),
        denominator=("Opened_tables",),
        invert=False,
        empty_value=100.0,
        default_warning="99:",
        default_critical="95:",
        help_text="Check the table cache hitrate (Open_tables vs Opened_tables).",
    ),
    RatioSpec(
        command="bufferpool",
        label="InnoDB buffer pool hitrate",
        numerator=("Innodb_buffer_pool_reads",),
        denominator=("Innodb_buffer_pool_read_requests",),
        invert=True,
        empty_value=100.0,
        default_warning="99:",
        default_critical="95:",
        help_text="Check the InnoDB buffer pool hitrate (disk reads vs requests).",
    ),
    RatioSpec(
        command="tablelocks",
        label="Table lock contention",
        numerator=("Table_locks_waited",),
        denominator=("Table_locks_waited", "Table_locks_immediate"),
        invert=False,
        empty_value=0.0,
        default_warning="1",
        default_critical="2",
        help_text="Check the table lock contention (waited vs immediate locks).",
    ),
    RatioSpec(
        command="indexusage",
        label="Index usage",
        numerator=("Handler_read_rnd", "Handler_read_rnd_next"),
        denominator=(
            "Handler_read_first",
            "Handler_read_key",
            "Handler_read_next",
            "Handler_read_prev",
            "Handler_read_rnd",
            "Handler_read_rnd_next",
        ),
        invert=True,
        empty_value=100.0,
        default_warning="90:",
        default_critical="80:",
        help_text="Check index usage vs full scans (Handler_read_* counters).",
    ),
    RatioSpec(
        command="tmpdisktables",
        label="Temporary tables created on disk",
        numerator=("Created_tmp_disk_tables",),
        denominator=("Created_tmp_tables",),
        invert=False,
        empty_value=0.0,
        default_warning="25",
        default_critical="50",
        help_text="Check the share of temporary tables created on disk.",
    ),
)


class RatioService:
    """Service computing a percentage from two status counter sets."""

    def __init__(
        self,
        spec: RatioSpec,
        client: MySQLClientProtocol,
        verbose_level: int = 0,
    ) -> None:
        """Initialize with a ratio spec and a MySQL client."""
        self.spec = spec
        self.client = client
        self.logger = get_verbose_logger(__name__, verbose_level)

    def get_result(self) -> ServiceResult:
        """Return the ratio as a percentage clamped to the 0-100 range."""
        self.logger.method_entry("get_result")

        status = self.client.get_global_status()
        numerator = sum_counters(status, self.spec.numerator, self.spec.hint)
        denominator = sum_counters(status, self.spec.denominator, self.spec.hint)

        percent = self._percent(numerator, denominator)
        counters = ", ".join(
            f"{key}={status[key]}"
            for key in dict.fromkeys(self.spec.numerator + self.spec.denominator)
        )
        details: list[str] = [f"{self.spec.label}: {percent}% ({counters})"]
        result: ServiceResult = {"value": percent, "details": details, "uom": "%"}

        self.logger.info(f"{self.spec.label}: {percent}%")
        self.logger.method_exit("get_result", result)
        return result

    def _percent(self, numerator: int, denominator: int) -> float:
        """Compute the clamped percentage, honouring empty_value on zero data."""
        if denominator == 0:
            return self.spec.empty_value
        ratio = numerator * 100.0 / denominator
        percent = 100.0 - ratio if self.spec.invert else ratio
        return round(min(100.0, max(0.0, percent)), 2)
