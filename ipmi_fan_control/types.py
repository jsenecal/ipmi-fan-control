"""Type definitions for the IPMI fan control module."""

from typing import Any, Dict, Protocol

# Define types for IPMI interfaces
IPMIInterface = Any  # Replace with actual type when available
IPMIConnection = Any  # Replace with actual type when available

# Sensor types
SensorReading = Dict[str, Any]
FanSensor = Dict[str, Any]
TemperatureSensor = Dict[str, Any]

# Define a protocol for callback functions
class StatusCallback(Protocol):
    """Protocol for status callback functions."""
    
    def __call__(self, status: Dict[str, Any]) -> None:
        """Called with status data."""
        ...