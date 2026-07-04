"""Unit tests for the verbose logger."""

from check_mysql.core.logging_config import get_verbose_logger


class TestVerboseLogger:
    """Tests for VerboseLogger across verbosity levels."""

    def test_silent_by_default(self, caplog):
        """Level 0 logs nothing."""
        logger = get_verbose_logger("test.silent", 0)
        logger.info("info")
        logger.debug("debug")
        logger.trace("trace")
        assert caplog.records == []

    def test_level_1_logs_info_only(self, caplog):
        """Level 1 logs info but not debug."""
        logger = get_verbose_logger("test.info", 1)
        with caplog.at_level("DEBUG", logger="test.info"):
            logger.info("visible")
            logger.debug("hidden")
        messages = [record.message for record in caplog.records]
        assert "visible" in messages
        assert "hidden" not in messages

    def test_level_2_logs_debug_and_sql(self, caplog):
        """Level 2 logs debug messages and SQL queries."""
        logger = get_verbose_logger("test.debug", 2)
        with caplog.at_level("DEBUG", logger="test.debug"):
            logger.debug("debugging")
            logger.sql_query("SELECT 1")
            logger.sql_query("SELECT 1", 0.005)
        messages = [record.message for record in caplog.records]
        assert "debugging" in messages
        assert any("SELECT 1" in message for message in messages)

    def test_level_3_logs_traces(self, caplog):
        """Level 3 logs trace, method entry and method exit."""
        logger = get_verbose_logger("test.trace", 3)
        with caplog.at_level("DEBUG", logger="test.trace"):
            logger.trace("tracing")
            logger.method_entry("get_result", key="value")
            logger.method_exit("get_result", 42)
        messages = [record.message for record in caplog.records]
        assert any("tracing" in message for message in messages)
        assert any("-> get_result" in message for message in messages)
        assert any("<- get_result" in message for message in messages)
