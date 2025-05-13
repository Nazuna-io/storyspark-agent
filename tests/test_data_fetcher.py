# tests/test_data_fetcher.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import json
import os
import time

from src.data_fetcher import (
    get_new_items, 
    fetch_rss, 
    fetch_subreddit_json,
    load_state, 
    save_state,
    _parse_rfc822_datetime,
    _parse_unix_timestamp
)

@pytest.fixture
def mock_config():
    """Sample configuration for testing."""
    return {
        'sources': {
            'rss_feeds': [
                {'url': 'http://example.com/feed.xml', 'name': 'Example Feed'}
            ],
            'subreddits': [
                {'name': 'test', 'limit': 25}
            ]
        }
    }

@pytest.fixture
def mock_timestamps():
    """Sample timestamp state for testing."""
    return {
        'rss_http://example.com/feed.xml': datetime(2024, 1, 1, tzinfo=timezone.utc),
        'reddit_test': datetime(2024, 1, 1, tzinfo=timezone.utc)
    }

class TestDatetimeParsing:
    """Test datetime parsing helper functions."""
    
    def test_parse_rfc822_datetime_string(self):
        """Test parsing RFC822 datetime string."""
        dt_str = "Wed, 02 Oct 2002 13:00:00 GMT"
        result = _parse_rfc822_datetime(dt_str)
        assert result == datetime(2002, 10, 2, 13, 0, 0, tzinfo=timezone.utc)
    
    def test_parse_rfc822_datetime_iso(self):
        """Test parsing ISO format datetime string."""
        dt_str = "2024-01-01T12:00:00+00:00"
        result = _parse_rfc822_datetime(dt_str)
        assert result == datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    def test_parse_rfc822_datetime_already_datetime(self):
        """Test when input is already a datetime object."""
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = _parse_rfc822_datetime(dt)
        assert result == dt
    
    def test_parse_unix_timestamp(self):
        """Test parsing Unix timestamp."""
        ts = 1704196800  # 2024-01-02 12:00:00 UTC
        result = _parse_unix_timestamp(ts)
        assert result == datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    
    def test_parse_unix_timestamp_string(self):
        """Test parsing Unix timestamp as string."""
        ts = "1704196800"
        result = _parse_unix_timestamp(ts)
        assert result == datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)

class TestLoadSaveState:
    """Test state loading and saving functions."""
    
    def test_load_state_file_not_exists(self, tmp_path):
        """Test loading state when file doesn't exist."""
        state_file = tmp_path / "nonexistent.json"
        result = load_state(str(state_file))
        assert result == {}
    
    def test_load_state_valid_file(self, tmp_path):
        """Test loading state from valid file."""
        state_file = tmp_path / "state.json"
        test_data = {
            "last_timestamps": {
                'test_source': '2024-01-01T00:00:00+00:00'
            }
        }
        state_file.write_text(json.dumps(test_data))
        
        result = load_state(str(state_file))
        assert 'test_source' in result
        assert isinstance(result['test_source'], datetime)
        assert result['test_source'] == datetime(2024, 1, 1, tzinfo=timezone.utc)
    
    def test_save_state(self, tmp_path):
        """Test saving state to file."""
        state_file = tmp_path / "state.json"
        timestamps = {
            'source1': datetime(2024, 1, 1, tzinfo=timezone.utc),
            'source2': datetime(2024, 1, 2, tzinfo=timezone.utc)
        }
        
        save_state(timestamps, str(state_file))
        
        # Verify file contents
        saved_data = json.loads(state_file.read_text())
        assert saved_data['last_timestamps']['source1'] == '2024-01-01T00:00:00+00:00'
        assert saved_data['last_timestamps']['source2'] == '2024-01-02T00:00:00+00:00'


