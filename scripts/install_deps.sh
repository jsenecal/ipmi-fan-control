#!/bin/bash
# Install dependencies for IPMI Fan Control

# Exit immediately if a command exits with a non-zero status
set -e

echo "📦 Installing dependencies for IPMI Fan Control..."

# Create virtual environment if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install typer rich python-ipmi pyyaml

# Check if ipmitool is installed
if ! command -v ipmitool &> /dev/null; then
    echo "⚠️ ipmitool is not installed."
    echo "The tool will work better with ipmitool installed."
    echo "To install ipmitool:"
    echo "  Debian/Ubuntu: sudo apt install ipmitool"
    echo "  RHEL/CentOS/Fedora: sudo dnf install ipmitool"
    echo "  Arch Linux: sudo pacman -S ipmitool"
else
    echo "✅ ipmitool is already installed."
fi

# Install the package in development mode
echo "Installing IPMI Fan Control..."
pip install -e .

echo "✅ Installation complete!"
echo ""
echo "To use the tool, activate the virtual environment first:"
echo "  source .venv/bin/activate"
echo ""
echo "Then run the tool:"
echo "  ipmi-fan --help"