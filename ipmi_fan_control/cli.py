"""CLI interface for Dell IPMI fan control."""

import json
import shutil
import sys
import time
from enum import Enum
from typing import Any, Dict, List, Optional

import typer
import yaml

# Try to use the ipmitool implementation first, fallback to python-ipmi if not available
try:
    # Check if ipmitool is installed
    if shutil.which("ipmitool"):
        from ipmi_fan_control.ipmitool import (
            DellIPMIToolFanController as IPMIController,
        )

        USING_IPMITOOL = True
    else:
        from ipmi_fan_control.ipmi import DellIPMIFanController as IPMIController

        USING_IPMITOOL = False
except ImportError:
    from ipmi_fan_control.ipmi import DellIPMIFanController as IPMIController

    USING_IPMITOOL = False

import atexit
import signal

from ipmi_fan_control.enhanced_logger import logger


class OutputFormat(str, Enum):
    """Output format options."""

    TABLE = "table"
    JSON = "json"
    YAML = "yaml"


app = typer.Typer(help="Control fan speeds on Dell servers via IPMI")

# Global variables for cleanup
_controller = None
_auto_restore = True


def cleanup_and_restore():
    """Restore automatic fan control on exit."""
    global _controller, _auto_restore
    if _controller and _auto_restore:
        try:
            logger.info("Restoring automatic fan control...")
            _controller.set_automatic_control()
            logger.success("Automatic fan control restored")
        except Exception as e:
            logger.warning(f"Failed to restore automatic control: {str(e)}")


def setup_cleanup(controller, auto_restore: bool):
    """Set up cleanup handlers."""
    global _controller, _auto_restore
    _controller = controller
    _auto_restore = auto_restore

    if auto_restore:
        # Register cleanup function for normal exit
        atexit.register(cleanup_and_restore)

        # Register signal handlers for Ctrl+C and SIGTERM
        def signal_handler(signum, frame):
            cleanup_and_restore()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


def connect_controller(controller, output_format):
    """Helper function to connect to controller."""
    if output_format == OutputFormat.TABLE:
        logger.status("Connecting to iDRAC...")

    if USING_IPMITOOL:
        controller.test_connection()
    else:
        controller.connect()


def handle_error(error_msg: str, output_format: OutputFormat, show_tips: bool = True):
    """Helper function to handle errors consistently."""
    if output_format == OutputFormat.TABLE:
        logger.error(error_msg)
        if show_tips:
            logger.print_troubleshooting_tips()
    elif output_format == OutputFormat.JSON:
        print(json.dumps({"error": error_msg}))
    elif output_format == OutputFormat.YAML:
        print(yaml.dump({"error": error_msg}))


def disconnect_controller(controller, output_format: OutputFormat):
    """Helper function to disconnect controller safely."""
    if not USING_IPMITOOL:
        try:
            controller.disconnect()
        except Exception as disconnect_err:
            if output_format == OutputFormat.TABLE:
                logger.warning(f"Warning during disconnect: {str(disconnect_err)}")


