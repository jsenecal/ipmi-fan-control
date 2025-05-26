#!/bin/bash
# Extract version from pyproject.toml

set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Extract version from pyproject.toml
version=$(grep '^version = ' "$PROJECT_ROOT/pyproject.toml" | sed 's/version = "\(.*\)"/\1/')

if [ -z "$version" ]; then
    echo "Error: Could not extract version from pyproject.toml" >&2
    exit 1
fi

echo "$version"