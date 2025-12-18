#!/bin/bash
# SweetSeek 服务器启动脚本

# 项目目录（修改为你的实际路径）
PROJECT_DIR="/Users/jackieren/Desktop/FCN_SweetSeek"

# 切换到项目目录
cd "$PROJECT_DIR" || exit 1

# 激活虚拟环境
source .venv/bin/activate

# 启动服务器（后台运行）
nohup python3 app.py > server.log 2>&1 &

# 获取进程ID
PID=$!

echo "SweetSeek 服务器已启动"
echo "进程ID: $PID"
echo "访问地址: http://localhost:5001"
echo "日志文件: $PROJECT_DIR/server.log"
echo ""
echo "停止服务器: pkill -f 'python.*app.py'"
