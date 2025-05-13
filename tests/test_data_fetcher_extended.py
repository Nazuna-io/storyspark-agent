# tests/test_data_fetcher_extended.py
from unittest.mock import patch, Mock

import time
import requests
from src.data_fetcher import fetch_rss, fetch_subreddit_json, _parse_rfc822_datetime, _parse_unix_timestamp

def test_parse_rfc822_datetime_struct_time_error():
    """Test parsing time.struct_time with error."""
    with patch('time.mktime', side_effect=Exception("mktime error")):
        result = _parse_rfc822_datetime(time.struct_time((2024, 1, 1, 0, 0, 0, 0, 0, 0)))
        assert result is None

def test_parse_rfc822_datetime_unknown_type():
    """Test parsing unknown type."""
    result = _parse_rfc822_datetime({'some': 'dict'})
    assert result is None

def test_parse_unix_timestamp_error():
    """Test parsing invalid Unix timestamp."""
    result = _parse_unix_timestamp("not-a-number")
    assert result is None

def test_fetch_rss_bozo_feed():
    """Test RSS feed with bozo flag."""
    import time
    time_struct = time.struct_time((2024, 1, 2, 12, 0, 0, 0, 0, 0))
    
    with patch('feedparser.parse') as mock_parse:
        mock_entry = Mock()
        mock_entry.configure_mock(**{
            'title': 'Test',
            'link': 'http://test.com/1',
            'id': 'test1',
            'published_parsed': time_struct,
            'summary': 'Test content',
            'get': lambda key, default=None: {
                'title': 'Test',
                'link': 'http://test.com/1',
                'id': 'test1',
                'published_parsed': time_struct,
                'summary': 'Test content'
            }.get(key, default)
        })
        
        mock_feed = Mock()
        mock_feed.title = 'Test Feed'
        mock_feed.get = lambda key, default=None: getattr(mock_feed, key, default) if hasattr(mock_feed, key) else default
        
        mock_result = Mock(
            bozo=True,  # Bozo flag set
            bozo_exception='Parse error',
            status=200,
            feed=mock_feed,
            entries=[mock_entry]
        )
        mock_result.get = lambda key, default=None: getattr(mock_result, key, default) if hasattr(mock_result, key) else default
        
        mock_parse.return_value = mock_result
        
        items = fetch_rss('http://test.com/feed.xml', None)
        assert len(items) == 1  # Should still process entries

def test_fetch_rss_high_status_code():
    """Test RSS feed with error status code."""
    with patch('feedparser.parse') as mock_parse:
        mock_result = Mock(
            bozo=False,
            status=500,
            entries=[]
        )
        mock_result.get = lambda key, default=None: getattr(mock_result, key, default) if hasattr(mock_result, key) else default
        
        mock_parse.return_value = mock_result
        
        items = fetch_rss('http://test.com/feed.xml', None)
        assert len(items) == 0

def test_fetch_rss_entry_without_timestamp():
    """Test RSS entry without valid timestamp."""
    with patch('feedparser.parse') as mock_parse:
        mock_entry = Mock()
        mock_entry.configure_mock(**{
            'title': 'Test',
            'link': 'http://test.com/1',
            'id': 'test1',
            'summary': 'Test content',
            'get': lambda key, default=None: {
                'title': 'Test',
                'link': 'http://test.com/1',
                'id': 'test1',
                'summary': 'Test content'
            }.get(key, default)
        })
        # No timestamp fields
        
        mock_feed = Mock()
        mock_feed.title = 'Test Feed'
        mock_feed.get = lambda key, default=None: getattr(mock_feed, key, default) if hasattr(mock_feed, key) else default
        
        mock_result = Mock(
            bozo=False,
            status=200,
            feed=mock_feed,
            entries=[mock_entry]
        )
        mock_result.get = lambda key, default=None: getattr(mock_result, key, default) if hasattr(mock_result, key) else default
        
        mock_parse.return_value = mock_result
        
        items = fetch_rss('http://test.com/feed.xml', None)
        assert len(items) == 0  # Should skip entries without timestamps

