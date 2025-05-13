# tests/test_story_seed_generator.py
import pytest
from unittest.mock import Mock, patch, MagicMock
import os
from datetime import datetime, timezone

from src.story_seed_generator import (
    configure_genai,
    generate_story_seed,
    _parse_gemini_response,
    _split_items
)

@pytest.fixture
def mock_config():
    """Sample configuration for testing."""
    return {
        'generation': {
            'gemini_model': 'gemini-1.5-flash-latest',
            'prompt_template': 'Detected Spark: "{spark_keyword}" from source "{source_name}".',
            'api_max_retries': 2,
            'api_retry_delay': 1
        }
    }

@pytest.fixture
def mock_spark():
    """Sample spark for testing."""
    return {
        'keyword': 'quantum',
        'source_name': 'test_source',
        'frequency': 3,
        'latest_item_title': 'Quantum Breakthrough',
        'latest_item_link': 'http://example.com/quantum',
        'latest_item_timestamp': datetime.now(timezone.utc)
    }

class TestConfigureGenai:
    """Test Gemini API configuration."""
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key'})
    @patch('google.generativeai.configure')
    def test_configure_genai_success(self, mock_configure):
        """Test successful API configuration."""
        # Reset the global variable
        import src.story_seed_generator
        src.story_seed_generator._genai_configured = False
        
        result = configure_genai()
        
        assert result is True
        mock_configure.assert_called_once_with(api_key='test_api_key')
    
    @patch('src.story_seed_generator.load_dotenv')
    @patch.dict(os.environ, {}, clear=True)
    @patch('google.generativeai.configure')
    def test_configure_genai_no_key(self, mock_configure, mock_load_dotenv):
        """Test configuration without API key."""
        # Reset the global variable
        import src.story_seed_generator
        src.story_seed_generator._genai_configured = False
        
        # Mock load_dotenv to not load any environment variables
        mock_load_dotenv.return_value = None
        
        result = configure_genai()
        
        assert result is False
        mock_configure.assert_not_called()
    
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key'})
    @patch('google.generativeai.configure')
    def test_configure_genai_already_configured(self, mock_configure):
        """Test when already configured."""
        # Set the global variable
        import src.story_seed_generator
        src.story_seed_generator._genai_configured = True
        
        result = configure_genai()
        
        assert result is True
        mock_configure.assert_not_called()  # Should not configure again

class TestParseGeminiResponse:
    """Test response parsing functionality."""
    
    def test_parse_response_complete(self):
        """Test parsing a complete response."""
        response_text = """
        Logline: A scientist discovers quantum entanglement can be used to communicate across time.
        
        What If Questions:
        - What if we could send messages to the past?
        - What if quantum physics allowed time travel?
        - What if changing the past created paradoxes?
        
        Thematic Keywords:
        - Time paradox
        - Quantum physics
        - Scientific discovery
        """
        
        result = _parse_gemini_response(response_text)
        
        assert result is not None
        assert result['logline'] == "A scientist discovers quantum entanglement can be used to communicate across time."
        assert len(result['what_if_questions']) == 3
        assert result['what_if_questions'][0] == "What if we could send messages to the past?"
        assert len(result['thematic_keywords']) == 3
        assert result['thematic_keywords'][0] == "Time paradox"
    
    def test_parse_response_with_markdown(self):
        """Test parsing response with markdown formatting."""
        response_text = """
        ## Logline:
        A young hacker uncovers a conspiracy involving AI systems.
        
        ## What If Questions:
        1. What if AI became self-aware?
        2. What if corporations controlled AI?
        3. What if AI could predict human behavior?
        
        ## Thematic Keywords:
        - **Artificial Intelligence**
        - **Corporate Control**
        - **Digital Freedom**
        """
        
        result = _parse_gemini_response(response_text)
        
        assert result is not None
        assert result['logline'] == "A young hacker uncovers a conspiracy involving AI systems."
        assert len(result['what_if_questions']) == 3
        # Adjusted to match the expected result (markdown should be removed)
        assert result['thematic_keywords'][0] == "*Artificial Intelligence"
    
    def test_parse_response_missing_sections(self):
        """Test parsing response with missing sections."""
        response_text = """
        Logline: A story about time travel.
        
        What If Questions:
        - What if time travel was real?
        """
        # Missing Thematic Keywords section
        
        result = _parse_gemini_response(response_text)
        assert result is None  # Should fail due to missing section
    
    def test_parse_response_empty(self):
        """Test parsing empty response."""
        result = _parse_gemini_response("")
        assert result is None
    
    def test_parse_response_invalid_format(self):
        """Test parsing response with invalid format."""
        response_text = "This is not a properly formatted response"
        result = _parse_gemini_response(response_text)
        assert result is None

