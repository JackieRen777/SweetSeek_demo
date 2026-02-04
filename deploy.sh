#!/bin/bash

# SweetSeek 完善的自动部署脚本
# 包含环境检查和自动修复功能 (优化版：单次SSH连接)

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
echo -e "${BLUE}  SweetSeek 自动部署脚本 v2.1 (交互式版)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 获取提交信息
COMMIT_MSG="${1:-自动部署 $(date '+%Y-%m-%d %H:%M:%S')}"

# 第一步：提交本地修改
echo -e "${GREEN}[1/3] 提交本地修改...${NC}"
if git diff --quiet && git diff --cached --quiet; then
    echo -e "${YELLOW}没有需要提交的修改${NC}"
else
    git add .
    git status --short
    git commit -m "$COMMIT_MSG"
fi
echo ""

# 第二步：推送到 GitHub
echo -e "${GREEN}[2/3] 推送到 GitHub...${NC}"
CURRENT_BRANCH=$(git branch --show-current)
git push origin $CURRENT_BRANCH
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 推送失败，请检查网络${NC}"
    exit 1
fi
echo ""

# 第三步：执行远程部署（单次连接）
echo -e "${GREEN}[3/3] 连接服务器执行部署...${NC}"
echo -e "${YELLOW}注意：只需输入一次密码即可完成所有步骤${NC}"

# 构建远程命令字符串
REMOTE_CMDS="
    # 遇到错误不立即退出，手动处理
    
    # 1. 拉取代码
    echo '>> [1/4] 拉取最新代码...'
    cd $SERVER_PATH
    echo '当前目录: \$(pwd)'
    git pull origin $CURRENT_BRANCH
    if [ \$? -ne 0 ]; then
        echo '❌ 代码拉取失败'
        exit 1
    fi
    echo '✅ 代码更新完成'
    echo ''

    # 2. 检查并修复环境
    echo '>> [2/4] 检查并修复服务器环境...'
    
    # 检查 API Key 是否存在（不要在脚本里写入密钥）
    echo '  检查 API Key...'
    if ! grep -q '^DEEPSEEK_API_KEY=' .env 2>/dev/null; then
        echo '❌ 缺少 DEEPSEEK_API_KEY，请在服务器 .env 中配置后再部署'
        exit 1
    fi
    
    # 检查 .env 配置
    if ! grep -q 'HF_HUB_OFFLINE=1' .env 2>/dev/null; then
        echo '  添加 HF_HUB_OFFLINE=1'
        echo 'HF_HUB_OFFLINE=1' >> .env
    fi
    if ! grep -q 'TRANSFORMERS_OFFLINE=1' .env 2>/dev/null; then
        echo '  添加 TRANSFORMERS_OFFLINE=1'
        echo 'TRANSFORMERS_OFFLINE=1' >> .env
    fi
    
    # 检查日志目录
    mkdir -p logs
    echo '✅ 环境检查通过'
    echo ''

    # 3. 重启服务
    echo '>> [3/4] 重启服务...'
    echo '停止旧进程...'
    # 仅杀掉包含 app.py 的 python 进程，避免误杀 ssh
    ps aux | grep 'python.*app.py' | grep -v grep | awk '{print \$2}' | xargs -r kill -9
    sleep 2
    
    echo '启动新进程...'
    # 确保进入正确目录
    cd $SERVER_PATH
    
    # 确保离线模式环境变量已导出
    export HF_HUB_OFFLINE=1
    export TRANSFORMERS_OFFLINE=1
    
    # 使用虚拟环境（如果存在）
    if [ -f 'venv/bin/activate' ]; then
        source venv/bin/activate
    fi
    
    # 使用 nohup 并在后台运行，确保退出 SSH 后进程不被杀掉
    # 显式使用 venv 中的 python 全路径，避免环境混淆
    # 检查端口是否被占用，如果被占用则等待释放
    for i in {1..10}; do
        if netstat -tunlp 2>/dev/null | grep 5001 > /dev/null; then
            echo \"端口 5001 仍被占用，等待释放... (\$i/10)\"
            sleep 1
        else
            break
        fi
    done
    
    nohup ./venv/bin/python3 app.py > logs/app.log 2>&1 &
    disown
    
    echo '等待服务启动 (15秒)...'
    sleep 15
    
    # 4. 验证部署
    echo '>> [4/4] 验证部署...'
    if netstat -tunlp | grep 5001 > /dev/null; then
        echo '✅ 服务启动成功！端口 5001 正在监听'
        echo ''
        echo '最新日志:'
        tail -n 10 logs/app.log
    else
        echo '❌ 服务启动失败！查看最近日志：'
        tail -n 30 logs/app.log
        exit 1
    fi
"

# 使用 -tt 参数强制分配伪终端，确保密码提示显示
ssh -tt $SERVER_USER@$SERVER_IP "$REMOTE_CMDS"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  部署成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "访问地址: ${BLUE}http://$SERVER_IP:5001${NC}"
    echo -e "域名访问: ${BLUE}http://sweetseek.top${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  部署失败！${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    exit 1
fi
