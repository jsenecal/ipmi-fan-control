"""PID controller for temperature-based fan control."""

import time
from typing import Optional


class PIDController:
    """PID controller for fan speed based on temperature."""

    def __init__(
        self,
        kp: float = 0.1,   # Extremely gentle proportional gain
        ki: float = 0.02,  # Very minimal integral gain
        kd: float = 0.01,  # Very minimal derivative gain
        output_min: float = 30.0,  # Minimum fan speed (%)
        output_max: float = 100.0,  # Maximum fan speed (%)
        sample_time: float = 1.0,  # Default sampling time in seconds
    ):
        """Initialize PID controller with tuning parameters.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            output_min: Minimum output value (fan speed percentage)
            output_max: Maximum output value (fan speed percentage)
            sample_time: Time between updates in seconds
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self.sample_time = sample_time
        
        # Internal state
        self.setpoint = 0.0
        self.last_error = 0.0
        self.integral = 0.0
        self.last_input = 0.0
        self.last_output = 0.0
        self.last_time = time.time()
        
        # Internal flags
        self.auto_mode = False
        self.initialized = False

    def set_tunings(self, kp: float, ki: float, kd: float) -> None:
        """Set PID tuning parameters.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd

    def set_output_limits(self, output_min: float, output_max: float) -> None:
        """Set output limits.

        Args:
            output_min: Minimum output value
            output_max: Maximum output value
        """
        if output_min > output_max:
            return
        
        self.output_min = output_min
        self.output_max = output_max
        
        # Adjust integral term to prevent windup
        if self.auto_mode:
            self.integral = max(min(self.integral, self.output_max), self.output_min)

    def set_setpoint(self, setpoint: float) -> None:
        """Set the target temperature.

        Args:
            setpoint: Target temperature value
        """
        self.setpoint = setpoint

    def set_sample_time(self, sample_time: float) -> None:
        """Set PID sample time in seconds.

        Args:
            sample_time: Sample time in seconds
        """
        if sample_time > 0:
            ratio = sample_time / self.sample_time
            self.ki *= ratio
            self.kd /= ratio
            self.sample_time = sample_time

    def compute(self, input_val: float, now: Optional[float] = None) -> float:
        """Calculate PID output value based on input temperature.

        Args:
            input_val: Current temperature
            now: Current time (if None, uses time.time())

        Returns:
            New fan speed percentage
        """
        if not self.auto_mode:
            return 0.0
        
        if now is None:
            now = time.time()
        
        # Time elapsed since last calculation
        time_change = now - self.last_time
        
        # Skip update if not enough time has elapsed
        if time_change < self.sample_time and self.initialized:
            return self.last_output
        
        # Calculate error for cooling system (negative = need less cooling, positive = need more cooling)
        # For cooling: input_val > setpoint means we need more cooling (positive error)
        error = input_val - self.setpoint
        
        # Special handling for first calculation (avoid derivative kick and large initial change)
        if not self.initialized:
            # Start with a moderate fan speed based on error
            if error > 0:  # Temperature above target, needs cooling
                # Set initial output based on how far we are from setpoint
                # Small offset from target: start at 35%, large offset: start at 60%
                error_magnitude = min(error, 15.0) / 15.0  # Normalize to 0-1 range, cap at 15°C difference
                initial_output = 35.0 + (error_magnitude * 25.0)  # Scale from 35% to 60%
                self.last_output = initial_output
                self.integral = initial_output * 0.3  # Set integral term to provide some initial momentum
            else:  # Temperature at or below target
                self.last_output = self.output_min
                self.integral = self.output_min * 0.3
                
            derivative = 0.0
            self.last_error = error
            self.last_input = input_val
            self.last_time = now
            self.initialized = True
            return self.last_output
        
        # Calculate derivative on input to avoid derivative kick on setpoint changes
        derivative = (input_val - self.last_input) / time_change
        
        # Calculate integral with anti-windup
        if self.auto_mode:
            # Apply smaller integral update during large changes to reduce oscillation
            integral_scale = 1.0
            if abs(error) > 8.0:
                integral_scale = 0.3  # Reduce integral effect during large temperature jumps
                
            self.integral += self.ki * error * time_change * integral_scale
            self.integral = max(min(self.integral, self.output_max), self.output_min)
        
        # Calculate base response using a non-linear curve for smoother response
        # This creates a gentler curve rather than a linear response to error
        base_output = self._calculate_base_response(error)
        
        # Calculate PID output - for cooling, positive error means more cooling (higher fan speed)
        pid_component = self.kp * error + self.kd * derivative + self.integral
        
        # Blend base response with PID component
        # For smaller errors, use more of the base response and less PID
        blend_factor = min(abs(error / 5.0), 1.0)  # 0-1 based on error magnitude
        output = (base_output * (1.0 - blend_factor)) + (pid_component * blend_factor)
        
        # Apply output limits
        output = max(min(output, self.output_max), self.output_min)
        
        # Limit rate of change for smoother transitions (prevent sudden large jumps)
        # Much gentler rate limiting to prevent oscillation
        max_change_per_second = 5.0  # Maximum 5% change per second
        max_change = max_change_per_second * time_change
        
        # Apply more aggressive limiting for small errors to prevent oscillation
        if abs(error) < 2.0:
            max_change = max_change * 0.5  # Even slower rate of change near setpoint
            
        if abs(output - self.last_output) > max_change:
            if output > self.last_output:
                output = self.last_output + max_change
            else:
                output = self.last_output - max_change
        
        # Save state for next calculation
        self.last_error = error
        self.last_input = input_val
        self.last_output = output
        self.last_time = now
        
        return output

    def initialize(self) -> None:
        """Reset PID controller state."""
        self.last_error = 0.0
        self.integral = 0.0
        self.last_input = 0.0
        self.initialized = False

    def set_auto_mode(self, auto_mode: bool, current_input: Optional[float] = None) -> None:
        """Enable or disable automatic mode.

        Args:
            auto_mode: True for auto mode, False for manual
            current_input: Current temperature (needed when switching to auto)
        """
        if auto_mode and not self.auto_mode:
            # Switching from manual to auto
            self.initialize()
            if current_input is not None:
                self.last_input = current_input
                self.integral = self.last_output
        
        self.auto_mode = auto_mode
        
    def _calculate_base_response(self, error: float) -> float:
        """Calculate a base fan speed using a smooth curve based on error.
        
        This creates a smoother, more predictable response than pure PID for small changes.
        
        Args:
            error: Current error (positive means need more cooling)
            
        Returns:
            Base fan speed percentage
        """
        # For negative errors (below setpoint), use minimum fan speed
        if error <= -1.0:
            return self.output_min
            
        # For errors between -1°C and 0°C, gradual ramp from min to middle range
        if error < 0.0:
            # Map -1 to 0 range to min_output to mid-level (40%)
            t = error + 1.0  # 0 to 1
            return self.output_min + (t * (40.0 - self.output_min))
            
        # For errors between 0°C and 5°C, gradual ramp from middle to higher
        if error <= 5.0:
            # Map 0 to 5 range to 40% to 75%
            t = error / 5.0  # 0 to 1
            return 40.0 + (t * 35.0)  # 40% to 75%
            
        # For errors above 5°C, exponential curve to max
        # Cap at 15°C to avoid going beyond max
        capped_error = min(error - 5.0, 10.0)  # 0 to 10 range
        t = capped_error / 10.0  # 0 to 1
        
        # Apply exponential curve: t^2 gives more aggressive response at higher errors
        t_squared = t * t
        return 75.0 + (t_squared * (self.output_max - 75.0))  # 75% to max