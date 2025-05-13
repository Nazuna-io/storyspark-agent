# src/story_seed_generator.py
import os
import google.generativeai as genai
import logging
from datetime import datetime, timezone
import re
import time
from typing import Dict, Optional, List, Any
from dotenv import load_dotenv # Added to load .env file

logger = logging.getLogger(__name__)

# --- Gemini API Configuration ---

_genai_configured = False

def configure_genai():
    """Configures the Google Gemini API client using the API key from env. Idempotent."""
    global _genai_configured
    if _genai_configured:
        return True # Already configured

    # Load environment variables from .env file, if present
    load_dotenv()

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY environment variable not set or found in .env file.")
        # Don't raise here, let the caller handle the lack of configuration
        # Raise ValueError("API key not found. Please set the GOOGLE_API_KEY environment variable.")
        return False # Configuration failed
    try:
        genai.configure(api_key=api_key)
        logger.info("Google Generative AI client configured successfully.")
        _genai_configured = True
        return True # Configuration successful
    except Exception as e:
        logger.error(f"Failed to configure Google Generative AI: {e}", exc_info=True)
        _genai_configured = False # Ensure it can be retried if temporary issue
        return False # Configuration failed

# --- Response Parsing Logic ---
def _parse_gemini_response(text: str) -> Optional[Dict[str, Any]]:
    """Parses the text response from Gemini to extract structured story seed data."""
    if not text:
        logger.warning("Received empty text from Gemini response for parsing.")
        return None

    try:
        # Regex patterns updated to handle potential markdown formatting (##, **, numbering/bullets) in headings
        logline_pattern = r"(?:^|\n)\s*(?:##\s*)?(?:\*\*)?(?:\d+\.|\*|-)?\s*\bLogline:?\s*(?:\*\*)?\s*(.*?)(?=\n\s*\n|\n\s*(?:##\s*)?(?:\*\*)?(?:\d+\.|\*|-)?\s*\b(?:What If Questions|Thematic Keywords):?|$)" # Corrected unbalanced parenthesis in lookahead
        questions_pattern = r"(?:^|\n)\s*(?:##\s*)?(?:\*\*)?(?:\d+\.|\*|-)?\s*\bWhat If Questions:?\s*(?:\*\*)?\s*(.*)(?=\n\s*(?:##\s*)?(?:\*\*)?(?:\d+\.|\*|-)?\s*\bThematic Keywords:?)"
        keywords_pattern = r"(?:^|\n)\s*(?:##\s*)?(?:\*\*)?(?:\d+\.|\*|-)?\s*\bThematic Keywords:?\s*(?:\*\*)?\s*(.*)(?:$)"

        logline_match = re.search(logline_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)
        questions_match = re.search(questions_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)
        keywords_match = re.search(keywords_pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)

        logline = logline_match.group(1).strip() if logline_match else None

        questions_raw = questions_match.group(1).strip() if questions_match else ""
        # Split questions primarily by newline, then clean up potential list markers
        questions_split = questions_raw.split('\n')
        what_if_questions = _split_items('\n'.join(questions_split))

        keywords_raw = keywords_match.group(1).strip() if keywords_match else ""
        # Split keywords primarily by newline, then clean up
        keywords_split = keywords_raw.split('\n')
        thematic_keywords = _split_items('\n'.join(keywords_split))

        # --- Validation of Parsed Content ---
        if not logline:
            logger.warning(f"Could not parse Logline from LLM response.\nResponse snippet:\n{text[:500]}...")
            return None # Require logline
        if not what_if_questions:
            logger.warning(f"Could not parse 'What If Questions' from LLM response.\nResponse snippet:\n{text[:500]}...")
            # Decide if we allow seeds without questions/keywords. For now, let's require them.
            return None
        if not thematic_keywords:
            logger.warning(f"Could not parse 'Thematic Keywords' from LLM response.\nResponse snippet:\n{text[:500]}...")
            return None

        logger.info("Successfully parsed LLM response into logline, questions, and keywords.")
        return {
            'logline': logline,
            'what_if_questions': what_if_questions[:3], # Ensure max 3
            'thematic_keywords': thematic_keywords[:3]   # Ensure max 3
        }

    except Exception as e:
        logger.error(f"Error parsing Gemini response: {e}\nResponse Text (first 500 chars):\n{text[:500]}...", exc_info=True)
        return None

