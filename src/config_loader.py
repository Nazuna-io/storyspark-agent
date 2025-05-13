# src/config_loader.py
import logging
import os
from typing import Any, Dict

import yaml

logger = logging.getLogger(__name__)


def load_config(path: str = "config.yaml") -> Dict[str, Any]:
    """Loads the configuration from a YAML file and performs basic validation."""
    if not os.path.exists(path):
        logger.error(f"Configuration file not found at '{path}'")
        raise FileNotFoundError(f"Configuration file not found at '{path}'")

    try:
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        logger.info(f"Configuration loaded successfully from '{path}'")

        # Basic validation
        if not config:
            logger.error(f"Config file '{path}' is empty or invalid YAML.")
            raise ValueError(f"Config file '{path}' is empty or invalid.")

        # Ensure top-level keys exist
        required_keys = ["sources", "trend_detection", "generation", "logging", "agent"]
        for key in required_keys:
            if key not in config:
                logger.error(f"Missing required configuration section: '{key}' in '{path}'")
                raise ValueError(f"Missing required configuration section: '{key}'")

        # Validate sources structure and provide defaults
        config["sources"] = config.get("sources", {})
        if not isinstance(config["sources"], dict):
            raise ValueError("Config 'sources' section must be a dictionary.")
        config["sources"].setdefault("rss_feeds", [])
        config["sources"].setdefault("subreddits", [])
        if not isinstance(config["sources"]["rss_feeds"], list):
            raise ValueError("Config 'sources.rss_feeds' must be a list.")
        if not isinstance(config["sources"]["subreddits"], list):
            raise ValueError("Config 'sources.subreddits' must be a list.")

        # Ensure nested dictionaries exist and provide defaults
        config.setdefault("trend_detection", {})
        config.setdefault("generation", {})
        config.setdefault("logging", {})
        config.setdefault("agent", {})

        if not isinstance(config["trend_detection"], dict):
            raise ValueError("'trend_detection' must be a dictionary.")
        if not isinstance(config["generation"], dict):
            raise ValueError("'generation' must be a dictionary.")
        if not isinstance(config["logging"], dict):
            raise ValueError("'logging' must be a dictionary.")
        if not isinstance(config["agent"], dict):
            raise ValueError("'agent' must be a dictionary.")

        # Validate specific required sub-keys and types
        # Removed check for logging.output_file as log_file is used
        # if not config['logging'].get('output_file') or not isinstance(config['logging']['output_file'], str):
        #      raise ValueError("Missing or invalid 'logging.output_file' (string) in configuration.")
        if not config["logging"].get("log_file") or not isinstance(config["logging"]["log_file"], str):
            raise ValueError("Missing or invalid 'logging.log_file' (string) in configuration.")
        if not config["agent"].get("schedule_interval_minutes") or not isinstance(
            config["agent"]["schedule_interval_minutes"], int
        ):
            raise ValueError("Missing or invalid 'agent.schedule_interval_minutes' (integer) in configuration.")
        if not config["generation"].get("prompt_template") or not isinstance(
            config["generation"]["prompt_template"], str
        ):
            raise ValueError("Missing or invalid 'generation.prompt_template' (string) in configuration.")
        if not config["trend_detection"].get("history_window_days") or not isinstance(
            config["trend_detection"]["history_window_days"], int
        ):
            raise ValueError("Missing or invalid 'trend_detection.history_window_days' (integer) in configuration.")
        # Corrected check for stopwords: ensure key exists and value is a list
        if "stopwords" not in config["trend_detection"] or not isinstance(config["trend_detection"]["stopwords"], list):
            raise ValueError("Missing or invalid 'trend_detection.stopwords' (list) in configuration.")

        logger.info("Configuration validated successfully.")

        return config
    except FileNotFoundError:
        # Already logged, just re-raise
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing configuration file '{path}': {e}")
        raise
    except ValueError:
        # Validation errors, already logged, re-raise
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading config from '{path}': {e}", exc_info=True)
        raise
