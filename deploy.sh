#!/bin/bash

# SweetSeek 完善的自动部署脚本
# 包含环境检查和自动修复功能

# 服务器配置
SERVER_IP="8.137.32.247"
SERVER_USER="root"
SERVER_PATH="/www/wwwroot/FCN_SweetSeek"

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  SweetSeek 自动部署脚本 v2.0${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 获取提交信息
COMMIT_MSG="${1:-自动部署 $(date '+%Y-%m-%d %H:%M:%S')}"

# 第一步：提交本地修改
echo -e "${GREEN}[1/7] 提交本地修改...${NC}"
git add .
git status --short
git commit -m "$COMMIT_MSG" || echo "没有新的修改需要提交"
echo ""

# 第二步：推送到 GitHub
echo -e "${GREEN}[2/7] 推送到 GitHub...${NC}"
git push origin $(git branch --show-current)
echo ""

# 第三步：服务器拉取代码
echo -e "${GREEN}[3/7] 服务器拉取代码...${NC}"
ssh root@$SERVER_IP << 'ENDSSH'
cd /www/wwwroot/FCN_SweetSeek
echo "当前目录: $(pwd)"
echo "从 GitHub 拉取最新代码..."
git pull origin RenJiaqi
echo "代码更新完成！"
ENDSSH
echo ""

# 第四步：检查并修复环境
echo -e "${GREEN}[4/7] 检查并修复服务器环境...${NC}"
ssh root@$SERVER_IP << 'ENDSSH'
cd /www/wwwroot/FCN_SweetSeek

echo "检查 .env 配置..."
# 确保离线模式配置存在
if ! grep -q "HF_HUB_OFFLINE=1" .env 2>/dev/null; then
    echo "  添加 HF_HUB_OFFLINE=1"
    echo "HF_HUB_OFFLINE=1" >> .env
fi

if ! grep -q "TRANSFORMERS_OFFLINE=1" .env 2>/dev/null; then
    echo "  添加 TRANSFORMERS_OFFLINE=1"
    echo "TRANSFORMERS_OFFLINE=1" >> .env
fi

echo "检查模型文件..."
if [ ! -d "models/models--BAAI--bge-small-zh-v1.5/snapshots" ]; then
    echo "  ⚠️  警告：模型文件不存在！"
    echo "  需要运行: scp -r models/models--BAAI--bge-small-zh-v1.5 root@8.137.32.247:/www/wwwroot/FCN_SweetSeek/models/"
    exit 1
fi

echo "检查日志目录..."
mkdir -p logs

echo "✅ 环境检查通过"
ENDSSH

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 环境检查失败！请先修复问题。${NC}"
    exit 1
fi
echo ""

# 第五步：停止旧进程
echo -e "${GREEN}[5/7] 停止旧进程...${NC}"
ssh root@$SERVER_IP << 'ENDSSH'
cd /www/wwwroot/FCN_SweetSeek
pkill -f "python.*app.py" || echo "没有运行中的进程"
sleep 2
ENDSSH
echo ""

# 第六步：启动新进程
echo -e "${GREEN}[6/7] 启动新进程...${NC}"
ssh root@$SERVER_IP << 'ENDSSH'
cd /www/wwwroot/FCN_SweetSeek
source venv/bin/activate
nohup python app.py > logs/app.log 2>&1 &
echo "等待服务启动..."
sleep 8
ENDSSH
echo ""

# 第七步：验证部署
echo -e "${GREEN}[7/7] 验证部署...${NC}"
ssh root@$SERVER_IP << 'ENDSSH'
cd /www/wwwroot/FCN_SweetSeek

if netstat -tunlp | grep 5001 > /dev/null; then
    echo "✅ 服务启动成功！端口 5001 正在监听"
else
    echo "❌ 服务启动失败！查看最近日志："
    tail -30 logs/app.log
    exit 1
fi
ENDSSH

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  部署成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "访问地址: ${BLUE}http://8.137.32.247:5001${NC}"
    echo -e "备案完成后: ${BLUE}http://sweetseek.top${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  部署失败！${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo "请检查服务器日志：ssh root@8.137.32.247 'tail -50 /www/wwwroot/FCN_SweetSeek/logs/app.log'"
    echo ""
    exit 1
fi