@app.callback()
def callback(
    ctx: typer.Context,
    host: str = typer.Option(
        "localhost",
        "--host",
        "-H",
        envvar="IPMI_HOST",
        help="BMC hostname or IP address (env: IPMI_HOST)",
    ),
    port: int = typer.Option(
        623, "--port", "-P", envvar="IPMI_PORT", help="BMC port (env: IPMI_PORT)"
    ),
    username: str = typer.Option(
        "",
        "--username",
        "-u",
        envvar="IPMI_USERNAME",
        help="BMC username (env: IPMI_USERNAME)",
    ),
    password: str = typer.Option(
        "",
        "--password",
        "-p",
        envvar="IPMI_PASSWORD",
        help="BMC password (env: IPMI_PASSWORD)",
    ),
    interface: str = typer.Option(
        "lanplus",
        "--interface",
        "-i",
        envvar="IPMI_INTERFACE",
        help="IPMI interface type (lanplus or lan) (env: IPMI_INTERFACE)",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        envvar="IPMI_DEBUG",
        help="Enable debug mode with additional logging (env: IPMI_DEBUG)",
    ),
    auto_restore: bool = typer.Option(
        True,
        "--auto-restore/--no-auto-restore",
        envvar="IPMI_AUTO_RESTORE",
        help="Automatically restore Dell default dynamic fan control on exit (env: IPMI_AUTO_RESTORE)",
    ),
    output: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--output",
        "-o",
        envvar="IPMI_OUTPUT_FORMAT",
        help="Output format (table, json, or yaml) (env: IPMI_OUTPUT_FORMAT)",
    ),
):
    """Set up IPMI connection parameters."""
    # Configure logging if debug mode is enabled
    if debug:
        import logging

        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        # Enable pyipmi debug logging if applicable
        if not USING_IPMITOOL:
            try:
                import pyipmi

                pyipmi_logger = logging.getLogger("pyipmi")
                pyipmi_logger.setLevel(logging.DEBUG)
            except ImportError:
                pass

        logger.info("Debug mode enabled")

    # Show which IPMI implementation we're using
    if debug:
        if USING_IPMITOOL:
            logger.info("Using ipmitool implementation")
        else:
            logger.info("Using python-ipmi implementation")

    # Create controller instance
    if USING_IPMITOOL:
        # For ipmitool implementation
        controller = IPMIController(
            interface=interface,
            host=host,
            port=port,
            username=username,
            password=password,
            verify=False,  # Don't verify connection in constructor
        )
    else:
        # For python-ipmi implementation
        controller = IPMIController(
            interface_type=interface,
            host=host,
            port=port,
            username=username,
            password=password,
        )

    # Store controller, output format, and auto_restore flag in context
    ctx.obj = {
        "controller": controller,
        "output_format": output,
        "auto_restore": auto_restore,
    }


def format_sensor_data(
    sensors: List[Dict[str, Any]], sensor_type: str
) -> List[Dict[str, Any]]:
    """Helper function to format sensor data for JSON/YAML output."""
    clean_data = []
    for sensor in sensors:
        if sensor_type == "fan":
            clean_sensor = {
                "id": sensor["id"],
                "name": sensor["name"],
                "speed": sensor["current_speed"],
                "unit": sensor["unit"],
                "status": sensor["status"],
            }
        else:  # temperature
            clean_sensor = {
                "id": sensor["id"],
                "name": sensor["name"],
                "temperature": sensor["current_temp"],
                "unit": sensor["unit"],
                "status": sensor["status"],
            }
        clean_data.append(clean_sensor)
    return clean_data


@app.command("status")
def status(ctx: typer.Context):
    """Display current fan speeds."""
    controller = ctx.obj["controller"]
    output_format = ctx.obj["output_format"]

    try:
        connect_controller(controller, output_format)

        if output_format == OutputFormat.TABLE:
            logger.status("Reading fan sensors...")

        fans = controller.get_fan_speeds()

        if not fans:
            if output_format == OutputFormat.TABLE:
                logger.warning("No fans detected in this system")
            elif output_format == OutputFormat.JSON:
                print(json.dumps({"fans": []}))
            elif output_format == OutputFormat.YAML:
                print(yaml.dump({"fans": []}))
            return

        # Format the results based on the selected output format
        if output_format == OutputFormat.TABLE:
            logger.print_fan_data(fans)
        elif output_format == OutputFormat.JSON:
            clean_fans = format_sensor_data(fans, "fan")
            print(json.dumps({"fans": clean_fans}, indent=2))
        elif output_format == OutputFormat.YAML:
            clean_fans = format_sensor_data(fans, "fan")
            print(yaml.dump({"fans": clean_fans}, sort_keys=False))

    except Exception as e:
        handle_error(f"Error reading fan status: {str(e)}", output_format)
        sys.exit(1)
    finally:
        disconnect_controller(controller, output_format)


def output_result(
    result_data: Dict[str, Any], output_format: OutputFormat, success_msg: str = ""
):
    """Helper function to output results consistently."""
    if output_format == OutputFormat.TABLE and success_msg:
        logger.success(success_msg)
    elif output_format == OutputFormat.JSON:
        print(json.dumps(result_data))
    elif output_format == OutputFormat.YAML:
        print(yaml.dump(result_data))


