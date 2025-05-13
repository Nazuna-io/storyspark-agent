# tests/integration/test_debug3.py
import pytest
from unittest.mock import patch, Mock
import logging
import os

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)


def test_with_mock_gemini():
    """Test with mocked Gemini but no feedparser yet."""
    config = {
        'sources': {
            'rss_feeds': [],
            'subreddits': []
        },
        'trend_detection': {
            'history_window_days': 7
        },
        'generation': {
            'api_key': 'test-key'
        },
        'agent': {
            'data_dir': '/tmp/test'
        }
    }
    
    # Set API key in environment
    os.environ['GOOGLE_API_KEY'] = 'test-key'
    
    from src.main import run_agent_cycle
    
    with patch('google.generativeai.GenerativeModel') as mock_genai:
        mock_model = Mock()
        mock_response = Mock()
        mock_response.candidates = [Mock(content=Mock(parts=[Mock(text="Test response")]))]
        mock_model.generate_content.return_value = mock_response
        mock_genai.return_value = mock_model
        
        print("Starting test cycle with mock Gemini...")
        history, timestamps, seeds = run_agent_cycle(config, [], {})
        print(f"Result: history={len(history)}, timestamps={len(timestamps)}, seeds={len(seeds)}")
        
        # Should have no new items (no sources)
        assert history == []
        assert seeds == []


def test_full_integration_minimal():
    """Test full integration with minimal mocking."""
    config = {
        'sources': {
            'rss_feeds': [{'url': 'http://test.com/feed.xml'}],
            'subreddits': []
        },
        'trend_detection': {
            'history_window_days': 7,
            'min_keyword_frequency': 1,
            'frequency_threshold': 1.0,
            'stopwords': ['the', 'a']
        },
        'generation': {
            'api_key': 'test-key',
            'prompt_template': 'Generate for {spark_keyword} from {source_name}'
        },
        'agent': {
            'data_dir': '/tmp/test'
        }
    }
    
    os.environ['GOOGLE_API_KEY'] = 'test-key'
    
    from src.main import run_agent_cycle
    import time
    time_struct = time.struct_time((2024, 1, 2, 12, 0, 0, 0, 0, 0))
    
    with patch('feedparser.parse') as mock_parse:
        # Create simple entry with repeated word
        mock_entry = Mock()
        entry_dict = {
            'title': 'test test test',
            'link': 'http://test.com/1',
            'id': 'test1',
            'published_parsed': time_struct,
            'summary': 'test test test'
        }
        mock_entry.configure_mock(**entry_dict)
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
        
        with patch('google.generativeai.GenerativeModel') as mock_genai:
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
            print(f"Result: history={len(history)}, timestamps={len(timestamps)}, seeds={len(seeds)}")
            
            # Check we got results
            assert len(history) > 0  # Should have fetched items
            assert len(timestamps) > 0  # Should have updated timestamps
            print(f"Seeds generated: {seeds}")
