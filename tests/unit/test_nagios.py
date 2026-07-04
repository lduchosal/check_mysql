"""Unit tests for the Nagios plugin runner."""

from check_mysql.core.exceptions import CriticalError, ValidationError
from check_mysql.core.models import ServiceResult
from check_mysql.core.nagios import NagiosPlugin


class StubService:
    """Service returning a canned result or raising a canned error."""

    def __init__(self, result=None, error=None):
        """Initialize with a result or an exception to raise."""
        self.result = result
        self.error = error

    def get_result(self) -> ServiceResult:
        """Return the canned result or raise the canned error."""
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def _check(value, warning, critical, command="uptime", details=None, uom=None):
    """Run a NagiosPlugin check over a stub service and return the exit code."""
    result: ServiceResult = {"value": value, "details": details or ["detail line"]}
    if uom is not None:
        result["uom"] = uom
    return NagiosPlugin(StubService(result), command).check(
        warning=warning, critical=critical
    )


class TestExitCodes:
    """Exit codes across threshold configurations."""

    def test_ok_inside_range(self, capsys):
        """A value inside both ranges exits 0."""
        assert _check(50, "80", "95") == 0
        assert "MYSQL OK" in capsys.readouterr().out

    def test_warning_above_threshold(self, capsys):
        """A value above the warning range exits 1."""
        assert _check(85, "80", "95") == 1
        assert "MYSQL WARNING" in capsys.readouterr().out

    def test_critical_above_threshold(self, capsys):
        """A value above the critical range exits 2."""
        assert _check(99, "80", "95") == 2
        assert "MYSQL CRITICAL" in capsys.readouterr().out

    def test_inverted_range_for_uptime(self):
        """A '300:' range alerts when the value drops below 300."""
        assert _check(86400, "3600:", "300:") == 0
        assert _check(1800, "3600:", "300:") == 1
        assert _check(60, "3600:", "300:") == 2


class TestOutput:
    """Rendering of details and performance data."""

    def test_details_and_perfdata(self, capsys):
        """The headline carries the first detail and perfdata the metric."""
        code = _check(
            42, "80", "95", command="connections", details=["Connections: 42/151"]
        )
        out = capsys.readouterr().out
        assert code == 0
        assert "Connections: 42/151" in out
        assert "connections=42" in out

    def test_uom_lands_in_perfdata(self, capsys):
        """The unit of measure is appended to the perfdata value."""
        _check(3.42, "100", "500", command="latency", uom="ms")
        assert "latency=3.42ms" in capsys.readouterr().out

    def test_long_output_keeps_extra_details(self, capsys):
        """Additional detail lines are emitted as long output."""
        _check(10, "80", "95", details=["headline", "second line"])
        out = capsys.readouterr().out
        assert "headline" in out
        assert "second line" in out


class TestErrorHandling:
    """Error paths map to the right Nagios exit codes."""

    def test_critical_error_exits_2(self, capsys):
        """A CriticalError bypasses thresholds and exits 2."""
        plugin = NagiosPlugin(
            StubService(error=CriticalError("Replication threads stopped")),
            "replication",
        )
        assert plugin.check(warning="60", critical="300") == 2
        out = capsys.readouterr().out
        assert "MYSQL CRITICAL" in out
        assert "Replication threads stopped" in out

    def test_unexpected_error_exits_3(self, capsys):
        """Any other exception exits 3 (UNKNOWN)."""
        plugin = NagiosPlugin(
            StubService(error=ValidationError("No Uptime in SHOW GLOBAL STATUS")),
            "uptime",
        )
        assert plugin.check(warning="3600:", critical="300:") == 3
        assert "UNKNOWN" in capsys.readouterr().out
