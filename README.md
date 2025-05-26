# Dell IPMI Fan Control

A command-line tool to manage Dell server fan speeds using IPMI. Features include manual fan control, automatic control, and an advanced PID controller for temperature-based fan management.

This tool supports two backends:
1. ipmitool (preferred) - uses the system's ipmitool command for better compatibility
2. python-ipmi library - used as fallback if ipmitool is not installed

## Installation

There are several ways to install this tool:

### Using the dependency installation script (recommended)

This script creates a virtual environment, installs all dependencies, and installs the tool:

```bash
# Run the dependency installation script
./scripts/install_deps.sh

# Activate the virtual environment
source .venv/bin/activate

# Now you can use the tool
ipmi-fan --help
```

### Manual installation

```bash
# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate

# Install using pip
pip install .

# Or install with uv
uv pip install .
```

## Usage

### Command Line

```bash
# Show help
ipmi-fan --help

# Connect to a Dell iDRAC using lanplus interface (default)
ipmi-fan --host 192.168.1.100 --username root --password calvin status

# If lanplus doesn't work, try the lan interface
ipmi-fan --host 192.168.1.100 --username root --password calvin --interface lan status

# Get current fan speeds
ipmi-fan status

# Get current temperature sensors
ipmi-fan temp

# Set fan speed to 50%
ipmi-fan set 50

# Enable automatic fan control
ipmi-fan auto

# Run PID temperature control with default settings
ipmi-fan pid

# Enable debug mode for troubleshooting
ipmi-fan --debug status

# Test compatibility with your Dell server (read-only test)
ipmi-fan --host 192.168.1.100 --username root --password calvin test

# Test compatibility including fan control (brief fan speed adjustment)
ipmi-fan --host 192.168.1.100 --username root --password calvin test --full

# Run diagnostic tests showing raw output from IPMI commands
ipmi-fan --host 192.168.1.100 --username root --password calvin test --diagnostic

# Output in JSON format
ipmi-fan --output json status

# Output in YAML format
ipmi-fan --output yaml temp

# Run PID control with default settings (extremely gentle response)
ipmi-fan pid --target 65 

# Slightly more responsive PID control
ipmi-fan pid --target 65 --p 0.3 --i 0.05 --d 0.02 --min 35 --max 90

# Moderate response for better cooling
ipmi-fan pid --target 62 --p 0.6 --i 0.08 --d 0.04

# Run PID control for a specific time period (in seconds)
ipmi-fan pid --time 3600
```

### Environment Variables

All CLI parameters can be configured using environment variables. This is especially useful for Docker deployments or when you don't want to specify credentials on the command line.

```bash
# Connection settings
export IPMI_HOST=192.168.1.100
export IPMI_PORT=623
export IPMI_USERNAME=root
export IPMI_PASSWORD=calvin
export IPMI_INTERFACE=lanplus

# General settings
export IPMI_DEBUG=false
export IPMI_AUTO_RESTORE=true
export IPMI_OUTPUT_FORMAT=table

# PID controller settings
export IPMI_PID_TARGET_TEMP=60.0
export IPMI_PID_INTERVAL=30.0
export IPMI_PID_P_GAIN=0.1
export IPMI_PID_I_GAIN=0.02
export IPMI_PID_D_GAIN=0.01
export IPMI_PID_MIN_SPEED=30.0
export IPMI_PID_MAX_SPEED=100.0

# Test settings
export IPMI_TEST_QUICK=true
export IPMI_TEST_DIAGNOSTIC=false

# Now you can run commands without specifying parameters
ipmi-fan status
ipmi-fan pid
```

You can also use a `.env` file:

```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your settings
nano .env

# The tool will automatically read the .env file
ipmi-fan status
```

### Docker Usage

The tool includes full Docker support for easy deployment and isolation:

