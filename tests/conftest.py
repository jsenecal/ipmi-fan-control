"""Shared fixtures and configuration for pytest."""

import os
import sys

import pytest

# Add the project root to the path to make imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(autouse=True)
def mock_shutil_which():
    """Mock shutil.which to always find ipmitool for testing."""
    import shutil
    
    original_which = shutil.which
    
    def mock_which(cmd, *args, **kwargs):
        if cmd == "ipmitool":
            return "/usr/bin/ipmitool"
        return original_which(cmd, *args, **kwargs)
    
    shutil.which = mock_which
    yield
    shutil.which = original_which