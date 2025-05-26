# Multi-stage Dockerfile for IPMI Fan Control
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml setup.py ./
COPY ipmi_fan_control/ ./ipmi_fan_control/
COPY README.md ./

# Build wheel
RUN pip install build && python -m build --wheel

# Runtime stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ipmitool \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r ipmi && useradd -r -g ipmi -s /bin/false ipmi

# Set working directory
WORKDIR /app

# Copy wheel from builder stage
COPY --from=builder /app/dist/*.whl /tmp/

# Install the application
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Environment file template not needed for this application

# Create data directory for logs/configs
RUN mkdir -p /app/data && chown -R ipmi:ipmi /app

# Switch to non-root user
USER ipmi

# Set environment variables for better container behavior
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=5s --retries=3 \
    CMD ipmi-fan status || exit 1

# Default command - shows help
CMD ["ipmi-fan", "--help"]

# Labels for metadata
LABEL maintainer="IPMI Fan Control"
LABEL description="Dell IPMI Fan Control Tool"
LABEL version="0.1.0"
LABEL org.opencontainers.image.source="https://github.com/jsenecal/ipmi-fan-control"
LABEL org.opencontainers.image.licenses="MIT"