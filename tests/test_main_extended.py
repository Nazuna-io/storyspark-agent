# tests/test_main_extended.py
import json
import os
import tempfile
from unittest.mock import Mock, patch

from src.main import _ensure_data_dir, _load_json, _save_json, main, save_seeds_to_markdown


def test_ensure_data_dir_creates():
    """Test that _ensure_data_dir creates directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = os.path.join(tmpdir, "nonexistent")
        with patch("src.main.DATA_DIR", data_dir):
            _ensure_data_dir()
            assert os.path.exists(data_dir)


def test_ensure_data_dir_exists():
    """Test that _ensure_data_dir handles existing directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("src.main.DATA_DIR", tmpdir):
            _ensure_data_dir()  # Should not error
            assert os.path.exists(tmpdir)


def test_save_json_creates_dir():
    """Test that _save_json creates directory if needed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "subdir", "test.json")
        with patch("src.main.DATA_DIR", os.path.join(tmpdir, "subdir")):
            _save_json({"test": "data"}, filepath)
            assert os.path.exists(filepath)

            with open(filepath) as f:
                data = json.load(f)
                assert data["test"] == "data"


def test_load_json_file_not_exists():
    """Test _load_json when file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "nonexistent.json")
        result = _load_json(filepath, default={"default": "value"})
        assert result == {"default": "value"}


def test_load_json_invalid_json():
    """Test _load_json with invalid JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "invalid.json")
        with open(filepath, "w") as f:
            f.write("invalid json")

        result = _load_json(filepath, default={"default": "value"})
        assert result == {"default": "value"}


def test_save_seeds_to_markdown_empty():
    """Test saving empty seeds to markdown."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "output.md")
        with patch("src.main.DATA_DIR", tmpdir):
            save_seeds_to_markdown([], filepath)

            assert os.path.exists(filepath)
            with open(filepath) as f:
                content = f.read()
                assert "No story seeds generated yet" in content


def test_save_seeds_to_markdown_with_data():
    """Test saving seeds with data to markdown."""
    seeds = [
        {
            "spark_keyword": "test",
            "source_name": "Test Source",
            "logline": "Test logline",
            "what_if_questions": ["Question 1", "Question 2"],
            "thematic_keywords": ["Theme 1", "Theme 2"],
        }
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "output.md")
        with patch("src.main.DATA_DIR", tmpdir):
            save_seeds_to_markdown(seeds, filepath)

            assert os.path.exists(filepath)
            with open(filepath) as f:
                content = f.read()
                assert "Test Source" in content
                assert "Test logline" in content
                assert "Question 1" in content


def test_save_seeds_error_handling():
    """Test error handling in save_seeds_to_markdown."""
    with patch("builtins.open", side_effect=IOError("Cannot write")):
        # Should not raise, just log
        save_seeds_to_markdown([{"test": "data"}], "/invalid/path.md")


def test_main_no_config():
    """Test main function when config fails to load."""
    with patch("src.config_loader.load_config", return_value=None):
        with patch("sys.exit") as mock_exit:
            main()
            mock_exit.assert_called_once_with(1)


def test_main_immediate_run():
    """Test main function with immediate run enabled."""
    mock_config = {
        "agent": {"run_immediately_on_start": True, "schedule_interval_minutes": 60},
        "logging": {"output_file": "test.md"},
    }

    with patch("src.config_loader.load_config", return_value=mock_config):
        with patch("src.logger_config.setup_logging"):
            with patch("src.main._ensure_data_dir"):
                with patch("src.main.load_fetcher_state", return_value={}):
                    with patch("src.main._load_json", return_value=[]):
                        with patch("src.main.save_seeds_to_markdown"):
                            with patch("src.main.run_agent_cycle", return_value=([], {}, [])):
                                with patch("schedule.every"):
                                    with patch("time.sleep", side_effect=KeyboardInterrupt):
                                        try:
                                            main()
                                        except KeyboardInterrupt:
                                            pass  # Expected
