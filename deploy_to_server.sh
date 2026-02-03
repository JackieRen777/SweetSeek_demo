#!/bin/bash
# 一键部署到服务器脚本
# 使用方法: bash deploy_to_server.sh

echo "=========================================="
echo "🚀 一键部署到服务器"
echo "=========================================="

# 服务器信息
SERVER="root@8.137.32.247"
PROJECT_DIR="/www/wwwroot/FCN_SweetSeek"

echo ""
echo "步骤 1/5: 检查本地Git状态..."
if git diff-index --quiet HEAD --; then
    echo "✅ 本地没有未提交的更改"
else
    echo "⚠️  本地有未提交的更改，请先在Kiro中提交！"
    echo ""
    echo "在Kiro中操作："
    echo "1. 打开源代码管理面板"
    echo "2. 暂存所有更改 (+)"
    echo "3. 输入提交信息: 修正结构逻辑错误"
    echo "4. 提交 (✓)"
    echo "5. 同步更改（推送到GitHub）"
    echo ""
    read -p "完成后按回车继续..."
fi

echo ""
echo "步骤 2/5: 推送到GitHub..."
git push origin RenJiaqi
if [ $? -eq 0 ]; then
    echo "✅ 推送成功"
else
    echo "❌ 推送失败，请检查网络或在Kiro中手动同步"
    exit 1
fi

echo ""
echo "步骤 3/5: 连接服务器并拉取代码..."
ssh $SERVER << ENDSSH
    cd $PROJECT_DIR
    echo "当前目录: \$(pwd)"
    echo "拉取最新代码..."
    git pull origin RenJiaqi
    
    if [ \$? -eq 0 ]; then
        echo "✅ 代码拉取成功"
    else
        echo "❌ 代码拉取失败"
        exit 1
    fi
ENDSSH

if [ $? -ne 0 ]; then
    echo "❌ 服务器操作失败"
    exit 1
fi

echo ""
echo "步骤 4/5: 重启服务器应用..."
ssh $SERVER << ENDSSH
    cd $PROJECT_DIR
    
    echo "停止旧进程..."
    pkill -f "python3 app.py"
    sleep 3
    
    echo "启动新进程..."
    nohup python3 app.py > logs/app.log 2>&1 &
    sleep 2
    
    echo "验证进程..."
    if ps aux | grep "python3 app.py" | grep -v grep > /dev/null; then
        echo "✅ 应用启动成功"
    else
        echo "❌ 应用启动失败"
        exit 1
    fi
ENDSSH

if [ $? -ne 0 ]; then
    echo "❌ 应用重启失败"
    exit 1
fi

echo ""
echo "步骤 5/5: 健康检查..."
ssh $SERVER << ENDSSH
    curl -s http://localhost:5001/api/health | python3 -m json.tool
ENDSSH

echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "请测试："
echo "1. 访问 http://sweetseek.top"
echo "2. 强制刷新 Cmd+Shift+R"
echo "3. 测试功能是否正常"
echo ""
echo "查看服务器日志："
echo "ssh $SERVER 'tail -f $PROJECT_DIR/logs/sweetseek.log'"
echo ""
