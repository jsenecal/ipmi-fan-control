#!/bin/bash
# Run ruff linter on the project

# Don't exit immediately on error to provide better feedback
set +e

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

# Check if ruff is installed
if ! command -v ruff &> /dev/null; then
    echo "📦 Ruff is not installed. Installing now..."
    pip install ruff
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install ruff. Please check pip installation."
        deactivate
        exit 1
    fi
fi

echo "🔍 Running ruff linter..."
ruff check .

# Get exit code from linting
exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✅ Linting passed!"
else
    echo "❌ Linting failed with code $exit_code."
    echo "Run './lint.sh --fix' to automatically fix issues."
fi

# Check if --fix flag was passed
if [ "$1" == "--fix" ]; then
    echo "🔧 Attempting to fix linting issues..."
    ruff check --fix .
    fix_exit_code=$?
    if [ $fix_exit_code -eq 0 ]; then
        echo "✅ All fixable issues resolved!"
        exit_code=0
    else
        echo "⚠️ Some issues could not be fixed automatically. Exit code: $fix_exit_code"
    fi
fi

# Deactivate the virtual environment
deactivate

exit $exit_code