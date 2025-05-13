# src/main.py
import schedule
import time
import logging
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple

# Project modules
from src.config_loader import load_config
from src.logger_config import setup_logging
from src.data_fetcher import (
    get_new_items, load_state as load_fetcher_state, 
    save_state as save_fetcher_state, FetchedItem, TimestampState
)
from src.trend_detector import detect_sparks
from src.story_seed_generator import configure_genai, generate_story_seed

# --- Constants ---
CONFIG_FILE = 'config.yaml'
HISTORY_FILE = 'data/history_items.json'
SEEDS_FILE = 'data/generated_seeds.json'
STATE_FILE = 'data/fetcher_state.json' # Keep consistent with data_fetcher default
DATA_DIR = 'data' # Directory to store state, history, seeds

# --- Global logger instance ---
# Logger will be configured by setup_logging
logger = logging.getLogger(__name__)

# --- Helper Functions for Data Persistence ---

def _ensure_data_dir():
    """Ensures the data directory exists."""
    if not os.path.exists(DATA_DIR):
        logger.info(f"Creating data directory: {DATA_DIR}")
        os.makedirs(DATA_DIR)

def _save_json(data: Any, filepath: str):
    """Saves data to a JSON file."""
    try:
        _ensure_data_dir()
        with open(filepath, 'w', encoding='utf-8') as f:
            # Use custom encoder for datetime
            json.dump(data, f, indent=4, ensure_ascii=False, default=_datetime_serializer)
        logger.debug(f"Successfully saved data to {filepath}")
    except Exception as e:
        logger.error(f"Error saving data to {filepath}: {e}", exc_info=True)

def _load_json(filepath: str, default: Any = None) -> Any:
    """Loads data from a JSON file, returning a default value if not found or error occurs."""
    if not os.path.exists(filepath):
        logger.warning(f"File not found: {filepath}. Returning default.")
        return default
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # Use custom object hook for datetime
            data = json.load(f, object_hook=_datetime_parser)
        logger.debug(f"Successfully loaded data from {filepath}")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {filepath}: {e}. Returning default.")
        return default
    except Exception as e:
        logger.error(f"Error loading data from {filepath}: {e}. Returning default.", exc_info=True)
        return default

# --- JSON Serialization/Deserialization Helpers for Datetime ---

def _datetime_serializer(obj):
    """JSON serializer for datetime objects."""
    if isinstance(obj, datetime):
        # Store in ISO 8601 format with timezone info (or 'Z' for UTC)
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def _datetime_parser(dct):
    """JSON object hook to parse ISO 8601 datetime strings back to datetime objects."""
    for key, value in dct.items():
        if isinstance(value, str):
            try:
                # Attempt to parse ISO 8601 format
                # Handle both 'Z' and '+00:00' for UTC timezone indication
                if value.endswith('Z'):
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                else:
                    dt = datetime.fromisoformat(value)
                # Ensure timezone-aware (assume UTC if no timezone info)
                # Note: fromisoformat handles timezone correctly if present
                # If original was naive, it might become aware here if parsed correctly
                dct[key] = dt
            except (ValueError, TypeError):
                # Not a valid ISO datetime string, leave as is
                pass
    return dct

# --- Function to save seeds to Markdown ---

def save_seeds_to_markdown(seeds: List[Dict[str, Any]], filepath: str):
    """Saves a list of generated story seeds to a markdown file."""
    try:
        _ensure_data_dir() # Ensures data directory if filepath is within it, though config implies root for .md
        content = "# Story Sparks Output\n\n"
        if not seeds:
            content += "No story seeds generated yet.\n"
        else:
            for seed in seeds:
                content += (f"## Spark: {seed.get('spark_keyword', 'N/A')} "
                           f"(Source: {seed.get('source_name', 'N/A')})\n\n")
                content += f"**Logline:**\n{seed.get('logline', 'N/A')}\n\n"
                content += "**What If Questions:**\n"
                what_if_questions = seed.get('what_if_questions', [])
                if isinstance(what_if_questions, list) and what_if_questions:
                    for q in what_if_questions:
                        content += f"- {q}\n"
                else:
                    content += "- N/A\n"
                content += "\n"

                content += "**Thematic Keywords:**\n"
                thematic_keywords = seed.get('thematic_keywords', [])
                if isinstance(thematic_keywords, list) and thematic_keywords:
                    for k in thematic_keywords:
                        content += f"- {k}\n"
                else:
                    content += "- N/A\n"
                content += "\n---\n\n"

        # Determine the actual path. If output_file is just a name, it's in the root.
        # If it contains slashes, it might be a relative path.
        # For now, assuming it's a simple filename in the project root or data/ as configured.
        # The config has 'output_file: story_sparks.md', so it implies project root.
        # If it were 'data/story_sparks.md', _ensure_data_dir would be relevant.
        
        # If the filepath for markdown is NOT in DATA_DIR, _ensure_data_dir isn't needed for it.
        # However, config_loader ensures logging.output_file exists.
        # We should write to the path directly as given by config.

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Successfully saved {len(seeds)} seeds to Markdown: {filepath}")

    except Exception as e:
        logger.error(f"Error saving seeds to Markdown file {filepath}: {e}", exc_info=True)

