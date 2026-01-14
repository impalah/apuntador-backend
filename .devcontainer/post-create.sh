#!/bin/bash
set -e

echo "Setting up Python + Rust development environment..."

# Python setup
echo "Setting up Python environment..."
cd /workspaces/apuntador-backend/python
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -e . || echo " Python dependencies will be installed on first use"
cd /workspaces/apuntador-backend

# Rust setup
echo "Setting up Rust environment..."
cd /workspaces/apuntador-backend/rust
source $HOME/.cargo/env
cargo fetch || echo " Rust dependencies will be fetched on first build"
cd /workspaces/apuntador-backend

# Create .env if not exists
if [ ! -f "python/.env" ] && [ -f ".env.example" ]; then
    echo " Creating python/.env from template..."
    cp .env.example python/.env
fi

if [ ! -f "rust/.env" ] && [ -f ".env.example" ]; then
    echo " Creating rust/.env from template..."
    cp .env.example rust/.env
fi

echo ""
echo " Environment setup complete!"
echo ""
echo " Quick Start:"
echo "   Python: cd python && make dev"
echo "   Rust:   cd rust && make dev"
echo ""
echo " Documentation:"
echo "   - docs/DEVELOPMENT_WORKFLOW.md"
echo "   - docs/MIGRATION_CONTEXT.md"
echo "   - docs/COPILOT_USAGE.md"
