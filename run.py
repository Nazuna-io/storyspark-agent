#!/usr/bin/env python3
"""
StorySpark Agent - Entry point script
"""
import os
import sys

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Import and run main - noqa: E402
from main import main  # noqa: E402

if __name__ == "__main__":
    main()
