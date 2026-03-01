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

# 2. 远程执行
echo -e "${GREEN}[2/4] 连接服务器执行部署...${NC}"

REMOTE_CMDS="
    set -e  # 遇到错误立即退出

    echo '>> 进入项目目录...'
    cd $SERVER_PATH
    
    echo '>> 拉取最新代码...'
    git pull origin \$(git branch --show-current)

    # ---------------------------
    # 前端部署 (React)
    # ---------------------------
    echo '>> [前端] 开始构建 React 应用...'
    cd frontend-react
    
    # 检查 Node 环境
    if ! command -v npm &> /dev/null; then
        echo '❌ 未找到 npm，尝试自动安装 Node.js (v20)...'
        
        # 自动安装 Node.js
        if command -v curl &> /dev/null; then
            curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
            
            # 检测包管理器
            if command -v apt-get &> /dev/null; then
                apt-get install -y nodejs
            elif command -v yum &> /dev/null; then
                yum install -y nodejs
            else
                echo '❌ 无法确定包管理器，请手动安装 Node.js'
                exit 1
            fi
        else
            echo '❌ 未找到 curl，无法自动安装'
            exit 1
        fi
        
        # 再次检查
        if ! command -v npm &> /dev/null; then
            echo '❌ Node.js 安装失败，请手动处理'
            exit 1
        fi
        echo '✅ Node.js 安装成功'
    fi

    echo '   安装依赖...'
    npm install --silent
    
    echo '   编译构建...'
    npm run build
    
    echo '✅ 前端构建完成'
    cd ..

    # ---------------------------
    # 后端部署 (Flask + Gunicorn)
    # ---------------------------
    echo '>> [后端] 配置 Python 环境...'
    
    if [ ! -d 'venv' ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    
    echo '   安装 Python 依赖...'
    pip install -r requirements.txt --quiet
    pip install gunicorn gevent --quiet

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