@app.command("set")
def set_speed(
    ctx: typer.Context,
    percentage: int = typer.Argument(
        ..., min=0, max=100, help="Fan speed percentage (0-100)"
    ),
):
    """Set fan speed to a specific percentage."""
    controller = ctx.obj["controller"]
    output_format = ctx.obj["output_format"]
    auto_restore = ctx.obj["auto_restore"]

    # Set up cleanup handlers
    setup_cleanup(controller, auto_restore)

    try:
        connect_controller(controller, output_format)
        controller.set_fan_speed(percentage)

        result_data = {"result": "success", "fan_speed": percentage}
        output_result(result_data, output_format, f"Fan speed set to {percentage}%")

        if output_format == OutputFormat.TABLE and auto_restore:
            logger.info("Automatic fan control will be restored on exit")

    except Exception as e:
        handle_error(
            f"Error setting fan speed: {str(e)}", output_format, show_tips=False
        )
        sys.exit(1)
    finally:
        disconnect_controller(controller, output_format)


@app.command("auto")
def auto_control(ctx: typer.Context):
    """Enable automatic fan control."""
    controller = ctx.obj["controller"]
    output_format = ctx.obj["output_format"]

    try:
        # For ipmitool implementation, we need to test the connection
        if USING_IPMITOOL:
            controller.test_connection()
        else:
            controller.connect()

        controller.set_automatic_control()

        if output_format == OutputFormat.TABLE:
            logger.success("Automatic fan control enabled")
        elif output_format == OutputFormat.JSON:
            print(json.dumps({"result": "success", "mode": "automatic"}))
        elif output_format == OutputFormat.YAML:
            print(yaml.dump({"result": "success", "mode": "automatic"}))

    except Exception as e:
        error_msg = f"Error enabling automatic fan control: {str(e)}"
        if output_format == OutputFormat.TABLE:
            logger.error(error_msg)
        elif output_format == OutputFormat.JSON:
            print(json.dumps({"error": error_msg}))
        elif output_format == OutputFormat.YAML:
            print(yaml.dump({"error": error_msg}))

        sys.exit(1)
    finally:
        # Only disconnect for python-ipmi implementation
        if not USING_IPMITOOL:
            try:
                controller.disconnect()
            except Exception as disconnect_err:
                if output_format == OutputFormat.TABLE:
                    logger.warning(f"Warning during disconnect: {str(disconnect_err)}")


@app.command("test")
def test_compatibility(
    ctx: typer.Context,
    quick: bool = typer.Option(
        True,
        "--quick/--full",
        envvar="IPMI_TEST_QUICK",
        help="Quick test (status only) or full test (including brief fan control) (env: IPMI_TEST_QUICK)",
    ),
    diagnostic: bool = typer.Option(
        False,
        "--diagnostic",
        envvar="IPMI_TEST_DIAGNOSTIC",
        help="Run additional diagnostic tests and show raw command outputs (env: IPMI_TEST_DIAGNOSTIC)",
    ),
):
    """Test Dell server compatibility."""
    controller = ctx.obj["controller"]
    output_format = ctx.obj["output_format"]

    # Test mode only supports table output for now
    if output_format != OutputFormat.TABLE:
        logger.warning("Note: Test mode only supports table output format")

    logger.section_header("Testing Dell server compatibility...")

    try:
        # Step 1: Connect to the server
        logger.status("Testing connection to iDRAC...")
        if USING_IPMITOOL:
            controller.test_connection()

            # Run diagnostics if requested
            if diagnostic and USING_IPMITOOL:
                logger.success("Connection OK")
                logger.section_header("Running diagnostic tests...")

                # Try various IPMI commands and show their output
                commands = [
                    "chassis status",
                    "sensor reading",
                    "sdr list",
                    "mc info",
                ]

                for cmd in commands:
                    logger.info(f"Testing command: {cmd}")
                    try:
                        output = controller._run_command(cmd)
                        logger.success("Command succeeded")
                        # Print the raw output with line numbers
                        for i, line in enumerate(output.strip().split("\n")):
                            if (
                                i < 10
                            ):  # Only show first 10 lines to avoid flooding console
                                logger.info(f"  {i + 1}. {line}")
                            elif i == 10:
                                logger.info("  ... (output truncated)")
                                break
                    except Exception as e:
                        logger.error(f"Command failed: {str(e)}")

                # Special test for raw OEM commands
                logger.info("Testing Dell OEM commands:")
                try:
                    # Test getting the version of the OEM commands subsystem
                    # This is usually a safe "read-only" OEM command
                    cmd = "raw 0x30 0xF0"  # Dell get version command
                    output = controller._run_command(cmd)
                    logger.success(f"OEM command succeeded: {output}")
                except Exception as e:
                    logger.error(f"OEM command failed: {str(e)}")

                logger.info("Diagnostics complete")
            else:
                logger.success("Connection OK")
        else:
            controller.connect()
            logger.success("Connection OK")

        # Step 2: Read fan speeds
        logger.status("Testing reading fan speeds...")
        fans = controller.get_fan_speeds()
        if not fans:
            logger.warning("No fans detected")
        else:
            logger.success(f"Found {len(fans)} fans")

        # Step 3: Read temperatures
        logger.status("Testing reading temperature sensors...")
        temps = controller.get_temperature_sensors()
        if not temps:
            logger.warning("No temperature sensors detected")
        else:
            logger.success(f"Found {len(temps)} temperature sensors")

        # Skip if quick test
        if not quick:
            # Step 4: Test manual fan control
            logger.status("Testing manual fan control...")
            # Set manual fan control
            controller._set_manual_mode()
            logger.success("Manual mode enabled")

            # Step 5: Set fan speed to 50%
            logger.status("Testing setting fan speed to 50%...")
            controller.set_fan_speed(50)
            logger.success("Fan speed set successfully")

            # Brief pause to let fans adjust
            time.sleep(2)

            # Step 6: Return to automatic control
            logger.status("Testing return to automatic control...")
            controller.set_automatic_control()
            logger.success("Automatic control restored")

        # Overall result
        logger.section_header(
            "✓ Compatibility test passed! Your Dell server appears to be compatible."
        )
        logger.info("Detected hardware:")

        # Display fan info
        if fans:
            logger.print_fan_data(fans)

        # Display temperature info
        if temps:
            logger.print_temperature_data(temps)

    except Exception as e:
        logger.error(f"Compatibility test failed: {str(e)}")
        logger.print_troubleshooting_tips()
        sys.exit(1)
    finally:
        # Only disconnect for python-ipmi implementation
        if not USING_IPMITOOL:
            try:
                controller.disconnect()
            except Exception:
                pass


