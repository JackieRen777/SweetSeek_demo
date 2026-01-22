#!/bin/bash

# SweetSeek 自动部署脚本
# 用法: ./deploy.sh "提交信息"

# 服务器配置
SERVER_IP="8.137.32.247"
SERVER_USER="root"
SERVER_PATH="/www/wwwroot/FCN_SweetSeek"

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  SweetSeek 自动部署脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 获取提交信息
COMMIT_MSG="${1:-自动部署 $(date '+%Y-%m-%d %H:%M:%S')}"

# 第一步：提交本地修改
echo -e "${GREEN}[1/4] 提交本地修改...${NC}"
git add .
git status --short
git commit -m "$COMMIT_MSG" || echo "没有新的修改需要提交"
echo ""

# 第二步：推送到远程仓库（可选，如果 GitHub 连接慢可以跳过）
echo -e "${GREEN}[2/4] 推送到远程仓库...${NC}"
git push origin $(git branch --show-current) 2>/dev/null || echo "GitHub 推送失败，跳过（不影响部署）"
echo ""

# 第三步：直接推送到服务器
echo -e "${GREEN}[3/4] 推送代码到服务器...${NC}"
# 使用 rsync 直接同步文件到服务器（更快更可靠）
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '.git' \
  --exclude 'chroma_db' --exclude 'models' --exclude '.env' \
  --exclude 'sweet_related_paper/papers/*.pdf' \
  ./ root@8.137.32.247:/www/wwwroot/FCN_SweetSeek/
echo "代码同步完成！"
echo ""

# 第四步：重启服务
echo -e "${GREEN}[4/4] 重启服务...${NC}"
ssh root@8.137.32.247 << 'ENDSSH'
echo "重启 SweetSeek 服务..."
supervisorctl restart sweetseek 2>/dev/null || {
    echo "Supervisor 未找到，尝试手动重启..."
    pkill -f "python.*app.py" || true
    cd /www/wwwroot/FCN_SweetSeek
    source venv/bin/activate
    nohup python app.py > logs/app.log 2>&1 &
    echo "服务已重启！"
}
echo "服务重启完成！"
ENDSSH
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "访问地址: ${BLUE}http://8.137.32.247:5001${NC}"
echo -e "备案完成后: ${BLUE}http://sweetseek.top${NC}"
echo ""
