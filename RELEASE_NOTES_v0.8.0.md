# Release Notes for v0.8.0

## 🎉 Beta Release v0.8.0

This is the first public beta release of StorySpark Agent, an AI-powered tool that monitors Reddit and RSS feeds for trending topics and generates story ideas using Google's Gemini AI.

### ✨ Features

- **CLI-based monitoring agent**: Runs from the command line with configurable options
- **Multi-source data collection**: Monitors RSS feeds and Reddit subreddits
- **Smart trend detection**: Identifies "sparks" (trending keywords) using frequency analysis
- **AI-powered story generation**: Creates story ideas with loglines, what-if questions, and themes
- **Flexible output formats**: Saves results as both Markdown and JSON
- **Configurable logging**: Multiple log levels for debugging and monitoring
- **Robust error handling**: Gracefully handles API failures and network issues
- **Comprehensive test suite**: 145 tests with 88% code coverage
- **CI/CD pipeline**: Automated testing with GitHub Actions

### 📋 Current Limitations

This beta release has the following limitations:

- **Append-only file operations**: Data is only appended to files, not updated
- **CLI interface only**: No graphical user interface available
- **Google Gemini only**: Only supports Google's Gemini AI for story generation
- **Fixed scheduling**: Reports run hourly (not customizable)
- **No email notifications**: Output is saved to files only

### 🔧 Installation

```bash
# Clone the repository
git clone https://github.com/Nazuna-io/storyspark-agent.git
cd storyspark-agent

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up configuration
cp .env.example .env
# Add your Google Gemini API key to .env
```

### 🚀 Usage

```bash
# Run the agent
python src/main.py

# Or use the command after installing
storyspark-agent
```

### 🗺️ Roadmap

Planned features for future releases:

- Email report functionality
- Customizable report frequency
- PyPI package distribution
- Gradio web UI for browsing and searching sparks
- Multiple AI provider support (OpenAI, Anthropic, etc.)
- Database storage options
- RESTful API endpoints
- Docker containerization

### 🐛 Known Issues

- Google Gemini API sometimes has rate limiting issues
- Some RSS feeds with non-standard formats may not parse correctly

### 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](https://github.com/Nazuna-io/storyspark-agent/blob/main/README.md#contributing) for details.

### 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/Nazuna-io/storyspark-agent/blob/main/LICENSE) file for details.

### 🙏 Acknowledgments

- Thanks to the Google Gemini team for the AI API
- Built with Python and modern async patterns
- Inspired by Reddit's trending algorithm