# --- Main Agent Cycle ---

def run_agent_cycle(
    config: Dict[str, Any], 
    history: List[FetchedItem], 
    current_timestamps: TimestampState
) -> Tuple[List[FetchedItem], TimestampState, List[Dict[str, Any]]]:
    """Runs one complete cycle: fetch -> analyze -> generate."""
    logger.info("--- Starting Agent Cycle ---")

    # 1. Fetch New Items
    logger.info("Fetching new items...")
    new_items, updated_timestamps = get_new_items(config, current_timestamps)
    if not new_items:
        logger.info("No new items fetched in this cycle.")
        logger.info("--- Agent Cycle Complete (No new items) ---")
        # Return current history and updated timestamps (might have changed even with 0 items)
        return history, updated_timestamps, []

    # 2. Update History (Keep only relevant window)
    history_window_days = config.get('trend_detection', {}).get('history_window_days', 7)
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=history_window_days)

    # Combine history and new items, sort by timestamp
    combined_items = history + new_items
    combined_items.sort(key=lambda x: x.get('timestamp', datetime.min.replace(tzinfo=timezone.utc)))

    # Filter out items older than the history window *from the combined list*
    updated_history = [item for item in combined_items if item.get('timestamp') and item['timestamp'] >= cutoff_date]
    items_purged = len(combined_items) - len(updated_history)
    if items_purged > 0:
        logger.info(f"Purged {items_purged} old items from history (older than {history_window_days} days).")

    # Separate the items *strictly older* than the newest batch for baseline comparison
    # Find the timestamp of the first *new* item in the sorted list
    first_new_item_ts = min(item['timestamp'] for item in new_items) if new_items else datetime.now(timezone.utc)
    baseline_history = [item for item in updated_history if item['timestamp'] < first_new_item_ts]

    logger.info(f"History contains {len(updated_history)} items (after update/purge). "
                f"Using {len(baseline_history)} for baseline comparison.")

    # 3. Detect Sparks
    logger.info("Detecting sparks...")
    detected_sparks = detect_sparks(new_items, baseline_history, config)
    if not detected_sparks:
        logger.info("No sparks detected in this cycle.")
        logger.info("--- Agent Cycle Complete (No sparks) ---")
        # Return updated history and timestamps
        return updated_history, updated_timestamps, []

    # 4. Generate Story Seeds
    max_sparks = config.get('agent', {}).get('max_sparks_per_cycle') # Get the limit
    sparks_to_process = detected_sparks
    if max_sparks is not None and max_sparks > 0 and len(detected_sparks) > max_sparks:
        logger.info(f"Limiting seed generation to {max_sparks} sparks (out of {len(detected_sparks)} detected).")
        sparks_to_process = detected_sparks[:max_sparks]
    else:
        logger.info(f"Generating story seeds for {len(sparks_to_process)} sparks...")

    generated_seeds = []
    # Ensure API client is configured *before* the loop
    if not configure_genai():
        logger.error("Failed to configure Gemini API. Skipping seed generation.")
    else:
        for spark in sparks_to_process: # Iterate over the limited list
            seed = generate_story_seed(spark, config)
            if seed:
                generated_seeds.append(seed)
                logger.info(f"Successfully generated seed for spark: {seed['spark_keyword']}")
            else:
                logger.warning(f"Failed to generate seed for spark: {spark.get('keyword', 'N/A')}")

    logger.info(f"Generated {len(generated_seeds)} story seeds.")
    logger.info("--- Agent Cycle Complete ---")

    return updated_history, updated_timestamps, generated_seeds

