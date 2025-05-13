# tests/test_main_simple.py
import json
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from src.main import _datetime_parser, _datetime_serializer, _save_json, save_seeds_to_markdown


def test_datetime_serializer_with_timezone():
    """Test datetime serializer with timezone-aware datetime."""
    dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    result = _datetime_serializer(dt)
    assert result == "2024-01-01T12:00:00+00:00"


def test_datetime_serializer_invalid_type():
    """Test datetime serializer with invalid type."""
    with pytest.raises(TypeError):
        _datetime_serializer("not a datetime")


def test_datetime_parser_invalid_iso():
    """Test datetime parser with invalid ISO string."""
    # Test with invalid format that should remain as string
    result = _datetime_parser({"date": "invalid-date-format"})
    assert result["date"] == "invalid-date-format"  # Should remain unchanged


def test_save_json_with_datetime():
    """Test saving JSON with datetime objects."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test.json")
        data = {"timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc), "text": "test"}

        with patch("src.main.DATA_DIR", tmpdir):
            _save_json(data, filepath)

            # Verify it was saved correctly
            with open(filepath) as f:
                saved_data = json.load(f)
                assert saved_data["timestamp"] == "2024-01-01T00:00:00+00:00"
                assert saved_data["text"] == "test"


def test_save_json_io_error():
    """Test save_json with IO error."""
    with patch("builtins.open", side_effect=IOError("Cannot write")):
        # Should not raise, just log
        _save_json({"test": "data"}, "/invalid/path.json")


def test_save_seeds_markdown_with_empty_fields():
    """Test saving seeds with empty fields."""
    seeds = [
        {
            "spark_keyword": "test",
            "source_name": "Test Source",
            "logline": None,  # Empty logline
            "what_if_questions": [],  # Empty list
            "thematic_keywords": None,  # None value
        }
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "output.md")
        save_seeds_to_markdown(seeds, filepath)

        with open(filepath) as f:
            content = f.read()
            assert "N/A" in content  # Should use N/A for empty fields
