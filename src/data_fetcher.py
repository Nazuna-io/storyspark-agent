# src/data_fetcher.py
import feedparser
import requests
import json
import logging
from datetime import datetime, timezone, timedelta
import time
import os
from typing import List, Dict, Tuple, Optional, Any

logger = logging.getLogger(__name__)
STATE_FILE = "fetcher_state.json"
# Good practice: Customize User-Agent with contact info
USER_AGENT = "StorySparkAgent/1.0 (github.com/Nazuna-io/storyspark-agent; contact: your_email@example.com)"

# --- Type Aliases ---
FetchedItem = Dict[str, Any]
FetcherState = Dict[str, Dict[str, Optional[datetime]]]
TimestampState = Dict[str, Optional[datetime]] # Maps source_key -> last_timestamp

# --- Timestamp Parsing Helpers ---

def _parse_rfc822_datetime(dt_str: Any) -> Optional[datetime]:
    """Robustly parses various datetime formats found in feeds into timezone-aware UTC datetime."""
    if isinstance(dt_str, datetime):
        # If already a datetime object
        if dt_str.tzinfo:
            return dt_str.astimezone(timezone.utc)
        else:
            return dt_str.replace(tzinfo=timezone.utc) # Assume UTC if naive

    if isinstance(dt_str, time.struct_time):
        # If it's a time.struct_time (common from feedparser)
        try:
            dt = datetime.fromtimestamp(time.mktime(dt_str), timezone.utc)
            return dt
        except Exception as e:
            logger.warning(f"Could not convert struct_time to datetime: {dt_str}, Error: {e}")
            return None

    if isinstance(dt_str, str):
        # If it's a string, try parsing known formats
        fmts = [
            "%a, %d %b %Y %H:%M:%S %Z",      # RFC 822 (e.g., 'Wed, 02 Oct 2002 13:00:00 GMT')
            "%a, %d %b %Y %H:%M:%S %z",      # RFC 822 with offset (e.g., 'Wed, 02 Oct 2002 08:00:00 -0500')
            "%Y-%m-%dT%H:%M:%S%z",          # ISO 8601 variant (e.g., '2003-12-13T18:30:02+00:00')
            "%Y-%m-%dT%H:%M:%S.%f%z",     # ISO 8601 with microseconds
            "%Y-%m-%dT%H:%M:%SZ",           # ISO 8601 UTC Zulu time ('Z' suffix)
        ]
        for fmt in fmts:
            try:
                dt = datetime.strptime(dt_str, fmt)
                # Ensure timezone-aware UTC
                if dt.tzinfo:
                    return dt.astimezone(timezone.utc)
                else:
                    # Should not happen with %Z/%z, but handle just in case
                    return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue # Try next format

        # If standard formats fail, log a warning
        logger.debug(f"Could not parse datetime string with standard formats: '{dt_str}'")
        return None

    # If it's not a recognized type
    logger.warning(f"Cannot parse unrecognized type for datetime: {type(dt_str)}, value: {dt_str}")
    return None

def _parse_unix_timestamp(ts: float | int | str) -> Optional[datetime]:
    """Converts a Unix timestamp (potentially as str) to a timezone-aware UTC datetime."""
    try:
        # Convert to float first to handle potential string inputs
        unix_ts = float(ts)
        return datetime.fromtimestamp(unix_ts, timezone.utc)
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not parse Unix timestamp: '{ts}', Error: {e}")
        return None