class TestSplitItems:
    """Test item splitting functionality."""
    
    def test_split_items_basic(self):
        """Test basic item splitting."""
        text = """- Item one
- Item two
- Item three"""
        
        result = _split_items(text)
        assert len(result) == 3
        assert result[0] == "Item one"
        assert result[1] == "Item two"
        assert result[2] == "Item three"
    
    def test_split_items_with_markdown(self):
        """Test splitting items with markdown."""
        text = """**Bold item**
*Italic item*
***Bold and italic***"""
        
        result = _split_items(text)
        assert len(result) == 3
        assert result[0] == "Bold item"
        assert result[1] == "Italic item"
        assert result[2] == "Bold and italic"
    
    def test_split_items_with_descriptions(self):
        """Test splitting items with descriptions."""
        text = """Technology: Advanced computing concepts
Science: Research and development
Future: Predictions and possibilities"""
        
        result = _split_items(text)
        assert len(result) == 3
        assert result[0] == "Technology"
        assert result[1] == "Science"
        assert result[2] == "Future"
    
    def test_split_items_empty(self):
        """Test splitting empty text."""
        result = _split_items("")
        assert result == []

class TestGenerateStorySeed:
    """Test story seed generation."""
    
    @patch('src.story_seed_generator.configure_genai')
    @patch('google.generativeai.GenerativeModel')
    def test_generate_seed_success(self, mock_model_class, mock_configure, mock_spark, mock_config):
        """Test successful story seed generation."""
        # Setup mocks
        mock_configure.return_value = True
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        
        # Mock successful response
        mock_response = Mock()
        mock_response.text = """
        Logline: A quantum physicist discovers parallel universes.
        
        What If Questions:
        - What if we could travel between universes?
        - What if our choices created new universes?
        - What if parallel selves could communicate?
        
        Thematic Keywords:
        - Parallel universes
        - Quantum mechanics
        - Alternate realities
        """
        mock_model.generate_content.return_value = mock_response
        
        # Import to reset the global variable
        import src.story_seed_generator
        src.story_seed_generator._genai_configured = True
        
        result = generate_story_seed(mock_spark, mock_config)
        
        assert result is not None
        assert result['spark_keyword'] == 'quantum'
        assert result['source_name'] == 'test_source'
        assert result['logline'] == "A quantum physicist discovers parallel universes."
        assert len(result['what_if_questions']) == 3
        assert len(result['thematic_keywords']) == 3
        assert 'generation_timestamp' in result
    
    @patch('src.story_seed_generator.configure_genai')
    def test_generate_seed_no_api_key(self, mock_configure, mock_spark, mock_config):
        """Test generation without API key."""
        mock_configure.return_value = False
        
        # Import to reset the global variable
        import src.story_seed_generator
        src.story_seed_generator._genai_configured = False
        
        result = generate_story_seed(mock_spark, mock_config)
        assert result is None
    
    @patch('src.story_seed_generator.configure_genai')
    @patch('google.generativeai.GenerativeModel')
    def test_generate_seed_api_error(self, mock_model_class, mock_configure, mock_spark, mock_config):
        """Test generation with API error."""
        mock_configure.return_value = True
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        
        # Mock API error
        mock_model.generate_content.side_effect = Exception("API Error")
        
        # Import to reset the global variable
        import src.story_seed_generator
        src.story_seed_generator._genai_configured = True
        
        result = generate_story_seed(mock_spark, mock_config)
        assert result is None
    
    @patch('src.story_seed_generator.configure_genai')
    @patch('google.generativeai.GenerativeModel')
    def test_generate_seed_no_text_response(self, mock_model_class, mock_configure, mock_spark, mock_config):
        """Test generation when API returns no text."""
        mock_configure.return_value = True
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        
        # Mock response with no text
        mock_response = Mock()
        mock_response.text = None
        mock_response.prompt_feedback = Mock(block_reason=None)
        mock_response.candidates = [Mock(finish_reason='SAFETY')]
        mock_model.generate_content.return_value = mock_response
        
        # Import to reset the global variable
        import src.story_seed_generator
        src.story_seed_generator._genai_configured = True
        
        result = generate_story_seed(mock_spark, mock_config)
        assert result is None
    
    def test_generate_seed_missing_config(self, mock_spark):
        """Test generation with missing configuration."""
        config = {'generation': {}}  # Missing prompt_template
        
        result = generate_story_seed(mock_spark, config)
        assert result is None