class TestFetchRss:
    """Test RSS feed fetching functionality."""
    
    @patch('feedparser.parse')
    def test_fetch_rss_success(self, mock_parse):
        """Test successful RSS feed fetch."""
        # Convert tuple to time.struct_time
        time_tuple1 = time.struct_time((2024, 1, 2, 12, 0, 0, 0, 0, 0))
        time_tuple2 = time.struct_time((2024, 1, 3, 12, 0, 0, 0, 0, 0))
        
        # Mock feed response
        entry1 = Mock()
        entry1.configure_mock(**{
            'title': 'Test Article 1',
            'link': 'http://example.com/1',
            'id': 'item1',
            'published_parsed': time_tuple1,
            'summary': 'Summary 1',
            'description': 'Description 1',
            'get': lambda key, default=None: {
                'title': 'Test Article 1',
                'link': 'http://example.com/1',
                'id': 'item1',
                'published_parsed': time_tuple1,
                'summary': 'Summary 1',
                'description': 'Description 1',
            }.get(key, default)
        })
        
        entry2 = Mock()
        entry2.configure_mock(**{
            'title': 'Test Article 2',
            'link': 'http://example.com/2',
            'id': 'item2',
            'published_parsed': time_tuple2,
            'summary': 'Summary 2',
            'description': 'Description 2',
            'get': lambda key, default=None: {
                'title': 'Test Article 2',
                'link': 'http://example.com/2',
                'id': 'item2',
                'published_parsed': time_tuple2,
                'summary': 'Summary 2',
                'description': 'Description 2',
            }.get(key, default)
        })
        
        mock_parse.return_value = Mock(
            bozo=False,
            status=200,
            feed=Mock(title='Test Feed'),
            entries=[entry1, entry2]
        )
        # Add get method to the mock
        mock_parse.return_value.get = lambda key, default=None: getattr(mock_parse.return_value, key, default) if hasattr(mock_parse.return_value, key) else default
        mock_parse.return_value.feed.get = lambda key, default=None: getattr(mock_parse.return_value.feed, key, default) if hasattr(mock_parse.return_value.feed, key) else default
        
        items = fetch_rss(
            'http://example.com/feed.xml',
            datetime(2024, 1, 1, tzinfo=timezone.utc)
        )
        
        assert len(items) == 2
        assert items[0]['title'] == 'Test Article 1'
        assert items[0]['link'] == 'http://example.com/1'
        assert items[0]['source_name'] == 'Test Feed'
        assert 'timestamp' in items[0]
    
    @patch('feedparser.parse')
    def test_fetch_rss_empty_feed(self, mock_parse):
        """Test fetching empty RSS feed."""
        mock_response = Mock(bozo=False, status=200, entries=[])
        mock_response.get = lambda key, default=None: getattr(mock_response, key, default) if hasattr(mock_response, key) else default
        mock_parse.return_value = mock_response
        
        items = fetch_rss(
            'http://example.com/feed.xml',
            datetime(2024, 1, 1, tzinfo=timezone.utc)
        )
        
        assert items == []
    
    @patch('feedparser.parse')
    def test_fetch_rss_error(self, mock_parse):
        """Test RSS feed fetch with error."""
        mock_parse.side_effect = Exception("Network error")
        
        items = fetch_rss(
            'http://example.com/feed.xml',
            datetime(2024, 1, 1, tzinfo=timezone.utc)
        )
        
        assert items == []
    
    @patch('feedparser.parse')
    def test_fetch_rss_404(self, mock_parse):
        """Test RSS feed returning 404."""
        mock_response = Mock(bozo=False, status=404, entries=[])
        mock_response.get = lambda key, default=None: 404 if key == "status" else default
        mock_parse.return_value = mock_response
        
        items = fetch_rss(
            'http://example.com/feed.xml',
            datetime(2024, 1, 1, tzinfo=timezone.utc)
        )
        
        assert items == []