@app.command("temp")
def temp_status(ctx: typer.Context):
    """Display current temperature sensors."""
    controller = ctx.obj["controller"]
    output_format = ctx.obj["output_format"]

    try:
        if output_format == OutputFormat.TABLE:
            logger.status("Connecting to iDRAC...")

        # For ipmitool implementation, we need to test the connection
        if USING_IPMITOOL:
            controller.test_connection()
        else:
            controller.connect()

        if output_format == OutputFormat.TABLE:
            logger.status("Reading temperature sensors...")

        temps = controller.get_temperature_sensors()

        if not temps:
            if output_format == OutputFormat.TABLE:
                logger.warning("No temperature sensors detected")
            elif output_format == OutputFormat.JSON:
                print(json.dumps({"temperatures": []}))
            elif output_format == OutputFormat.YAML:
                print(yaml.dump({"temperatures": []}))
            return

        # Format the results based on the selected output format
        if output_format == OutputFormat.TABLE:
            logger.print_temperature_data(temps)

        elif output_format == OutputFormat.JSON:
            # Clean up temperature data for JSON output
            clean_temps = []
            for temp in temps:
                clean_temp = {
                    "id": temp["id"],
                    "name": temp["name"],
                    "temperature": temp["current_temp"],
                    "unit": temp["unit"],
                    "status": temp["status"],
                }
                clean_temps.append(clean_temp)

            # Output formatted JSON
            print(json.dumps({"temperatures": clean_temps}, indent=2))

        elif output_format == OutputFormat.YAML:
            # Clean up temperature data for YAML output
            clean_temps = []
            for temp in temps:
                clean_temp = {
                    "id": temp["id"],
                    "name": temp["name"],
                    "temperature": temp["current_temp"],
                    "unit": temp["unit"],
                    "status": temp["status"],
                }
                clean_temps.append(clean_temp)

            # Output formatted YAML
            print(yaml.dump({"temperatures": clean_temps}, sort_keys=False))

    except Exception as e:
        error_msg = f"Error reading temperature status: {str(e)}"
        if output_format == OutputFormat.TABLE:
            logger.error(error_msg)
            logger.print_troubleshooting_tips()
        elif output_format == OutputFormat.JSON:
            print(json.dumps({"error": error_msg}))
        elif output_format == OutputFormat.YAML:
            print(yaml.dump({"error": error_msg}))

        sys.exit(1)
    finally:
        # Only disconnect for python-ipmi implementation
        if not USING_IPMITOOL:
            try:
                controller.disconnect()
            except Exception as disconnect_err:
                if output_format == OutputFormat.TABLE:
                    logger.warning(f"Warning during disconnect: {str(disconnect_err)}")


