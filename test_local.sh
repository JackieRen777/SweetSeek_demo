#!/bin/bash
# 本地测试脚本

echo "=========================================="
echo "🧪 启动本地测试环境"
echo "=========================================="

# 检查端口是否被占用
if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  端口 5001 已被占用，正在停止旧进程..."
    pkill -f "python3 app.py"
    sleep 2
fi

# 启动应用
echo ""
echo "🚀 启动Flask应用..."
echo "📍 访问地址: http://localhost:5001"
echo "🛑 停止服务: 按 Ctrl+C"
echo ""
echo "=========================================="
echo ""

# 前台运行，可以看到实时日志
python3 app.py
