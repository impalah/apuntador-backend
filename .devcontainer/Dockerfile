FROM mcr.microsoft.com/devcontainers/python:2-3.14-bookworm

# Install system dependencies (Rust build tools + utilities)
RUN apt-get update && \
    apt-get install -y \
    unzip curl groff less jq git \
    build-essential pkg-config libssl-dev protobuf-compiler && \
    rm -rf /var/lib/apt/lists/*

# Install uv globally
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/ && \
    mv /root/.local/bin/uvx /usr/local/bin/ && \
    chmod +x /usr/local/bin/uv /usr/local/bin/uvx

# Install AWS CLI v2 with automatic architecture detection
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        AWS_CLI_URL="https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip"; \
    elif [ "$ARCH" = "aarch64" ]; then \
        AWS_CLI_URL="https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip"; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    curl "$AWS_CLI_URL" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws

# Install Terraform with automatic architecture detection
RUN ARCH=$(uname -m) && \
    TERRAFORM_VERSION="1.10.4" && \
    if [ "$ARCH" = "x86_64" ]; then \
        TERRAFORM_ARCH="amd64"; \
    elif [ "$ARCH" = "aarch64" ]; then \
        TERRAFORM_ARCH="arm64"; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    curl -LO "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_${TERRAFORM_ARCH}.zip" && \
    unzip "terraform_${TERRAFORM_VERSION}_linux_${TERRAFORM_ARCH}.zip" && \
    mv terraform /usr/local/bin/ && \
    chmod +x /usr/local/bin/terraform && \
    rm -f "terraform_${TERRAFORM_VERSION}_linux_${TERRAFORM_ARCH}.zip"

# Install Rust
USER vscode
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && . $HOME/.cargo/env \
    && rustup component add clippy rustfmt rust-analyzer

# Install Rust cargo tools
RUN . $HOME/.cargo/env \
    && cargo install cargo-watch cargo-edit cargo-audit

# Install uv (fast Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add Rust to PATH
ENV PATH="/home/vscode/.cargo/bin:${PATH}"

USER vscode
