# tests/integration/test_debug2.py
import pytest
from unittest.mock import patch, Mock
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)


def test_with_mock_feedparser():
    """Test with mocked feedparser."""
    config = {
        'sources': {
            'rss_feeds': [{'url': 'http://test.com/feed.xml'}],
            'subreddits': []
        },
        'trend_detection': {
            'history_window_days': 7
        },
        'agent': {
            'data_dir': '/tmp/test'
        }
    }
    
    from src.main import run_agent_cycle
    
    with patch('feedparser.parse') as mock_parse:
        # Return empty feed
        mock_parse.return_value = Mock(
            bozo=False,
            status=200,
            entries=[],
            feed=Mock(title='Test')
        )
        mock_parse.return_value.get = lambda key, default=None: getattr(mock_parse.return_value, key, default) if hasattr(mock_parse.return_value, key) else default
        
        print("Starting test cycle with mock feedparser...")
        history, timestamps, seeds = run_agent_cycle(config, [], {})
        print(f"Result: history={len(history)}, timestamps={len(timestamps)}, seeds={len(seeds)}")
        
        # Should have no new items
        assert history == []
        assert seeds == []
