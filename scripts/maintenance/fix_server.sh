#!/bin/bash

# SweetSeek 服务器修复脚本
# 该脚本用于：
# 1. 杀掉所有相关的 Python/Gunicorn 进程
# 2. 检查并创建必要的目录
# 3. 提供一键启动建议

echo "=================================================="
echo "🧹 SweetSeek 服务器清理与修复工具"
echo "=================================================="

# 1. 强力清理进程
echo "[1/3] 正在清理旧进程..."
# 杀掉 gunicorn
pkill -9 gunicorn
# 杀掉 python3 app.py
pkill -9 -f "python3 app.py"

# 再次检查
if pgrep -f "app.py" > /dev/null; then
    echo "⚠️ 警告：仍有进程未被杀死，尝试使用更强力的手段..."
    kill -9 $(pgrep -f "app.py")
else
    echo "✅ 所有相关进程已清理干净"
fi

# 2. 检查数据目录
echo "[2/3] 检查数据目录..."
DATA_DIR="/data/sweetseek_db"
if [ ! -d "$DATA_DIR" ]; then
    echo "创建数据目录: $DATA_DIR"
    mkdir -p "$DATA_DIR"
    # 尝试设置权限（假设 www 用户）
    chown -R www:www "$DATA_DIR" 2>/dev/null || echo "⚠️ 无法设置 www 用户权限（可能用户不存在），请手动检查"
else
    echo "✅ 数据目录已存在: $DATA_DIR"
fi

# 3. 宝塔部署建议
echo "[3/3] 下一步操作建议..."
echo "--------------------------------------------------"
echo "现在您可以回到宝塔面板 -> Python项目："
echo "1. 点击【添加项目】"
echo "2. 项目名称：sweetseek_prod"
echo "3. 端口：8001 (强烈建议使用新端口，避开 5001)"
echo "4. 启动方式：Gunicorn"
echo "5. 启动文件：app.py"
echo "--------------------------------------------------"
echo "添加成功后，请记得去 Nginx 配置文件中："
echo "将 proxy_pass http://127.0.0.1:5001; 改为 http://127.0.0.1:8001;"
echo "并确保添加了 'proxy_buffering off;'"
echo "--------------------------------------------------"

echo "🎉 脚本执行完毕！"
