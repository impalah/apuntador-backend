#!/bin/bash
# Quick start script for Python backend

set -e

echo "🐍 Apuntador Python Backend - Quick Start"
echo "========================================"

# Check if in devcontainer
if [ ! -f /.dockerenv ]; then
    echo "⚠️  WARNING: Not running in devcontainer"
    echo "   Recommended: Open python/ folder and 'Reopen in Container'"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check .env
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp ../.env.example .env
    echo "⚠️  IMPORTANT: Edit .env and add your OAuth credentials!"
    echo ""
fi

# Install dependencies
echo "📦 Installing dependencies..."
if command -v uv &> /dev/null; then
    uv pip install -e .
else
    pip install -e .
fi

# Run tests
echo "🧪 Running tests..."
pytest tests/ -v --tb=short || {
    echo "⚠️  Some tests failed, but continuing..."
}

# Start server
echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Starting development server..."
echo "   URL: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo "   Health: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop"
echo ""

uvicorn apuntador.main:app --reload --host 0.0.0.0 --port 8000
