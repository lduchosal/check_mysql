"""Unit tests for the latency service."""

from check_mysql.services.latency_service import LatencyService
from tests.fixtures.mock_mysql_client import MockMySQLClient


class TestLatencyService:
    """Tests for LatencyService.get_result."""

    def test_returns_rounded_milliseconds(self):
        """The ping duration is rounded to two decimals."""
        result = LatencyService(MockMySQLClient(ping_ms=3.4567)).get_result()
        assert result["value"] == 3.46
        assert result["uom"] == "ms"
        assert "3.46 ms" in result["details"][0]

    def test_fast_ping_reads_zero(self):
        """A sub-hundredth ping rounds down to 0.0."""
        service = LatencyService(MockMySQLClient(ping_ms=0.001))
        assert service.get_result()["value"] == 0.0
