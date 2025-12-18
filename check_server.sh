#!/bin/bash
# SweetSeek 服务器状态检查脚本

echo "检查 SweetSeek 服务器状态..."
echo ""

# 检查进程
if pgrep -f "python.*app.py" > /dev/null; then
    PID=$(pgrep -f "python.*app.py")
    echo "✅ 服务器正在运行"
    echo "   进程ID: $PID"
    echo ""
    
    # 检查端口
    if lsof -i :5001 > /dev/null 2>&1; then
        echo "✅ 端口5001已监听"
    else
        echo "⚠️  端口5001未监听"
    fi
    
    # 测试API
    echo ""
    echo "测试API连接..."
    if curl -s http://localhost:5001/api/stats > /dev/null 2>&1; then
        echo "✅ API响应正常"
        echo ""
        echo "访问地址: http://localhost:5001"
    else
        echo "❌ API无响应"
    fi
else
    echo "❌ 服务器未运行"
    echo ""
    echo "启动服务器: ./start_server.sh"
fi
