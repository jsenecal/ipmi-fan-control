#!/bin/bash
# Run the test suite

# Exit immediately if a command exits with a non-zero status
set -e

# Create a virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv .venv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment. Please check your Python installation."
        exit 1
    fi
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo "❌ Failed to activate virtual environment."
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install --quiet -e ".[dev]" --break-system-packages || pip install --quiet -e ".[dev]"
pip install --quiet pytest pytest-cov pytest-mock --break-system-packages || pip install --quiet pytest pytest-cov pytest-mock

# Run the tests
echo "🧪 Running tests..."
pytest $@

# Show coverage report if the tests pass
if [ $? -eq 0 ]; then
    echo "📊 Generating coverage report..."
    pytest --cov=ipmi_fan_control tests/
fi

# Deactivate virtual environment
deactivate
echo "✅ Testing completed."