# --- State Management Functions ---
def _load_fetcher_state(path: str = STATE_FILE) -> TimestampState:
    """Loads the last fetched timestamps from the state file."""
    if not os.path.exists(path):
        logger.info(f"Fetcher state file '{path}' not found. Starting fresh.")
        return {}

    try:
        with open(path, 'r', encoding='utf-8') as f:
            state_data = json.load(f)

        if not isinstance(state_data, dict) or "last_timestamps" not in state_data:
            logger.warning(f"Invalid format in state file '{path}'. Starting fresh.")
            return {}

        loaded_timestamps: TimestampState = {}
        for source_key, ts_str in state_data.get("last_timestamps", {}).items():
            if ts_str is None:
                 loaded_timestamps[source_key] = None
                 continue
            try:
                # Ensure timestamps are timezone-aware UTC upon loading
                dt = datetime.fromisoformat(ts_str)
                if dt.tzinfo is None:
                     # This case should ideally not happen if saved correctly,
                     # but handle if state file was manually edited or corrupted.
                     logger.warning(f"Loaded naive timestamp '{ts_str}' for {source_key}, assuming UTC.")
                     dt = dt.replace(tzinfo=timezone.utc)
                else:
                     dt = dt.astimezone(timezone.utc)
                loaded_timestamps[source_key] = dt
            except (ValueError, TypeError):
                 logger.warning(f"Could not parse timestamp from state for {source_key}: '{ts_str}'. Ignoring this entry.")
                 # Decide whether to store None or skip the key. Storing None might be safer.
                 loaded_timestamps[source_key] = None

        logger.info(f"Fetcher state loaded successfully from '{path}'")
        return loaded_timestamps
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from state file '{path}'. Starting fresh.")
        return {}
    except Exception as e:
        logger.error(f"Error loading fetcher state from '{path}': {e}", exc_info=True)
        return {} # Return default empty state on error

def _save_fetcher_state(timestamps: TimestampState, path: str = STATE_FILE):
    """Saves the last fetched timestamps to the state file."""
    try:
        # Prepare data for JSON serialization (datetime -> ISO string)
        serializable_timestamps: Dict[str, Optional[str]] = {}
        for source_key, dt_obj in timestamps.items():
            if isinstance(dt_obj, datetime):
                # Ensure it's UTC before saving
                if dt_obj.tzinfo is None:
                    logger.warning(f"Attempting to save naive datetime {dt_obj} for {source_key}. Assuming UTC.")
                    dt_utc = dt_obj.replace(tzinfo=timezone.utc)
                else:
                    dt_utc = dt_obj.astimezone(timezone.utc)
                serializable_timestamps[source_key] = dt_utc.isoformat()
            elif dt_obj is None:
                 # Store None as null in JSON
                 serializable_timestamps[source_key] = None
            else:
                 logger.warning(f"Invalid type in timestamp state for {source_key}: {type(dt_obj)}. Storing as null.")
                 serializable_timestamps[source_key] = None

        state_to_save = {"last_timestamps": serializable_timestamps}

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(state_to_save, f, indent=4)
        logger.debug(f"Fetcher state saved to '{path}'")
    except IOError as e:
        logger.error(f"Could not write fetcher state to '{path}': {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred saving fetcher state: {e}", exc_info=True)

