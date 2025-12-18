#!/bin/bash
# SweetSeek 服务器管理
# 用法：
#   ./server.sh start     # 后台启动
#   ./server.sh stop      # 停止服务器
#   ./server.sh restart   # 重启服务器
#   ./server.sh status    # 查看状态
#   ./server.sh dev       # 前台启动（开发模式）

# 切换到脚本所在目录
cd "$(dirname "$0")" || exit 1

# 显示使用帮助
show_help() {
    echo "用法: ./server.sh [命令]"
    echo ""
    echo "命令:"
    echo "  start      后台启动服务器"
    echo "  stop       停止服务器"
    echo "  restart    重启服务器"
    echo "  status     查看服务器状态"
    echo "  dev        前台启动（开发模式）"
    echo ""
}

# 检查虚拟环境
check_venv() {
    if [ ! -d ".venv" ]; then
        echo "📦 创建虚拟环境..."
        python3 -m venv .venv
    fi
    
    source .venv/bin/activate
    
    if [ ! -f ".venv/installed" ]; then
        echo "📥 安装依赖..."
        pip install -r requirements.txt > /dev/null 2>&1
        touch .venv/installed
    fi
}

# 启动服务器（后台）
start_server() {
    # 检查是否已运行
    if pgrep -f "python.*app.py" > /dev/null; then
        echo "⚠️  服务器已在运行"
        echo "   查看状态: ./server.sh status"
        exit 1
    fi
    
    check_venv
    
    # 后台启动
    nohup python3 app.py > /dev/null 2>&1 &
    
    echo "✅ SweetSeek 已启动（后台）"
    echo "   访问: http://localhost:5001"
    echo "   停止: ./server.sh stop"
    echo ""
    echo "💡 提示: 首次启动需要加载模型，请等待30秒后访问"
}

# 停止服务器
stop_server() {
    if pgrep -f "python.*app.py" > /dev/null; then
        pkill -f "python.*app.py"
        echo "✅ SweetSeek 已停止"
    else
        echo "⚠️  服务器未运行"
    fi
}

# 重启服务器
restart_server() {
    echo "🔄 重启服务器..."
    stop_server
    sleep 2
    start_server
}

# 查看状态
show_status() {
    echo "📊 SweetSeek 服务器状态"
    echo ""
    
    if pgrep -f "python.*app.py" > /dev/null; then
        PID=$(pgrep -f "python.*app.py")
        echo "✅ 服务器正在运行 (PID: $PID)"
        
        # 测试 API
        if curl -s http://localhost:5001/api/stats > /dev/null 2>&1; then
            echo "✅ API 响应正常"
            echo ""
            echo "访问: http://localhost:5001"
        else
            echo "⚠️  API 无响应（可能正在启动）"
        fi
    else
        echo "❌ 服务器未运行"
        echo ""
        echo "启动: ./server.sh start"
    fi
}

# 前台启动（开发模式）
dev_mode() {
    # 检查是否已运行
    if pgrep -f "python.*app.py" > /dev/null; then
        echo "⚠️  服务器已在运行"
        echo "   请先停止: ./server.sh stop"
        exit 1
    fi
    
    check_venv
    
    echo "================================"
    echo "   SweetSeek 启动中..."
    echo "================================"
    echo ""
    echo "访问: http://localhost:5001"
    echo "停止: Ctrl+C"
    echo ""
    
    # 前台运行
    python3 app.py
}

# 主逻辑
case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        show_status
        ;;
    dev)
        dev_mode
        ;;
    *)
        show_help
        exit 1
        ;;
esac
