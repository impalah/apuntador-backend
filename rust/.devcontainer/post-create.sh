#!/bin/bash
set -e

echo "🦀 Setting up Rust development environment..."

# Install cargo-watch for hot reload
if ! command -v cargo-watch &> /dev/null; then
    echo "📦 Installing cargo-watch..."
    cargo install cargo-watch
fi

# Install cargo-edit for dependency management
if ! command -v cargo-edit &> /dev/null; then
    echo "📦 Installing cargo-edit..."
    cargo install cargo-edit
fi

# Fetch dependencies
echo "📦 Fetching dependencies..."
cargo fetch

echo "✅ Rust environment ready!"
