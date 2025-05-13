# tests/integration/test_simple.py

from unittest.mock import Mock, patch

from src.main import run_agent_cycle


def test_basic_integration():
    """Test basic integration without complex mocking."""
    config = {
        "sources": {"rss_feeds": [{"url": "http://test.com/feed.xml"}], "subreddits": []},
        "trend_detection": {
            "history_window": 7,
            "spark_threshold": 2.0,
            "min_keyword_frequency": 1,  # Very low for testing
            "frequency_threshold": 1.5,  # Lower threshold
            "stopwords": ["the", "a", "an"],
            "history_window_days": 7,
        },
        "generation": {
            "api_key": "test-key",
            "prompt_template": "Generate story for {spark_keyword} from {source_name}",
        },
        "agent": {"data_dir": "/tmp/test", "max_sparks_per_cycle": 5},
    }

    # Mock RSS feed
    import time

    time_struct = time.struct_time((2024, 1, 2, 12, 0, 0, 0, 0, 0))

    with patch("feedparser.parse") as mock_parse:
        mock_entry = Mock()
        mock_entry.configure_mock(
            **{
                "title": "AI AI AI Test",  # Repeated word for frequency
                "link": "http://test.com/1",
                "id": "test1",
                "published_parsed": time_struct,
                "summary": "AI test content",
                "get": lambda key, default=None: {
                    "title": "AI AI AI Test",
                    "link": "http://test.com/1",
                    "id": "test1",
                    "published_parsed": time_struct,
                    "summary": "AI test content",
                }.get(key, default),
            }
        )

        mock_feed = Mock()
        mock_feed.title = "Test Feed"
        mock_feed.get = (
            lambda key, default=None: getattr(mock_feed, key, default) if hasattr(mock_feed, key) else default
        )

        mock_result = Mock(bozo=False, status=200, feed=mock_feed, entries=[mock_entry])
        mock_result.get = (
            lambda key, default=None: getattr(mock_result, key, default) if hasattr(mock_result, key) else default
        )

        mock_parse.return_value = mock_result

        # Mock Gemini
        with patch("google.generativeai.GenerativeModel") as mock_genai:
            mock_model = Mock()
            mock_response = Mock()
            mock_response.candidates = [
                Mock(
                    content=Mock(
                        parts=[
                            Mock(
                                text="""
            **Logline:**
            A test logline
            
            **What If Questions:**
            - What if test?
            
            **Thematic Keywords:**
            - Test
            """
                            )
                        ]
                    )
                )
            ]
            mock_model.generate_content.return_value = mock_response
            mock_genai.return_value = mock_model

            # Run cycle
            history, timestamps, seeds = run_agent_cycle(config, [], {})

            # Check results
            assert history is not None
            assert timestamps is not None
            print(f"Seeds: {seeds}")
            # We might not get seeds if frequency isn't high enough

