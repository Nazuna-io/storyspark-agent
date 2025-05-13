# tests/integration/test_debug_simple.py
import os
os.environ['GOOGLE_API_KEY'] = 'test-key'

import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timezone, timedelta
from src.main import run_agent_cycle


def test_simple_full_workflow():
    """Test simple workflow with all mocks."""
    print("Test starting...")
    config = {
        'sources': {
            'rss_feeds': [{'url': 'http://test.com/feed.xml'}],
            'subreddits': []
        },
        'trend_detection': {
            'history_window_days': 7,
            'min_keyword_frequency': 1,
            'frequency_threshold': 1.0,
            'stopwords': ['the']
        },
        'generation': {
            'api_key': 'test-key',
            'prompt_template': 'Generate for {spark_keyword} from {source_name}'
        },
        'agent': {
            'data_dir': '/tmp/test'
        }
    }
    
    # Recent date
    recent_date = datetime.now(timezone.utc) - timedelta(hours=1)
    import time
    time_struct = time.struct_time(recent_date.timetuple()[:9])
    
    print("Setting up mocks...")
    
    # Mock feedparser
    with patch('feedparser.parse') as mock_parse:
        entry_dict = {
            'title': 'Test Article',
            'link': 'http://test.com/1',
            'id': 'test1',
            'published_parsed': time_struct,
            'summary': 'Test content keyword keyword keyword'
        }
        mock_entry = Mock(**entry_dict)
        mock_entry.get = lambda key, default=None: entry_dict.get(key, default)
        
        mock_feed = Mock(title='Test Feed')
        mock_feed.get = lambda key, default=None: getattr(mock_feed, key, default) if hasattr(mock_feed, key) else default
        
        mock_result = Mock(
            bozo=False,
            status=200,
            feed=mock_feed,
            entries=[mock_entry]
        )
        mock_result.get = lambda key, default=None: getattr(mock_result, key, default) if hasattr(mock_result, key) else default
        mock_parse.return_value = mock_result
        
        print("Feedparser mocked")
        
        # Mock Gemini
        with patch('google.generativeai.configure') as mock_configure:
            with patch('google.generativeai.GenerativeModel') as mock_genai:
                mock_model = Mock()
                mock_response = Mock()
                # Ensure response.text works
                mock_response.text = """**Logline:**
A test story

**What If Questions:**
- Question 1

**Thematic Keywords:**
- Keyword 1"""
                mock_model.generate_content.return_value = mock_response
                mock_genai.return_value = mock_model
                
                print("Gemini mocked")
                print("Running cycle...")
                
                # Run the cycle
                history, timestamps, seeds = run_agent_cycle(config, [], {})
                
                print(f"Results: history={len(history)}, timestamps={len(timestamps)}, seeds={len(seeds)}")
                
                # Should have results
                assert len(history) > 0
                assert len(seeds) > 0
                
                print("Test completed!")
