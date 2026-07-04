"""Nagios plugin implementation."""

from typing import Any, List, Optional

import nagiosplugin

from check_mysql.core.exceptions import CriticalError
from check_mysql.core.models import CheckServiceProtocol, ServiceResult


class MySQLSummary(nagiosplugin.Summary):
    """Summary rendering the service detail lines.

    The first detail line becomes the status headline; the remaining lines are
    emitted as Nagios long output.
    """

    def __init__(self, details: Optional[List[str]]) -> None:
        """Initialize with detail lines."""
        self.details = details or []

    def ok(self, results: nagiosplugin.Results) -> str:
        """Return detailed output for the OK state."""
        del results  # required by the nagiosplugin.Summary interface, unused here
        return self._format_details()

    def problem(self, results: nagiosplugin.Results) -> str:
        """Return detailed output for problem states (WARNING, CRITICAL)."""
        del results  # required by the nagiosplugin.Summary interface, unused here
        return self._format_details()

    def _format_details(self) -> str:
        """Join the detail lines for output."""
        return "\n".join(self.details)


class MySQLResource(nagiosplugin.Resource):
    """Resource reporting a single scalar value under the MYSQL banner."""

    def __init__(
        self, command_name: str, value: float, uom: Optional[str] = None
    ) -> None:
        """Initialize with the command name, the probed value and optional unit."""
        super().__init__()
        self.command_name = command_name
        self.value = value
        self.uom = uom

    @property
    def name(self) -> str:
        """Return the service name displayed in the status line."""
        return "MYSQL"

    def probe(self) -> List[nagiosplugin.Metric]:
        """Return the single metric for the check."""
        return [nagiosplugin.Metric(self.command_name, self.value, uom=self.uom)]


class NagiosPlugin:
    """Nagios plugin runner for MySQL checks."""

    def __init__(self, service: CheckServiceProtocol, command_name: str) -> None:
        """Initialize with a service and command name."""
        self.service = service
        self.command_name = command_name

    def check(
        self,
        warning: Optional[str] = None,
        critical: Optional[str] = None,
        verbose: int = 0,
    ) -> int:
        """Execute the check and return the Nagios exit code.

        Thresholds are standard Nagios range specifications, e.g. ``95`` (alert
        above 95), ``300:`` (alert below 300) or ``10:20`` (alert outside).
        """
        try:
            result: ServiceResult = self.service.get_result()
            value = result["value"]
            details = result.get("details", [])
            uom = result.get("uom")

            check = nagiosplugin.Check(
                MySQLResource(self.command_name, value, uom),
                nagiosplugin.ScalarContext(self.command_name, warning, critical),
                MySQLSummary(details),
            )

            # Run the check and return the exit code instead of exiting.
            # This mirrors Check.main() but stops short of Runtime.sysexit(),
            # so we never have to swallow the SystemExit it would raise.
            # nagiosplugin ships no type hints, hence the Any handle.
            runtime: Any = nagiosplugin.Runtime()
            runtime.verbose = verbose
            runtime.run(check)
            print(str(runtime.output), end="")
            return int(runtime.exitcode)

        except CriticalError as exc:
            print(f"MYSQL CRITICAL - {exc}")
            return 2
        except Exception as exc:
            print(f"UNKNOWN: {exc}")
            return 3
