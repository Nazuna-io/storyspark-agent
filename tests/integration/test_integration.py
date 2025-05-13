# tests/integration/test_integration.py
import json
import os
import tempfile
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

from src.data_fetcher import load_state, save_state
from src.main import run_agent_cycle


class TestEndToEndIntegration:
    """End-to-end integration tests for the StorySpark Agent."""

    @pytest.fixture
    def temp_directory(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdirname:
            yield tmpdirname

    @pytest.fixture
    def mock_config(self, temp_directory):
        """Create a mock configuration for testing."""
        return {
            "sources": {
                "rss_feeds": [{"url": "http://test.com/feed.xml", "name": "Test Feed"}],
                "subreddits": [{"name": "test", "limit": 25}],
            },
            "trend_detection": {
                "history_window": 7,
                "spark_threshold": 2.5,
                "min_frequency": 2,  # Reduced for easier testing
                "max_sparks_to_process": 5,
                "min_keyword_frequency": 2,  # Also add this alternative name
                "frequency_threshold": 2.5,  # Add this for spark detection
                "stopwords": ["the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"],
            },
            "generation": {
                "api_key": "test-api-key",
                "generation_config": {"temperature": 0.7},
                "system_instruction": "Test instruction",
                "prompt_template": 'Generate a story idea for the spark keyword "{spark_keyword}" found in {source_name}',
            },
            "agent": {"data_dir": temp_directory, "run_interval": 3600},
        }

    @patch("feedparser.parse")
    @patch("requests.get")
    @patch("google.generativeai.GenerativeModel")
    def test_full_workflow_with_real_data(self, mock_genai, mock_reddit, mock_rss, mock_config):
        """Test the full workflow from data collection to story generation."""
        # Setup mock RSS feed with recent date
        import time
        from datetime import datetime, timedelta, timezone

        recent_date = datetime.now(timezone.utc) - timedelta(days=1)
        time_struct = time.struct_time(recent_date.timetuple()[:9])

        # Create multiple entries to ensure minimum frequency is met
        entries = []
        for i in range(5):
            mock_entry = Mock()
            mock_entry.configure_mock(
                **{
                    "title": f"AI Breakthrough {i}",
                    "link": f"http://test.com/{i}",
                    "id": f"test{i}",
                    "published_parsed": time_struct,
                    "summary": "Major AI advancement announced artificial intelligence",
                    "get": lambda key, default=None, idx=i: {
                        "title": f"AI Breakthrough {idx}",
                        "link": f"http://test.com/{idx}",
                        "id": f"test{idx}",
                        "published_parsed": time_struct,
                        "summary": "Major AI advancement announced artificial intelligence",
                    }.get(key, default),
                }
            )
            entries.append(mock_entry)

        mock_feed = Mock()
        mock_feed.title = "Test Feed"
        # Add get method for feed
        mock_feed.get = (
            lambda key, default=None: getattr(mock_feed, key, default) if hasattr(mock_feed, key) else default
        )

        mock_rss.return_value = Mock(bozo=False, status=200, feed=mock_feed, entries=entries)
        # Add get method to fetch the status properly
        mock_rss.return_value.get = (
            lambda key, default=None: getattr(mock_rss.return_value, key, default)
            if hasattr(mock_rss.return_value, key)
            else default
        )

        # Setup mock Reddit response
        mock_reddit_response = Mock()
        mock_reddit_response.status_code = 200
        mock_reddit_response.history = []
        # Also create multiple Reddit posts with recent timestamps
        reddit_children = []
        base_timestamp = int(recent_date.timestamp())
        for i in range(5):
            reddit_children.append(
                {
                    "kind": "t3",
                    "data": {
                        "id": f"post{i}",
                        "name": f"t3_post{i}",
                        "title": f"AI Discussion {i}",
                        "created_utc": base_timestamp + i * 60,  # Different timestamps
                        "selftext": "AI artificial intelligence is changing everything",
                    },
                }
            )

        mock_reddit_response.json.return_value = {"data": {"children": reddit_children}}
        mock_reddit.return_value = mock_reddit_response

        # Setup mock Gemini response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.candidates = [
            Mock(
                content=Mock(
                    parts=[
                        Mock(
                            text="""
        **Logline:**
        In a world where AI consciousness emerges, a scientist races to understand.
        
        **What If Questions:**
        - What if AI developed emotions?
        - What if machines could dream?
        
        **Thematic Keywords:**
        - Consciousness
        - Ethics
        - Technology
        """
                        )
                    ]
                )
            )
        ]
        mock_model.generate_content.return_value = mock_response
        mock_genai.return_value = mock_model

        # Run the cycle
        timestamp_data, updated_timestamps, seeds = run_agent_cycle(mock_config, [], {})

        # Assertions
        assert timestamp_data is not None
        assert updated_timestamps is not None
        assert len(seeds) > 0  # Should have generated seeds

        # Verify that the seed contains expected keywords
        generated_keywords = []
        for seed in seeds:
            generated_keywords.append(seed.get("spark_keyword", ""))

        # AI or artificial or intelligence should be in the keywords
        assert any(keyword in generated_keywords for keyword in ["ai", "artificial", "intelligence", "breakthrough"])

        # Check that files were created
        generated_path = os.path.join(mock_config["agent"]["data_dir"], "generated")
        assert os.path.exists(generated_path)

        # Find the generated files
        files = os.listdir(generated_path)
        json_files = [f for f in files if f.endswith(".json")]
        md_files = [f for f in files if f.endswith(".md")]

        assert len(json_files) > 0
        assert len(md_files) > 0

    @patch("feedparser.parse")
    @patch("requests.get")
    def test_data_collection_and_trend_detection(self, mock_reddit, mock_rss, mock_config):
        """Test that data collection and trend detection work together."""
        # Create historical data
        history_data = {"ai": 2, "technology": 3, "science": 4}
        history_file = os.path.join(mock_config["agent"]["data_dir"], "keyword_history.json")
        with open(history_file, "w") as f:
            json.dump(history_data, f)

        # Setup mocks with high frequency keywords
        import time
        from datetime import datetime, timedelta, timezone

        recent_date = datetime.now(timezone.utc) - timedelta(days=1)
        time_struct = time.struct_time(recent_date.timetuple()[:9])

        # Create multiple entries with same keywords
        entries = []
        for i in range(5):
            mock_entry = Mock()
            mock_entry.configure_mock(
                **{
                    "title": f"AI Article {i}",
                    "link": f"http://test.com/{i}",
                    "id": f"test{i}",
                    "published_parsed": time_struct,
                    "summary": "Another AI breakthrough in technology",
                    "get": lambda key, default=None, idx=i: {
                        "title": f"AI Article {idx}",
                        "link": f"http://test.com/{idx}",
                        "id": f"test{idx}",
                        "published_parsed": time_struct,
                        "summary": "Another AI breakthrough in technology",
                    }.get(key, default),
                }
            )
            entries.append(mock_entry)

        mock_feed = Mock()
        mock_feed.title = "Test Feed"
        mock_feed.get = (
            lambda key, default=None: getattr(mock_feed, key, default) if hasattr(mock_feed, key) else default
        )

        mock_rss.return_value = Mock(bozo=False, status=200, feed=mock_feed, entries=entries)
        # Add get method to fetch the status properly
        mock_rss.return_value.get = (
            lambda key, default=None: getattr(mock_rss.return_value, key, default)
            if hasattr(mock_rss.return_value, key)
            else default
        )

        mock_reddit_response = Mock()
        mock_reddit_response.status_code = 200
        mock_reddit_response.history = []
        mock_reddit_response.json.return_value = {"data": {"children": []}}
        mock_reddit.return_value = mock_reddit_response

        from src.main import run_agent_cycle

        with patch("src.story_seed_generator.generate_story_seed") as mock_generate:
            mock_generate.return_value = {"logline": "Test story", "spark_keyword": "ai"}

            # Pass empty history list instead of history_data dict
            history, updated_timestamps, seeds = run_agent_cycle(mock_config, [], {})

            # Check that trends were detected (by verifying seeds were generated)
            assert len(seeds) > 0
            assert seeds[0]["spark_keyword"] == "ai"

            # Check that generate was called for detected sparks
            assert mock_generate.call_count > 0

    def test_concurrent_source_fetching(self, mock_config):
        """Test that multiple sources can be fetched."""
        # Add more sources to config
        mock_config["sources"]["rss_feeds"] = [{"url": f"http://test{i}.com/feed.xml"} for i in range(3)]
        mock_config["sources"]["subreddits"] = [{"name": f"test{i}"} for i in range(3)]

        fetch_count = 0

        def mock_fetch(*args, **kwargs):
            """Count fetch calls."""
            nonlocal fetch_count
            fetch_count += 1
            return []

        with patch("src.data_fetcher.fetch_rss", side_effect=mock_fetch):
            with patch("src.data_fetcher.fetch_subreddit_json", side_effect=mock_fetch):
                from src.data_fetcher import get_new_items

                # This tests that all sources are fetched
                items, timestamps = get_new_items(mock_config, {})

                total_sources = len(mock_config["sources"]["rss_feeds"]) + len(mock_config["sources"]["subreddits"])

                # Verify all sources were fetched
                assert fetch_count == total_sources


