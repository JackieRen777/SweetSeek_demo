#!/bin/bash

echo "正在重启 SweetSeek 服务..."
echo "请输入服务器密码：Fcn509509"
echo ""

ssh root@8.137.32.247 << 'EOF'
cd /www/wwwroot/FCN_SweetSeek
echo "1. 停止旧进程..."
pkill -f "python.*app.py"
sleep 2

echo "2. 启动新进程..."
source venv/bin/activate
nohup python app.py > logs/app.log 2>&1 &
sleep 3

echo "3. 检查服务状态..."
if netstat -tunlp | grep 5001 > /dev/null; then
    echo "✅ 服务启动成功！"
    echo "访问地址: http://8.137.32.247:5001"
else
    echo "❌ 服务启动失败，查看日志："
    tail -20 logs/app.log
fi
EOF