def _split_items(item_string: str) -> List[str]:
    """Splits a string of items (like questions or keywords) into a list.
    It also cleans each item by removing list markers, surrounding markdown (like **),
    and extracts only the primary keyword if a description (separated by a colon) is present."""
    if not item_string:
        return []
    
    processed_items = []
    raw_lines = item_string.strip().split('\n')
    
    for line_content in raw_lines:
        # 1. Initial strip and skip if empty or a markdown horizontal rule
        item = line_content.strip()
        if not item or item.startswith("---"):
            continue
            
        # 2. Remove leading/trailing list markers (e.g., '* ', '- ')
        item = re.sub(r"^\s*[\*\-]\s*|\s*[\*\-]\s*$", "", item).strip()
        
        # 3. Iteratively remove surrounding markdown bold/italic (*, **)
        #    e.g., "**text**" -> "text", "*text*" -> "text", "***text***" -> "text"
        while item.startswith('**') and item.endswith('**') and len(item) > 3: # len > 3 for "**a**"
            item = item[2:-2].strip()
        while item.startswith('*') and item.endswith('*') and len(item) > 1: # len > 1 for "*a*"
            item = item[1:-1].strip()

        # 4. If a colon is present (likely separating keyword from description), take only the part before it.
        #    Also, re-strip markdown from this part, in case of "**Keyword**: description"
        if ':' in item:
            keyword_part = item.split(':', 1)[0].strip()
            # Re-apply step 3 to keyword_part
            while keyword_part.startswith('**') and keyword_part.endswith('**') and len(keyword_part) > 3:
                keyword_part = keyword_part[2:-2].strip()
            while keyword_part.startswith('*') and keyword_part.endswith('*') and len(keyword_part) > 1:
                keyword_part = keyword_part[1:-1].strip()
            item = keyword_part

        # 5. Add to list if not empty after processing
        if item:
            processed_items.append(item)
            
    return processed_items