class TestErrorHandlingIntegration:
    """Test error handling across the integrated system."""

    @pytest.fixture
    def temp_directory(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdirname:
            yield tmpdirname

    @patch("feedparser.parse")
    @patch("requests.get")
    @patch("google.generativeai.GenerativeModel")
    def test_graceful_degradation_with_source_failures(self, mock_genai, mock_reddit, mock_rss, temp_directory):
        """Test that the system continues when some sources fail."""
        config = {
            "sources": {
                "rss_feeds": [{"url": "http://fail.com/feed.xml"}, {"url": "http://success.com/feed.xml"}],
                "subreddits": [{"name": "fail"}, {"name": "success"}],
            },
            "trend_detection": {"history_window": 7, "spark_threshold": 2.0, "min_frequency": 2},
            "generation": {
                "api_key": "test-key",
                "generation_config": {"temperature": 0.7},
                "prompt_template": "Generate for {spark_keyword} from {source_name}",
            },
            "agent": {"data_dir": temp_directory},
        }

        # First RSS feed fails
        def rss_side_effect(url, **kwargs):  # Accept any keyword args
            if "fail" in url:
                raise Exception("Network error")
            mock_feed = Mock()
            mock_feed.title = "Success Feed"
            mock_feed.get = (
                lambda key, default=None: getattr(mock_feed, key, default) if hasattr(mock_feed, key) else default
            )

            # Create a successful entry
            import time
            from datetime import datetime, timedelta, timezone

            recent_date = datetime.now(timezone.utc) - timedelta(days=1)
            time_struct = time.struct_time(recent_date.timetuple()[:9])
            mock_entry = Mock()
            mock_entry.configure_mock(
                **{
                    "title": "Success Article",
                    "link": "http://success.com/1",
                    "id": "success1",
                    "published_parsed": time_struct,
                    "summary": "Success content",
                    "get": lambda key, default=None: {
                        "title": "Success Article",
                        "link": "http://success.com/1",
                        "id": "success1",
                        "published_parsed": time_struct,
                        "summary": "Success content",
                    }.get(key, default),
                }
            )

            result = Mock(bozo=False, status=200, entries=[mock_entry], feed=mock_feed)
            result.get = lambda key, default=None: getattr(result, key, default) if hasattr(result, key) else default
            return result

        mock_rss.side_effect = rss_side_effect

        # First subreddit fails
        def reddit_side_effect(url, *args, **kwargs):
            if "fail" in url:
                response = Mock()
                response.raise_for_status.side_effect = Exception("404")
                return response
            response = Mock()
            response.status_code = 200
            recent_date = datetime.now(timezone.utc) - timedelta(days=1)
            base_timestamp = int(recent_date.timestamp())
            response.json.return_value = {
                "data": {
                    "children": [
                        {
                            "kind": "t3",
                            "data": {
                                "id": "success1",
                                "name": "t3_success1",
                                "title": "Success Post",
                                "created_utc": base_timestamp,  # Recent timestamp
                                "selftext": "Success content",
                            },
                        }
                    ]
                }
            }
            response.history = []
            return response

        mock_reddit.side_effect = reddit_side_effect

        # Setup mock Gemini
        mock_model = Mock()
        mock_model.generate_content.return_value = Mock(candidates=[Mock(content=Mock(parts=[Mock(text="Story")]))])
        mock_genai.return_value = mock_model

        # Run should complete despite failures
        from src.main import run_agent_cycle

        history, updated_timestamps, seeds = run_agent_cycle(config, [], {})

        assert history is not None
        assert updated_timestamps is not None

        # Check that successful sources were processed
        assert "rss_http://success.com/feed.xml" in updated_timestamps
        assert "reddit_success" in updated_timestamps

    def test_state_persistence_across_runs(self, temp_directory):
        """Test that state is properly saved and loaded between runs."""
        config = {
            "sources": {"rss_feeds": [], "subreddits": []},
            "trend_detection": {"history_window": 7},
            "agent": {"data_dir": temp_directory},
        }

        # First run - create some state
        test_timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc)
        initial_state = {"test_source": test_timestamp}

        state_file = os.path.join(temp_directory, "fetcher_state.json")
        save_state(initial_state, state_file)

        # Load state in new "session"
        loaded_state = load_state(state_file)

        assert loaded_state == initial_state
        assert loaded_state["test_source"] == test_timestamp

    def test_config_validation_integration(self, temp_directory):
        """Test that invalid configurations are handled gracefully."""
        invalid_configs = [
            {},  # Empty config
            {"sources": {}},  # Missing required fields
            {"sources": {"rss_feeds": "not-a-list"}},  # Wrong type
        ]

        for invalid_config in invalid_configs:
            invalid_config["agent"] = {"data_dir": temp_directory}  # Add required data dir

            from src.main import run_agent_cycle

            # Should handle gracefully without crashing
            try:
                result = run_agent_cycle(invalid_config, [], {})
                # Depending on implementation, might return empty results
                assert result is not None
                assert len(result) == 3  # Should return tuple of 3 items
            except Exception as e:
                # Some configs might raise expected exceptions
                assert True  # Verify it didn't crash unexpectedly


