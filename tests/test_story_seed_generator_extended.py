# tests/test_story_seed_generator_extended.py
import os
from unittest.mock import Mock, patch

from src.story_seed_generator import _parse_gemini_response, configure_genai, generate_story_seed


def test_configure_genai_already_configured():
    """Test configure_genai when already configured."""
    with patch("src.story_seed_generator._genai_configured", True):
        result = configure_genai()
        assert result is True


def test_configure_genai_no_api_key():
    """Test configure_genai when API key is missing."""
    with patch.dict(os.environ, {}, clear=True):
        with patch("src.story_seed_generator.load_dotenv") as mock_load_dotenv:
            mock_load_dotenv.return_value = None  # Simulates no .env file
            with patch("src.story_seed_generator._genai_configured", False):
                result = configure_genai()
                assert result is False


def test_configure_genai_exception():
    """Test configure_genai when configuration fails."""
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
        with patch("src.story_seed_generator._genai_configured", False):
            with patch("google.generativeai.configure", side_effect=Exception("Config error")):
                result = configure_genai()
                assert result is False


def test_parse_response_no_logline():
    """Test parsing response without logline."""
    text = """
    **What If Questions:**
    - Question 1

    **Thematic Keywords:**
    - Keyword 1
    """
    result = _parse_gemini_response(text)
    assert result is None  # Should require logline


def test_parse_response_empty_text():
    """Test parsing empty response."""
    result = _parse_gemini_response("")
    assert result is None


def test_parse_response_exception():
    """Test parsing response with exception."""
    with patch("re.search", side_effect=Exception("Regex error")):
        result = _parse_gemini_response("Test text")
        assert result is None


def test_generate_story_seed_no_prompt_template():
    """Test generate_story_seed without prompt template."""
    spark = {"keyword": "test"}
    config = {"generation": {}}  # No prompt_template

    result = generate_story_seed(spark, config)
    assert result is None


def test_generate_story_seed_format_error():
    """Test generate_story_seed with format error."""
    spark = {"keyword": "test"}
    config = {"generation": {"prompt_template": "Template with {missing_key}"}}

    result = generate_story_seed(spark, config)
    assert result is None


def test_generate_story_seed_api_error():
    """Test generate_story_seed with API error."""
    spark = {"keyword": "test", "source_name": "Test Source"}
    config = {
        "generation": {
            "prompt_template": "Generate for {spark_keyword} from {source_name}",
            "api_max_retries": 1,
            "api_retry_delay": 0.1,
        }
    }

    with patch("src.story_seed_generator._genai_configured", True):
        with patch("google.generativeai.GenerativeModel") as mock_model:
            mock_model.side_effect = Exception("API Error")

            result = generate_story_seed(spark, config)
            assert result is None


def test_generate_story_seed_no_text_with_retry():
    """Test generate_story_seed with no text response and retry."""
    spark = {"keyword": "test", "source_name": "Test Source"}
    config = {
        "generation": {
            "prompt_template": "Generate for {spark_keyword} from {source_name}",
            "api_max_retries": 1,
            "api_retry_delay": 0.01,
        }
    }

    with patch("src.story_seed_generator._genai_configured", True):
        with patch("google.generativeai.GenerativeModel") as mock_genai:
            mock_model = Mock()
            mock_response = Mock()
            # First attempt returns no text
            mock_response.text = None
            mock_response.candidates = [Mock(finish_reason="STOP")]
            mock_response.prompt_feedback = Mock(block_reason=None)
            mock_model.generate_content.return_value = mock_response
            mock_genai.return_value = mock_model

            result = generate_story_seed(spark, config)
            assert result is None
            # Should retry
            assert mock_model.generate_content.call_count == 2


def test_generate_story_seed_blocked_content():
    """Test generate_story_seed with blocked content."""
    spark = {"keyword": "test", "source_name": "Test Source"}
    config = {
        "generation": {"prompt_template": "Generate for {spark_keyword} from {source_name}", "api_max_retries": 1}
    }

    with patch("src.story_seed_generator._genai_configured", True):
        with patch("google.generativeai.GenerativeModel") as mock_genai:
            mock_model = Mock()
            mock_response = Mock()
            mock_response.text = None
            mock_response.candidates = []
            mock_response.prompt_feedback = Mock(block_reason="SAFETY")
            mock_model.generate_content.return_value = mock_response
            mock_genai.return_value = mock_model

            result = generate_story_seed(spark, config)
            assert result is None
            # Should not retry for safety block
            assert mock_model.generate_content.call_count == 1


def test_generate_story_seed_max_tokens():
    """Test generate_story_seed with max tokens reached."""
    spark = {"keyword": "test", "source_name": "Test Source"}
    config = {"generation": {"prompt_template": "Generate for {spark_keyword} from {source_name}"}}

    with patch("src.story_seed_generator._genai_configured", True):
        with patch("google.generativeai.GenerativeModel") as mock_genai:
            mock_model = Mock()
            mock_response = Mock()
            mock_response.text = None
            mock_response.candidates = [Mock(finish_reason="MAX_TOKENS")]
            mock_response.prompt_feedback = Mock(block_reason=None)
            mock_model.generate_content.return_value = mock_response
            mock_genai.return_value = mock_model

            result = generate_story_seed(spark, config)
            assert result is None