```bash
# Build the Docker image
./scripts/docker-run.sh build

# Copy and edit environment file
cp .env.example .env
# Edit .env with your IPMI credentials

# Run various commands
./scripts/docker-run.sh status          # Check fan status
./scripts/docker-run.sh temp            # Check temperatures
./scripts/docker-run.sh test            # Quick compatibility test
./scripts/docker-run.sh test full       # Full compatibility test
./scripts/docker-run.sh set 50          # Set fan speed to 50%
./scripts/docker-run.sh auto            # Enable automatic control
./scripts/docker-run.sh pid 65          # Run PID control (target 65°C)

# Open interactive shell in container
./scripts/docker-run.sh shell

# Using docker-compose for persistent service
docker-compose up -d
docker-compose logs -f
```

#### Docker Environment Variables

The Docker containers use the same environment variables as the CLI. You can either:

1. Use a `.env` file (recommended):
   ```bash
   cp .env.example .env
   # Edit .env file
   docker-compose up
   ```

2. Set variables directly in docker-compose.yml or pass them to docker run:
   ```bash
   docker run --rm -e IPMI_HOST=192.168.1.100 -e IPMI_USERNAME=root ipmi-fan-control status
   ```

## PID Controller

The tool includes a PID (Proportional-Integral-Derivative) controller for advanced temperature-based fan speed management. This allows you to:

- Set a target temperature for your server
- Automatically adjust fan speeds to maintain that temperature
- Fine-tune the PID parameters for your specific hardware
- Monitor temperatures and fan speeds in real time

### PID Parameters

- `--target`: Target temperature in Celsius (default: 60.0)
- `--interval`: Monitoring interval in seconds (default: 30.0)
- `--p`: Proportional gain (default: 0.1) - Controls immediate response to temperature differences
- `--i`: Integral gain (default: 0.02) - Controls response to persistent temperature differences
- `--d`: Derivative gain (default: 0.01) - Controls response to rapid temperature changes
- `--min`: Minimum fan speed percentage (default: 30.0)
- `--max`: Maximum fan speed percentage (default: 100.0)

#### Advanced Control System

The fan controller combines:
1. A smooth response curve that maps temperature errors to fan speeds
2. A gentle PID controller for fine-tuning the response
3. Rate limiting to prevent sudden fan speed changes

#### PID Tuning Tips

The default values are extremely conservative to prevent oscillation. For different behaviors:

- **Ultra stable (no oscillation)**: Use ultra-low values (e.g., `--p 0.05 --i 0.01 --d 0.005`)
- **More responsive**: Increase P value (e.g., `--p 0.3 --i 0.05 --d 0.02`)
- **Aggressive cooling**: Higher values (e.g., `--p 0.8 --i 0.1 --d 0.05`) - use with caution
- **Reduce oscillation**: Decrease all values, especially the I value
- **Better setpoint tracking**: Increase I value slightly, but be cautious

The PID controller includes rate limiting and initial ramp-up management to prevent fan speed jumps.

## Requirements

- Python 3.8+
- typer and rich libraries (for the CLI interface)
- ipmitool (recommended) - provides better compatibility with Dell servers
- python-ipmi library (alternative backend if ipmitool is not available)
- PyYAML (for YAML output format support)

### Installing Dependencies

Make sure all Python dependencies are installed:

```bash
# Install with pip
pip install typer rich python-ipmi pyyaml

# Or with uv
uv pip install typer rich python-ipmi pyyaml
```

For ipmitool:
```bash
# Debian/Ubuntu
sudo apt install ipmitool

# RHEL/CentOS/Fedora
sudo dnf install ipmitool

# Arch Linux
sudo pacman -S ipmitool
```

## Development

### Linting

