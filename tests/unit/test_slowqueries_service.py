"""Unit tests for the slow queries service."""

import pytest

from check_mysql.core.exceptions import ValidationError
from check_mysql.services.slowqueries_service import SlowQueriesService
from tests.fixtures.mock_mysql_client import MockMySQLClient


class TestSlowQueriesService:
    """Tests for SlowQueriesService.get_result."""

    def test_returns_the_counter(self):
        """The fixture counter is returned with an hourly rate detail."""
        result = SlowQueriesService(MockMySQLClient()).get_result()
        assert result["value"] == 12
        assert result["uom"] == "c"
        assert "12 slow queries" in result["details"][0]
        assert "/hour" in result["details"][0]

    def test_no_rate_without_uptime(self):
        """Without an Uptime counter the detail skips the rate."""
        client = MockMySQLClient(status={"Slow_queries": "5"})
        result = SlowQueriesService(client).get_result()
        assert result["value"] == 5
        assert "/hour" not in result["details"][0]

    def test_invalid_uptime_is_tolerated(self):
        """A non-numeric Uptime only drops the rate detail."""
        client = MockMySQLClient(status={"Slow_queries": "5", "Uptime": "soon"})
        assert SlowQueriesService(client).get_result()["value"] == 5

    def test_missing_counter_raises(self):
        """A server not reporting Slow_queries raises ValidationError."""
        service = SlowQueriesService(MockMySQLClient(status={}))
        with pytest.raises(ValidationError, match="No Slow_queries"):
            service.get_result()

    def test_invalid_counter_raises(self):
        """A non-numeric Slow_queries raises ValidationError."""
        client = MockMySQLClient(status={"Slow_queries": "lots"})
        with pytest.raises(ValidationError, match="Invalid Slow_queries"):
            SlowQueriesService(client).get_result()
