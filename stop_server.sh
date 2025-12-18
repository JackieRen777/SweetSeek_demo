#!/bin/bash
# SweetSeek 服务器停止脚本

echo "正在停止 SweetSeek 服务器..."

# 查找并停止进程
pkill -f "python.*app.py"

if [ $? -eq 0 ]; then
    echo "✅ 服务器已停止"
else
    echo "⚠️  没有找到运行中的服务器"
fi