This project uses [ruff](https://github.com/astral-sh/ruff) for linting. To run the linter:

```bash
# Run linter
./scripts/lint.sh

# Run linter and automatically fix issues
./scripts/lint.sh --fix
```

The linter configuration is in `pyproject.toml` and includes:
- Code style checks (PEP 8)
- Import sorting
- Basic Pylint rules
- Maximum complexity limits

### Testing

This project uses pytest for testing. To run the tests:

```bash
# Run the test suite with the provided script
./scripts/run_tests.sh

# Run specific tests
./scripts/run_tests.sh tests/test_pid_controller.py

# Run tests with specific markers
./scripts/run_tests.sh -m "not slow"

# Generate a coverage report
./scripts/run_tests.sh --cov=ipmi_fan_control
```

The test suite includes:
- Unit tests for the PID controller
- Unit tests for the IPMI interface
- Integration tests for the CLI commands

You can also run pytest directly if you have it installed:
```bash
python -m pytest
```

## Dell Server Compatibility

This tool is specifically designed for Dell PowerEdge servers with iDRAC management interfaces. It uses Dell-specific IPMI commands to control fan speeds.

### Verified Dell OEM Commands
The tool uses these verified Dell-specific IPMI commands:
```bash
# Enable manual fan control
ipmitool raw 0x30 0x30 0x01 0x00

# Set fan speed to 30% (hex 0x1e)
ipmitool raw 0x30 0x30 0x02 0xff 0x1e

# Set fan speed to 40% (hex 0x28)
ipmitool raw 0x30 0x30 0x02 0xff 0x28

# Return to automatic fan control
ipmitool raw 0x30 0x30 0x01 0x01
```

### Tested Server Models
These commands have been tested on:
- Dell PowerEdge R7xx series (R710, R720, R730, etc.)
- Dell PowerEdge R6xx series (R610, R620, R630, etc.)
- Dell PowerEdge R4xx series
- Dell PowerEdge T series

Note: While these commands work on most Dell PowerEdge servers with iDRAC, there might be slight variations between server generations. The tool is designed to be compatible with as many models as possible.

## Warning

Manually controlling server fans can potentially cause overheating if not used carefully. Always monitor temperatures when using manual fan control and revert to automatic control if you're unsure. The PID controller provides a safer alternative by automatically adjusting fan speeds based on temperature.

## Troubleshooting

If you encounter issues connecting to your Dell iDRAC, try the following:

### Connection Issues
1. Verify your iDRAC IP address, username, and password
2. Ensure network connectivity to the iDRAC (try pinging it)
3. Check if IPMI over LAN is enabled in iDRAC settings
4. **Try both interface types**: If `lanplus` (default) doesn't work, try `lan`:
   ```bash
   ipmi-fan --interface lan --host 192.168.1.100 --username root --password calvin status
   ```
5. **Install ipmitool** for better compatibility:
   ```bash
   # Debian/Ubuntu
   sudo apt install ipmitool
   
   # RHEL/CentOS/Fedora
   sudo dnf install ipmitool
   
   # Arch Linux
   sudo pacman -S ipmitool
   ```
6. Run the diagnostic test which shows raw command outputs:
   ```bash
   ipmi-fan --host 192.168.1.100 --username root --password calvin test --diagnostic
   ```

7. Enable debug mode with the `--debug` flag:
   ```bash
   ipmi-fan --debug --host 192.168.1.100 --username root --password calvin status
   ```

### Verify ipmitool works directly
This can help isolate if the issue is with the tool or your IPMI setup:

```bash
# Try reading the chassis status
ipmitool -I lanplus -H 192.168.1.100 -U root -P calvin chassis status

# Try reading sensor data
ipmitool -I lanplus -H 192.168.1.100 -U root -P calvin sdr type fan
```

### Sensor Reading Issues
If you can connect but can't read fan or temperature data:
1. Check that your account has sufficient privileges in iDRAC
2. Try updating your iDRAC firmware to the latest version
3. Different Dell server generations may require specific IPMI commands - check compatibility notes

### Dell Server Model Compatibility
The tool uses standard Dell IPMI commands, but specific implementations can vary between models. You may need to modify the Dell OEM constants in either:
- `ipmi_fan_control/ipmitool.py` for the ipmitool implementation
- `ipmi_fan_control/ipmi.py` for the python-ipmi implementation

The tool automatically chooses the best implementation, preferring ipmitool for better compatibility.