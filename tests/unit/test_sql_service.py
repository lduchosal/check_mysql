"""Unit tests for the arbitrary SQL scalar service."""

from check_mysql.services.sql_service import SqlService
from tests.fixtures.mock_mysql_client import MockMySQLClient


class TestSqlService:
    """Tests for SqlService.get_result."""

    def test_returns_the_scalar(self):
        """The client scalar becomes the check value."""
        client = MockMySQLClient(scalar=5.0)
        statement = "SELECT COUNT(*) FROM queue"
        result = SqlService(statement, client).get_result()
        assert result["value"] == 5.0
        assert statement in result["details"][0]
        assert client.last_scalar_query == statement

    def test_integer_looking_output(self):
        """Whole floats render without a trailing .0 in the details."""
        result = SqlService("SELECT 42", MockMySQLClient(scalar=42.0)).get_result()
        assert "SQL result: 42 " in result["details"][0]

    def test_negative_scalar(self):
        """Negative results are passed through untouched."""
        result = SqlService("SELECT -7", MockMySQLClient(scalar=-7.0)).get_result()
        assert result["value"] == -7.0
