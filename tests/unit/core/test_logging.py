"""
Tests for the logging configuration system.

Tests structured logging, file handling, platform-specific directories,
and log rotation functionality.
"""

import json
import logging
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from tino.core.logging import (
    ColoredConsoleFormatter,
    LogLevel,
    StructuredFormatter,
    TinoLogger,
    cleanup_logging,
    configure_logging,
    get_logger,
)


class TestStructuredFormatter:
    """Test the structured JSON formatter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = StructuredFormatter()

    def test_basic_formatting(self):
        """Test basic log record formatting."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_function",
        )

        formatted = self.formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test.logger"
        assert log_data["message"] == "Test message"
        assert log_data["module"] == "test"
        assert log_data["function"] == "test_function"
        assert log_data["line"] == 42
        assert "timestamp" in log_data

    def test_exception_formatting(self):
        """Test formatting with exception information."""
        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=exc_info,  # Pass actual exception info
                func="test_function",
            )

        formatted = self.formatter.format(record)
        log_data = json.loads(formatted)

        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"
        assert log_data["exception"]["message"] == "Test exception"
        assert "traceback" in log_data["exception"]

    def test_extra_fields(self):
        """Test formatting with extra fields."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_function",
        )

        # Add extra fields
        record.user_id = "12345"
        record.session_id = "abcdef"

        formatted = self.formatter.format(record)
        log_data = json.loads(formatted)

        assert "extra" in log_data
        assert log_data["extra"]["user_id"] == "12345"
        assert log_data["extra"]["session_id"] == "abcdef"


class TestColoredConsoleFormatter:
    """Test the colored console formatter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = ColoredConsoleFormatter()

    def test_basic_formatting(self):
        """Test basic console formatting."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_function",
        )

        formatted = self.formatter.format(record)

        # Should contain color codes for INFO level
        assert "\033[32m" in formatted  # Green color
        assert "\033[0m" in formatted  # Reset code
        assert "[    INFO]" in formatted
        assert "test.logger: Test message" in formatted

    def test_different_log_levels_have_different_colors(self):
        """Test that different log levels use different colors."""
        levels = [
            (logging.DEBUG, "\033[36m"),  # Cyan
            (logging.INFO, "\033[32m"),  # Green
            (logging.WARNING, "\033[33m"),  # Yellow
            (logging.ERROR, "\033[31m"),  # Red
            (logging.CRITICAL, "\033[35m"),  # Magenta
        ]

        for level, color_code in levels:
            record = logging.LogRecord(
                name="test.logger",
                level=level,
                pathname="test.py",
                lineno=42,
                msg="Test message",
                args=(),
                exc_info=None,
                func="test_function",
            )

            formatted = self.formatter.format(record)
            assert color_code in formatted

    def test_exception_formatting(self):
        """Test console formatting with exceptions."""
        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=exc_info,
                func="test_function",
            )

        formatted = self.formatter.format(record)

        # Should contain exception information
        assert "ValueError" in formatted
        assert "Test exception" in formatted


class TestTinoLogger:
    """Test the main TinoLogger class."""

    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()

        # Mock platformdirs to use temp directory
        with (
            patch("tino.core.logging.user_log_dir") as mock_log_dir,
            patch("tino.core.logging.user_cache_dir") as mock_cache_dir,
        ):
            mock_log_dir.return_value = str(Path(self.temp_dir) / "logs")
            mock_cache_dir.return_value = str(Path(self.temp_dir) / "cache")
            self.logger = TinoLogger("test_tino")

    def test_initialization(self):
        """Test logger initialization."""
        assert self.logger.app_name == "test_tino"
        assert self.logger.log_dir.exists()
        assert self.logger.cache_dir.exists()
        assert not self.logger._configured

    def test_configure_console_only(self):
        """Test configuration with console output only."""
        self.logger.configure(level="DEBUG", console_output=True, file_output=False)

        assert self.logger._configured
        assert "console" in self.logger._handlers
        assert "file" not in self.logger._handlers

    def test_configure_file_only(self):
        """Test configuration with file output only."""
        self.logger.configure(level="INFO", console_output=False, file_output=True)

        assert self.logger._configured
        assert "file" in self.logger._handlers
        assert "console" not in self.logger._handlers

        # Check that log file exists
        log_file = self.logger.log_dir / "tino.log"
        assert log_file.exists()

    def test_configure_structured_logs(self):
        """Test configuration with structured JSON logging."""
        self.logger.configure(
            structured_logs=True, console_output=True, file_output=True
        )

        # Both handlers should use structured formatter
        console_handler = self.logger._handlers["console"]
        file_handler = self.logger._handlers["file"]

        assert isinstance(console_handler.formatter, StructuredFormatter)
        assert isinstance(file_handler.formatter, StructuredFormatter)

    def test_configure_debug_mode(self):
        """Test configuration with debug mode enabled."""
        self.logger.configure(debug_mode=True, file_output=True)

        assert "debug" in self.logger._handlers

        # Check that debug log file exists
        debug_file = self.logger.log_dir / "debug.log"
        assert debug_file.exists()

    def test_get_logger(self):
        """Test getting a named logger."""
        self.logger.configure()
        logger = self.logger.get_logger("test.module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_set_level(self):
        """Test changing log levels."""
        self.logger.configure(console_output=True)

        # Set level for specific handler
        self.logger.set_level("DEBUG", "console")
        console_handler = self.logger._handlers["console"]
        assert console_handler.level == logging.DEBUG

        # Set level for all handlers
        self.logger.set_level("ERROR")
        assert console_handler.level == logging.ERROR

    def test_cleanup(self):
        """Test cleaning up handlers."""
        self.logger.configure(console_output=True, file_output=True)

        assert len(self.logger._handlers) > 0
        assert self.logger._configured

        self.logger.cleanup()

        assert len(self.logger._handlers) == 0
        assert not self.logger._configured

    def test_get_log_files(self):
        """Test getting list of log files."""
        self.logger.configure(file_output=True, debug_mode=True)

        # Write some logs to ensure files are created
        logger = self.logger.get_logger("test")
        logger.info("Test message")
        logger.debug("Debug message")

        log_files = self.logger.get_log_files()

        # Should have at least main log and debug log
        log_names = [f.name for f in log_files]
        assert "tino.log" in log_names
        assert "debug.log" in log_names

    def test_get_log_stats(self):
        """Test getting logging statistics."""
        self.logger.configure(console_output=True, file_output=True)

        stats = self.logger.get_log_stats()

        assert stats["configured"] is True
        assert "console" in stats["handlers"]
        assert "file" in stats["handlers"]
        assert "log_directory" in stats
        assert "log_files" in stats

    def test_rotate_logs(self):
        """Test manual log rotation."""
        self.logger.configure(file_output=True)

        # Write some data to log file
        logger = self.logger.get_logger("test")
        logger.info("Before rotation")

        # Rotate logs
        result = self.logger.rotate_logs()
        assert result is True

        # Write more data
        logger.info("After rotation")

        # Should have created backup file
        log_files = self.logger.get_log_files()
        backup_files = [f for f in log_files if ".1" in f.name]
        assert len(backup_files) > 0


class TestLogLevel:
    """Test the LogLevel context manager."""

    def test_temporary_level_change(self):
        """Test temporarily changing log level."""
        logger = logging.getLogger("test.temp")
        original_level = logger.level

        with LogLevel("DEBUG", "test.temp"):
            assert logger.level == logging.DEBUG

        # Should be restored after context
        assert logger.level == original_level

    def test_root_logger_level_change(self):
        """Test changing root logger level."""
        root_logger = logging.getLogger()
        original_level = root_logger.level

        with LogLevel("CRITICAL"):
            assert root_logger.level == logging.CRITICAL

        assert root_logger.level == original_level


class TestModuleFunctions:
    """Test module-level functions."""

    def setup_method(self):
        """Set up clean state."""
        cleanup_logging()

    def teardown_method(self):
        """Clean up after tests."""
        cleanup_logging()

    def test_get_logger_creates_default(self):
        """Test that get_logger creates default logger if needed."""
        with patch("tino.core.logging.TinoLogger") as mock_tino_logger:
            mock_instance = Mock()
            mock_tino_logger.return_value = mock_instance

            get_logger("test.module")  # Just get logger instance

            mock_tino_logger.assert_called_once()
            mock_instance.configure.assert_called_once()
            mock_instance.get_logger.assert_called_with("test.module")

    def test_configure_logging_creates_logger(self):
        """Test that configure_logging creates and configures logger."""
        with patch("tino.core.logging.TinoLogger") as mock_tino_logger:
            mock_instance = Mock()
            mock_tino_logger.return_value = mock_instance

            result = configure_logging(level="DEBUG", console_output=False)

            mock_tino_logger.assert_called_once()
            mock_instance.configure.assert_called_with(
                level="DEBUG", console_output=False
            )
            assert result == mock_instance

    def test_cleanup_logging(self):
        """Test cleaning up default logger."""
        # Set up a mock default logger
        with patch("tino.core.logging._default_logger", Mock()) as mock_logger:
            cleanup_logging()
            mock_logger.cleanup.assert_called_once()


class TestIntegrationLogging:
    """Integration tests for logging functionality."""

    def setup_method(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()

        with (
            patch("tino.core.logging.user_log_dir") as mock_log_dir,
            patch("tino.core.logging.user_cache_dir") as mock_cache_dir,
        ):
            mock_log_dir.return_value = str(Path(self.temp_dir) / "logs")
            mock_cache_dir.return_value = str(Path(self.temp_dir) / "cache")
            self.logger_instance = TinoLogger("integration_test")

    def test_end_to_end_logging(self):
        """Test complete logging workflow."""
        # Configure logging
        self.logger_instance.configure(
            level="DEBUG", console_output=True, file_output=True, debug_mode=True
        )

        # Get logger and write messages
        logger = self.logger_instance.get_logger("integration.test")

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # Check that files were created
        log_files = self.logger_instance.get_log_files()
        assert len(log_files) >= 2  # At least main log and debug log

        # Check file contents
        main_log = self.logger_instance.log_dir / "tino.log"
        debug_log = self.logger_instance.log_dir / "debug.log"

        assert main_log.exists()
        assert debug_log.exists()

        main_content = main_log.read_text()
        debug_content = debug_log.read_text()

        # Main log should have info and above
        assert "Info message" in main_content
        assert "Warning message" in main_content
        assert "Error message" in main_content

        # Debug log should have all messages
        assert "Debug message" in debug_content
        assert "Info message" in debug_content
        assert "Warning message" in debug_content
        assert "Error message" in debug_content

    def test_logging_with_exceptions(self):
        """Test logging exception information."""
        self.logger_instance.configure(file_output=True)
        logger = self.logger_instance.get_logger("exception.test")

        try:
            raise ValueError("Test exception for logging")
        except ValueError:
            logger.exception("Exception occurred")

        # Check that exception was logged
        log_file = self.logger_instance.log_dir / "tino.log"
        content = log_file.read_text()

        assert "Exception occurred" in content
        assert "ValueError" in content
        assert "Test exception for logging" in content

    def test_structured_logging_output(self):
        """Test structured JSON logging output."""
        self.logger_instance.configure(structured_logs=True, file_output=True)

        logger = self.logger_instance.get_logger("structured.test")
        logger.info("Structured log message", extra={"user_id": 123, "action": "login"})

        # Check JSON output
        log_file = self.logger_instance.log_dir / "tino.log"
        content = log_file.read_text()

        # Should be valid JSON
        log_lines = [line for line in content.strip().split("\n") if line]
        assert len(log_lines) >= 1

        # Find the test message (not the configuration message)
        test_log = None
        for line in log_lines:
            log_entry = json.loads(line)
            if log_entry.get("logger") == "structured.test":
                test_log = log_entry
                break

        assert test_log is not None, "Could not find test log entry"
        assert test_log["message"] == "Structured log message"
        assert test_log["level"] == "INFO"
        assert test_log["logger"] == "structured.test"
