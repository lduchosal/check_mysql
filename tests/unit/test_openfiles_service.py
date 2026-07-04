"""Unit tests for the open files service."""

import pytest

from check_mysql.core.exceptions import ValidationError
from check_mysql.services.openfiles_service import OpenFilesService
from tests.fixtures.mock_mysql_client import MockMySQLClient


class TestOpenFilesService:
    """Tests for OpenFilesService.get_result."""

    def test_returns_the_usage_percentage(self):
        """The fixture usage is returned as a percentage of the limit."""
        result = OpenFilesService(MockMySQLClient()).get_result()
        assert result["value"] == 1.17
        assert result["uom"] == "%"
        assert "12/1024" in result["details"][0]

    def test_missing_counter_raises(self):
        """A server not reporting Open_files raises ValidationError."""
        service = OpenFilesService(MockMySQLClient(status={}))
        with pytest.raises(ValidationError, match="No Open_files"):
            service.get_result()

    def test_missing_limit_raises(self):
        """A server not reporting open_files_limit raises ValidationError."""
        service = OpenFilesService(MockMySQLClient(variables={}))
        with pytest.raises(ValidationError, match="No open_files_limit"):
            service.get_result()

    def test_zero_limit_raises(self):
        """A zero open_files_limit cannot produce a percentage."""
        client = MockMySQLClient(variables={"open_files_limit": "0"})
        with pytest.raises(ValidationError, match="Invalid open_files_limit"):
            OpenFilesService(client).get_result()
