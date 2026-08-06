#!/bin/bash

echo "正在重启 SweetSeek 服务..."
echo ""

ssh -tt root@8.136.8.223 << 'EOF'
cd /www/wwwroot/FCN_SweetSeek
echo "1. 停止旧进程..."
pkill -f "python.*app.py"
netstat -tunlp 2>/dev/null | grep 5001 | awk '{print $7}' | cut -d'/' -f1 | xargs -r kill -9
sleep 2

echo "2. 启动新进程..."
mkdir -p logs
nohup ./venv/bin/python3 app.py > logs/app.log 2>&1 &

echo "3. 检查服务状态..."
for i in {1..20}; do
    if netstat -tunlp 2>/dev/null | grep 5001 > /dev/null; then
        break
    fi
    sleep 1
done

if netstat -tunlp | grep 5001 > /dev/null; then
    echo "✅ 服务启动成功！"
    echo "访问地址: http://8.136.8.223:5001"
else
    echo "❌ 服务启动失败，查看日志："
    tail -20 logs/app.log
fi
EOF
