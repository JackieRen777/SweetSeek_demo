#!/bin/bash
# 在服务器上修复参考文献显示问题

echo "=========================================="
echo "修复参考文献显示问题"
echo "=========================================="

# 1. 拉取最新代码
echo ""
echo "步骤 1: 拉取最新代码..."
cd /www/wwwroot/FCN_SweetSeek
git pull origin RenJiaqi

# 2. 运行路径修复脚本
echo ""
echo "步骤 2: 修复向量数据库中的路径格式..."
python3 fix_vector_db_paths.py

# 3. 重启Flask应用
echo ""
echo "步骤 3: 重启Flask应用..."
pkill -f "python3 app.py"
sleep 2
nohup python3 app.py > logs/app.log 2>&1 &

echo ""
echo "=========================================="
echo "✅ 修复完成！"
echo "=========================================="
echo ""
echo "请在浏览器中测试："
echo "1. 访问 http://sweetseek.top"
echo "2. 清除浏览器缓存 (Cmd+Shift+R)"
echo "3. 提问并查看参考文献是否正常显示期刊名和年份"
echo ""
