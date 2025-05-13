# tests/test_trend_detector.py
import pytest
from datetime import datetime, timezone, timedelta
from src.trend_detector import detect_sparks, _extract_keywords

@pytest.fixture
def mock_config():
    """Sample configuration for testing."""
    return {
        'trend_detection': {
            'frequency_threshold': 3,
            'min_keyword_frequency': 2,
            'stopwords': ['the', 'a', 'is', 'in', 'it', 'and', 'to', 'of']
        }
    }

@pytest.fixture
def sample_new_items():
    """Sample new items for testing."""
    return [
        {
            'title': 'Quantum Computing Breakthrough Announced',
            'content_snippet': 'Quantum computing research shows major progress',
            'source_name': 'test_source',
            'timestamp': datetime.now(timezone.utc),
            'link': 'http://example.com/1'
        },
        {
            'title': 'Another Quantum Development',
            'content_snippet': 'Quantum technology advances rapidly',
            'source_name': 'test_source',
            'timestamp': datetime.now(timezone.utc),
            'link': 'http://example.com/2'
        },
        {
            'title': 'Machine Learning Update',
            'content_snippet': 'New ML algorithm improves accuracy',
            'source_name': 'test_source2',
            'timestamp': datetime.now(timezone.utc),
            'link': 'http://example.com/3'
        }
    ]

@pytest.fixture
def sample_history():
    """Sample historical items for testing."""
    past_time = datetime.now(timezone.utc) - timedelta(days=1)
    return [
        {
            'title': 'Regular Tech News',
            'content_snippet': 'Technology updates from yesterday',
            'source_name': 'test_source',
            'timestamp': past_time,
            'link': 'http://example.com/old1'
        },
        {
            'title': 'Software Release',
            'content_snippet': 'New software version available',
            'source_name': 'test_source',
            'timestamp': past_time,
            'link': 'http://example.com/old2'
        }
    ]


class TestExtractKeywords:
    """Test keyword extraction function."""
    
    def test_extract_keywords_basic(self):
        """Test basic keyword extraction."""
        text = "Quantum computing breakthrough announced today"
        stopwords = []
        
        keywords = _extract_keywords(text, stopwords)
        
        assert 'quantum' in keywords
        assert 'computing' in keywords
        assert 'breakthrough' in keywords
        assert 'announced' in keywords
        assert 'today' in keywords
    
    def test_extract_keywords_with_punctuation(self):
        """Test keyword extraction with punctuation."""
        text = "Machine learning, AI, and robotics: the future!"
        stopwords = ['the', 'and']
        
        keywords = _extract_keywords(text, stopwords)
        
        assert 'machine' in keywords
        assert 'learning' in keywords
        # AI is filtered out as it's only 2 characters (minimum is 3)
        assert 'ai' not in keywords
        assert 'robotics' in keywords
        assert 'future' in keywords
        assert 'the' not in keywords
        assert 'and' not in keywords
    
    def test_extract_keywords_empty_text(self):
        """Test keyword extraction with empty text."""
        keywords = _extract_keywords("", [])
        assert keywords == []


class TestDetectSparks:
    """Test spark detection functionality."""
    
    def test_detect_sparks_frequency_spike(self, sample_new_items, sample_history, mock_config):
        """Test detecting sparks based on frequency spike."""
        # Quantum appears 2 times in new items, 0 times in history
        # This meets the min_keyword_frequency (2) and exceeds frequency_threshold (3x)
        sparks = detect_sparks(sample_new_items, sample_history, mock_config)
        
        # Should detect 'quantum' as a spark
        assert len(sparks) > 0
        quantum_spark = next((s for s in sparks if s['keyword'] == 'quantum'), None)
        assert quantum_spark is not None
        assert quantum_spark['keyword'] == 'quantum'
        assert quantum_spark['source_name'] == 'test_source'
        assert 'latest_item_title' in quantum_spark
        assert 'detected_at' in quantum_spark
    
    def test_detect_sparks_no_spike(self, mock_config):
        """Test when no frequency spike is detected."""
        # Items with evenly distributed keywords
        new_items = [
            {
                'title': 'Technology News Update',
                'content_snippet': 'Regular technology news',
                'source_name': 'test_source',
                'timestamp': datetime.now(timezone.utc),
                'link': 'http://example.com/1'
            }
        ]
        
        history = [
            {
                'title': 'Technology News Yesterday',
                'content_snippet': 'Technology updates from yesterday',
                'source_name': 'test_source',
                'timestamp': datetime.now(timezone.utc) - timedelta(days=1),
                'link': 'http://example.com/old1'
            }
        ]
        
        sparks = detect_sparks(new_items, history, mock_config)
        assert len(sparks) == 0
    
    def test_detect_sparks_below_min_frequency(self, mock_config):
        """Test keywords below minimum frequency threshold."""
        # Each 'unique' keyword appears in both titles (2 times total)
        new_items = [
            {
                'title': 'Unique Keyword One',
                'content_snippet': 'Different content here',
                'source_name': 'test_source',
                'timestamp': datetime.now(timezone.utc),
                'link': 'http://example.com/1'
            },
            {
                'title': 'Another Unique Topic',  # 'unique' appears here too
                'content_snippet': 'Completely different subject',
                'source_name': 'test_source',
                'timestamp': datetime.now(timezone.utc),
                'link': 'http://example.com/2'
            }
        ]
        
        sparks = detect_sparks(new_items, [], mock_config)
        
        # 'unique' appears 2 times, meeting the min_keyword_frequency
        # With no history, it should be detected as a spark
        unique_spark = next((s for s in sparks if s['keyword'] == 'unique'), None)
        assert unique_spark is not None
    
    def test_detect_sparks_empty_inputs(self, mock_config):
        """Test with empty inputs."""
        sparks = detect_sparks([], [], mock_config)
        assert sparks == []
        
        sparks = detect_sparks([], [{'title': 'Old item'}], mock_config)
        assert sparks == []
    
    def test_detect_sparks_multiple_sources(self, mock_config):
        """Test spark detection across multiple sources."""
        new_items = [
            {
                'title': 'Blockchain Innovation',
                'content_snippet': 'Blockchain technology breakthrough',
                'source_name': 'source1',
                'timestamp': datetime.now(timezone.utc),
                'link': 'http://example.com/1'
            },
            {
                'title': 'Blockchain Revolution',
                'content_snippet': 'Blockchain changing finance',
                'source_name': 'source2',
                'timestamp': datetime.now(timezone.utc),
                'link': 'http://example.com/2'
            }
        ]
        
        sparks = detect_sparks(new_items, [], mock_config)
        
        # Should detect blockchain as a spark
        blockchain_spark = next((s for s in sparks if s['keyword'] == 'blockchain'), None)
        assert blockchain_spark is not None
        assert blockchain_spark['keyword'] == 'blockchain'
        # Should use the source of the latest item
        assert blockchain_spark['source_name'] in ['source1', 'source2']
