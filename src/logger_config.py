# src/logger_config.py
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Any, Dict


def setup_logging(config: Dict[str, Any]):
    """Configures logging based on the provided configuration dictionary.

    Sets up root logger level, format, and handlers (console, file).
    """
    log_config = config.get("logging", {})

    log_level_str = log_config.get("log_level", "INFO").upper()
    log_format_str = log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    log_file = log_config.get("log_file")  # Path to log file, if None, only console logging
    log_file_max_bytes = log_config.get("file_max_bytes", 10 * 1024 * 1024)  # 10 MB default
    log_file_backup_count = log_config.get("file_backup_count", 3)  # 3 backup files default

    # Validate log_level_str before using getattr
    if log_level_str not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        raise ValueError(f"Invalid log level: {log_level_str}")

    # Get the numeric log level
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Create formatter
    formatter = logging.Formatter(log_format_str)

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates if called multiple times (though it shouldn't be)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # --- Console Handler ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)  # Console logs at the specified level
    root_logger.addHandler(console_handler)

    # --- File Handler (Optional) ---
    if log_file:
        try:
            # Ensure log directory exists
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
                print(f"Created log directory: {log_dir}")  # Use print as logging might not be fully set up

            # Use RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_file, maxBytes=log_file_max_bytes, backupCount=log_file_backup_count, encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            # You might want the file logger to capture more detail, e.g., DEBUG
            file_log_level_str = log_config.get("file_level", log_level_str).upper()
            file_log_level = getattr(logging, file_log_level_str, log_level)
            file_handler.setLevel(file_log_level)

            root_logger.addHandler(file_handler)
            print(f"Logging configured. Level: {log_level_str}, File: {log_file} (Level: {file_log_level_str})")

        except Exception as e:
            # Use print because logging might have failed
            print(f"Error setting up file logging handler for {log_file}: {e}", file=sys.stderr)
    else:
        print(f"Logging configured. Level: {log_level_str}, Console only.")


# Example usage (usually called from main.py):
# if __name__ == '__main__':
#     # Dummy config for testing
#     test_config = {
#         'logging': {
#             'log_level': 'DEBUG',
#             'format': '%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s',
#             'log_file': 'logs/agent_test.log',
#             'file_level': 'DEBUG',
#             'file_max_bytes': 1024*1024, # 1MB
#             'file_backup_count': 1
#         }
#     }
#     setup_logging(test_config)
#     logging.debug('This is a debug message.')
#     logging.info('This is an info message.')
#     logging.warning('This is a warning message.')
#     logging.error('This is an error message.')
#     logging.critical('This is a critical message.')