# --- Story Seed Generation Function ---
def generate_story_seed(spark: Dict[str, Any], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generates a story seed using the Gemini API based on a detected spark."""
    # Ensure API is configured
    if not _genai_configured:
        logger.info("Attempting to configure Gemini API before generation...")
        if not configure_genai():
            logger.error("Gemini client not configured and configuration attempt failed. Cannot generate seed.")
            return None
        # If configure_genai() succeeded, _genai_configured is now True

    gen_config = config.get('generation', {})
    model_name = gen_config.get('gemini_model', 'gemini-1.5-flash-latest') # Default to flash
    prompt_template = gen_config.get('prompt_template')
    api_max_retries = gen_config.get('api_max_retries', 2) # Default 2 retries (3 total attempts)
    api_retry_delay = gen_config.get('api_retry_delay', 5) # Default 5 seconds

    spark_keyword = spark.get('keyword', 'Unknown Keyword')
    source_name = spark.get('source_name', 'Unknown Source')
    # Include item title/link if available for more context in prompt?
    # item_title = spark.get('latest_item_title', '')
    # item_link = spark.get('latest_item_link', '')

    if not prompt_template:
        logger.error("Prompt template 'generation.prompt_template' is missing in the configuration.")
        return None

    # --- Prompt Formatting ---
    try:
        # Provide keyword and source to the template
        prompt = prompt_template.format(spark_keyword=spark_keyword, source_name=source_name)
    except KeyError as e:
        logger.error(f"Error formatting prompt template. Missing key: {e}. Template: '{prompt_template}'")
        return None

    logger.info(f"Generating story seed for spark: '{spark_keyword}' from '{source_name}' using model '{model_name}'")
    logger.debug(f"Formatted Prompt:\n------\n{prompt}\n------")

    # --- API Call with Retries --- 
    for attempt in range(api_max_retries + 1):
        try:
            model = genai.GenerativeModel(model_name)
            # Consider adding safety settings if required (e.g., blocking harmful content)
            # Consult Gemini documentation for available settings and categories
            # safety_settings = {
            #     'HARM_CATEGORY_HARASSMENT': 'BLOCK_MEDIUM_AND_ABOVE',
            #     'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_MEDIUM_AND_ABOVE',
            # }
            response = model.generate_content(prompt) #, safety_settings=safety_settings)

            # --- Response Handling --- 
            # Check response.text first, as it's the most direct way to get the content
            response_text = None
            try:
                response_text = response.text
            except ValueError:
                 # This can happen if the response was blocked. Check feedback.
                 logger.warning(f"ValueError accessing response.text, possibly due to content blocking.")
            except AttributeError:
                # Handle cases where the response structure might be different
                 logger.warning(f"AttributeError accessing response.text. Response structure might be unexpected.")

            if response_text:
                logger.debug(f"Raw Gemini response for spark '{spark_keyword}':\n------ START RAW RESPONSE ------\n{response_text}\n------ END RAW RESPONSE ------")
                # --- Parsing the Successful Response --- 
                parsed_content = _parse_gemini_response(response_text)

                if parsed_content:
                    story_seed = {
                        'spark_keyword': spark_keyword,
                        'source_name': source_name,
                        'logline': parsed_content['logline'],
                        'what_if_questions': parsed_content['what_if_questions'],
                        'thematic_keywords': parsed_content['thematic_keywords'],
                        'generation_timestamp': datetime.now(timezone.utc),
                        # Link back to the item that triggered the spark
                        'triggering_item_title': spark.get('latest_item_title'),
                        'triggering_item_link': spark.get('latest_item_link'),
                        'triggering_item_timestamp': spark.get('latest_item_timestamp')
                    }
                    logger.info(f"Successfully generated and parsed story seed for spark: '{spark_keyword}'")
                    return story_seed # Success!
                else:
                    # Parsing failed, error logged within _parse_gemini_response
                    # Don't retry if parsing failed on a seemingly valid response
                    logger.error(f"Failed to parse the Gemini response for spark '{spark_keyword}'. See previous logs. Raw response snippet:\n{response_text[:500]}...")
                    return None # Parsing failure is final for this attempt
            else:
                # Handle cases where response.text was not accessible or empty
                block_reason = None
                safety_ratings = None
                finish_reason = None
                try:
                    if response.prompt_feedback and response.prompt_feedback.block_reason:
                        block_reason = response.prompt_feedback.block_reason
                        safety_ratings = response.prompt_feedback.safety_ratings
                    elif response.candidates:
                         finish_reason = response.candidates[0].finish_reason
                         if hasattr(response.candidates[0], 'safety_ratings'):
                              safety_ratings = response.candidates[0].safety_ratings
                except Exception as e:
                     logger.debug(f"Error accessing detailed response feedback: {e}")

                logger.warning(f"Gemini API returned no text content for spark '{spark_keyword}' (Attempt {attempt+1}/{api_max_retries+1}). Finish Reason: {finish_reason}, Block Reason: {block_reason}, Safety Ratings: {safety_ratings}")

                # Decide whether to retry based on the reason
                should_retry = False
                if finish_reason == 'STOP' and not block_reason:
                    # Model finished normally but produced no text - unlikely, maybe retry?
                    logger.warning("Model stopped normally but produced no text. Retrying might help.")
                    should_retry = True
                elif finish_reason == 'MAX_TOKENS':
                    logger.warning("Generation stopped due to max tokens. Consider revising prompt or model settings. No retry.")
                    return None # No point retrying
                elif block_reason: 
                    logger.warning(f"Generation blocked due to safety settings ({block_reason}). No retry.")
                    return None # Safety block is final
                elif finish_reason in ['SAFETY', 'RECITATION']:
                    logger.warning(f"Generation stopped due to safety/recitation ({finish_reason}). No retry.")
                    return None # Final
                else: # Other reasons (e.g., API error inferred, unspecified) might warrant a retry
                    should_retry = True

                if should_retry and attempt < api_max_retries:
                    delay = api_retry_delay * (attempt + 1) # Basic exponential backoff
                    logger.info(f"Retrying Gemini request (attempt {attempt + 2}/{api_max_retries + 1}) after {delay} seconds...")
                    time.sleep(delay)
                    continue # Go to next iteration of the loop
                else:
                    logger.error(f"Gemini returned no text content after {attempt + 1} attempts or retry not warranted.")
                    return None # Failure after retries or non-retryable issue

        except Exception as e:
            # Catch other potential API errors (network, auth issues caught by configure_genai usually)
            logger.error(f"Error during Gemini API call (attempt {attempt + 1}/{api_max_retries + 1}) for spark '{spark_keyword}': {e}", exc_info=True)
            if attempt < api_max_retries:
                delay = api_retry_delay * (attempt + 1)
                logger.info(f"Retrying Gemini request after error (attempt {attempt + 2}/{api_max_retries + 1}) after {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error(f"Failed to generate story seed after {api_max_retries + 1} attempts due to API errors.")
                return None # Exhausted retries

    return None # Should only be reached if all retries fail
