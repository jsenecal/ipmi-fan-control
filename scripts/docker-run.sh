#!/bin/bash
# Docker helper script for IPMI Fan Control

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ ${1}${NC}"
}

print_success() {
    echo -e "${GREEN}✓ ${1}${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ ${1}${NC}"
}

print_error() {
    echo -e "${RED}✗ ${1}${NC}"
}

# Function to check if .env file exists
check_env_file() {
    if [ ! -f .env ]; then
        print_warning ".env file not found"
        print_info "Creating .env from template..."
        cp .env.example .env
        print_warning "Please edit .env file with your IPMI credentials before running the container"
        return 1
    fi
    return 0
}

# Function to build the Docker image
build_image() {
    local push_flag="$1"
    
    # Get version from pyproject.toml
    local version=$(./scripts/get_version.sh)
    if [ $? -ne 0 ]; then
        print_error "Failed to get version"
        exit 1
    fi
    
    print_info "Building Docker image version ${version}..."
    
    # Build with version as build arg
    docker build --build-arg VERSION="$version" \
        -t jsenecal/ipmi-fan-control:latest \
        -t jsenecal/ipmi-fan-control:"$version" .
    
    print_success "Docker image built successfully (version: $version)"
    
    # Push if requested
    if [ "$push_flag" = "--push" ] || [ "$push_flag" = "-p" ]; then
        print_info "Pushing Docker images..."
        docker push jsenecal/ipmi-fan-control:latest
        docker push jsenecal/ipmi-fan-control:"$version"
        print_success "Docker images pushed successfully"
    fi
}

# Function to run different commands
run_status() {
    print_info "Running fan status check..."
    docker run --rm --env-file .env --network host jsenecal/ipmi-fan-control:latest ipmi-fan status
}

run_temp() {
    print_info "Running temperature status check..."
    docker run --rm --env-file .env --network host jsenecal/ipmi-fan-control:latest ipmi-fan temp
}

run_test() {
    local test_type="${1:-quick}"
    if [ "$test_type" = "full" ]; then
        print_info "Running full compatibility test..."
        docker run --rm --env-file .env --network host jsenecal/ipmi-fan-control:latest ipmi-fan test --full
    else
        print_info "Running quick compatibility test..."
        docker run --rm --env-file .env --network host jsenecal/ipmi-fan-control:latest ipmi-fan test --quick
    fi
}

run_set_speed() {
    local speed="$1"
    if [ -z "$speed" ]; then
        print_error "Please specify fan speed percentage (0-100)"
        exit 1
    fi
    print_info "Setting fan speed to ${speed}%..."
    docker run --rm --env-file .env --network host jsenecal/ipmi-fan-control:latest ipmi-fan set "$speed"
}

run_auto() {
    print_info "Enabling automatic fan control..."
    docker run --rm --env-file .env --network host jsenecal/ipmi-fan-control:latest ipmi-fan auto
}

run_pid() {
    local target_temp="${1:-60}"
    print_info "Starting PID temperature control (target: ${target_temp}°C)..."
    print_warning "Press Ctrl+C to stop"
    docker run --rm --env-file .env --network host -it jsenecal/ipmi-fan-control:latest ipmi-fan pid --target "$target_temp"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [command] [options]"
    echo
    echo "Commands:"
    echo "  build [--push|-p]  Build the Docker image (optionally push to registry)"
    echo "  status             Show fan status"
    echo "  temp               Show temperature sensors"
    echo "  test [quick|full]  Run compatibility test (default: quick)"
    echo "  set <percentage>   Set fan speed (0-100%)"
    echo "  auto               Enable automatic fan control"
    echo "  pid [target_temp]  Run PID temperature control (default: 60°C)"
    echo "  shell              Open interactive shell in container"
    echo "  logs               Show container logs (when running with docker-compose)"
    echo
    echo "Examples:"
    echo "  $0 build          # Build image locally"
    echo "  $0 build --push   # Build and push to registry"
    echo "  $0 status"
    echo "  $0 test full"
    echo "  $0 set 50"
    echo "  $0 pid 65"
    echo
    echo "Note: Ensure your .env file is configured with correct IPMI credentials"
}

# Main script logic
case "${1:-}" in
    build)
        build_image "$2"
        ;;
    status)
        check_env_file && run_status
        ;;
    temp)
        check_env_file && run_temp
        ;;
    test)
        check_env_file && run_test "$2"
        ;;
    set)
        check_env_file && run_set_speed "$2"
        ;;
    auto)
        check_env_file && run_auto
        ;;
    pid)
        check_env_file && run_pid "$2"
        ;;
    shell)
        print_info "Opening interactive shell..."
        docker run --rm --env-file .env --network host -it jsenecal/ipmi-fan-control:latest /bin/bash
        ;;
    logs)
        print_info "Showing container logs..."
        docker-compose logs -f
        ;;
    *)
        show_usage
        exit 1
        ;;
esac