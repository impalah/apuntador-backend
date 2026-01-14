FROM mcr.microsoft.com/devcontainers/base:bookworm

# Install system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    build-essential \
    curl \
    git \
    pkg-config \
    libssl-dev \
    protobuf-compiler \
    python3 \
    python3-pip \
    python3-venv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

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
