# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0] - 2025-05-13

### Added
- Initial beta release of StorySpark Agent
- Command-line interface for running the agent
- RSS feed monitoring for trending topics
- Reddit subreddit monitoring (r/futurology)
- Trend detection algorithm to identify "sparks" (trending keywords)
- Story idea generation using Google Gemini AI
- Markdown output file with generated story ideas
- JSON storage for history and generated seeds
- Comprehensive test suite with 88% code coverage
- CI/CD pipeline with GitHub Actions
- Pre-commit hooks for code quality
- Logging system with configurable levels

### Current Limitations
- File operations are append-only
- CLI interface only (no GUI)
- Google Gemini is the only supported AI provider
- Fixed report frequency (hourly)
- No email notifications

### Planned Features (To-Do)
- Email report functionality
- Customizable report frequency
- PyPI package distribution
- Gradio UI for browsing and searching sparks
- Multiple AI provider support
- Database storage option
- Web API endpoints
- Docker containerization

## [Unreleased]
- Work in progress features will be documented here
