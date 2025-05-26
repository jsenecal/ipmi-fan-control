"""Enhanced logging using Rich's logging handler."""

import logging
from typing import Any, Dict, List

from rich.console import Console
from rich.logging import RichHandler


class EnhancedLogger:
    """Enhanced logger using Rich for colored output without tables."""
    
    def __init__(self, name: str = "ipmi-fan-control", level: int = logging.INFO):
        """Initialize the enhanced logger.
        
        Args:
            name: Logger name
            level: Logging level
        """
        self.console = Console()
        
        # Set up the logger with Rich handler
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Remove existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Add Rich handler
        rich_handler = RichHandler(
            console=self.console,
            show_time=False,
            show_path=False,
            rich_tracebacks=True,
            markup=True
        )
        rich_handler.setFormatter(logging.Formatter(fmt="%(message)s"))
        self.logger.addHandler(rich_handler)
    
    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(f"[dim cyan]🔍 {message}[/dim cyan]")
    
    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(f"[white]{message}[/white]")
    
    def success(self, message: str) -> None:
        """Log success message."""
        self.logger.info(f"[green]✓ {message}[/green]")
    
    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(f"[yellow]⚠ {message}[/yellow]")
    
    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(f"[red]✗ {message}[/red]")
    
    def critical(self, message: str) -> None:
        """Log critical message."""
        self.logger.critical(f"[bold red]✗ {message}[/bold red]")
    
    def status(self, message: str) -> None:
        """Log status message."""
        self.logger.info(f"[cyan]→ {message}[/cyan]")
    
    def section_header(self, title: str) -> None:
        """Print a section header."""
        self.logger.info(f"\n[bold cyan]═══ {title} ═══[/bold cyan]")
    
    def print_fan_data(self, fans: List[Dict[str, Any]]) -> None:
        """Print fan data in a structured format without tables.
        
        Args:
            fans: List of fan dictionaries
        """
        if not fans:
            self.warning("No fans detected in this system")
            return
        
        self.section_header("Dell Server Fan Status")
        
        for fan in fans:
            # Color status based on value
            status = fan['status'].lower()
            if status in ['ok', 'normal', 'good']:
                status_color = "green"
            elif status in ['warning', 'caution']:
                status_color = "yellow"
            else:
                status_color = "red"
            
            # Color speed based on level (assuming RPM values)
            speed = fan['current_speed']
            if isinstance(speed, (int, float)):
                if speed < 2000:
                    speed_color = "green"
                elif speed < 4000:
                    speed_color = "yellow"
                else:
                    speed_color = "red"
            else:
                speed_color = "white"
            
            self.logger.info(
                f"  [cyan]{fan['id']}[/cyan] "
                f"[bold white]{fan['name']}[/bold white]: "
                f"[{speed_color}]{speed}[/{speed_color}] "
                f"[blue]{fan['unit']}[/blue] "
                f"([{status_color}]{fan['status']}[/{status_color}])"
            )
    
    def print_temperature_data(self, temps: List[Dict[str, Any]]) -> None:
        """Print temperature data in a structured format without tables.
        
        Args:
            temps: List of temperature sensor dictionaries
        """
        if not temps:
            self.warning("No temperature sensors detected")
            return
        
        self.section_header("Dell Server Temperature Status")
        
        for temp in temps:
            # Color temperature based on value
            temp_val = temp['current_temp']
            if isinstance(temp_val, (int, float)):
                if temp_val < 40:
                    temp_color = "green"
                elif temp_val < 60:
                    temp_color = "yellow"
                elif temp_val < 80:
                    temp_color = "magenta"
                else:
                    temp_color = "red"
            else:
                temp_color = "white"
            
            # Color status based on value
            status = temp['status'].lower()
            if status in ['ok', 'normal', 'good']:
                status_color = "green"
            elif status in ['warning', 'caution']:
                status_color = "yellow"
            else:
                status_color = "red"
            
            self.logger.info(
                f"  [cyan]{temp['id']}[/cyan] "
                f"[bold white]{temp['name']}[/bold white]: "
                f"[{temp_color}]{temp_val}[/{temp_color}] "
                f"[blue]{temp['unit']}[/blue] "
                f"([{status_color}]{temp['status']}[/{status_color}])"
            )
    
    def print_pid_status(self, status: Dict[str, Any]) -> None:
        """Print PID controller status.
        
        Args:
            status: Status dictionary with temperature, target, and fan_speed
        """
        temp = status.get('temperature', 0)
        target = status.get('target', 0)
        fan_speed = status.get('fan_speed', 0)
        error = temp - target
        
        # Color temperature based on how close to target
        if abs(error) < 1:
            temp_color = "green"
        elif abs(error) < 3:
            temp_color = "yellow"
        else:
            temp_color = "red"
        
        # Color fan speed based on level
        if fan_speed < 40:
            fan_color = "green"
        elif fan_speed < 70:
            fan_color = "yellow"
        else:
            fan_color = "red"
        
        # Color error based on magnitude
        if abs(error) < 1:
            error_color = "green"
        elif abs(error) < 3:
            error_color = "yellow"
        else:
            error_color = "red"
        
        import time
        timestamp = time.strftime("%H:%M:%S")
        
        self.logger.info(
            f"[dim white]{timestamp}[/dim white] | "
            f"Temp: [{temp_color}]{temp:.1f}°C[/{temp_color}] | "
            f"Target: [cyan]{target:.1f}°C[/cyan] | "
            f"Fan: [{fan_color}]{fan_speed}%[/{fan_color}] | "
            f"Error: [{error_color}]{error:+.1f}°C[/{error_color}]"
        )
    
    def print_troubleshooting_tips(self) -> None:
        """Print troubleshooting tips."""
        self.section_header("Troubleshooting Tips")
        
        tips = [
            "Verify iDRAC IP address, username, and password",
            "Ensure network connectivity to the iDRAC", 
            "Check if IPMI over LAN is enabled in iDRAC settings",
            "Try using the --interface parameter ('lan' or 'lanplus')",
            "Make sure 'ipmitool' is installed on your system",
            "Try installing ipmitool: 'sudo apt install ipmitool' or equivalent"
        ]
        
        for i, tip in enumerate(tips, 1):
            self.logger.info(f"  [yellow]{i}.[/yellow] {tip}")


# Global logger instance
logger = EnhancedLogger()