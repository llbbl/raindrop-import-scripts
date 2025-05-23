import os
import pytest
import logging
import tempfile
from common.logging import setup_logging, get_logger


class TestLogging:
    """Tests for the logging module."""

    def test_setup_logging_console_only(self):
        """Test that setup_logging configures logging with console output only."""
        # Reset the logger before testing
        import common.logging
        common.logging.logger = None

        # Set up logging without a log file
        setup_logging()

        # Get the logger
        logger = get_logger()

        # Check that the logger is configured correctly
        assert logger.level == logging.INFO

        # Check that there's at least one handler
        assert len(logger.handlers) >= 1

        # Check that there are no file handlers
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 0

    def test_setup_logging_with_file(self):
        """Test that setup_logging configures logging with both console and file output."""
        # Reset the logger before testing
        import common.logging
        common.logging.logger = None

        # Create a temporary log file
        with tempfile.NamedTemporaryFile(suffix=".log") as temp_file:
            # Set up logging with a log file
            setup_logging(temp_file.name)

            # Get the logger
            logger = get_logger()

            # Check that the logger is configured correctly
            assert logger.level == logging.INFO

            # Check that there's at least one handler
            assert len(logger.handlers) >= 1

            # Check that there's a file handler
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
            assert len(file_handlers) == 1

            # Check that the file handler is writing to the correct file
            assert file_handlers[0].baseFilename == temp_file.name

    def test_get_logger_without_setup(self):
        """Test that get_logger raises a RuntimeError if setup_logging hasn't been called."""
        # Reset the logger before testing
        import common.logging
        common.logging.logger = None

        # Try to get the logger without setting it up
        with pytest.raises(RuntimeError) as excinfo:
            get_logger()
        assert "Logger not initialized" in str(excinfo.value)

    def test_setup_logging_invalid_file(self, monkeypatch, capsys):
        """Test that setup_logging handles invalid log files gracefully."""
        # Reset the logger before testing
        import common.logging
        common.logging.logger = None

        # Store the original FileHandler
        original_file_handler = logging.FileHandler

        # Mock logging.FileHandler to raise an exception
        def mock_file_handler(*args, **kwargs):
            raise IOError("Mock file handler error")

        monkeypatch.setattr(logging, "FileHandler", mock_file_handler)

        try:
            # Set up logging with an invalid log file
            setup_logging("/invalid/path/to/log/file.log")

            # Check that a warning was printed
            captured = capsys.readouterr()
            assert "Warning: Could not set up logging to file" in captured.out

            # Get the logger
            logger = get_logger()

            # Check that the logger is still configured with console output
            assert logger.level == logging.INFO

            # Check that there's at least one handler
            assert len(logger.handlers) >= 1

            # Check that there are no file handlers (using the original FileHandler class)
            # We can't use isinstance here because FileHandler is mocked
            # Just check that we have the expected number of handlers
            assert len(logger.handlers) == 1
        finally:
            # Restore the original FileHandler
            monkeypatch.setattr(logging, "FileHandler", original_file_handler)
