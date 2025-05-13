"""Setup script for StorySpark Agent."""
import os

from setuptools import find_packages, setup

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="storyspark-agent",
    version="0.8.0",
    author="Nazuna-io",
    description="AI-powered agent that monitors Reddit and RSS feeds for trending topics and generates story ideas",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Nazuna-io/storyspark-agent",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=[
        "feedparser>=6.0.0",
        "requests>=2.31.0",
        "google-generativeai>=0.8.0",
        "schedule>=1.2.0",
        "pyyaml>=6.0",
        "python-dotenv",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.4",
            "pytest-cov>=4.1.0",
            "pytest-timeout>=2.2.0",
            "black>=23.1.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.1",
            "bandit>=1.7.4",
            "pre-commit>=3.6.0",
            "types-requests>=2.31.0",
            "types-PyYAML>=6.0.12",
        ]
    },
    entry_points={
        "console_scripts": [
            "storyspark=src.main:main",
            "storyspark-agent=src.main:main",
        ],
    },
)
