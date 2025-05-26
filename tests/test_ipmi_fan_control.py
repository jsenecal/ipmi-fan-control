"""Tests for the IPMI fan control module."""

import unittest
from unittest.mock import Mock, patch

from ipmi_fan_control.ipmi import DellIPMIFanController


class TestDellIPMIFanController(unittest.TestCase):
    """Test the Dell IPMI fan controller."""

    @patch('pyipmi.create_connection')
    @patch('pyipmi.interfaces.create_interface')
    def setUp(self, mock_create_interface, mock_create_connection):
        """Set up the test environment."""
        self.mock_interface = Mock()
        self.mock_ipmi = Mock()
        
        mock_create_interface.return_value = self.mock_interface
        mock_create_connection.return_value = self.mock_ipmi
        
        self.mock_ipmi.session = Mock()
        self.mock_ipmi.session.set_session_type_rmcp = Mock()
        self.mock_ipmi.session.set_auth_type_user = Mock()
        
        self.controller = DellIPMIFanController(
            host="192.168.1.100",
            username="test",
            password="test"
        )

    def test_connect(self):
        """Test connecting to the IPMI interface."""
        self.controller.connect()
        
        self.mock_ipmi.session.set_session_type_rmcp.assert_called_once_with(
            "192.168.1.100", port=623
        )
        self.mock_ipmi.session.set_auth_type_user.assert_called_once_with(
            "test", "test"
        )
        self.assertTrue(self.controller.connected)

    def test_disconnect(self):
        """Test disconnecting from the IPMI interface."""
        self.controller.connected = True
        self.controller.disconnect()
        
        self.mock_ipmi.session.close.assert_called_once()
        self.assertFalse(self.controller.connected)

    def test_set_fan_speed(self):
        """Test setting fan speed."""
        self.controller.connected = True
        self.controller._set_manual_mode = Mock()
        
        self.controller.set_fan_speed(50)
        
        self.controller._set_manual_mode.assert_called_once()
        self.mock_ipmi.raw_command.assert_called()

    def test_set_automatic_control(self):
        """Test enabling automatic fan control."""
        self.controller.connected = True
        
        self.controller.set_automatic_control()
        
        self.mock_ipmi.raw_command.assert_called()


if __name__ == "__main__":
    unittest.main()