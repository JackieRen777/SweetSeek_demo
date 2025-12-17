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

# Ask if user wants to enable file monitoring
echo ""
read -p "启用文件监控（自动处理新文献）? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔍 启动文件监控系统..."
    python auto_update_system.py &
    WATCHER_PID=$!
    echo "✅ 文件监控已启动 (PID: $WATCHER_PID)"
    echo "   现在可以直接拖文件到 food_research_data/papers/ 目录"
    echo ""
    
    # Cleanup function
    cleanup() {
        echo ""
        echo "🛑 停止文件监控..."
        kill $WATCHER_PID 2>/dev/null
        echo "👋 再见！"
        exit 0
    }
    
    # Register cleanup on exit
    trap cleanup SIGINT SIGTERM
fi

# Start the application
echo ""
echo "================================"
echo "🚀 Starting SweetSeek..."
echo "================================"
echo ""
python app.py

# Cleanup on exit (if watcher was started)
if [[ $REPLY =~ ^[Yy]$ ]]; then
    kill $WATCHER_PID 2>/dev/null
fi
