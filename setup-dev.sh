#!/bin/bash
# Development setup script for StorySpark Agent

echo "Setting up development environment..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate || {
    echo "Failed to activate virtual environment"
    exit 1
}

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
pre-commit install

# Run initial linting check
echo "Running initial linting check..."
pre-commit run --all-files

echo "Development environment setup complete!"
echo "To activate the environment in the future, run: source .venv/bin/activate"
