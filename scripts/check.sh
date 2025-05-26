#!/bin/bash
# Create a temporary virtual environment and run ruff

# Exit immediately if a command exits with a non-zero status
set -e

# Create temporary venv
echo "📦 Creating temporary virtual environment..."
python -m venv .venv_temp || {
    echo "❌ Failed to create virtual environment"
    exit 1
}

# Activate venv
echo "🔄 Activating virtual environment..."
source .venv_temp/bin/activate || {
    echo "❌ Failed to activate virtual environment"
    rm -rf .venv_temp
    exit 1
}

# Install ruff
echo "📦 Installing ruff..."
pip install ruff || {
    echo "❌ Failed to install ruff"
    deactivate
    rm -rf .venv_temp
    exit 1
}

# Run linter
echo "🔍 Running ruff linter..."
ruff check .
RESULT=$?

# Cleanup
deactivate
rm -rf .venv_temp
echo "🧹 Temporary environment cleanup complete."

# Return the ruff exit code
if [ $RESULT -eq 0 ]; then
    echo "✅ No linting issues found!"
else
    echo "❌ Linting issues found. See above for details."
fi

exit $RESULT