#!/bin/bash
# SweetSeek 启动脚本
# 用法：
#   ./start.sh          # 前台运行（开发模式）
#   ./start.sh -d       # 后台运行（日常使用）

# 切换到脚本所在目录
cd "$(dirname "$0")" || exit 1

# 检查是否后台模式
DAEMON_MODE=false
if [[ "$1" == "-d" ]] || [[ "$1" == "--daemon" ]]; then
    DAEMON_MODE=true
fi

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv .venv
fi

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖（仅首次）
if [ ! -f ".venv/installed" ]; then
    echo "📥 安装依赖..."
    pip install -r requirements.txt > /dev/null 2>&1
    touch .venv/installed
fi

# 后台模式
if [ "$DAEMON_MODE" = true ]; then
    # 检查是否已运行
    if pgrep -f "python.*app.py" > /dev/null; then
        echo "⚠️  服务器已在运行"
        echo "   停止: ./stop.sh"
        exit 1
    fi
    
    # 后台启动
    nohup python3 app.py > /dev/null 2>&1 &
    
    echo "⏳ 启动中..."
    sleep 3
    
    if pgrep -f "python.*app.py" > /dev/null; then
        echo "✅ SweetSeek 已启动（后台）"
        echo "   访问: http://localhost:5001"
        echo "   停止: ./stop.sh"
        echo ""
        echo "💡 提示: 首次启动需要加载模型，请等待30秒后访问"
    else
        echo "❌ 启动失败，请查看日志"
        exit 1
    fi
else
    # 前台模式
    echo "================================"
    echo "   SweetSeek 启动中..."
    echo "================================"
    echo ""
    echo "访问: http://localhost:5001"
    echo "停止: Ctrl+C"
    echo ""
    
    # 前台运行
    python3 app.py
fi
