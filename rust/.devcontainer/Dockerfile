FROM mcr.microsoft.com/devcontainers/rust:1-bookworm

# Install additional tools
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    pkg-config \
    libssl-dev \
    protobuf-compiler \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install cargo tools
RUN cargo install cargo-watch cargo-edit cargo-audit cargo-deny

USER vscode
