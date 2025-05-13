# StorySpark Agent

[![Version](https://img.shields.io/badge/version-0.8.0-blue.svg)](https://github.com/Nazuna-io/storyspark-agent/releases)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/Nazuna-io/storyspark-agent/actions/workflows/test.yml/badge.svg)](https://github.com/Nazuna-io/storyspark-agent/actions)
[![Coverage](https://img.shields.io/badge/coverage-88%25-brightgreen.svg)](https://codecov.io/gh/Nazuna-io/storyspark-agent)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

An AI-powered agent that monitors Reddit and RSS feeds for trending topics ("sparks") and generates story ideas using Google's Gemini AI.

> **⚠️ Beta Software**: This is version 0.8.0 - a beta release with limited functionality. See [Current Limitations](#current-limitations) below.

## Features

- 🔍 **Trend Detection**: Monitors multiple sources for emerging topics
- 🤖 **AI-Powered**: Uses Google Gemini to generate creative story ideas
- 📊 **Smart Filtering**: Identifies significant frequency spikes in keywords
- ⏰ **Scheduled Runs**: Automatically checks sources at configured intervals
- 📝 **Markdown Output**: Generates formatted story ideas with loglines, what-if questions, and themes

## Quick Start

1. **Clone the repository**:
   ```bash
   git clone git@github.com:Nazuna-io/storyspark-agent.git
   cd storyspark-agent
   ```

2. **Set up Python environment** (requires Python 3.10+):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure API key**:
   ```bash
   cp .env.example .env
   # Edit .env and add your Google Gemini API key
   ```

4. **Configure sources** (edit `config.yaml`):
   ```yaml
   sources:
     rss_feeds:
       - url: "https://example.com/feed.xml"
     subreddits:
       - name: "technology"
       - name: "science"
   ```

5. **Run the agent**:
   ```bash
   python run.py
   # Or directly:
   python src/main.py
   ```

## Configuration

The agent is configured via `config.yaml`:

- **sources**: RSS feeds and subreddits to monitor
- **trend_detection**: Parameters for identifying trending topics
- **generation**: Gemini API settings and prompt templates
- **logging**: Log levels and output files
- **agent**: Scheduling and runtime parameters

## How It Works

1. **Data Collection**: Fetches new posts from configured RSS feeds and Reddit
2. **Trend Analysis**: Compares keyword frequencies against historical data
3. **Spark Detection**: Identifies keywords with significant frequency spikes
4. **Story Generation**: Uses Gemini AI to create story ideas for each spark
5. **Output**: Saves results to markdown and JSON files

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### Linting and Code Quality

The project uses several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **Flake8**: Style guide enforcement
- **mypy**: Static type checking
- **Bandit**: Security linting

Run all linters:
```bash
pre-commit run --all-files
```

Or run individual tools:
```bash
black src/
isort src/
flake8 src/
mypy src/
bandit -r src/
```

### Running Tests

```bash
pytest -v --cov=src --cov-report=term-missing
```

Current test coverage: 83%

### Code Structure

```
src/
├── main.py              # Entry point and scheduler
├── data_fetcher.py      # RSS and Reddit data collection
├── trend_detector.py    # Keyword analysis and spark detection
├── story_seed_generator.py  # Gemini AI integration
├── config_loader.py     # Configuration management
└── logger_config.py     # Logging setup
```

### Security Considerations

- API keys are stored in environment variables
- All external API calls have error handling
- Rate limiting is respected for Reddit API

### Dependency Scanning

The project uses `pip-audit` for dependency vulnerability scanning:

```bash
pip-audit
```

### Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality:

```bash
# Install pre-commit
pip install pre-commit

# Set up the git hook scripts
pre-commit install

# Run against all files
pre-commit run --all-files
```

The pre-commit configuration includes:
- Code formatting (black)
- Import sorting (isort)
- Linting (flake8)
- Type checking (mypy)
- Security checks (bandit)

### Deployment

See the [Deployment Guide](DEPLOYMENT.md) for instructions on deploying the StorySpark Agent to production environments.

## Example Output

```markdown
## Spark: quantum (Source: r/science)

**Logline:**
A researcher discovers quantum entanglement can transmit consciousness between parallel universes.

**What If Questions:**
- What if you could share memories with your parallel self?
- What if quantum mechanics allowed true teleportation?
- What if consciousness exists in multiple dimensions?

**Thematic Keywords:**
- Parallel universes
- Quantum consciousness
- Identity paradox
```

## Current Limitations (v0.8.0)

This beta release has the following limitations:

- **Append-only file operations**: Data is only appended to files, not updated
- **CLI interface only**: No graphical user interface available
- **Google Gemini only**: Only supports Google's Gemini AI for story generation
- **Fixed scheduling**: Reports run hourly (not customizable)
- **No email notifications**: Output is saved to files only

## Roadmap

Planned features for future releases:

- [ ] Email report functionality
- [ ] Customizable report frequency
- [ ] PyPI package distribution
- [ ] Gradio web UI for browsing and searching sparks
- [ ] Multiple AI provider support (OpenAI, Anthropic, etc.)
- [ ] Database storage options
- [ ] RESTful API endpoints
- [ ] Docker containerization
- [ ] Real-time monitoring dashboard

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Uses Google Gemini for AI story generation
- Inspired by Reddit's trending algorithm
- Built with Python and modern async patterns