@app.command("pid")
def pid_control(
    ctx: typer.Context,
    target_temp: float = typer.Option(
        60.0,
        "--target",
        "-t",
        envvar="IPMI_PID_TARGET_TEMP",
        help="Target temperature in Celsius (env: IPMI_PID_TARGET_TEMP)",
    ),
    interval: float = typer.Option(
        30.0,
        "--interval",
        "-i",
        envvar="IPMI_PID_INTERVAL",
        help="Monitoring interval in seconds (env: IPMI_PID_INTERVAL)",
    ),
    p_gain: float = typer.Option(
        0.1,
        "--p",
        envvar="IPMI_PID_P_GAIN",
        help="Proportional gain (env: IPMI_PID_P_GAIN)",
    ),
    i_gain: float = typer.Option(
        0.02,
        "--i",
        envvar="IPMI_PID_I_GAIN",
        help="Integral gain (env: IPMI_PID_I_GAIN)",
    ),
    d_gain: float = typer.Option(
        0.01,
        "--d",
        envvar="IPMI_PID_D_GAIN",
        help="Derivative gain (env: IPMI_PID_D_GAIN)",
    ),
    min_speed: float = typer.Option(
        30.0,
        "--min",
        envvar="IPMI_PID_MIN_SPEED",
        help="Minimum fan speed percentage (env: IPMI_PID_MIN_SPEED)",
    ),
    max_speed: float = typer.Option(
        100.0,
        "--max",
        envvar="IPMI_PID_MAX_SPEED",
        help="Maximum fan speed percentage (env: IPMI_PID_MAX_SPEED)",
    ),
    runtime: Optional[int] = typer.Option(
        None,
        "--time",
        envvar="IPMI_PID_RUNTIME",
        help="Run time in seconds (runs until Ctrl+C if not specified) (env: IPMI_PID_RUNTIME)",
    ),
):
    """Run temperature-based fan control with PID controller."""
    controller = ctx.obj["controller"]
    output_format = ctx.obj["output_format"]
    auto_restore = ctx.obj["auto_restore"]

    # Set up cleanup handlers
    setup_cleanup(controller, auto_restore)

    # PID controller only supports table output format
    if output_format != OutputFormat.TABLE:
        logger.warning("Note: PID control only supports table output format")

    try:
        # For ipmitool implementation, we need to test the connection
        if USING_IPMITOOL:
            controller.test_connection()
        else:
            controller.connect()

        # Configure PID controller
        controller.configure_pid(p_gain, i_gain, d_gain, min_speed, max_speed)
        controller.set_target_temperature(target_temp)
        controller.set_monitor_interval(interval)

        logger.section_header(
            f"PID Temperature Control - Target: {target_temp}°C | Interval: {interval}s"
        )

        if auto_restore:
            logger.info("Automatic fan control will be restored on exit")

        def update_display(status):
            """Callback for updating the display."""
            logger.print_pid_status(status)

        # Start monitoring
        controller.start_temperature_monitoring(
            target_temp=target_temp, interval=interval, callback=update_display
        )

        try:
            if runtime:
                # Run for specified duration
                time.sleep(runtime)
            else:
                # Run until interrupted
                logger.info("PID control started. Press Ctrl+C to stop...")
                while True:
                    time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            # Ensure we stop monitoring when done
            controller.stop_temperature_monitoring()
            logger.success("PID temperature control stopped")

    except Exception as e:
        logger.error(f"Error in PID temperature control: {str(e)}")
        sys.exit(1)
    finally:
        # Only disconnect for python-ipmi implementation
        if not USING_IPMITOOL:
            try:
                if hasattr(controller, "disconnect"):
                    controller.disconnect()
            except Exception:
                pass


if __name__ == "__main__":
    app()
