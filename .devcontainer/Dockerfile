FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

# Install uv and move binary to global PATH
RUN curl -Ls https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/ && \
    mv /root/.local/bin/uvx /usr/local/bin/

# Install AWS CLI v2 and jq with automatic architecture detection
RUN apt-get update && \
    apt-get install -y unzip curl groff less jq && \
    ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        AWS_CLI_URL="https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip"; \
    elif [ "$ARCH" = "aarch64" ]; then \
        AWS_CLI_URL="https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip"; \
    else \
        echo "❌ Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    curl "$AWS_CLI_URL" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws

# Set working directory
WORKDIR /workspace

# Copy files to sync dependencies
COPY pyproject.toml ./
COPY uv.lock* ./

# Don't create environment or install here - that's done by postCreateCommand
