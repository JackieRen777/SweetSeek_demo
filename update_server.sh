#!/bin/bash
# 服务器更新脚本

echo "=========================================="
echo "🚀 更新服务器代码"
echo "=========================================="
echo ""

SERVER="root@8.137.32.247"

ssh -T $SERVER << 'ENDSSH'
    cd /www/wwwroot/FCN_SweetSeek
    
    echo "📍 当前目录: $(pwd)"
    echo ""
    
    echo "📌 当前分支: $(git branch --show-current)"
    echo ""
    
    echo "📥 拉取最新代码..."
    git pull origin RenJiaqi
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ 代码拉取成功"
        echo ""
        
        echo "🔄 重启应用..."
        pkill -f "python3 app.py"
        sleep 3
        nohup python3 app.py > logs/app.log 2>&1 &
        sleep 2
        
        echo ""
        echo "🔍 验证服务状态..."
        if ps aux | grep "python3 app.py" | grep -v grep > /dev/null; then
            echo "✅ 应用启动成功"
            echo ""
            ps aux | grep "python3 app.py" | grep -v grep | head -1
        else
            echo "❌ 应用启动失败"
            echo ""
            echo "查看日志："
            tail -20 logs/sweetseek.log
            exit 1
        fi
        
        echo ""
        echo "🏥 健康检查..."
        curl -s http://localhost:5001/api/health | python3 -m json.tool 2>/dev/null || echo "健康检查失败"
        
        echo ""
        echo "📋 最新日志（最后10行）:"
        tail -10 logs/sweetseek.log
        
    else
        echo ""
        echo "❌ 代码拉取失败"
        exit 1
    fi
ENDSSH

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ 服务器更新完成！"
    echo "=========================================="
    echo ""
    echo "请测试："
    echo "1. 访问 http://sweetseek.top"
    echo "2. 强制刷新 Cmd+Shift+R"
    echo "3. 测试功能"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "❌ 服务器更新失败"
    echo "=========================================="
    echo ""
    exit 1
fi
