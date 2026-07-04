"""Unit tests for the uptime service."""

import pytest

from check_mysql.core.exceptions import ValidationError
from check_mysql.services.uptime_service import UptimeService
from tests.fixtures.mock_mysql_client import MockMySQLClient


class TestUptimeService:
    """Tests for UptimeService.get_result."""

    def test_returns_uptime_seconds(self):
        """The fixture uptime is returned as the value with a detail line."""
        result = UptimeService(MockMySQLClient()).get_result()
        assert result["value"] == 864000
        assert result["uom"] == "s"
        assert "864000 seconds" in result["details"][0]

    def test_human_readable_duration(self):
        """The detail line carries a duration in days."""
        service = UptimeService(MockMySQLClient())
        assert "10 days" in service.get_result()["details"][0]

    def test_missing_uptime_raises(self):
        """A server not reporting Uptime raises ValidationError."""
        service = UptimeService(MockMySQLClient(status={}))
        with pytest.raises(ValidationError, match="No Uptime"):
            service.get_result()

    def test_invalid_uptime_raises(self):
        """A non-numeric Uptime raises ValidationError."""
        service = UptimeService(MockMySQLClient(status={"Uptime": "soon"}))
        with pytest.raises(ValidationError, match="Invalid Uptime"):
            service.get_result()