# --- Main Execution ---

def main():
    """Main function to load config, set up logging, and run the scheduler."""
    # --- Initial Setup ---
    print("Starting StorySpark Agent...") # Use print before logging is setup

    # Load Configuration
    config = load_config(CONFIG_FILE)

    if not config:
        print(f"FATAL: Could not load configuration from {CONFIG_FILE}. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Logging setup might print info about log files/levels
    setup_logging(config)

    logger = logging.getLogger(__name__) # Get logger instance AFTER setup is complete

    logger.info("StorySpark Agent started.")
    logger.info(f"Loaded configuration from {CONFIG_FILE}.")

    # Load initial state
    _ensure_data_dir() # Ensure data dir exists before loading
    logger.info("Loading previous state...")
    current_timestamps: TimestampState = load_fetcher_state(STATE_FILE)
    history: List[FetchedItem] = _load_json(HISTORY_FILE, default=[])
    all_generated_seeds: List[Dict[str, Any]] = _load_json(SEEDS_FILE, default=[])
    logger.info(f"Loaded {len(history)} history items and {len(all_generated_seeds)} previously generated seeds.")
    logger.debug(f"Initial fetcher timestamps: {current_timestamps}")

    # Ensure existing seeds are written to Markdown at startup
    if all_generated_seeds:
        markdown_output_file = config.get('logging', {}).get('output_file')
        if markdown_output_file:
            logger.info(f"Writing {len(all_generated_seeds)} existing seeds to Markdown: {markdown_output_file}")
            save_seeds_to_markdown(all_generated_seeds, markdown_output_file)
        else:
            logger.warning("Markdown output file not specified in config. Cannot write existing seeds.")

    # --- Scheduling --- 
    schedule_interval_minutes = config.get('agent', {}).get('schedule_interval_minutes', 60)
    logger.info(f"Agent cycle scheduled to run every {schedule_interval_minutes} minutes.")

    # --- Define the job --- 
    # Use a mutable list to pass 'history' and 'current_timestamps' by reference effectively
    # so the scheduled job modifies the main script's variables.
    # Note: A class-based approach would be cleaner for managing state.
    state_container = {'history': history, 'timestamps': current_timestamps}

    def scheduled_job() -> None:
        logger.info("Scheduler triggered agent cycle.")
        try:
            # Pass current state from container
            updated_history, updated_timestamps, new_seeds = run_agent_cycle(
                config,
                state_container['history'],
                state_container['timestamps']
            )
            # Update state in container
            state_container['history'] = updated_history
            state_container['timestamps'] = updated_timestamps

            # Save updated state and history
            save_fetcher_state(updated_timestamps, STATE_FILE)
            _save_json(updated_history, HISTORY_FILE)

            # Append and save new seeds
            if new_seeds:
                all_generated_seeds.extend(new_seeds)
                _save_json(all_generated_seeds, SEEDS_FILE)
                logger.info(f"Appended {len(new_seeds)} new seeds. Total seeds: {len(all_generated_seeds)}.")

                # Save to Markdown as well
                markdown_output_file = config.get('logging', {}).get('output_file')
                if markdown_output_file:
                    save_seeds_to_markdown(all_generated_seeds, markdown_output_file)
                else:
                    logger.warning("Markdown output file not specified in config. Skipping markdown generation.")

        except Exception as e:
            logger.critical(f"Unhandled exception in scheduled job: {e}", exc_info=True)
            # Decide if the agent should stop or continue after a critical error

    # --- Run Immediately and Schedule --- 
    run_immediately = config.get('agent', {}).get('run_immediately_on_start', True)
    if run_immediately:
        logger.info("Running initial agent cycle immediately upon start...")
        scheduled_job() # Run the first cycle right away

    # Schedule the job
    schedule.every(schedule_interval_minutes).minutes.do(scheduled_job)
    logger.info("Scheduler started. Waiting for next cycle...")

    # --- Keep Running --- 
    while True:
        schedule.run_pending()
        time.sleep(1) # Check schedule every second

if __name__ == "__main__":
    main()
