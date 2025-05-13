#!/bin/bash
# Fix all flake8 errors

# Fix unused imports in tests
sed -i "/^import pytest$/d" tests/integration/test_debug.py
sed -i "/^from unittest.mock import Mock$/d" tests/integration/test_debug.py
sed -i "/^from unittest.mock import patch$/d" tests/integration/test_debug.py
sed -i "/^import pytest$/d" tests/integration/test_debug2.py
sed -i "/^import pytest$/d" tests/integration/test_debug3.py
sed -i "/^import pytest$/d" tests/integration/test_debug4.py
sed -i "/^import pytest$/d" tests/integration/test_integration.py
sed -i "/^from unittest.mock import MagicMock$/d" tests/integration/test_integration.py
sed -i "/^from src.config_loader import load_config$/d" tests/integration/test_integration.py
sed -i "/^from src.story_seed_generator import generate_story_seed$/d" tests/integration/test_integration.py
sed -i "/^import pytest$/d" tests/test_simple.py
sed -i "/^import os$/d" tests/test_config_loader.py
sed -i "/^import os$/d" tests/test_config_loader_extended.py
sed -i "/^import os$/d" tests/test_data_fetcher.py
sed -i "/^from unittest.mock import MagicMock$/d" tests/test_data_fetcher.py
sed -i "/^from datetime import datetime$/d" tests/test_data_fetcher_extended.py
sed -i "/^from datetime import timezone$/d" tests/test_data_fetcher_extended.py
sed -i "/^import feedparser$/d" tests/test_data_fetcher_extended.py
sed -i "/^import pytest$/d" tests/test_data_fetcher_extended.py
sed -i "/^import os$/d" tests/test_logger_config.py
sed -i "/^import os$/d" tests/test_main.py
sed -i "/^from unittest.mock import MagicMock$/d" tests/test_main.py
sed -i "/^from unittest.mock import Mock$/d" tests/test_main.py
sed -i "/^import sys$/d" tests/test_main_extended.py
sed -i "/^from datetime import datetime$/d" tests/test_main_extended.py
sed -i "/^from datetime import timezone$/d" tests/test_main_extended.py
sed -i "/^from unittest.mock import Mock$/d" tests/test_main_extended.py
sed -i "/^import pytest$/d" tests/test_main_extended.py
sed -i "/^from unittest.mock import Mock$/d" tests/test_main_simple.py
sed -i "/^from unittest.mock import MagicMock$/d" tests/test_story_seed_generator.py

# Fix unused imports in src
sed -i "s/from datetime import datetime, timedelta$/from datetime import datetime/" src/trend_detector.py
sed -i "s/from typing import List, Dict, Set, Tuple, Any$/from typing import List, Dict, Set, Any/" src/trend_detector.py

# Fix module level imports not at top of file - add noqa comment
sed -i "s/^import pytest$/import pytest  # noqa: E402/" tests/integration/test_debug_simple.py
sed -i "12s/from main import main$/from main import main  # noqa: E402/" run.py

echo "Fixed flake8 issues"
