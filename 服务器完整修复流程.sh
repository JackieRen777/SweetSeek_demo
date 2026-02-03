#!/bin/bash
# 服务器完整修复流程
# 在本地运行，通过SSH连接到服务器执行所有操作

SERVER="root@8.137.32.247"
PROJECT_DIR="/www/wwwroot/FCN_SweetSeek"

echo "=========================================="
echo "SweetSeek 服务器修复流程"
echo "=========================================="

# 步骤1: 停止所有旧进程
echo ""
echo "[步骤 1/5] 停止所有旧的Python进程..."
ssh $SERVER << 'EOF'
cd /www/wwwroot/FCN_SweetSeek
echo "正在停止所有 app.py 进程..."
pkill -f "python.*app.py"
sleep 3
echo "检查是否还有进程在运行..."
ps aux | grep "python.*app.py" | grep -v grep || echo "✅ 所有进程已停止"
EOF

# 步骤2: 上传修复脚本
echo ""
echo "[步骤 2/5] 上传路径修复脚本..."
scp fix_paths_simple.py $SERVER:$PROJECT_DIR/
echo "✅ 脚本上传完成"

# 步骤3: 运行修复脚本
echo ""
echo "[步骤 3/5] 运行路径修复脚本..."
ssh $SERVER << 'EOF'
cd /www/wwwroot/FCN_SweetSeek
echo "使用虚拟环境的Python运行修复脚本..."
/www/wwwroot/FCN_SweetSeek/venv/bin/python fix_paths_simple.py
EOF

# 步骤4: 重启应用
echo ""
echo "[步骤 4/5] 重启应用..."
ssh $SERVER << 'EOF'
cd /www/wwwroot/FCN_SweetSeek
echo "启动应用..."
nohup /www/wwwroot/FCN_SweetSeek/venv/bin/python app.py > logs/app.log 2>&1 &
sleep 5
echo "检查应用状态..."
ps aux | grep "python.*app.py" | grep -v grep
EOF

# 步骤5: 验证服务
echo ""
echo "[步骤 5/5] 验证服务状态..."
ssh $SERVER << 'EOF'
cd /www/wwwroot/FCN_SweetSeek
echo "检查端口监听..."
netstat -tlnp | grep 5001 || ss -tlnp | grep 5001
echo ""
echo "查看最新日志..."
tail -30 logs/app.log
EOF

echo ""
echo "=========================================="
echo "修复流程完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 访问 http://sweetseek.top 测试网站"
echo "2. 强制刷新浏览器（Cmd+Shift+R）"
echo "3. 提问并检查 References 是否正常显示"
echo ""
