#!/bin/bash
# 完全重新部署到服务器
# 包括：提交本地代码 -> 推送GitHub -> 服务器重置 -> 重建索引

echo "=========================================="
echo "🚀 完全重新部署到服务器"
echo "=========================================="

SERVER="root@8.137.32.247"
PROJECT_DIR="/www/wwwroot/FCN_SweetSeek"

# ============================================
# 第一部分：本地操作
# ============================================

echo ""
echo "【第一部分：本地操作】"
echo "=========================================="

echo ""
echo "[1/3] 检查Git状态..."
git status

echo ""
echo "[2/3] 添加所有更改..."
git add .

echo ""
echo "[3/3] 提交更改..."
git commit -m "修正结构逻辑错误" || echo "没有新的更改需要提交"

echo ""
echo "推送到GitHub..."
git push origin RenJiaqi

if [ $? -eq 0 ]; then
    echo "✅ 代码已推送到GitHub"
else
    echo "❌ 推送失败，请检查网络或Git配置"
    exit 1
fi

# ============================================
# 第二部分：服务器操作
# ============================================

echo ""
echo "【第二部分：服务器操作】"
echo "=========================================="

ssh $SERVER << 'ENDSSH'
    set -e  # 遇到错误立即退出
    
    echo ""
    echo "[1/7] 停止所有应用进程..."
    pkill -9 -f "python.*app.py" || echo "没有运行的进程"
    sleep 2
    ps aux | grep "python.*app.py" | grep -v grep || echo "✅ 所有进程已停止"
    
    echo ""
    echo "[2/7] 进入项目目录..."
    cd /www/wwwroot/FCN_SweetSeek
    pwd
    
    echo ""
    echo "[3/7] 删除向量数据库（强制重建）..."
    rm -rf chroma_db
    echo "✅ 向量数据库已删除"
    
    echo ""
    echo "[4/7] 重置Git状态..."
    git reset --hard HEAD
    echo "✅ Git已重置"
    
    echo ""
    echo "[5/7] 拉取最新代码..."
    git pull origin RenJiaqi
    echo "✅ 代码已更新"
    
    echo ""
    echo "[6/7] 显示最新提交..."
    git log -1 --oneline
    
    echo ""
    echo "[7/7] 启动应用（后台运行，重建索引）..."
    nohup /www/wwwroot/FCN_SweetSeek/venv/bin/python app.py > logs/app.log 2>&1 &
    echo "✅ 应用已启动"
    
    echo ""
    echo "等待10秒让应用初始化..."
    sleep 10
    
    echo ""
    echo "检查进程状态..."
    ps aux | grep "python.*app.py" | grep -v grep
    
    echo ""
    echo "检查端口监听..."
    netstat -tlnp | grep 5001 || ss -tlnp | grep 5001
    
    echo ""
    echo "=========================================="
    echo "查看启动日志（最后30行）"
    echo "=========================================="
    tail -30 logs/app.log
ENDSSH

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ 部署完成！"
    echo "=========================================="
    echo ""
    echo "⏳ 注意：索引重建需要2-5分钟"
    echo ""
    echo "下一步："
    echo "1. 等待2-5分钟让索引重建完成"
    echo "2. 访问 http://sweetseek.top"
    echo "3. 强制刷新浏览器（Cmd+Shift+R）"
    echo "4. 测试References是否正常显示"
    echo ""
    echo "查看实时日志："
    echo "ssh $SERVER 'tail -f $PROJECT_DIR/logs/app.log'"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "❌ 部署失败"
    echo "=========================================="
    exit 1
fi
