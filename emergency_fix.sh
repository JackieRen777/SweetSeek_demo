#!/bin/bash
# 紧急修复脚本 - 更新服务器代码并修复references显示

echo "=========================================="
echo "🚨 紧急修复 - References显示问题"
echo "=========================================="

# 服务器信息
SERVER="root@8.137.32.247"
PROJECT_DIR="/www/wwwroot/FCN_SweetSeek"

echo ""
echo "步骤 1: 连接服务器并拉取最新代码..."
ssh $SERVER << 'ENDSSH'
cd /www/wwwroot/FCN_SweetSeek

echo "当前分支:"
git branch

echo ""
echo "拉取最新代码..."
git pull origin RenJiaqi

echo ""
echo "步骤 2: 修复向量数据库路径..."
python3 fix_vector_db_paths.py

echo ""
echo "步骤 3: 重启Flask应用..."
pkill -f "python3 app.py"
sleep 3

# 启动应用
cd /www/wwwroot/FCN_SweetSeek
nohup python3 app.py > logs/app.log 2>&1 &

sleep 2

echo ""
echo "步骤 4: 验证服务状态..."
ps aux | grep "python3 app.py" | grep -v grep

echo ""
echo "步骤 5: 检查健康状态..."
curl -s http://localhost:5001/api/health | python3 -m json.tool

echo ""
echo "步骤 6: 查看最新日志..."
tail -20 logs/sweetseek.log

echo ""
echo "=========================================="
echo "✅ 修复完成！"
echo "=========================================="
echo ""
echo "请测试："
echo "1. 访问 http://sweetseek.top"
echo "2. 强制刷新 (Cmd+Shift+R)"
echo "3. 提问并检查references"
echo ""

ENDSSH

echo ""
echo "本地操作完成！"
