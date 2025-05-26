#!/bin/bash
# Install script using UV

# Exit immediately if a command exits with a non-zero status
set -e

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV is not installed. Please install it first: https://github.com/astral-sh/uv"
    exit 1
fi

# Install dependencies and the package
echo "📦 Installing Dell IPMI Fan Control with UV..."
uv pip install -e .

if [ $? -eq 0 ]; then
    echo "✅ Installation complete! You can now use 'ipmi-fan' command."
else
    echo "❌ Installation failed. Please check the error messages above."
    exit 1
fi