#!/bin/bash
# SweetSeek Startup Script

echo "================================"
echo "   SweetSeek Starting..."
echo "================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "   Please copy .env.example to .env and configure your API key"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies if needed
if [ ! -f ".venv/installed" ]; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
    touch .venv/installed
fi

# Start the application
echo ""
echo "================================"
echo "🚀 Starting SweetSeek..."
echo "================================"
echo ""
python app.py
