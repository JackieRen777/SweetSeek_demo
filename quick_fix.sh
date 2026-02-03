#!/bin/bash
# 一键修复脚本 - 在服务器上运行

echo "=========================================="
echo "🚨 快速修复 References 显示问题"
echo "=========================================="

# 进入项目目录
cd /www/wwwroot/FCN_SweetSeek || exit 1

# 1. 拉取最新代码
echo ""
echo "📥 拉取最新代码..."
git pull origin RenJiaqi

# 2. 修复向量数据库路径
echo ""
echo "🔧 修复向量数据库路径..."
python3 fix_vector_db_paths.py

# 3. 重启Flask应用
echo ""
echo "🔄 重启Flask应用..."
pkill -f "python3 app.py"
sleep 3
nohup python3 app.py > logs/app.log 2>&1 &

# 4. 等待启动
sleep 2

# 5. 验证
echo ""
echo "✅ 验证服务状态..."
if ps aux | grep "python3 app.py" | grep -v grep > /dev/null; then
    echo "✅ Flask应用正在运行"
else
    echo "❌ Flask应用未运行！"
    exit 1
fi

# 6. 健康检查
echo ""
echo "🏥 健康检查..."
curl -s http://localhost:5001/api/health | python3 -m json.tool

# 7. 显示最新日志
echo ""
echo "📋 最新日志（最后10行）:"
tail -10 logs/sweetseek.log

echo ""
echo "=========================================="
echo "✅ 修复完成！"
echo "=========================================="
echo ""
echo "请在浏览器测试："
echo "1. 访问 http://sweetseek.top"
echo "2. 强制刷新 Cmd+Shift+R"
echo "3. 提问并检查references显示"
echo ""
