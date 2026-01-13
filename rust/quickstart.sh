#!/bin/bash
# Quick start script for Rust backend

set -e

echo "🦀 Apuntador Rust Backend - Quick Start"
echo "======================================="

# Check if in devcontainer
if [ ! -f /.dockerenv ]; then
    echo "⚠️  WARNING: Not running in devcontainer"
    echo "   Recommended: Open rust/ folder and 'Reopen in Container'"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Rust installation
if ! command -v cargo &> /dev/null; then
    echo "❌ Rust not found! Installing..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source $HOME/.cargo/env
fi

# Check .env
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp ../.env.example .env
    echo "⚠️  IMPORTANT: Edit .env and add your OAuth credentials!"
    echo ""
fi

# Build project
echo "🔨 Building project..."
cargo build

# Run tests
echo "🧪 Running tests..."
cargo test || {
    echo "⚠️  Some tests failed, but continuing..."
}

# Start server
echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Starting development server..."
echo "   URL: http://localhost:8000"
echo "   Health: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop"
echo ""

cargo run --bin server