class TestFetchSubredditJson:
    """Test subreddit post fetching functionality."""
    
    @patch('requests.get')
    def test_fetch_subreddit_success(self, mock_get):
        """Test successful subreddit fetch."""
        # Mock Reddit API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.history = []
        mock_response.json.return_value = {
            'data': {
                'children': [
                    {
                        'kind': 't3',
                        'data': {
                            'id': 'post1',
                            'name': 't3_post1',
                            'title': 'Test Post 1',
                            'url': 'http://reddit.com/r/test/1',
                            'permalink': '/r/test/comments/post1/test_post_1/',
                            'created_utc': 1704196800,  # 2024-01-02 12:00:00 UTC
                            'selftext': 'Post content 1'
                        }
                    },
                    {
                        'kind': 't3',
                        'data': {
                            'id': 'post2',
                            'name': 't3_post2',
                            'title': 'Test Post 2',
                            'url': 'http://reddit.com/r/test/2',
                            'permalink': '/r/test/comments/post2/test_post_2/',
                            'created_utc': 1704283200,  # 2024-01-03 12:00:00 UTC
                            'selftext': ''  # No self text
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        items = fetch_subreddit_json(
            'test',
            datetime(2024, 1, 1, tzinfo=timezone.utc)
        )
        
        assert len(items) == 2
        assert items[0]['title'] == 'Test Post 1'
        assert items[0]['link'] == 'https://www.reddit.com/r/test/comments/post1/test_post_1/'
        assert items[0]['source_name'] == 'r/test'
        assert items[0]['content_snippet'] == 'Post content 1'
    
    @patch('requests.get')
    def test_fetch_subreddit_error(self, mock_get):
        """Test subreddit fetch with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("404 Not Found")
        mock_get.return_value = mock_response
        
        items = fetch_subreddit_json(
            'nonexistent',
            datetime(2024, 1, 1, tzinfo=timezone.utc)
        )
        
        assert items == []
    
    @patch('requests.get')
    def test_fetch_subreddit_network_error(self, mock_get):
        """Test subreddit fetch with network error."""
        mock_get.side_effect = Exception("Connection error")
        
        items = fetch_subreddit_json(
            'test',
            datetime(2024, 1, 1, tzinfo=timezone.utc)
        )
        
        assert items == []


class TestGetNewItems:
    """Test the main get_new_items function."""
    
    @patch('src.data_fetcher.fetch_rss')
    @patch('src.data_fetcher.fetch_subreddit_json')
    def test_get_new_items_all_sources(self, mock_fetch_reddit, mock_fetch_rss, mock_config, mock_timestamps):
        """Test fetching from all configured sources."""
        # Mock RSS feed results
        mock_fetch_rss.return_value = [
            {
                'title': 'RSS Item 1',
                'timestamp': datetime(2024, 1, 2, tzinfo=timezone.utc),
                'source': 'http://example.com/feed.xml'
            }
        ]
        
        # Mock Reddit results
        mock_fetch_reddit.return_value = [
            {
                'title': 'Reddit Post 1',
                'timestamp': datetime(2024, 1, 3, tzinfo=timezone.utc),
                'source': 'reddit_test'
            }
        ]
        
        items, new_timestamps = get_new_items(mock_config, mock_timestamps)
        
        assert len(items) == 2
        assert any(item['title'] == 'RSS Item 1' for item in items)
        assert any(item['title'] == 'Reddit Post 1' for item in items)
        
        # Check timestamp updates
        assert new_timestamps['rss_http://example.com/feed.xml'] == datetime(2024, 1, 2, tzinfo=timezone.utc)
        assert new_timestamps['reddit_test'] == datetime(2024, 1, 3, tzinfo=timezone.utc)
    
    @patch('src.data_fetcher.fetch_rss')
    @patch('src.data_fetcher.fetch_subreddit_json')
    def test_get_new_items_no_results(self, mock_fetch_reddit, mock_fetch_rss, mock_config, mock_timestamps):
        """Test when no new items are found."""
        mock_fetch_rss.return_value = []
        mock_fetch_reddit.return_value = []
        
        items, new_timestamps = get_new_items(mock_config, mock_timestamps)
        
        assert items == []
        # Timestamps should remain unchanged when no new items
        assert new_timestamps == mock_timestamps
    
    @patch('src.data_fetcher.fetch_rss')
    @patch('src.data_fetcher.fetch_subreddit_json')
    def test_get_new_items_invalid_config(self, mock_fetch_reddit, mock_fetch_rss):
        """Test with invalid source configurations."""
        config = {
            'sources': {
                'rss_feeds': [
                    {'invalid': 'config'},  # Missing 'url'
                    {'url': 'http://example.com/feed.xml'}
                ],
                'subreddits': [
                    {'invalid': 'config'},  # Missing 'name'
                    {'name': 'test'}
                ]
            }
        }
        timestamps = {}
        
        # Mock successful fetches for valid configs
        mock_fetch_rss.return_value = [
            {'title': 'RSS Item', 'timestamp': datetime.now(timezone.utc)}
        ]
        mock_fetch_reddit.return_value = [
            {'title': 'Reddit Post', 'timestamp': datetime.now(timezone.utc)}
        ]
        
        items, new_timestamps = get_new_items(config, timestamps)
        
        # Should still fetch from valid sources
        assert len(items) == 2
        assert mock_fetch_rss.call_count == 1  # Only called for valid config
        assert mock_fetch_reddit.call_count == 1  # Only called for valid config
    
    @patch('src.data_fetcher.fetch_rss')
    @patch('src.data_fetcher.fetch_subreddit_json')
    def test_get_new_items_sorted_by_timestamp(self, mock_fetch_reddit, mock_fetch_rss, mock_config):
        """Test that items are sorted by timestamp."""
        # Create items with different timestamps
        now = datetime.now(timezone.utc)
        mock_fetch_rss.return_value = [
            {'title': 'RSS Item 1', 'timestamp': now + timedelta(hours=2)},
            {'title': 'RSS Item 2', 'timestamp': now}
        ]
        mock_fetch_reddit.return_value = [
            {'title': 'Reddit Post 1', 'timestamp': now + timedelta(hours=1)},
            {'title': 'Reddit Post 2', 'timestamp': now + timedelta(hours=3)}
        ]
        
        items, _ = get_new_items(mock_config, {})
        
        # Check items are sorted by timestamp (oldest first)
        assert len(items) == 4
        assert items[0]['timestamp'] <= items[1]['timestamp']
        assert items[1]['timestamp'] <= items[2]['timestamp']
        assert items[2]['timestamp'] <= items[3]['timestamp']