# --- Fetching Functions ---
def fetch_rss(feed_url: str, last_timestamp: Optional[datetime]) -> List[FetchedItem]:
    """Fetches new items from an RSS feed since the last timestamp."""
    items: List[FetchedItem] = []
    logger.info(f"Fetching RSS feed: {feed_url}")
    try:
        # Add request headers - some feeds require a User-Agent
        headers = {'User-Agent': USER_AGENT}
        # Set a timeout for the request
        feed_data = feedparser.parse(feed_url, agent=USER_AGENT, request_headers=headers, etag=None, modified=None) # Disable etag/modified for simplicity in MVP

        if feed_data.bozo:
            ex = feed_data.get('bozo_exception', 'Unknown parsing error')
            # Log as warning, but still try to process entries
            logger.warning(f"Potential issue parsing feed {feed_url}: {ex}")

        if feed_data.get("status") == 404:
            logger.error(f"Feed {feed_url} returned 404 Not Found.")
            return []
        if feed_data.get("status", 200) >= 400:
             logger.error(f"Feed {feed_url} returned status {feed_data.get('status')}")
             # Could implement retries here later
             return []

        if not feed_data.entries:
             logger.info(f"No entries found in feed: {feed_url}")
             return []

        source_name = feed_data.feed.get('title', feed_url) # Use feed title if available
        processed_ids = set()

        # Iterate through entries (consider sorting if needed, but feedparser often gives chronological)
        for entry in feed_data.entries:
            entry_timestamp: Optional[datetime] = None
            # Prefer 'published_parsed', fallback to 'updated_parsed'
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                entry_timestamp = _parse_rfc822_datetime(entry.published_parsed)
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                entry_timestamp = _parse_rfc822_datetime(entry.updated_parsed)
            # Add a fallback using 'updated' or 'published' string fields if parsed versions fail
            elif hasattr(entry, 'published') and entry.published:
                entry_timestamp = _parse_rfc822_datetime(entry.published)
            elif hasattr(entry, 'updated') and entry.updated:
                 entry_timestamp = _parse_rfc822_datetime(entry.updated)


            if entry_timestamp is None:
                logger.debug(f"Skipping entry in '{source_name}' with no valid timestamp: {entry.get('link', entry.get('title', 'Unknown'))}")
                continue

            # Timestamps are parsed into UTC by _parse_rfc822_datetime

            # Check against last_timestamp
            if last_timestamp is not None and entry_timestamp <= last_timestamp:
                # Item is not new, skip it
                continue

            # --- Extract Item Details --- 
            item_id = entry.get('id', entry.get('link')) # Use 'id' if present, else 'link'
            if not item_id:
                logger.warning(f"Skipping entry in '{source_name}' with no ID or Link. Title: {entry.get('title')}")
                continue

            # Avoid processing duplicate IDs within the same fetch operation
            if item_id in processed_ids:
                 logger.debug(f"Skipping duplicate item ID '{item_id}' in '{source_name}' during fetch.")
                 continue
            processed_ids.add(item_id)

            content_snippet = entry.get('summary', entry.get('description', ''))
            # Basic HTML tag removal (very rudimentary, consider BeautifulSoup later if needed)
            if content_snippet and isinstance(content_snippet, str):
                import re
                content_snippet = re.sub('<[^<]+?>', '', content_snippet).strip()
            else:
                content_snippet = ''

            title = entry.get('title', 'No Title')
            link = entry.get('link') # May be None

            item: FetchedItem = {
                'id': item_id,
                'title': title,
                'content_snippet': content_snippet[:500] if content_snippet else '', # Limit snippet length
                'source_name': source_name,
                'timestamp': entry_timestamp,
                'link': link
            }
            items.append(item)

        # Sort the collected new items by timestamp ascending (oldest first)
        items.sort(key=lambda x: x['timestamp'])
        logger.info(f"Fetched {len(items)} new items from {source_name} ({feed_url})")

    except ConnectionRefusedError as e:
         logger.error(f"Connection refused when fetching RSS feed {feed_url}: {e}")
    except requests.exceptions.RequestException as e: # Catch potential network errors if feedparser uses requests internally
        logger.error(f"Network error fetching RSS feed {feed_url}: {e}")
    except Exception as e:
        logger.error(f"Failed to fetch or parse RSS feed {feed_url}: {e}", exc_info=True)

    return items

