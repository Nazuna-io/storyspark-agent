# src/trend_detector.py
import logging
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Set, Tuple, Any

logger = logging.getLogger(__name__)

# --- Text Cleaning and Keyword Extraction ---

def _clean_text(text: str) -> str:
    """Basic text cleaning: lowercase, remove punctuation/numbers, extra whitespace."""
    if not text: return ""
    text = text.lower()
    # Remove URLs first
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    # Remove punctuation and numbers
    text = re.sub(r'[^\w\s]', '', text) # Keep word characters and whitespace
    text = re.sub(r'\d+', '', text) # Remove digits
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _extract_keywords(text: str, stopwords: Set[str]) -> List[str]:
    """Extracts keywords from cleaned text, excluding stopwords and short words."""
    cleaned_text = _clean_text(text)
    words = cleaned_text.split()
    # Filter out stopwords and words shorter than 3 characters
    keywords = [word for word in words if word not in stopwords and len(word) > 2]
    return keywords

# --- Spark Detection Logic ---

def detect_sparks(new_items: List[Dict[str, Any]], 
                  history_items: List[Dict[str, Any]], 
                  config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Detects 'sparks' (keyword frequency spikes) in new items compared to history.

    Args:
        new_items: List of newly fetched items (dictionaries).
        history_items: List of items from the recent history (dictionaries).
        config: The application configuration dictionary.

    Returns:
        A list of 'spark' dictionaries, each containing the keyword and the
        most recent item associated with it.
    """
    sparks: List[Dict[str, Any]] = []
    td_config = config.get('trend_detection', {})
    stopwords = set(td_config.get('stopwords', []))
    min_keyword_frequency = td_config.get('min_keyword_frequency', 2)
    frequency_threshold_multiplier = td_config.get('frequency_threshold', 3.0) # Use float for comparison

    if not new_items:
        logger.info("No new items to analyze for sparks.")
        return []

    logger.info(f"Analyzing {len(new_items)} new items against {len(history_items)} history items for sparks.")

    # --- Calculate Keyword Frequencies ---
    new_keywords_all: List[str] = []
    new_item_keywords: Dict[str, List[str]] = {} # keyword -> list of item titles where it appeared
    keyword_latest_item: Dict[str, Dict[str, Any]] = {} # keyword -> latest item containing it

    for item in new_items:
        text_to_analyze = f"{item.get('title', '')} {item.get('content_snippet', '')}"
        keywords = _extract_keywords(text_to_analyze, stopwords)
        new_keywords_all.extend(keywords)
        # Track which keywords appear in which new item titles and the latest item itself
        for keyword in set(keywords): # Use set to count each keyword once per item for association
            if keyword not in new_item_keywords:
                 new_item_keywords[keyword] = []
                 keyword_latest_item[keyword] = item # Store the first encountered item
            new_item_keywords[keyword].append(item.get('title', 'Unknown Title'))
            # Update if current item is newer
            if item.get('timestamp') > keyword_latest_item[keyword].get('timestamp'):
                keyword_latest_item[keyword] = item

    new_freq = Counter(new_keywords_all)

    history_keywords_all: List[str] = []
    for item in history_items:
        text_to_analyze = f"{item.get('title', '')} {item.get('content_snippet', '')}"
        history_keywords_all.extend(_extract_keywords(text_to_analyze, stopwords))

    history_freq = Counter(history_keywords_all)

    # --- Compare Frequencies and Identify Sparks ---
    logger.debug(f"New item keyword counts (Top 10): {new_freq.most_common(10)}")
    logger.debug(f"History keyword counts (Top 10): {history_freq.most_common(10)}")

    potential_sparks = set()
    for keyword, count in new_freq.items():
        if count < min_keyword_frequency:
            continue # Skip keywords below the minimum frequency in the new batch

        history_count = history_freq.get(keyword, 0)

        # --- Spike Detection Logic --- 
        is_spike = False
        if history_count == 0:
            # If keyword is completely new and meets min frequency, it's a spark
            is_spike = True
            logger.debug(f"Keyword '{keyword}' detected as new (count={count}).")
        elif history_count > 0:
            # If keyword existed, check if its frequency increased significantly
            # Avoid division by zero if frequency_threshold_multiplier is 0 or less
            if frequency_threshold_multiplier > 0 and \
               count >= (history_count * frequency_threshold_multiplier):
                is_spike = True
                logger.debug(f"Keyword '{keyword}' detected as spike (new_count={count}, history_count={history_count}, threshold={frequency_threshold_multiplier}x).)")
            # else:
                # logger.debug(f"Keyword '{keyword}' frequency did not meet threshold (new={count}, history={history_count})")
        
        if is_spike:
            potential_sparks.add(keyword)

    # --- Format Spark Output --- 
    for keyword in potential_sparks:
        if keyword in keyword_latest_item:
            latest_item = keyword_latest_item[keyword]
            spark_info = {
                'keyword': keyword,
                'detected_at': datetime.now(timezone.utc),
                # Include details from the latest item associated with the spark
                'source_name': latest_item.get('source_name', 'Unknown Source'),
                'latest_item_title': latest_item.get('title', 'No Title'),
                'latest_item_link': latest_item.get('link'),
                'latest_item_timestamp': latest_item.get('timestamp')
                # Consider adding frequency counts (new/history) if useful for debugging/context
                # 'new_frequency': new_freq[keyword],
                # 'history_frequency': history_freq.get(keyword, 0)
            }
            sparks.append(spark_info)
            logger.info(f"Detected Spark: '{keyword}' from source '{spark_info['source_name']}' (New Freq: {new_freq[keyword]}, Hist Freq: {history_freq.get(keyword, 0)}) - Assoc. item: {spark_info['latest_item_title']}")
        else:
             # This should not happen if logic is correct, but log if it does
             logger.warning(f"Detected spark keyword '{keyword}' but couldn't find its associated latest item.")

    logger.info(f"Detected {len(sparks)} sparks in this cycle.")
    return sparks
