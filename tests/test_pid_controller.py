"""Tests for the PID Controller module."""

import time
from unittest.mock import patch

import pytest

from ipmi_fan_control.pid import PIDController


class TestPIDController:
    """Test suite for the PID Controller."""

    def test_initialization(self):
        """Test PID controller initialization with default parameters."""
        pid = PIDController()
        assert pid.kp == 0.1
        assert pid.ki == 0.02
        assert pid.kd == 0.01
        assert pid.output_min == 30.0
        assert pid.output_max == 100.0
        assert pid.auto_mode is False
        assert pid.initialized is False

    def test_initialization_with_custom_parameters(self):
        """Test PID controller initialization with custom parameters."""
        pid = PIDController(
            kp=0.5, ki=0.1, kd=0.05, output_min=20.0, output_max=90.0, sample_time=2.0
        )
        assert pid.kp == 0.5
        assert pid.ki == 0.1
        assert pid.kd == 0.05
        assert pid.output_min == 20.0
        assert pid.output_max == 90.0
        assert pid.sample_time == 2.0

    def test_set_tunings(self):
        """Test setting new PID tuning parameters."""
        pid = PIDController()
        pid.set_tunings(1.0, 0.2, 0.3)
        assert pid.kp == 1.0
        assert pid.ki == 0.2
        assert pid.kd == 0.3

    def test_set_output_limits(self):
        """Test setting output limits."""
        pid = PIDController()
        pid.set_output_limits(40.0, 80.0)
        assert pid.output_min == 40.0
        assert pid.output_max == 80.0

    def test_set_setpoint(self):
        """Test setting the target temperature."""
        pid = PIDController()
        pid.set_setpoint(65.0)
        assert pid.setpoint == 65.0

    def test_set_sample_time(self):
        """Test setting sample time with adjustment of gains."""
        pid = PIDController(ki=0.1, kd=0.1, sample_time=1.0)
        original_ki = pid.ki
        original_kd = pid.kd
        
        # Double the sample time
        pid.set_sample_time(2.0)
        
        # ki should double, kd should halve
        assert pid.ki == original_ki * 2
        assert pid.kd == original_kd / 2
        assert pid.sample_time == 2.0

    def test_compute_below_setpoint(self):
        """Test compute when temperature is below setpoint."""
        pid = PIDController()
        pid.set_setpoint(60.0)
        pid.set_auto_mode(True)
        
        # Temperature below setpoint should result in minimum fan speed
        output = pid.compute(55.0)
        assert output == pytest.approx(pid.output_min, 0.1)

    def test_compute_above_setpoint(self):
        """Test compute when temperature is above setpoint."""
        pid = PIDController()
        pid.set_setpoint(60.0)
        pid.set_auto_mode(True)
        
        # Temperature above setpoint should result in higher fan speed
        output = pid.compute(65.0)
        assert output > pid.output_min

    def test_compute_at_setpoint(self):
        """Test compute when temperature is at setpoint."""
        pid = PIDController()
        pid.set_setpoint(60.0)
        pid.set_auto_mode(True)
        
        # At setpoint, should use a moderate fan speed
        output = pid.compute(60.0)
        # Expect a value equal to or above minimum (the base response at setpoint is 40.0)
        assert output >= pid.output_min
        assert output < pid.output_max

    def test_compute_respects_output_limits(self):
        """Test that compute respects output limits."""
        # Create a PID with extreme settings to test limits
        pid = PIDController(kp=100.0, ki=0.0, kd=0.0, output_min=40.0, output_max=80.0)
        pid.set_setpoint(60.0)
        pid.set_auto_mode(True)
        
        # Bypass rate limiting by setting initialized to True and a previous output already at max
        pid.initialized = True
        pid.last_output = 80.0
        pid.last_time = time.time() - 10.0  # Set last time 10 seconds ago to bypass rate limiting
        
        # Extreme temperature difference to force hitting the limit
        output = pid.compute(80.0)
        # Given the base response curve and the rate limiting, we should expect a value close to max
        assert output >= 75.0  # Using the base response at severe offset
        
        # Reset and try for min value
        pid.initialized = True
        pid.last_output = 40.0
        pid.last_time = time.time() - 10.0
        output = pid.compute(50.0)  # Below setpoint should use min
        assert output <= 40.0

    def test_base_response_curve(self):
        """Test the base response curve calculation."""
        pid = PIDController()
        pid.output_min = 30.0
        pid.output_max = 100.0
        
        # Below setpoint
        assert pid._calculate_base_response(-5.0) == 30.0
        
        # At setpoint
        response_at_setpoint = pid._calculate_base_response(0.0)
        assert response_at_setpoint >= 30.0
        assert response_at_setpoint <= 50.0
        
        # Slightly above setpoint
        response_above = pid._calculate_base_response(2.0)
        assert response_above > response_at_setpoint
        
        # Far above setpoint
        response_far_above = pid._calculate_base_response(10.0)
        assert response_far_above > response_above
        assert response_far_above <= 100.0

    def test_rate_limiting(self):
        """Test that fan speed changes are rate limited."""
        pid = PIDController()
        pid.set_setpoint(60.0)
        pid.set_auto_mode(True)
        
        # Initialize with a speed
        pid.last_output = 50.0
        pid.initialized = True
        
        # Mock time to control the exact time difference
        with patch('time.time', return_value=100.0):
            pid.last_time = 99.0  # 1 second ago
            
            # With max rate of 5% per second, and 1 second elapsed,
            # the output should not change by more than 5%
            output = pid.compute(70.0)  # Large error to force big change
            
            # Should be rate limited to 5% increase
            assert output <= 55.0

    def test_integration_over_time(self):
        """Test the integral term accumulates over time."""
        pid = PIDController(kp=0.0, ki=0.1, kd=0.0)
        pid.set_setpoint(60.0)
        pid.set_auto_mode(True)
        
        # First computation with a small error
        with patch('time.time', return_value=100.0):
            output1 = pid.compute(61.0)  # Error = 1
        
        # Second computation with the same error, but later in time
        with patch('time.time', return_value=101.0):
            output2 = pid.compute(61.0)  # Error = 1, 1 second later
        
        # The integral term should have accumulated, making output2 > output1
        assert output2 > output1