def fetch_subreddit_json(subreddit_name: str, last_timestamp: Optional[datetime]) -> List[FetchedItem]:
    """Fetches new posts from a public subreddit's JSON endpoint."""
    items: List[FetchedItem] = []
    # Basic cleaning of subreddit name (remove 'r/', etc.)
    subreddit_name = ''.join(c for c in subreddit_name if c.isalnum() or c == '_').strip()
    if not subreddit_name:
        logger.error("Invalid subreddit name provided (empty after cleaning).")
        return []

    # Use HTTPS, fetch 'new' posts, limit to ~100 (max allowed by Reddit)
    url = f"https://www.reddit.com/r/{subreddit_name}/new.json?limit=100"
    logger.info(f"Fetching Subreddit JSON: r/{subreddit_name} from {url}")
    headers = {'User-Agent': USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=20) # Set a reasonable timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        # Check for redirects (e.g., case sensitivity)
        if response.history:
            final_url = response.url
            logger.debug(f"Request for r/{subreddit_name} was redirected to {final_url}")
            # Extract subreddit name from final URL if needed (optional)

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response from {url}: {e}")
            logger.debug(f"Response text (first 500 chars): {response.text[:500]}")
            return []

        if 'data' not in data or 'children' not in data['data']:
             logger.warning(f"Unexpected JSON structure from r/{subreddit_name}. Skipping. Data: {str(data)[:500]}...")
             return []

        processed_ids = set()
        source_full_name = f"r/{subreddit_name}" # For use in the item

        # Posts are typically ordered newest first in the 'new.json' endpoint
        for post_container in data['data']['children']:
            if post_container.get('kind') != 't3': # 't3' denotes a Link (submission)
                 logger.debug(f"Skipping non-t3 item in r/{subreddit_name}: kind={post_container.get('kind')}")
                 continue
            post_data = post_container.get('data', {})
            created_utc = post_data.get('created_utc')

            if not created_utc:
                logger.debug(f"Skipping post in r/{subreddit_name} with no timestamp: ID={post_data.get('id')}, Title={post_data.get('title')}")
                continue

            post_timestamp = _parse_unix_timestamp(created_utc)
            if post_timestamp is None:
                 # Error already logged by _parse_unix_timestamp
                 continue

            # Check against last_timestamp
            if last_timestamp is not None and post_timestamp <= last_timestamp:
                # Optimization: Since Reddit 'new' is sorted newest first, we can stop checking
                # once we encounter a post older than or equal to the last timestamp.
                logger.debug(f"Reached post older than last timestamp in r/{subreddit_name}. Stopping iteration for this source.")
                break # Stop processing older posts for this subreddit

            # --- Extract Item Details --- 
            item_id = post_data.get('id') # Reddit post ID (e.g., 'xyz789')
            if not item_id:
                 logger.warning(f"Skipping post in r/{subreddit_name} with no ID. Title: {post_data.get('title')}")
                 continue
            # Use the 'name' field (e.g., 't3_xyz789') as a more robust unique ID if available
            full_item_id = post_data.get('name', f"t3_{item_id}")

            if full_item_id in processed_ids:
                 logger.debug(f"Skipping duplicate item ID '{full_item_id}' in r/{subreddit_name} during fetch.")
                 continue
            processed_ids.add(full_item_id)

            # Use 'selftext' for text posts, otherwise fallback to title as snippet
            content_snippet = post_data.get('selftext', '').strip()
            title = post_data.get('title', 'No Title').strip()
            link = post_data.get('url') # URL of the post itself or the linked content
            # Get permalink for direct link to reddit comments
            permalink = f"https://www.reddit.com{post_data.get('permalink', '')}" if post_data.get('permalink') else link

            item: FetchedItem = {
                'id': full_item_id, # Use the full 'name' (t3_id)
                'title': title,
                'content_snippet': content_snippet[:500] if content_snippet else '', # Limit snippet length
                'source_name': source_full_name,
                'timestamp': post_timestamp,
                'link': permalink # Prefer the permalink
            }
            items.append(item)

        # Sort the collected new items by timestamp ascending (oldest first)
        items.sort(key=lambda x: x['timestamp'])
        logger.info(f"Fetched {len(items)} new items from {source_full_name}")

    except requests.exceptions.HTTPError as e:
        # Specific handling for HTTP errors (like 404, 403, 5xx)
        if e.response.status_code == 404:
            logger.error(f"Subreddit r/{subreddit_name} not found (404). Please check the name.")
        elif e.response.status_code == 403:
            logger.error(f"Access forbidden (403) for r/{subreddit_name}. It might be private or quarantined.")
        elif e.response.status_code == 429: # Rate limited
            logger.warning(f"Rate limited (429) while fetching r/{subreddit_name}. Consider increasing interval.")
        else:
             logger.error(f"HTTP error fetching subreddit r/{subreddit_name}: {e}")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error fetching subreddit r/{subreddit_name}: {e}")
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout fetching subreddit r/{subreddit_name}: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Generic network error fetching subreddit r/{subreddit_name}: {e}")
    except Exception as e:
        logger.error(f"Failed to fetch or parse subreddit r/{subreddit_name}: {e}", exc_info=True)

    return items