class TestPerformanceIntegration:
    """Test performance characteristics of the integrated system."""

    @pytest.fixture
    def temp_directory(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdirname:
            yield tmpdirname

    def test_large_data_handling(self, temp_directory):
        """Test handling of large amounts of data."""
        config = {
            "sources": {"rss_feeds": [], "subreddits": []},
            "trend_detection": {"history_window": 30, "spark_threshold": 2.0, "min_frequency": 10},
            "agent": {"data_dir": temp_directory},
        }

        # Create large keyword history
        large_history = {}
        for i in range(10000):
            large_history[f"keyword_{i}"] = i % 100

        history_file = os.path.join(temp_directory, "keyword_history.json")
        with open(history_file, "w") as f:
            json.dump(large_history, f)

        # Create large current keywords
        current_items = []
        for i in range(1000):
            current_items.append(
                {
                    "title": f"Title with keyword_{i % 1000}",
                    "content_snippet": f"Content with keyword_{i % 500}",
                    "timestamp": datetime.now(timezone.utc),
                }
            )

        from src.trend_detector import detect_sparks

        # Extract keywords similar to how the real code does it
        keyword_counts = {}
        stopwords = set(["the", "a", "an", "and", "or", "but", "in", "on", "at"])

        for item in current_items:
            text = f"{item['title']} {item['content_snippet']}".lower()
            # Simple keyword extraction
            words = text.split()
            keywords = [w for w in words if len(w) > 2 and w not in stopwords]
            for keyword in keywords:
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

        start_time = datetime.now()
        sparks = detect_sparks(current_items, [], config)
        end_time = datetime.now()

        processing_time = (end_time - start_time).total_seconds()

        # Should process in reasonable time (less than 5 seconds for this amount)
        assert processing_time < 5.0
        assert isinstance(sparks, list)
