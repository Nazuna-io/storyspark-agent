# tests/test_config_loader_extended.py
from unittest.mock import mock_open, patch

import pytest
import yaml

from src.config_loader import load_config


def test_load_config_file_not_found():
    """Test load_config when file doesn't exist."""
    with patch("os.path.exists", return_value=False):
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent.yaml")


def test_load_config_invalid_yaml():
    """Test load_config with invalid YAML."""
    yaml_content = "invalid: yaml: content:"
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch("yaml.safe_load", side_effect=yaml.YAMLError("Invalid YAML")):
                with pytest.raises(yaml.YAMLError):
                    load_config("config.yaml")


def test_load_config_io_error():
    """Test load_config with IO error."""
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", side_effect=IOError("Cannot read file")):
            with pytest.raises(IOError):
                load_config("config.yaml")


def test_load_config_missing_required_keys():
    """Test load_config with missing required keys."""
    invalid_config = {"sources": {}}  # Missing other required keys
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=yaml.dump(invalid_config))):
            with pytest.raises(ValueError, match="Missing required configuration section"):
                load_config("config.yaml")


def test_load_config_invalid_types():
    """Test load_config with invalid types."""
    invalid_config = {
        "sources": "not-a-dict",  # Should be dict
        "trend_detection": {},
        "generation": {},
        "logging": {},
        "agent": {},
    }
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=yaml.dump(invalid_config))):
            with pytest.raises(ValueError, match="'sources' section must be a dictionary"):
                load_config("config.yaml")


def test_load_config_missing_required_subkeys():
    """Test load_config with missing required subkeys."""
    invalid_config = {
        "sources": {},
        "trend_detection": {"stopwords": []},  # Missing history_window_days
        "generation": {},  # Missing prompt_template
        "logging": {},  # Missing log_file
        "agent": {},  # Missing schedule_interval_minutes
    }
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=yaml.dump(invalid_config))):
            with pytest.raises(ValueError, match="Missing or invalid"):
                load_config("config.yaml")


def test_load_config_empty_file():
    """Test load_config with empty file."""
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data="")):
            with pytest.raises(ValueError, match="empty or invalid"):
                load_config("config.yaml")


def test_load_config_invalid_list_types():
    """Test load_config with invalid list types."""
    invalid_config = {
        "sources": {"rss_feeds": "not-a-list", "subreddits": []},  # Should be list
        "trend_detection": {"stopwords": [], "history_window_days": 7},
        "generation": {"prompt_template": "test"},
        "logging": {"log_file": "test.log"},
        "agent": {"schedule_interval_minutes": 60},
    }
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=yaml.dump(invalid_config))):
            with pytest.raises(ValueError, match="must be a list"):
                load_config("config.yaml")
