#!/bin/bash

# 重建向量索引脚本
# 用于修复路径不匹配导致的文献名称显示问题

echo "=========================================="
echo "  重建向量索引"
echo "=========================================="
echo ""

echo "[1/4] 停止服务..."
pkill -f "python.*app.py"
sleep 2
echo "✅ 服务已停止"
echo ""

echo "[2/4] 删除旧索引..."
rm -rf chroma_db
echo "✅ 旧索引已删除"
echo ""

echo "[3/4] 启动服务（自动重建索引）..."
source venv/bin/activate
nohup python app.py > logs/app.log 2>&1 &
echo "✅ 服务已启动，正在后台重建索引..."
echo ""

echo "[4/4] 监控索引重建进度..."
echo "提示：索引重建需要几分钟时间"
echo "可以使用以下命令查看进度："
echo "  tail -f logs/app.log"
echo ""

sleep 5

if netstat -tunlp | grep 5001 > /dev/null; then
    echo "✅ 服务运行正常"
    echo ""
    echo "索引重建正在后台进行，请等待几分钟后测试"
else
    echo "❌ 服务启动失败，查看日志："
    tail -30 logs/app.log
fi
