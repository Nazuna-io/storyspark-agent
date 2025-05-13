#!/usr/bin/env python3
"""
Fix all flake8 issues in the storyspark-agent project
"""
import os
import re


def fix_unused_imports(file_path, imports_to_remove):
    """Remove unused imports from a file"""
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "r") as f:
        content = f.read()

    for import_line in imports_to_remove:
        # Remove the import line
        pattern = f"^{re.escape(import_line)}$"
        content = re.sub(pattern, "", content, flags=re.MULTILINE)

    # Remove empty lines that were left behind
    content = re.sub(r"\n\n+", "\n\n", content)

    with open(file_path, "w") as f:
        f.write(content)

    print(f"Fixed imports in {file_path}")


def fix_module_import_at_top(file_path, line_pattern):
    """Add noqa comment to imports that need to be after sys.path modification"""
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "r") as f:
        content = f.read()

    # Add noqa comment to the specific import
    content = re.sub(line_pattern, r"\1  # noqa: E402", content)

    with open(file_path, "w") as f:
        f.write(content)

    print(f"Fixed module import in {file_path}")


def fix_long_lines(file_path):
    """Fix lines that are too long"""
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "r") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if len(line) > 120:
            # Handle specific long line patterns
            if "feedparser.parse" in line and "etag=None" in line:
                lines[
                    i
                ] = """        feed_data = feedparser.parse(
            feed_url, agent=USER_AGENT, request_headers=headers,
            etag=None, modified=None  # Disable etag/modified for simplicity in MVP
        )
"""
            # Add more specific patterns as needed

    with open(file_path, "w") as f:
        f.writelines(lines)

    print(f"Fixed long lines in {file_path}")


# Fix all the issues reported by flake8
fixes = {
    "tests/integration/test_debug.py": ["from unittest.mock import Mock, patch", "import pytest"],
    "tests/integration/test_debug2.py": ["import pytest"],
    "tests/integration/test_debug3.py": ["import pytest"],
    "tests/integration/test_debug4.py": ["import pytest"],
    "tests/integration/test_simple.py": ["import pytest"],
    "tests/test_config_loader.py": ["import os"],
    "tests/test_config_loader_extended.py": ["import os"],
    "tests/test_data_fetcher.py": ["import os", "from unittest.mock import MagicMock"],
    "tests/test_data_fetcher_extended.py": [
        "from datetime import datetime, timezone",
        "import feedparser",
        "import pytest",
    ],
    "tests/test_logger_config.py": ["import os"],
    "tests/test_main.py": ["import os", "from unittest.mock import MagicMock, Mock"],
    "tests/test_main_extended.py": [
        "import sys",
        "from datetime import datetime, timezone",
        "from unittest.mock import Mock",
        "import pytest",
    ],
    "tests/test_main_simple.py": ["from unittest.mock import Mock"],
    "tests/test_story_seed_generator.py": ["from unittest.mock import MagicMock"],
}

for file_path, imports in fixes.items():
    fix_unused_imports(file_path, imports)

# Fix module import at top issues
fix_module_import_at_top("run.py", r"(from main import main)$")
fix_module_import_at_top("tests/integration/test_debug_simple.py", r"(import pytest)$")

# Fix lines in src files
# Remove timedelta from trend_detector.py
with open("src/trend_detector.py", "r") as f:
    content = f.read()
content = content.replace("from datetime import datetime, timedelta", "from datetime import datetime")
content = content.replace("from typing import List, Dict, Set, Tuple, Any", "from typing import List, Dict, Set, Any")
with open("src/trend_detector.py", "w") as f:
    f.write(content)

print("All flake8 issues fixed!")
