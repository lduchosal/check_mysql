"""Unit tests for the long-running processes service."""

from check_mysql.services.longrunning_service import LongRunningService
from tests.fixtures.mock_mysql_client import MockMySQLClient


def _query_row(time_value, command="Query"):
    """Build a minimal processlist row."""
    return {"Id": 1, "User": "app", "Command": command, "Time": time_value}


class TestLongRunningService:
    """Tests for LongRunningService.get_result."""

    def test_counts_only_active_long_queries(self):
        """The fixture holds one long query among sleeping/daemon threads."""
        result = LongRunningService(MockMySQLClient()).get_result()
        assert result["value"] == 1
        assert "1 queries running longer than 60s" in result["details"][0]
        assert "(4 processes total)" in result["details"][0]
        assert "id 7" in result["details"][1]

    def test_empty_processlist(self):
        """No processes means zero long-running queries."""
        result = LongRunningService(MockMySQLClient(processlist=[])).get_result()
        assert result["value"] == 0
        assert len(result["details"]) == 1

    def test_idle_commands_are_ignored(self):
        """Sleep and daemon threads never count, whatever their Time."""
        rows = [_query_row(4000, "Sleep"), _query_row(864000, "Daemon")]
        result = LongRunningService(MockMySQLClient(processlist=rows)).get_result()
        assert result["value"] == 0

    def test_sixty_seconds_is_not_long_running_yet(self):
        """The threshold is strict: exactly 60s does not count."""
        rows = [_query_row(60)]
        result = LongRunningService(MockMySQLClient(processlist=rows)).get_result()
        assert result["value"] == 0

    def test_sixty_one_seconds_counts(self):
        """61 seconds crosses the threshold."""
        rows = [_query_row(61)]
        result = LongRunningService(MockMySQLClient(processlist=rows)).get_result()
        assert result["value"] == 1

    def test_string_time_is_parsed(self):
        """A Time column delivered as text is still compared."""
        rows = [_query_row("75")]
        result = LongRunningService(MockMySQLClient(processlist=rows)).get_result()
        assert result["value"] == 1

    def test_missing_or_invalid_time_is_ignored(self):
        """Rows without a usable Time column count as not long-running."""
        rows = [_query_row(None), _query_row("soon")]
        result = LongRunningService(MockMySQLClient(processlist=rows)).get_result()
        assert result["value"] == 0
