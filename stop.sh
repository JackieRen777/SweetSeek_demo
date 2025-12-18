#!/bin/bash
# SweetSeek 停止脚本

if pgrep -f "python.*app.py" > /dev/null; then
    pkill -f "python.*app.py"
    echo "✅ SweetSeek 已停止"
else
    echo "⚠️  服务器未运行"
fi
