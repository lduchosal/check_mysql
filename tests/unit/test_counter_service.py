"""Unit tests for the counter-rate services."""

import pytest

from check_mysql.core.exceptions import ValidationError
from check_mysql.services.counter_service import COUNTER_SPECS, CounterRateService
from tests.fixtures.mock_mysql_client import MockMySQLClient

SPECS = {spec.command: spec for spec in COUNTER_SPECS}

# Rates the shared fixture dataset must produce for each spec.
EXPECTED_FIXTURE_VALUES = [
    ("querycacheprunes", 0.1),
    ("bufferpoolwaits", 0.0),
    ("logwaits", 0.0),
]


class TestCounterRateService:
    """Tests for CounterRateService.get_result across the spec catalog."""

    def test_catalog_is_complete(self):
        """The catalog holds the three distinct backported counter checks."""
        assert len(SPECS) == len(COUNTER_SPECS) == 3

    @pytest.mark.parametrize("command,expected", EXPECTED_FIXTURE_VALUES)
    def test_fixture_values(self, command, expected):
        """Each spec computes the average rate per second since start."""
        result = CounterRateService(SPECS[command], MockMySQLClient()).get_result()
        assert result["value"] == expected
        assert SPECS[command].label in result["details"][0]
        assert "/s over 864000 seconds" in result["details"][0]

    def test_rate_is_rounded(self):
        """The rate keeps four decimal places."""
        client = MockMySQLClient(status={"Innodb_log_waits": "1", "Uptime": "3"})
        result = CounterRateService(SPECS["logwaits"], client).get_result()
        assert result["value"] == 0.3333

    def test_missing_counter_raises_with_hint(self):
        """MySQL 8 without a query cache raises with the removal hint."""
        client = MockMySQLClient(status={"Uptime": "100"})
        service = CounterRateService(SPECS["querycacheprunes"], client)
        with pytest.raises(ValidationError, match="query cache removed in MySQL 8.0"):
            service.get_result()

    def test_missing_uptime_raises(self):
        """A server not reporting Uptime raises ValidationError."""
        client = MockMySQLClient(status={"Innodb_log_waits": "5"})
        with pytest.raises(ValidationError, match="No Uptime"):
            CounterRateService(SPECS["logwaits"], client).get_result()

    def test_zero_uptime_raises(self):
        """A zero Uptime cannot produce a rate."""
        client = MockMySQLClient(status={"Innodb_log_waits": "5", "Uptime": "0"})
        with pytest.raises(ValidationError, match="Invalid Uptime"):
            CounterRateService(SPECS["logwaits"], client).get_result()
