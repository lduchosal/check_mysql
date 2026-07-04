"""Unit tests for the ratio services backported from check_mysql_health."""

import pytest

from check_mysql.core.exceptions import ValidationError
from check_mysql.services.ratio_service import RATIO_SPECS, RatioService
from tests.fixtures.mock_mysql_client import MockMySQLClient

SPECS = {spec.command: spec for spec in RATIO_SPECS}

# Percentages the shared fixture dataset must produce for each spec.
EXPECTED_FIXTURE_VALUES = [
    ("threadcache", 99.5),
    ("querycache", 90.0),
    ("keycache", 99.5),
    ("tablecache", 99.2),
    ("bufferpool", 99.9),
    ("tablelocks", 1.0),
    ("indexusage", 93.0),
    ("tmpdisktables", 25.0),
]


class TestRatioService:
    """Tests for RatioService.get_result across the spec catalog."""

    def test_catalog_is_complete(self):
        """The catalog holds the eight distinct backported ratio checks."""
        assert len(SPECS) == len(RATIO_SPECS) == 8

    @pytest.mark.parametrize("command,expected", EXPECTED_FIXTURE_VALUES)
    def test_fixture_values(self, command, expected):
        """Each spec computes the documented percentage from the fixture."""
        result = RatioService(SPECS[command], MockMySQLClient()).get_result()
        assert result["value"] == expected
        assert result["uom"] == "%"
        assert SPECS[command].label in result["details"][0]

    @pytest.mark.parametrize("command", [c for c, _ in EXPECTED_FIXTURE_VALUES])
    def test_zero_denominator_returns_empty_value(self, command):
        """An idle server (all counters at 0) reports the neutral value."""
        spec = SPECS[command]
        zeros = dict.fromkeys(spec.numerator + spec.denominator, "0")
        result = RatioService(spec, MockMySQLClient(status=zeros)).get_result()
        assert result["value"] == spec.empty_value

    def test_missing_counter_raises(self):
        """A missing counter raises ValidationError naming the counter."""
        service = RatioService(SPECS["threadcache"], MockMySQLClient(status={}))
        with pytest.raises(ValidationError, match="No Threads_created"):
            service.get_result()

    def test_querycache_hint_mentions_mysql8(self):
        """The MySQL 8 removal hint is part of the querycache error."""
        service = RatioService(SPECS["querycache"], MockMySQLClient(status={}))
        with pytest.raises(ValidationError, match="query cache removed in MySQL 8.0"):
            service.get_result()

    def test_invalid_counter_raises(self):
        """A non-numeric counter raises ValidationError."""
        client = MockMySQLClient(
            status={"Threads_created": "many", "Connections": "10"}
        )
        with pytest.raises(ValidationError, match="Invalid Threads_created"):
            RatioService(SPECS["threadcache"], client).get_result()

    def test_percentage_is_clamped_at_0(self):
        """Counter anomalies never push the value below 0."""
        client = MockMySQLClient(
            status={"Threads_created": "200", "Connections": "100"}
        )
        result = RatioService(SPECS["threadcache"], client).get_result()
        assert result["value"] == 0.0

    def test_percentage_is_clamped_at_100(self):
        """Open_tables above Opened_tables caps the hitrate at 100%."""
        client = MockMySQLClient(status={"Open_tables": "600", "Opened_tables": "500"})
        result = RatioService(SPECS["tablecache"], client).get_result()
        assert result["value"] == 100.0

    def test_details_show_the_counters(self):
        """The detail line exposes the raw counters behind the percentage."""
        result = RatioService(SPECS["threadcache"], MockMySQLClient()).get_result()
        assert "Threads_created=42" in result["details"][0]
        assert "Connections=8400" in result["details"][0]
