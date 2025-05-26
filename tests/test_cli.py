"""Integration tests for the CLI interface."""

import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

# Import the CLI
from ipmi_fan_control.cli import OutputFormat, app

# Import the controller
from ipmi_fan_control.ipmitool import DellIPMIToolFanController


@pytest.fixture
def mock_controller():
    """Create a mock IPMI controller for testing."""
    controller = MagicMock(spec=DellIPMIToolFanController)
    controller.test_connection.return_value = True
    controller.get_fan_speeds.return_value = [
        {
            "id": "33h", 
            "name": "System Fan 1", 
            "current_speed": 3240, 
            "unit": "RPM", 
            "status": "ok"
        },
        {
            "id": "34h", 
            "name": "System Fan 2", 
            "current_speed": 3120, 
            "unit": "RPM", 
            "status": "ok"
        }
    ]
    controller.get_temperature_sensors.return_value = [
        {
            "id": "04h", 
            "name": "Inlet Temp", 
            "current_temp": 22, 
            "unit": "degrees C", 
            "status": "ok"
        },
        {
            "id": "05h", 
            "name": "CPU Temp", 
            "current_temp": 45, 
            "unit": "degrees C", 
            "status": "ok"
        }
    ]
    controller.get_highest_temperature.return_value = 45.0
    return controller


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing Typer CLI."""
    return CliRunner()


class TestCLI:
    """Integration tests for the CLI interface."""

    @patch('ipmi_fan_control.cli.IPMIController')
    def test_status_command_table_output(self, mock_controller_class, cli_runner, mock_controller):
        """Test the status command with table output format."""
        mock_controller_class.return_value = mock_controller
        
        # Run the CLI status command
        result = cli_runner.invoke(app, ["status"])
        
        # Verify CLI called the controller correctly
        assert result.exit_code == 0
        mock_controller.test_connection.assert_called()
        mock_controller.get_fan_speeds.assert_called()
        
        # Check that output contains fan information
        assert "System Fan 1" in result.stdout
        assert "3240" in result.stdout
        assert "RPM" in result.stdout

    @patch('ipmi_fan_control.cli.IPMIController')
    def test_status_command_json_output(self, mock_controller_class, cli_runner, mock_controller):
        """Test the status command with JSON output format."""
        mock_controller_class.return_value = mock_controller
        
        # Run the CLI status command with JSON output
        with patch('ipmi_fan_control.cli.print') as mock_print:
            result = cli_runner.invoke(app, ["--output", "json", "status"])
            
            # Check that output is JSON and contains fan data
            assert result.exit_code == 0
            
            # Get the JSON string passed to print
            call_args = mock_print.call_args[0][0]
            data = json.loads(call_args)
            
            assert "fans" in data
            assert len(data["fans"]) == 2
            assert data["fans"][0]["name"] == "System Fan 1"
            assert data["fans"][0]["speed"] == 3240
            assert data["fans"][0]["unit"] == "RPM"

    @patch('ipmi_fan_control.cli.IPMIController')
    def test_temp_command(self, mock_controller_class, cli_runner, mock_controller):
        """Test the temp command."""
        mock_controller_class.return_value = mock_controller
        
        # Run the CLI temp command
        result = cli_runner.invoke(app, ["temp"])
        
        # Verify CLI called the controller correctly
        assert result.exit_code == 0
        mock_controller.test_connection.assert_called()
        mock_controller.get_temperature_sensors.assert_called()
        
        # Check that output contains temperature information
        assert "Inlet Temp" in result.stdout
        assert "CPU Temp" in result.stdout
        assert "45" in result.stdout
        assert "degrees C" in result.stdout

    @patch('ipmi_fan_control.cli.IPMIController')
    def test_set_command(self, mock_controller_class, cli_runner, mock_controller):
        """Test the set command."""
        mock_controller_class.return_value = mock_controller
        
        # Run the CLI set command
        result = cli_runner.invoke(app, ["set", "50"])
        
        # Verify CLI called the controller correctly
        assert result.exit_code == 0
        mock_controller.test_connection.assert_called()
        mock_controller.set_fan_speed.assert_called_with(50)
        
        # Check that output shows success
        assert "Fan speed set to 50%" in result.stdout

    @patch('ipmi_fan_control.cli.IPMIController')
    def test_auto_command(self, mock_controller_class, cli_runner, mock_controller):
        """Test the auto command."""
        mock_controller_class.return_value = mock_controller
        
        # Run the CLI auto command
        result = cli_runner.invoke(app, ["auto"])
        
        # Verify CLI called the controller correctly
        assert result.exit_code == 0
        mock_controller.test_connection.assert_called()
        mock_controller.set_automatic_control.assert_called()
        
        # Check that output shows success
        assert "Automatic fan control enabled" in result.stdout

    @patch('ipmi_fan_control.cli.IPMIController')
    def test_error_handling(self, mock_controller_class, cli_runner, mock_controller):
        """Test error handling in the CLI."""
        mock_controller_class.return_value = mock_controller
        
        # Make the controller method raise an exception
        mock_controller.get_fan_speeds.side_effect = RuntimeError("Test error")
        
        # Run the CLI status command
        result = cli_runner.invoke(app, ["status"])
        
        # Verify error is shown in output
        assert result.exit_code == 1  # Error exit code
        assert "Error reading fan status: Test error" in result.stdout
        
        # Check that troubleshooting tips are shown
        assert "Troubleshooting Tips" in result.stdout

    @patch('ipmi_fan_control.cli.IPMIController')
    @patch('ipmi_fan_control.cli.time')
    def test_pid_command(self, mock_time, mock_controller_class, cli_runner, mock_controller):
        """Test the PID command with a quick runtime."""
        mock_controller_class.return_value = mock_controller
        
        # Run the CLI PID command with a 1-second runtime to avoid hanging
        result = cli_runner.invoke(app, ["pid", "--time", "1"])
        
        # Verify CLI called the controller correctly
        mock_controller.test_connection.assert_called()
        mock_controller.configure_pid.assert_called()
        mock_controller.set_target_temperature.assert_called()
        mock_controller.set_monitor_interval.assert_called()
        mock_controller.start_temperature_monitoring.assert_called()
        
        # Should show successful completion
        assert "PID temperature control stopped" in result.stdout

    @patch('ipmi_fan_control.cli.IPMIController')
    def test_yaml_output_format(self, mock_controller_class, cli_runner, mock_controller):
        """Test YAML output format."""
        mock_controller_class.return_value = mock_controller
        
        with patch('ipmi_fan_control.cli.print') as mock_print:
            result = cli_runner.invoke(app, ["--output", "yaml", "status"])
            
            assert result.exit_code == 0
            call_args = mock_print.call_args[0][0]
            
            # YAML should contain fan information
            assert "fans:" in call_args
            assert "name: System Fan 1" in call_args
            assert "speed: 3240" in call_args

    @patch('ipmi_fan_control.cli.IPMIController')
    def test_connection_error(self, mock_controller_class, cli_runner, mock_controller):
        """Test connection error handling."""
        mock_controller_class.return_value = mock_controller
        mock_controller.test_connection.side_effect = RuntimeError("Connection failed")
        
        result = cli_runner.invoke(app, ["status"])
        
        assert result.exit_code == 1
        assert "Error reading fan status: Connection failed" in result.stdout

    @patch('ipmi_fan_control.cli.IPMIController')
    def test_set_command_invalid_speed(self, mock_controller_class, cli_runner, mock_controller):
        """Test set command with invalid speed values."""
        mock_controller_class.return_value = mock_controller
        
        # Test speed too high
        result = cli_runner.invoke(app, ["set", "150"])
        assert result.exit_code == 2  # Typer validation error
        
        # Test negative speed
        result = cli_runner.invoke(app, ["set", "-10"])
        assert result.exit_code == 2  # Typer validation error

    def test_cleanup_functions(self):
        """Test cleanup and setup functions."""
        from ipmi_fan_control.cli import cleanup_and_restore, setup_cleanup
        
        # Mock controller
        mock_controller = MagicMock()
        
        # Test setup cleanup with auto_restore=True
        with patch('ipmi_fan_control.cli.atexit.register') as mock_atexit:
            with patch('ipmi_fan_control.cli.signal.signal') as mock_signal:
                setup_cleanup(mock_controller, auto_restore=True)
                
                # Should register cleanup function
                mock_atexit.assert_called_once()
                
                # Should register signal handlers
                assert mock_signal.call_count == 2

        # Test setup cleanup with auto_restore=False
        with patch('ipmi_fan_control.cli.atexit.register') as mock_atexit:
            setup_cleanup(mock_controller, auto_restore=False)
            
            # Should not register cleanup
            mock_atexit.assert_not_called()

        # Test cleanup function with successful restore
        with patch('ipmi_fan_control.cli._controller', mock_controller):
            with patch('ipmi_fan_control.cli._auto_restore', True):
                cleanup_and_restore()
                mock_controller.set_automatic_control.assert_called_once()

        # Test cleanup function with controller exception
        mock_controller.set_automatic_control.side_effect = RuntimeError("Test error")
        with patch('ipmi_fan_control.cli._controller', mock_controller):
            with patch('ipmi_fan_control.cli._auto_restore', True):
                with patch('ipmi_fan_control.cli.logger.warning') as mock_warning:
                    cleanup_and_restore()
                    mock_warning.assert_called()

    @patch('ipmi_fan_control.cli.IPMIController')
    def test_temp_command_json_output(self, mock_controller_class, cli_runner, mock_controller):
        """Test temp command with JSON output."""
        mock_controller_class.return_value = mock_controller
        
        with patch('ipmi_fan_control.cli.print') as mock_print:
            result = cli_runner.invoke(app, ["--output", "json", "temp"])
            
            assert result.exit_code == 0
            call_args = mock_print.call_args[0][0]
            data = json.loads(call_args)
            
            assert "temperatures" in data
            assert len(data["temperatures"]) == 2
            assert data["temperatures"][0]["name"] == "Inlet Temp"

    @patch('ipmi_fan_control.cli.IPMIController')
    def test_connect_controller_helper(self, mock_controller_class, cli_runner, mock_controller):
        """Test the connect_controller helper function."""
        from ipmi_fan_control.cli import connect_controller
        
        mock_controller_class.return_value = mock_controller
        
        # Test successful connection
        controller = mock_controller_class()
        connect_controller(controller, OutputFormat.TABLE)
        mock_controller.test_connection.assert_called_once()

    @patch('ipmi_fan_control.cli.IPMIController')
    @patch('ipmi_fan_control.cli.shutil.which')
    def test_ipmitool_detection(self, mock_which, mock_controller_class, cli_runner):
        """Test ipmitool detection logic."""
        # This test ensures the import logic is covered
        mock_which.return_value = "/usr/bin/ipmitool"
        
        # Re-import the module to trigger detection logic
        import importlib

        import ipmi_fan_control.cli
        importlib.reload(ipmi_fan_control.cli)
        
        # Should have detected ipmitool
        mock_which.assert_called()

    @patch('ipmi_fan_control.cli.IPMIController')
    def test_signal_handler(self, mock_controller_class, cli_runner, mock_controller):
        """Test signal handler functionality."""
        import signal

        from ipmi_fan_control.cli import setup_cleanup
        
        mock_controller_class.return_value = mock_controller
        
        with patch('ipmi_fan_control.cli.cleanup_and_restore') as mock_cleanup:
            with patch('sys.exit') as mock_exit:
                # Set up signal handlers
                setup_cleanup(mock_controller, auto_restore=True)
                
                # Trigger signal handler
                handler_func = None
                with patch('ipmi_fan_control.cli.signal.signal') as mock_signal:
                    setup_cleanup(mock_controller, auto_restore=True)
                    # Get the signal handler function from the call
                    calls = mock_signal.call_args_list
                    if calls:
                        handler_func = calls[0][0][1]
                
                if handler_func:
                    # Call the signal handler
                    handler_func(signal.SIGINT, None)
                    mock_cleanup.assert_called()
                    mock_exit.assert_called_with(0)