def test_fetch_rss_entry_without_id():
    """Test RSS entry without ID or link."""
    import time
    time_struct = time.struct_time((2024, 1, 2, 12, 0, 0, 0, 0, 0))
    
    with patch('feedparser.parse') as mock_parse:
        mock_entry = Mock()
        mock_entry.configure_mock(**{
            'title': 'Test',
            'published_parsed': time_struct,
            'summary': 'Test content',
            'get': lambda key, default=None: {
                'title': 'Test',
                'published_parsed': time_struct,
                'summary': 'Test content'
            }.get(key, default)
        })
        # No id or link fields
        
        mock_feed = Mock()
        mock_feed.title = 'Test Feed'
        mock_feed.get = lambda key, default=None: getattr(mock_feed, key, default) if hasattr(mock_feed, key) else default
        
        mock_result = Mock(
            bozo=False,
            status=200,
            feed=mock_feed,
            entries=[mock_entry]
        )
        mock_result.get = lambda key, default=None: getattr(mock_result, key, default) if hasattr(mock_result, key) else default
        
        mock_parse.return_value = mock_result
        
        items = fetch_rss('http://test.com/feed.xml', None)
        assert len(items) == 0  # Should skip entries without ID

def test_fetch_rss_connection_refused():
    """Test RSS feed with connection refused error."""
    with patch('feedparser.parse', side_effect=ConnectionRefusedError("Connection refused")):
        items = fetch_rss('http://test.com/feed.xml', None)
        assert len(items) == 0

def test_fetch_rss_request_exception():
    """Test RSS feed with request exception."""
    with patch('feedparser.parse', side_effect=requests.exceptions.RequestException("Network error")):
        items = fetch_rss('http://test.com/feed.xml', None)
        assert len(items) == 0

def test_fetch_subreddit_json_invalid_name():
    """Test fetching subreddit with invalid name."""
    items = fetch_subreddit_json('###', None)
    assert len(items) == 0

def test_fetch_subreddit_json_redirect():
    """Test fetching subreddit with redirect."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.history = [Mock()]  # Has redirect history
        mock_response.url = 'https://www.reddit.com/r/Test/new.json'
        mock_response.json.return_value = {
            'data': {
                'children': []
            }
        }
        mock_get.return_value = mock_response
        
        items = fetch_subreddit_json('test', None)
        assert len(items) == 0

def test_fetch_subreddit_json_invalid_json():
    """Test fetching subreddit with invalid JSON response."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.history = []
        mock_response.json.side_effect = Exception("Invalid JSON")
        mock_response.text = "Not JSON"
        mock_get.return_value = mock_response
        
        items = fetch_subreddit_json('test', None)
        assert len(items) == 0

def test_fetch_subreddit_json_unexpected_structure():
    """Test fetching subreddit with unexpected JSON structure."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.history = []
        mock_response.json.return_value = {'unexpected': 'structure'}
        mock_get.return_value = mock_response
        
        items = fetch_subreddit_json('test', None)
        assert len(items) == 0

def test_fetch_subreddit_json_non_t3_kind():
    """Test fetching subreddit with non-t3 kind items."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.history = []
        mock_response.json.return_value = {
            'data': {
                'children': [
                    {
                        'kind': 't5',  # Not t3
                        'data': {}
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        items = fetch_subreddit_json('test', None)
        assert len(items) == 0

def test_fetch_subreddit_json_missing_timestamp():
    """Test fetching subreddit post without timestamp."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.history = []
        mock_response.json.return_value = {
            'data': {
                'children': [
                    {
                        'kind': 't3',
                        'data': {
                            'id': 'test1',
                            'title': 'Test'
                            # No created_utc
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        items = fetch_subreddit_json('test', None)
        assert len(items) == 0

def test_fetch_subreddit_json_missing_id():
    """Test fetching subreddit post without ID."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.history = []
        mock_response.json.return_value = {
            'data': {
                'children': [
                    {
                        'kind': 't3',
                        'data': {
                            'created_utc': 1704196800,
                            'title': 'Test'
                            # No id
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        items = fetch_subreddit_json('test', None)
        assert len(items) == 0

def test_fetch_subreddit_json_rate_limited():
    """Test fetching subreddit with rate limit error."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response
        mock_response.headers = {'retry-after': '60'}
        
        items = fetch_subreddit_json('test', None)
        assert len(items) == 0

def test_fetch_subreddit_json_forbidden():
    """Test fetching subreddit with forbidden error."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response
        
        items = fetch_subreddit_json('test', None)
        assert len(items) == 0

def test_fetch_subreddit_json_connection_error():
    """Test fetching subreddit with connection error."""
    with patch('requests.get', side_effect=requests.exceptions.ConnectionError("Connection error")):
        items = fetch_subreddit_json('test', None)
        assert len(items) == 0

def test_fetch_subreddit_json_timeout():
    """Test fetching subreddit with timeout."""
    with patch('requests.get', side_effect=requests.exceptions.Timeout("Timeout")):
        items = fetch_subreddit_json('test', None)
        assert len(items) == 0
