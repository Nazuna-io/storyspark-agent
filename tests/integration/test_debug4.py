# tests/integration/test_debug4.py
import logging
import os
from unittest.mock import Mock, patch

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)


def test_full_integration_analyze():
    """Test full integration and analyze results."""
    config = {
        "sources": {"rss_feeds": [{"url": "http://test.com/feed.xml"}], "subreddits": []},
        "trend_detection": {
            "history_window_days": 7,
            "min_keyword_frequency": 1,
            "frequency_threshold": 1.0,
            "stopwords": ["the", "a"],
        },
        "generation": {"api_key": "test-key", "prompt_template": "Generate for {spark_keyword} from {source_name}"},
        "agent": {"data_dir": "/tmp/test"},
    }

    os.environ["GOOGLE_API_KEY"] = "test-key"

    import time

    from src.main import run_agent_cycle

    time_struct = time.struct_time((2024, 1, 2, 12, 0, 0, 0, 0, 0))

    with patch("feedparser.parse") as mock_parse:
        # Create simple entry with repeated word
        mock_entry = Mock()
        entry_dict = {
            "title": "test test test",
            "link": "http://test.com/1",
            "id": "test1",
            "published_parsed": time_struct,
            "summary": "test content",
        }
        mock_entry.configure_mock(**entry_dict)
        mock_entry.get = lambda key, default=None: entry_dict.get(key, default)

        mock_feed = Mock(title="Test Feed")
        mock_feed.get = (
            lambda key, default=None: getattr(mock_feed, key, default) if hasattr(mock_feed, key) else default
        )

        mock_result = Mock(bozo=False, status=200, feed=mock_feed, entries=[mock_entry])
        mock_result.get = (
            lambda key, default=None: getattr(mock_result, key, default) if hasattr(mock_result, key) else default
        )

        mock_parse.return_value = mock_result

        with patch("google.generativeai.GenerativeModel") as mock_genai:
            mock_model = Mock()
            mock_response = Mock()
            response_text = """**Logline:**
Test logline

**What If Questions:**
- What if?

**Thematic Keywords:**
- Keyword1"""

            # Make the response work with .text property
            mock_response.text = response_text
            mock_response.candidates = [Mock(content=Mock(parts=[Mock(text=response_text)]))]
            mock_model.generate_content.return_value = mock_response
            mock_genai.return_value = mock_model

            print("Starting full test cycle...")
            history, timestamps, seeds = run_agent_cycle(config, [], {})
            print(f"Result: history={history}, timestamps={timestamps}, seeds={seeds}")

            # Analyze what happened
            if not history:
                print("No history - items might have been filtered by age")

            # Let's also try providing an older history item
            print("\nTrying with old history...")
            import datetime

            old_item = {
                "title": "old item",
                "timestamp": datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc),
                "content_snippet": "old content",
            }
            history2, timestamps2, seeds2 = run_agent_cycle(config, [old_item], {})
            print(f"Result2: history={history2}, timestamps={timestamps2}, seeds={seeds2}")
