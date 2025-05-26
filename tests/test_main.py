"""Tests for the main entry point."""

import importlib.util
import subprocess
import sys
from unittest.mock import patch


class TestMainEntryPoint:
    """Test the main entry point module."""

    def test_main_module_import(self):
        """Test that __main__.py can be imported without issues."""
        # Simply importing should work without calling app()
        import ipmi_fan_control.__main__
        
        # Should have the expected attributes
        assert hasattr(ipmi_fan_control.__main__, 'app')

    def test_main_module_direct_execution(self):
        """Test that __main__.py calls app() when executed directly."""
        # Mock the app function before any execution
        with patch('ipmi_fan_control.cli.app') as mock_app:
            # Load and execute the module as if it was run directly
            spec = importlib.util.spec_from_file_location(
                "__main__", 
                "/home/jsenecal/Code/ipmi-script/ipmi_fan_control/__main__.py"
            )
            main_module = importlib.util.module_from_spec(spec)
            
            # Set __name__ to "__main__" to trigger the execution block
            main_module.__name__ = "__main__"
            
            # Execute the module
            spec.loader.exec_module(main_module)
            
            # The app should be called when executed directly
            mock_app.assert_called_once()

    def test_python_m_execution(self):
        """Test that 'python -m ipmi_fan_control' works."""
        # This test actually runs the module to ensure it can be imported
        # and executed without errors (but we'll make it fail fast)
        result = subprocess.run(
            [sys.executable, '-m', 'ipmi_fan_control', '--help'],
            capture_output=True,
            check=False,
            text=True,
            timeout=10
        )
        
        # Should exit with 0 and show help text
        assert result.returncode == 0
        assert 'Usage:' in result.stdout or 'Commands:' in result.stdout