#!/bin/bash

# SweetSeek 自动部署脚本 v3.0 (React + Flask + Nginx)
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
echo -e "${BLUE}  SweetSeek 全栈部署脚本 v3.0${NC}"
echo -e "${BLUE}========================================${NC}"

# 1. 提交代码
echo -e "${GREEN}[1/5] 提交本地修改...${NC}"
git add .
git commit -m "Deploy: $(date '+%Y-%m-%d %H:%M:%S')"
git push origin $(git branch --show-current)

# 2. 本地构建前端 (解决服务器内存不足问题)
echo -e "${GREEN}[2/5] 本地构建前端...${NC}"
cd frontend-react
echo -e "${YELLOW}安装依赖...${NC}"
npm install --silent
echo -e "${YELLOW}开始构建...${NC}"
npm run build
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 本地构建失败${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 本地构建成功${NC}"
cd ..

# 3. 同步文件到服务器
echo -e "${GREEN}[3/5] 同步文件到服务器...${NC}"

# 检查并安装 rsync
echo -e "${YELLOW}检查服务器 rsync 环境...${NC}"
ssh $SERVER_USER@$SERVER_IP "
    if ! command -v rsync &> /dev/null; then
        echo '安装 rsync...'
        if command -v yum &> /dev/null; then
            yum install -y rsync
        elif command -v apt-get &> /dev/null; then
            apt-get install -y rsync
        fi
    fi
"

echo -e "${YELLOW}正在清理服务器旧文件...${NC}"
# 删除服务器上的旧构建文件，防止冲突
ssh $SERVER_USER@$SERVER_IP "rm -rf $SERVER_PATH/frontend-react/dist"

echo -e "${YELLOW}正在上传构建产物 (dist)...${NC}"
# 上传本地构建好的 dist 文件夹
rsync -avz --progress frontend-react/dist/ $SERVER_USER@$SERVER_IP:$SERVER_PATH/frontend-react/dist/

echo -e "${YELLOW}论文数据库使用独立数据目录，本次代码部署不上传 PDF。${NC}"

echo -e "${YELLOW}正在更新依赖配置...${NC}"
rsync -avz requirements.txt $SERVER_USER@$SERVER_IP:$SERVER_PATH/requirements.txt

# 4. 远程执行 (只负责后端和Nginx)
echo -e "${GREEN}[4/5] 连接服务器重启服务...${NC}"

REMOTE_CMDS="
    set -e
    
    echo '>> 进入项目目录...'
    cd $SERVER_PATH
    
    echo '>> 拉取最新代码 (仅更新后端代码)...'
    git pull origin \$(git branch --show-current)

    # ---------------------------
    # 前端部署 (跳过构建，直接使用上传的dist)
    # ---------------------------
    echo '>> [前端] 已使用本地构建产物，跳过服务器构建'

    # ---------------------------
    # 后端部署 (Flask + Gunicorn)
    # ---------------------------
    echo '>> [后端] 配置 Python 环境...'
    
    if [ ! -d 'venv' ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    
    echo '   升级 pip...'
    pip install --upgrade pip --quiet
    
    echo '   安装 Python 依赖...'
    # 使用阿里云镜像源加速，如果失败则回退到官方源
    pip install -r requirements.txt --quiet -i https://mirrors.aliyun.com/pypi/simple/ || pip install -r requirements.txt --quiet
    pip install gunicorn gevent --quiet -i https://mirrors.aliyun.com/pypi/simple/

    echo '   重启 Gunicorn 服务...'
    # 查找并杀掉旧进程
    ps aux | grep 'gunicorn' | grep 'sweetseek' | awk '{print \$2}' | xargs -r kill -9
    
    # 启动新进程
    nohup gunicorn -c gunicorn_config.py app:app > /www/wwwlogs/sweetseek_backend.log 2>&1 &
    
    echo '✅ 后端服务已启动 (端口 5001)'

    # ---------------------------
    # Nginx 配置
    # ---------------------------
    echo '>> [Nginx] 更新配置...'
    cp nginx_sweetseek.conf /etc/nginx/conf.d/sweetseek.conf 2>/dev/null || cp nginx_sweetseek.conf /www/server/nginx/conf/vhost/sweetseek.conf
    
    # 检查 Nginx 配置并重载
    nginx -t && nginx -s reload
    
    echo '✅ Nginx 重载完成'
    echo ''
    echo '🎉 部署全部完成！'
    echo '访问: http://sweetseek.top'
"

ssh -tt $SERVER_USER@$SERVER_IP "$REMOTE_CMDS"
