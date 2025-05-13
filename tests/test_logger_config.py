# tests/test_logger_config.py
import logging
from unittest.mock import mock_open, patch

import pytest

from src.logger_config import setup_logging


@pytest.fixture
def mock_config():
    """Sample configuration for testing."""
    return {"logging": {"log_level": "INFO", "log_file": "test_agent.log"}}


@pytest.fixture
def mock_config_debug():
    """Sample configuration with DEBUG level."""
    return {"logging": {"log_level": "DEBUG", "log_file": "test_debug.log"}}


@pytest.fixture
def mock_config_no_file():
    """Sample configuration without log file."""
    return {"logging": {"log_level": "WARNING"}}


class TestSetupLogging:
    """Test logging setup functionality."""

    def test_setup_logging_info_level(self, mock_config, caplog):
        """Test setup with INFO level."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers = []

        setup_logging(mock_config)

        # Test that INFO level is set
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_setup_logging_debug_level(self, mock_config_debug):
        """Test setup with DEBUG level."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers = []

        setup_logging(mock_config_debug)

        # Test that DEBUG level is set
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    @patch("builtins.open", mock_open())
    @patch("os.path.exists")
    def test_setup_logging_with_file(self, mock_exists, mock_config):
        """Test setup with file handler."""
        mock_exists.return_value = True

        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers = []

        setup_logging(mock_config)

        # Check that both console and file handlers are added
        assert len(root_logger.handlers) >= 1  # At least console handler

        # Find file handler
        file_handler = None
        for handler in root_logger.handlers:
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                file_handler = handler
                break

        assert file_handler is not None
        assert file_handler.baseFilename.endswith("test_agent.log")

    def test_setup_logging_no_file(self, mock_config_no_file):
        """Test setup without file handler."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers = []

        setup_logging(mock_config_no_file)

        # Check that only console handler is added
        assert len(root_logger.handlers) >= 1

        # Verify no file handler
        file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert len(file_handlers) == 0

    def test_setup_logging_default_level(self):
        """Test setup with default configuration."""
        config = {}

        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers = []

        setup_logging(config)

        # Should default to INFO level
        assert root_logger.level == logging.INFO

    def test_setup_logging_invalid_level(self):
        """Test setup with invalid log level."""
        config = {"logging": {"log_level": "INVALID_LEVEL"}}

        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers = []

        # Should raise ValueError for invalid level
        with pytest.raises(ValueError) as excinfo:
            setup_logging(config)

        assert "Invalid log level" in str(excinfo.value)

    @patch("builtins.open", mock_open())
    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_setup_logging_create_directory(self, mock_makedirs, mock_exists):
        """Test setup creates log directory if needed."""
        # Configure the log file to be in a subdirectory
        config = {"logging": {"log_level": "INFO", "log_file": "logs/test_agent.log"}}

        # Mock that directory doesn't exist
        mock_exists.return_value = False

        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers = []

        setup_logging(config)

        # Check that makedirs was called
        mock_makedirs.assert_called_once_with("logs")

    def test_setup_logging_console_handler(self, mock_config):
        """Test console handler is properly configured."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers = []

        setup_logging(mock_config)

        # Find console handler
        console_handler = None
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                console_handler = handler
                break

        assert console_handler is not None
        assert console_handler.level == logging.INFO

        # Test that formatter is properly set
        formatter = console_handler.formatter
        assert formatter is not None

        # Log a test message
        test_logger = logging.getLogger("test.module")
        test_logger.info("Test message")
