#!/bin/bash
# SweetSeek 自动启动脚本

cd "$(dirname "$0")" || exit 1
source .venv/bin/activate
nohup python3 app.py > /dev/null 2>&1 &

echo "✅ SweetSeek 已启动"
echo "访问: http://localhost:5001"