def get_new_items(config: Dict[str, Any], current_timestamps: TimestampState) -> Tuple[List[FetchedItem], TimestampState]:
    """Fetches new items from all configured sources and updates timestamps.

    Args:
        config: The loaded application configuration dictionary.
        current_timestamps: A dictionary mapping source keys to their last fetched datetime.

    Returns:
        A tuple containing:
          - A list of all new FetchedItem dictionaries from all sources, sorted by timestamp.
          - An updated dictionary of timestamps reflecting the latest item fetched per source.
    """
    all_new_items: List[FetchedItem] = []
    updated_timestamps = current_timestamps.copy() # Work on a copy
    sources_config = config.get('sources', {})
    rss_feeds = sources_config.get('rss_feeds', [])
    subreddits = sources_config.get('subreddits', [])

    # --- Fetch from RSS Feeds ---
    for feed_config in rss_feeds:
        if not isinstance(feed_config, dict) or 'url' not in feed_config:
            logger.warning(f"Skipping invalid RSS feed config item: {feed_config}")
            continue
        feed_url = feed_config['url']
        source_key = f"rss_{feed_url}" # Unique key for state tracking
        last_timestamp = current_timestamps.get(source_key)

        try:
            new_rss_items = fetch_rss(feed_url, last_timestamp)
            if new_rss_items:
                all_new_items.extend(new_rss_items)
                # Update timestamp state with the timestamp of the *latest* item fetched *in this batch*
                latest_item_ts = max(item['timestamp'] for item in new_rss_items)
                # Only update if the new latest is more recent than the stored one
                if last_timestamp is None or latest_item_ts > last_timestamp:
                     updated_timestamps[source_key] = latest_item_ts
            # else: If no new items, timestamp remains unchanged
        except Exception as e:
            logger.error(f"Error processing RSS feed {feed_url}: {e}", exc_info=True)
            # Continue to next source even if one fails

    # --- Fetch from Subreddits ---
    for sub_config in subreddits:
        if not isinstance(sub_config, dict) or 'name' not in sub_config:
            logger.warning(f"Skipping invalid subreddit config item: {sub_config}")
            continue
        subreddit_name = sub_config['name']
        source_key = f"reddit_{subreddit_name}" # Unique key for state tracking
        last_timestamp = current_timestamps.get(source_key)

        try:
            new_reddit_items = fetch_subreddit_json(subreddit_name, last_timestamp)
            if new_reddit_items:
                all_new_items.extend(new_reddit_items)
                # Update timestamp state with the timestamp of the *latest* item fetched *in this batch*
                latest_item_ts = max(item['timestamp'] for item in new_reddit_items)
                 # Only update if the new latest is more recent than the stored one
                if last_timestamp is None or latest_item_ts > last_timestamp:
                    updated_timestamps[source_key] = latest_item_ts
            # else: If no new items, timestamp remains unchanged
        except Exception as e:
            logger.error(f"Error processing subreddit r/{subreddit_name}: {e}", exc_info=True)
            # Continue to next source

    # Sort all collected items by timestamp before returning
    all_new_items.sort(key=lambda x: x['timestamp'])

    logger.info(f"Total new items fetched across all sources: {len(all_new_items)}")

    return all_new_items, updated_timestamps

# --- Public wrapper functions for state loading/saving (optional, but cleaner) ---

def load_state(path: str = STATE_FILE) -> TimestampState:
    """Public wrapper to load fetcher timestamp state."""
    return _load_fetcher_state(path)

def save_state(timestamps: TimestampState, path: str = STATE_FILE):
    """Public wrapper to save fetcher timestamp state."""
    _save_fetcher_state(timestamps, path)
