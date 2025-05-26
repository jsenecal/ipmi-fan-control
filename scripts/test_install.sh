#!/bin/bash
# Test the installation in a clean virtual environment

# Exit immediately if a command exits with a non-zero status
set -e

echo "🧪 Testing Dell IPMI Fan Control installation..."

# Create a clean test environment
echo "📦 Creating test virtual environment..."
python -m venv .venv_test

# Activate the environment
echo "🔄 Activating test environment..."
source .venv_test/bin/activate

# Install the package
echo "📦 Installing package..."
pip install -e .

# Test importing the package
echo "🔍 Testing package imports..."
python -c "
import ipmi_fan_control
from ipmi_fan_control import cli, ipmi, pid, types
print('✅ All imports successful!')
"

# Test the CLI command
echo "🔍 Testing CLI command availability..."
if command -v ipmi-fan &> /dev/null; then
    echo "✅ CLI command 'ipmi-fan' is available!"
    ipmi-fan --help
else
    echo "❌ CLI command 'ipmi-fan' not found!"
    exit 1
fi

# Clean up
deactivate
rm -rf .venv_test

echo "✅ Installation test completed successfully!"