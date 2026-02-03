#!/bin/bash
# 服务器完全重置 - 一键执行脚本

echo "=========================================="
echo "SweetSeek 服务器完全重置"
echo "=========================================="

# 1. 停止应用
echo ""
echo "[1/8] 停止应用..."
pkill -9 -f "python.*app.py"
sleep 2
ps aux | grep "python.*app.py" | grep -v grep || echo "✅ 所有进程已停止"

# 2. 进入项目目录
echo ""
echo "[2/8] 进入项目目录..."
cd /www/wwwroot/FCN_SweetSeek
pwd

# 3. 删除向量数据库
echo ""
echo "[3/8] 删除向量数据库..."
rm -rf chroma_db
echo "✅ 向量数据库已删除"

# 4. 重置Git
echo ""
echo "[4/8] 重置Git状态..."
git reset --hard HEAD
echo "✅ Git已重置"

# 5. 拉取最新代码
echo ""
echo "[5/8] 拉取最新代码..."
git pull origin RenJiaqi
echo "✅ 代码已更新"

# 6. 显示最新提交
echo ""
echo "[6/8] 最新提交："
git log -1 --oneline

# 7. 启动应用
echo ""
echo "[7/8] 启动应用（重建索引）..."
nohup /www/wwwroot/FCN_SweetSeek/venv/bin/python app.py > logs/app.log 2>&1 &
echo "✅ 应用已启动（后台运行）"

# 8. 等待并显示日志
echo ""
echo "[8/8] 等待启动（10秒）..."
sleep 10

echo ""
echo "=========================================="
echo "查看启动日志（按 Ctrl+C 停止）"
echo "=========================================="
tail -f logs/app.log
