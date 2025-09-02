"""IPMI interface for Dell server fan control using ipmitool."""

import re
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional, Union

from ipmi_fan_control.pid import PIDController
from ipmi_fan_control.types import StatusCallback


class DellIPMIToolFanController:
    """Interface for controlling fans via ipmitool on Dell servers."""

    # Dell-specific IPMI OEM commands (verified from Dell documentation and examples)
    DELL_CMD_ENABLE_MANUAL_FAN = "raw 0x30 0x30 0x01 0x00"  # Disable automatic fan control
    DELL_CMD_SET_FAN_SPEED = "raw 0x30 0x30 0x02 0xff"      # Append % value in hex
    DELL_CMD_ENABLE_AUTO_FAN = "raw 0x30 0x30 0x01 0x01"    # Enable automatic fan control

    def __init__(
        self,
        host: str = "localhost",
        port: int = 623,
        username: str = "",
        password: str = "",
        interface: str = "lanplus",
        verify: bool = True,
    ):
        """Initialize IPMI connection for Dell servers.

        Args:
            host: BMC hostname or IP
            port: BMC port
            username: BMC username
            password: BMC password
            interface: IPMI interface type (lanplus, lan, etc.)
            verify: Whether to verify connection on initialization
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.interface = interface
        self.base_cmd = self._build_base_cmd()
        
        # PID controller for temperature-based fan control
        self.pid = PIDController()
        self.target_temp = 60.0  # Default target temperature in celsius
        self.monitor_interval = 30.0  # Default monitoring interval in seconds
        
        # Temperature monitoring
        self.monitoring = False
        self.monitor_thread = None
        self.temp_callback = None
        
        # Connection status
        self.connected = False
        
        # Verify connection if requested
        if verify:
            self.test_connection()
    
    def _build_base_cmd(self) -> List[str]:
        """Build the base ipmitool command with connection parameters.

        Returns:
            Base command list for subprocess
        """
        cmd = ["ipmitool"]
        
        if self.host != "localhost":
            cmd.extend(["-I", self.interface, "-H", self.host, "-p", str(self.port)])
            
            if self.username:
                cmd.extend(["-U", self.username])
            
            if self.password:
                cmd.extend(["-P", self.password])
        
        return cmd
    
    def _run_command(self, command: Union[str, List[str]]) -> str:
        """Run an IPMI command and return the output.

        Args:
            command: Command to run (string or list of arguments)

        Returns:
            Command output as string

        Raises:
            RuntimeError: If command fails
        """
        if isinstance(command, str):
            full_cmd = self.base_cmd + command.split()
        else:
            full_cmd = self.base_cmd + command
        
        try:
            result = subprocess.run(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            raise RuntimeError(f"IPMI command failed: {error_msg}")
    
    def test_connection(self) -> bool:
        """Test connection to the iDRAC.

        Returns:
            True if connection is successful

        Raises:
            RuntimeError: If connection fails
        """
        try:
            # Try each command in order, stopping at the first one that works
            commands = [
                # List in order of preference - try the simplest commands first
                "chassis status",    # Works on virtually all IPMI implementations
                "sensor reading",    # Works well on Dell servers
                "sdr list",          # Also reliable on most servers
                "mc info"            # Basic management controller info
            ]
            
            for cmd in commands:
                try:
                    output = self._run_command(cmd)
                    if output.strip():  # Any non-empty response is good
                        self.connected = True
                        return True
                except Exception:
                    continue  # Try the next command
            
            # If we get here, all commands failed
            raise RuntimeError("Could not establish IPMI connection with any command")
            
        except Exception as e:
            self.connected = False
            raise RuntimeError(f"Failed to connect to Dell iDRAC at {self.host}: {str(e)}")
    
    def get_fan_speeds(self) -> List[Dict[str, Any]]:
        """Get current fan speeds from Dell server.

        Returns:
            List of dictionaries containing fan information
        """
        try:
            # Try two different commands to read fan data
            fans = []
            try:
                # First try with sensor reading (more compatible with some Dell servers)
                output = self._run_command("sensor reading")
                
                # Parse fan information from sensor reading
                for line in output.splitlines():
                    # Look for fan entries (usually contain "fan" in the name or "RPM" in the unit)
                    if "fan" in line.lower() or "rpm" in line.lower():
                        # Try to extract the parts - format can vary between Dell models
                        parts = line.split('|')
                        if len(parts) >= 3:
                            name = parts[0].strip()
                            value_part = parts[2].strip()
                            # Extract numeric value and unit
                            value_match = re.search(r'([\d\.]+)\s*(\w+)', value_part)
                            if value_match:
                                speed = value_match.group(1)
                                unit = value_match.group(2)
                                status = "ok"  # Assume ok if reading is returned
                                
                                # Generate a simple id if not present
                                sensor_id = f"fan{len(fans)+1}"
                                
                                fans.append({
                                    "id": sensor_id,
                                    "name": name,
                                    "current_speed": float(speed),
                                    "unit": unit,
                                    "status": status
                                })
            except Exception as e1:
                # If that fails, try the sdr type command
                try:
                    output = self._run_command("sdr type fan")
                    
                    # Parse fan information
                    for line in output.splitlines():
                        # Typical format: "System Fan 1    | 33h | ok  | 7.1 | 3240 RPM"
                        match = re.match(r'(.*?)\s+\|\s+(\w+h)\s+\|\s+(\w+)\s+\|\s+[\d\.]+\s+\|\s+([\d\.]+)\s+(\w+)', line)
                        if match:
                            name, sensor_id, status, speed, unit = match.groups()
                            fans.append({
                                "id": sensor_id,
                                "name": name.strip(),
                                "current_speed": float(speed),
                                "unit": unit,
                                "status": status
                            })
                except Exception:
                    # If both methods fail, raise the first error
                    raise e1
            
            return fans
        except Exception as e:
            raise RuntimeError(f"Failed to read fan data: {str(e)}") from e
    
    def get_temperature_sensors(self) -> List[Dict[str, Any]]:
        """Get temperature sensor readings from Dell server.

        Returns:
            List of dictionaries containing temperature sensor information
        """
        try:
            # Get temperature sensor readings
            # Try multiple commands in case one fails
            try:
                # First try specific temperature command
                output = self._run_command("sdr type temperature")
            except Exception:
                try:
                    # If that fails, try sensor list which includes temperatures
                    output = self._run_command("sensor list")
                except Exception:
                    # Last resort, try sensor reading
                    output = self._run_command("sensor reading")
            
            # Parse temperature information
            temps = []
            for line in output.splitlines():
                # Skip empty lines
                if not line.strip():
                    continue
                
                # Try different pattern matches for temperature readings
                
                # Typical format: "Inlet Temp       | 04h | ok  | 7.1 | 19 degrees C"
                match = re.match(r'(.*?)\s+\|\s+(\w+h?)\s+\|\s+(\w+)\s+\|\s+[\d\.]+\s+\|\s+([\d\.]+)\s+degrees\s+(\w)', line)
                if match:
                    name, sensor_id, status, temp, unit = match.groups()
                    temps.append({
                        "id": sensor_id,
                        "name": name.strip(),
                        "current_temp": float(temp),
                        "unit": f"degrees {unit}",
                        "status": status
                    })
                    continue
                
                # Alternative format: "Inlet Temp : 19 C"
                alt_match = re.search(r'(.*?)\s*:\s*([\d\.]+)\s*([CF])', line, re.IGNORECASE)
                if alt_match and ("temp" in line.lower() or "ambient" in line.lower()):
                    name, temp, unit = alt_match.groups()
                    temps.append({
                        "id": f"temp{len(temps)+1}",
                        "name": name.strip(),
                        "current_temp": float(temp),
                        "unit": f"degrees {unit}",
                        "status": "ok"
                    })
                    continue
            
            return temps
        except Exception as e:
            # Return empty list on error instead of raising exception
            print(f"Warning: Error reading temperature sensors: {str(e)}")
            return []
    
    def get_highest_temperature(self) -> float:
        """Get highest temperature reading from all sensors.

        Returns:
            Highest temperature in Celsius
        """
        try:
            temp_sensors = self.get_temperature_sensors()
            
            # If no sensors or empty list, return a default value
            if not temp_sensors:
                print("Warning: No temperature sensors found, using default temperature of 60.0°C")
                return 60.0
            
            # Filter out potentially invalid sensors and extract temperatures
            temps = []
            for sensor in temp_sensors:
                try:
                    # Only include sensors with valid numeric temperature values
                    if "current_temp" in sensor and isinstance(sensor["current_temp"], (int, float)):
                        temps.append(sensor["current_temp"])
                except (KeyError, TypeError, ValueError):
                    continue
            
            # If no valid temperatures found, return default
            if not temps:
                print("Warning: No valid temperature readings found, using default temperature of 60.0°C")
                return 60.0
                
            # Find max temperature
            max_temp = max(temps)
            return max_temp
        except Exception as e:
            # Default to a safe value on error
            print(f"Warning: Error finding highest temperature: {str(e)}, using default temperature of 60.0°C")
            return 60.0
    
    def set_fan_speed(self, percentage: int) -> None:
        """Set Dell server fan speed to a specific percentage.

        Args:
            percentage: Fan speed percentage (0-100)
        """
        if percentage < 0 or percentage > 100:
            raise ValueError("Fan speed percentage must be between 0 and 100")
        
        try:
            # Enable manual fan control mode first
            self._set_manual_mode()
            
            # Convert percentage to hex value (without '0x' prefix)
            hex_percentage = format(percentage, 'x')
            
            # Set fan speed - Dell specific command
            cmd = f"{self.DELL_CMD_SET_FAN_SPEED} 0x{hex_percentage}"
            self._run_command(cmd)
            
            # Add a small delay to allow fans to adjust
            time.sleep(0.5)
        except Exception as e:
            raise RuntimeError(f"Failed to set fan speed: {str(e)}") from e
    
    def set_automatic_control(self) -> None:
        """Enable automatic fan control on Dell server."""
        try:
            # Dell-specific command to return fan control to automatic mode
            self._run_command(self.DELL_CMD_ENABLE_AUTO_FAN)
        except Exception as e:
            raise RuntimeError(f"Failed to enable automatic fan control: {str(e)}") from e
    
    def _set_manual_mode(self) -> None:
        """Put Dell server fans in manual control mode."""
        try:
            # Dell-specific command to enable manual fan control
            self._run_command(self.DELL_CMD_ENABLE_MANUAL_FAN)
        except Exception as e:
            raise RuntimeError(f"Failed to set manual fan mode: {str(e)}") from e
    
    def configure_pid(
        self,
        kp: float = 2.0,
        ki: float = 0.5,
        kd: float = 0.25,
        min_fan_speed: float = 30.0,
        max_fan_speed: float = 100.0,
    ) -> None:
        """Configure PID controller parameters.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            min_fan_speed: Minimum fan speed percentage
            max_fan_speed: Maximum fan speed percentage
        """
        self.pid.set_tunings(kp, ki, kd)
        self.pid.set_output_limits(min_fan_speed, max_fan_speed)
    
    def set_target_temperature(self, temp: float) -> None:
        """Set target temperature for PID control.

        Args:
            temp: Target temperature in Celsius
        """
        self.target_temp = temp
        self.pid.set_setpoint(temp)
    
    def set_monitor_interval(self, interval: float) -> None:
        """Set temperature monitoring interval.

        Args:
            interval: Monitoring interval in seconds
        """
        self.monitor_interval = interval
        self.pid.set_sample_time(interval)
    
    def _temperature_monitor_loop(self, callback: Optional[StatusCallback] = None) -> None:
        """Background thread for temperature monitoring and fan control.

        Args:
            callback: Optional callback function for monitoring events
        """
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        while self.monitoring:
            try:
                # Get current highest temperature
                current_temp = self.get_highest_temperature()
                
                # Calculate fan speed with PID
                # Handle the case where compute returns None
                computed_speed = self.pid.compute(current_temp)
                if computed_speed is None:
                    # If PID returns None, use a default safe value
                    fan_speed = 50  # 50% is a reasonable default
                    print("Warning: PID controller returned None, using default fan speed of 50%")
                else:
                    fan_speed = int(computed_speed)
                
                # Validate fan speed within configured PID controller range
                fan_speed = max(min(fan_speed, self.pid.output_max), self.pid.output_min)
                
                # Set fan speed
                self.set_fan_speed(fan_speed)
                
                # Call callback if provided
                if callback:
                    try:
                        status = {
                            "temperature": current_temp,
                            "target": self.target_temp,
                            "fan_speed": fan_speed
                        }
                        callback(status)
                    except Exception as callback_err:
                        print(f"Warning: Error in callback: {str(callback_err)}")
                
                # Reset error counter on successful loop
                consecutive_errors = 0
                
                # Sleep until next interval
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                # Log error and continue
                consecutive_errors += 1
                
                # Use different messages based on error count
                if consecutive_errors >= max_consecutive_errors:
                    print(f"Critical error in temperature monitor (error #{consecutive_errors}): {str(e)}")
                    print("Multiple consecutive errors detected. Setting fans to 70% as a safety measure.")
                    try:
                        # Set fans to a safe speed
                        self.set_fan_speed(70)
                    except Exception:
                        pass
                else:
                    print(f"Error in temperature monitor (error #{consecutive_errors}): {str(e)}")
                
                # Wait a bit longer after errors to avoid rapid retries
                time.sleep(5 + (consecutive_errors * 3))
    
    def start_temperature_monitoring(
        self, 
        target_temp: Optional[float] = None, 
        interval: Optional[float] = None,
        callback: Optional[StatusCallback] = None
    ) -> None:
        """Start temperature-based fan control.

        Args:
            target_temp: Target temperature in Celsius (uses current value if None)
            interval: Monitoring interval in seconds (uses current value if None)
            callback: Optional callback for monitoring events
        """
        if self.monitoring:
            return
        
        # Test connection
        self.test_connection()
        
        # Update settings if provided
        if target_temp is not None:
            self.set_target_temperature(target_temp)
        
        if interval is not None:
            self.set_monitor_interval(interval)
        
        # Initialize PID controller
        self.pid.set_auto_mode(True, self.get_highest_temperature())
        
        # Set manual fan control mode
        self._set_manual_mode()
        
        # Store callback
        self.temp_callback = callback
        
        # Start monitoring thread
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._temperature_monitor_loop,
            args=(callback,),
            daemon=True
        )
        self.monitor_thread.start()
    
    def stop_temperature_monitoring(self) -> None:
        """Stop temperature-based fan control and return to automatic control."""
        if not self.monitoring:
            return
        
        # Stop monitoring thread
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(2.0)  # Wait up to 2 seconds for thread to stop
        
        # Reset PID controller
        self.pid.set_auto_mode(False)
        
        # Return to automatic fan control
        try:
            self.set_automatic_control()
        except Exception as e:
            print(f"Warning: Failed to restore automatic fan control: {str(e)}")