# tests/integration/test_debug.py
import pytest
from unittest.mock import patch, Mock
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)


def test_simple_cycle():
    """Test minimal cycle with debug output."""
    config = {
        'sources': {
            'rss_feeds': [],
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
    
    print("Starting test cycle...")
    history, timestamps, seeds = run_agent_cycle(config, [], {})
    print(f"Result: history={len(history)}, timestamps={len(timestamps)}, seeds={len(seeds)}")
    
    assert history == []
    assert timestamps == {}
    assert seeds == []
