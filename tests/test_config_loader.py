# tests/test_config_loader.py
import pytest
import yaml

# Assume config_loader is importable (adjust path if necessary)
from src.config_loader import load_config


# Simple placeholder test
def test_load_config_exists():
    """Tests that the load_config function exists and is callable."""
    assert callable(load_config)


# More tests would go here, e.g.:
# - Test loading a valid dummy config file
# - Test handling of a non-existent config file
# - Test handling of invalid YAML format
# - Test validation of required config sections (if implemented)


# Example of setting up a temporary config for testing
@pytest.fixture
def temp_config_file(tmp_path):
    config_content = {
        "agent": {"schedule_interval_minutes": 30},
        "sources": {"rss_feeds": [{"url": "http://example.com/rss"}], "subreddits": [{"name": "example"}]},
        "trend_detection": {"history_window_days": 7, "stopwords": []},
        "generation": {
            "gemini_model": "gemini-1.5-flash-latest",
            "prompt_template": "Test prompt for {spark_keyword} from {source_name}",
        },
        "logging": {"level": "INFO", "log_file": str(tmp_path / "test_agent.log")},
    }
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_content, f)
    return str(config_path)


def test_load_valid_config(temp_config_file):
    """Tests loading a basic valid config file."""
    config = load_config(temp_config_file)
    assert isinstance(config, dict)
    assert "agent" in config
    assert config["agent"]["schedule_interval_minutes"] == 30
    assert "sources" in config


# Add more specific tests as needed
