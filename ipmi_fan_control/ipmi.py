"""IPMI interface for Dell server fan control."""

import threading
import time
from typing import Any, Dict, List, Optional, cast

import pyipmi
import pyipmi.interfaces

from ipmi_fan_control.pid import PIDController
from ipmi_fan_control.types import IPMIInterface, StatusCallback


class DellIPMIFanController:
    """Interface for controlling fans via IPMI on Dell servers."""

    # Dell-specific IPMI constants
    IPMI_DELL_OEM_NETFN = 0x30
    IPMI_DELL_OEM_ENABLE_MANUAL_FAN_CMD = 0x30
    IPMI_DELL_OEM_SET_FAN_SPEED_CMD = 0x31
    IPMI_DELL_OEM_SET_AUTO_FAN_CMD = 0x32

    def __init__(
        self,
        interface_type: str = "rmcp",
        host: str = "localhost",
        port: int = 623,
        username: str = "",
        password: str = "",
    ):
        """Initialize IPMI connection for Dell servers.

        Args:
            interface_type: IPMI interface type (rmcp, ipmitool, etc.)
            host: BMC hostname or IP
            port: BMC port
            username: BMC username
            password: BMC password
        """
        self.interface = self._create_interface(interface_type)
        self.ipmi = pyipmi.create_connection(self.interface)
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.connected = False
        
        # PID controller for temperature-based fan control
        self.pid = PIDController()
        self.target_temp = 60.0  # Default target temperature in celsius
        self.monitor_interval = 30.0  # Default monitoring interval in seconds
        
        # Temperature monitoring
        self.monitoring = False
        self.monitor_thread = None
        self.temp_callback = None

    def _create_interface(self, interface_type: str) -> IPMIInterface:
        """Create the IPMI interface based on type.

        Args:
            interface_type: IPMI interface type

        Returns:
            IPMI interface object
        """
        if interface_type == "rmcp":
            return cast(IPMIInterface, pyipmi.interfaces.create_interface("rmcp"))
        else:
            return cast(IPMIInterface, pyipmi.interfaces.create_interface(interface_type))

    def connect(self) -> None:
        """Establish connection to Dell iDRAC."""
        try:
            # Set up the session with more robust error handling
            if not hasattr(self.ipmi, "session"):
                raise RuntimeError("IPMI session object not available. Check pyipmi version compatibility.")
            
            # Configure RMCP session
            self.ipmi.session.set_session_type_rmcp(self.host, port=self.port)
            self.ipmi.session.set_auth_type_user(self.username, self.password)
            
            # Set target (Dell iDRAC typically uses 0x20 as IPMB address)
            self.ipmi.target = pyipmi.Target(ipmb_address=0x20)
            
            # Test connection by trying to get device ID
            try:
                device_id = self.ipmi.get_device_id()
                if device_id is None:
                    raise RuntimeError("Received empty device ID from iDRAC")
            except Exception as e:
                raise RuntimeError(f"Failed to connect to iDRAC: {str(e)}")
                
            self.connected = True
        except Exception as e:
            self.connected = False
            raise RuntimeError(f"Failed to establish connection to Dell iDRAC at {self.host}: {str(e)}") from e

    def disconnect(self) -> None:
        """Close connection to iDRAC."""
        # Stop monitoring thread if running
        self.stop_temperature_monitoring()
        
        # Close session - with safer error handling
        try:
            if hasattr(self.ipmi, "session"):
                if hasattr(self.ipmi.session, "close"):
                    try:
                        # Make sure interface and session properties exist before using them
                        if (hasattr(self.ipmi.session, "interface") and 
                            self.ipmi.session.interface is not None and
                            hasattr(self.ipmi.session.interface, "_session") and
                            self.ipmi.session.interface._session is not None):
                            self.ipmi.session.close()
                    except AttributeError:
                        # Safely handle case where interface or _session is missing or None
                        pass
        except Exception as e:
            print(f"Warning: Could not close IPMI session cleanly: {str(e)}")
        
        self.connected = False

    def get_fan_speeds(self) -> List[Dict[str, Any]]:
        """Get current fan speeds from Dell server.

        Returns:
            List of dictionaries containing fan information
        """
        if not self.connected:
            self.connect()
        
        # Get SDR repository
        try:
            # Try to access SDR repository directly
            if hasattr(self.ipmi, "sdr_repository"):
                sdr = self.ipmi.sdr_repository
            else:
                # If not available directly, try to initialize it
                try:
                    # Attempt to get sdr repository from pyipmi 
                    # This works for newer versions of pyipmi
                    from pyipmi.sdr import SdrRepository
                    sdr = SdrRepository(self.ipmi)
                    # Cache it for future use
                    self.ipmi.sdr_repository = sdr
                except (ImportError, AttributeError):
                    raise RuntimeError("Unable to access SDR repository. Check pyipmi version compatibility.")
            
            # Find and return all fan sensors (Dell typically uses "Fan" prefix)
            fans = []
            for sensor in sdr.get_sensor_list():
                if "fan" in sensor.name.lower():
                    reading = sensor.read_sensor()
                    fans.append({
                        "id": sensor.id,
                        "name": sensor.name,
                        "current_speed": reading.raw,
                        "unit": "RPM",
                        "status": reading.state
                    })
            
            return fans
        except Exception as e:
            # Provide more detailed error information
            raise RuntimeError(f"Failed to read fan data: {str(e)}. Make sure you are connecting to a valid Dell iDRAC.") from e
        
    def get_temperature_sensors(self) -> List[Dict[str, Any]]:
        """Get temperature sensor readings from Dell server.

        Returns:
            List of dictionaries containing temperature sensor information
        """
        if not self.connected:
            self.connect()
        
        # Get SDR repository
        try:
            # Try to access SDR repository directly
            if hasattr(self.ipmi, "sdr_repository"):
                sdr = self.ipmi.sdr_repository
            else:
                # If not available directly, try to initialize it
                try:
                    # Attempt to get sdr repository from pyipmi
                    from pyipmi.sdr import SdrRepository
                    sdr = SdrRepository(self.ipmi)
                    # Cache it for future use
                    self.ipmi.sdr_repository = sdr
                except (ImportError, AttributeError):
                    raise RuntimeError("Unable to access SDR repository. Check pyipmi version compatibility.")
            
            # Find and return all temperature sensors
            temps = []
            for sensor in sdr.get_sensor_list():
                if any(term in sensor.name.lower() for term in ["temp", "temperature"]):
                    reading = sensor.read_sensor()
                    temps.append({
                        "id": sensor.id,
                        "name": sensor.name,
                        "current_temp": reading.raw,
                        "unit": "Celsius",
                        "status": reading.state
                    })
            
            return temps
        except Exception as e:
            # Provide more detailed error information
            raise RuntimeError(f"Failed to read temperature data: {str(e)}. Make sure you are connecting to a valid Dell iDRAC.") from e
    
    def get_highest_temperature(self) -> float:
        """Get highest temperature reading from all sensors.

        Returns:
            Highest temperature in Celsius
        """
        temp_sensors = self.get_temperature_sensors()
        if not temp_sensors:
            return 0.0
        
        max_temp = max(sensor["current_temp"] for sensor in temp_sensors)
        return max_temp

    def set_fan_speed(self, percentage: int) -> None:
        """Set Dell server fan speed to a specific percentage.

        Args:
            percentage: Fan speed percentage (0-100)
        """
        if not self.connected:
            self.connect()
        
        if percentage < 0 or percentage > 100:
            raise ValueError("Fan speed percentage must be between 0 and 100")
        
        # Enable manual fan control mode first (Dell-specific)
        self._set_manual_mode()
        
        # Set fan speed using Dell OEM command
        # For Dell servers, this typically takes a percentage value
        # Note: The exact data bytes may need adjustment based on specific Dell model
        data = [percentage]
        self.ipmi.raw_command(self.IPMI_DELL_OEM_NETFN, self.IPMI_DELL_OEM_SET_FAN_SPEED_CMD, *data)

    def set_automatic_control(self) -> None:
        """Enable automatic fan control on Dell server."""
        if not self.connected:
            self.connect()
        
        # Dell-specific command to return fan control to automatic mode
        data = [0x01]  # Typically 0x01 means "enable automatic control"
        self.ipmi.raw_command(self.IPMI_DELL_OEM_NETFN, self.IPMI_DELL_OEM_SET_AUTO_FAN_CMD, *data)

    def _set_manual_mode(self) -> None:
        """Put Dell server fans in manual control mode."""
        # Dell-specific command to enable manual fan control
        data = [0x01]  # Typically 0x01 means "enable manual control"
        self.ipmi.raw_command(self.IPMI_DELL_OEM_NETFN, self.IPMI_DELL_OEM_ENABLE_MANUAL_FAN_CMD, *data)
        
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
        while self.monitoring:
            try:
                # Get current highest temperature
                current_temp = self.get_highest_temperature()
                
                # Calculate fan speed with PID
                fan_speed = int(self.pid.compute(current_temp))
                
                # Set fan speed
                self.set_fan_speed(fan_speed)
                
                # Call callback if provided
                if callback:
                    status = {
                        "temperature": current_temp,
                        "target": self.target_temp,
                        "fan_speed": fan_speed
                    }
                    callback(status)
                
                # Sleep until next interval
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                # Log error and continue
                print(f"Error in temperature monitor: {str(e)}")
                time.sleep(5)  # Short sleep before retry
    
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
        
        if not self.connected:
            self.connect()
        
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
        if self.connected:
            self.set_automatic_control()