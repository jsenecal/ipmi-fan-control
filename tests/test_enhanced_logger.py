"""Tests for the enhanced logger module."""

import logging
from unittest.mock import patch, MagicMock

import pytest

from ipmi_fan_control.enhanced_logger import EnhancedLogger, logger


class TestEnhancedLogger:
    """Test the EnhancedLogger class."""

    def test_initialization_default(self):
        """Test logger initialization with default parameters."""
        test_logger = EnhancedLogger()
        
        assert test_logger.logger.name == "ipmi-fan-control"
        assert test_logger.logger.level == logging.INFO
        assert test_logger.console is not None

    def test_initialization_custom(self):
        """Test logger initialization with custom parameters."""
        test_logger = EnhancedLogger(name="test-logger", level=logging.DEBUG)
        
        assert test_logger.logger.name == "test-logger"
        assert test_logger.logger.level == logging.DEBUG

    def test_handler_setup(self):
        """Test that Rich handler is properly set up."""
        test_logger = EnhancedLogger()
        
        # Should have exactly one handler (Rich handler)
        assert len(test_logger.logger.handlers) == 1
        
        # Handler should be RichHandler
        from rich.logging import RichHandler
        assert isinstance(test_logger.logger.handlers[0], RichHandler)

    def test_debug_logging(self):
        """Test debug message logging."""
        test_logger = EnhancedLogger()
        
        with patch.object(test_logger.logger, 'debug') as mock_debug:
            test_logger.debug("Test debug message")
            mock_debug.assert_called_once_with("[dim cyan]🔍 Test debug message[/dim cyan]")

    def test_info_logging(self):
        """Test info message logging."""
        test_logger = EnhancedLogger()
        
        with patch.object(test_logger.logger, 'info') as mock_info:
            test_logger.info("Test info message")
            mock_info.assert_called_once_with("[white]Test info message[/white]")

    def test_success_logging(self):
        """Test success message logging."""
        test_logger = EnhancedLogger()
        
        with patch.object(test_logger.logger, 'info') as mock_info:
            test_logger.success("Test success message")
            mock_info.assert_called_once_with("[green]✓ Test success message[/green]")

    def test_warning_logging(self):
        """Test warning message logging."""
        test_logger = EnhancedLogger()
        
        with patch.object(test_logger.logger, 'warning') as mock_warning:
            test_logger.warning("Test warning message")
            mock_warning.assert_called_once_with("[yellow]⚠ Test warning message[/yellow]")

    def test_error_logging(self):
        """Test error message logging."""
        test_logger = EnhancedLogger()
        
        with patch.object(test_logger.logger, 'error') as mock_error:
            test_logger.error("Test error message")
            mock_error.assert_called_once_with("[red]✗ Test error message[/red]")

    def test_critical_logging(self):
        """Test critical message logging."""
        test_logger = EnhancedLogger()
        
        with patch.object(test_logger.logger, 'critical') as mock_critical:
            test_logger.critical("Test critical message")
            mock_critical.assert_called_once_with("[bold red]✗ Test critical message[/bold red]")

    def test_status_logging(self):
        """Test status message logging."""
        test_logger = EnhancedLogger()
        
        with patch.object(test_logger.logger, 'info') as mock_info:
            test_logger.status("Test status message")
            mock_info.assert_called_once_with("[cyan]→ Test status message[/cyan]")

    def test_section_header(self):
        """Test section header printing."""
        test_logger = EnhancedLogger()
        
        with patch.object(test_logger.logger, 'info') as mock_info:
            test_logger.section_header("Test Section")
            mock_info.assert_called_once_with("\n[bold cyan]═══ Test Section ═══[/bold cyan]")

    def test_print_fan_data_empty(self):
        """Test printing fan data with empty list."""
        test_logger = EnhancedLogger()
        
        with patch.object(test_logger, 'warning') as mock_warning:
            test_logger.print_fan_data([])
            mock_warning.assert_called_once_with("No fans detected in this system")

    def test_print_fan_data_with_fans(self):
        """Test printing fan data with actual fan data."""
        test_logger = EnhancedLogger()
        
        fans = [
            {
                'id': 'Fan1',
                'name': 'System Fan 1',
                'current_speed': 1500,
                'unit': 'RPM',
                'status': 'OK'
            },
            {
                'id': 'Fan2',
                'name': 'System Fan 2',
                'current_speed': 3500,
                'unit': 'RPM',
                'status': 'Warning'
            },
            {
                'id': 'Fan3',
                'name': 'System Fan 3',
                'current_speed': 5000,
                'unit': 'RPM',
                'status': 'Error'
            }
        ]
        
        with patch.object(test_logger.logger, 'info') as mock_info:
            test_logger.print_fan_data(fans)
            
            # Should call info multiple times (header + each fan)
            assert mock_info.call_count >= 4  # 1 header + 3 fans

    def test_print_fan_data_speed_colors(self):
        """Test fan speed color coding."""
        test_logger = EnhancedLogger()
        
        # Test low speed (green)
        fan_low = {
            'id': 'Fan1', 'name': 'Test Fan', 'current_speed': 1000,
            'unit': 'RPM', 'status': 'OK'
        }
        
        with patch.object(test_logger.logger, 'info') as mock_info:
            test_logger.print_fan_data([fan_low])
            # Should contain green color tag for low speed
            assert any('[green]1000[/green]' in str(call) for call in mock_info.call_args_list)

    def test_print_fan_data_non_numeric_speed(self):
        """Test fan data with non-numeric speed."""
        test_logger = EnhancedLogger()
        
        fan = {
            'id': 'Fan1', 'name': 'Test Fan', 'current_speed': 'N/A',
            'unit': 'RPM', 'status': 'OK'
        }
        
        with patch.object(test_logger.logger, 'info') as mock_info:
            test_logger.print_fan_data([fan])
            # Should handle non-numeric speed gracefully
            assert mock_info.called

    def test_print_temperature_data_empty(self):
        """Test printing temperature data with empty list."""
        test_logger = EnhancedLogger()
        
        with patch.object(test_logger, 'warning') as mock_warning:
            test_logger.print_temperature_data([])
            mock_warning.assert_called_once_with("No temperature sensors detected")

    def test_print_temperature_data_with_temps(self):
        """Test printing temperature data with actual temperature data."""
        test_logger = EnhancedLogger()
        
        temps = [
            {
                'id': 'Temp1',
                'name': 'CPU Temperature',
                'current_temp': 35,
                'unit': '°C',
                'status': 'OK'
            },
            {
                'id': 'Temp2',
                'name': 'System Temperature',
                'current_temp': 55,
                'unit': '°C',
                'status': 'Warning'
            },
            {
                'id': 'Temp3',
                'name': 'Hot Temperature',
                'current_temp': 85,
                'unit': '°C',
                'status': 'Critical'
            }
        ]
        
        with patch.object(test_logger.logger, 'info') as mock_info:
            test_logger.print_temperature_data(temps)
            
            # Should call info multiple times (header + each temp)
            assert mock_info.call_count >= 4  # 1 header + 3 temperatures

    def test_print_temperature_data_color_coding(self):
        """Test temperature color coding based on values."""
        test_logger = EnhancedLogger()
        
        # Test different temperature ranges
        temps = [
            {'id': 'T1', 'name': 'Cool', 'current_temp': 30, 'unit': '°C', 'status': 'OK'},    # green
            {'id': 'T2', 'name': 'Warm', 'current_temp': 50, 'unit': '°C', 'status': 'OK'},   # yellow
            {'id': 'T3', 'name': 'Hot', 'current_temp': 70, 'unit': '°C', 'status': 'OK'},    # magenta
            {'id': 'T4', 'name': 'Very Hot', 'current_temp': 90, 'unit': '°C', 'status': 'OK'} # red
        ]
        
        with patch.object(test_logger.logger, 'info') as mock_info:
            test_logger.print_temperature_data(temps)
            
            call_args_str = str(mock_info.call_args_list)
            # Should contain different color tags for different temperatures
            assert '[green]30[/green]' in call_args_str
            assert '[yellow]50[/yellow]' in call_args_str
            assert '[magenta]70[/magenta]' in call_args_str
            assert '[red]90[/red]' in call_args_str

    def test_print_temperature_data_non_numeric(self):
        """Test temperature data with non-numeric temperature."""
        test_logger = EnhancedLogger()
        
        temp = {
            'id': 'Temp1', 'name': 'Test Temp', 'current_temp': 'N/A',
            'unit': '°C', 'status': 'OK'
        }
        
        with patch.object(test_logger.logger, 'info') as mock_info:
            test_logger.print_temperature_data([temp])
            # Should handle non-numeric temperature gracefully
            assert mock_info.called

    def test_print_pid_status(self):
        """Test PID status printing."""
        test_logger = EnhancedLogger()
        
        status = {
            'temperature': 45.5,
            'target': 50.0,
            'fan_speed': 65
        }
        
        with patch('time.strftime', return_value='12:34:56'):
            with patch.object(test_logger.logger, 'info') as mock_info:
                test_logger.print_pid_status(status)
                
                mock_info.assert_called_once()
                call_args = str(mock_info.call_args)
                
                # Should contain timestamp and all values
                assert '12:34:56' in call_args
                assert '45.5°C' in call_args
                assert '50.0°C' in call_args
                assert '65%' in call_args
                assert '-4.5°C' in call_args  # error calculation

    def test_print_pid_status_color_coding(self):
        """Test PID status color coding."""
        test_logger = EnhancedLogger()
        
        # Test close to target (should be green)
        status_close = {
            'temperature': 49.5,
            'target': 50.0,
            'fan_speed': 30
        }
        
        with patch('time.strftime', return_value='12:34:56'):
            with patch.object(test_logger.logger, 'info') as mock_info:
                test_logger.print_pid_status(status_close)
                
                call_args_str = str(mock_info.call_args)
                # Temperature should be green when close to target
                assert '[green]49.5°C[/green]' in call_args_str
                # Fan speed should be green when low
                assert '[green]30%[/green]' in call_args_str

    def test_print_troubleshooting_tips(self):
        """Test troubleshooting tips printing."""
        test_logger = EnhancedLogger()
        
        with patch.object(test_logger.logger, 'info') as mock_info:
            test_logger.print_troubleshooting_tips()
            
            # Should call info multiple times (header + tips)
            assert mock_info.call_count >= 7  # 1 header + 6 tips
            
            # Check that tips are properly formatted
            call_args_list = [str(call) for call in mock_info.call_args_list]
            tip_calls = [call for call in call_args_list if '[yellow]' in call and '.[/yellow]' in call]
            assert len(tip_calls) == 6  # Should have 6 numbered tips

    def test_global_logger_instance(self):
        """Test that global logger instance is properly created."""
        from ipmi_fan_control.enhanced_logger import logger
        
        assert isinstance(logger, EnhancedLogger)
        assert logger.logger.name == "ipmi-fan-control"