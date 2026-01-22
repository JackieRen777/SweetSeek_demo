#!/bin/bash

# SweetSeek 智能推送脚本
# 自动生成更新摘要并推送到 GitHub 和服务器

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  SweetSeek 智能推送脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查是否有未提交的修改
if git diff --quiet && git diff --cached --quiet; then
    echo -e "${YELLOW}没有需要提交的修改${NC}"
    exit 0
fi

# 第一步：显示修改的文件
echo -e "${GREEN}[1/5] 检测到以下修改：${NC}"
echo ""
git status --short
echo ""

# 第二步：生成更新摘要
echo -e "${GREEN}[2/5] 生成更新摘要...${NC}"
echo ""

# 获取修改的文件列表
MODIFIED_FILES=$(git diff --name-only --cached 2>/dev/null)
if [ -z "$MODIFIED_FILES" ]; then
    MODIFIED_FILES=$(git diff --name-only)
fi

# 统计修改类型
ADDED_FILES=$(echo "$MODIFIED_FILES" | grep -E "^[^/]+\.(py|js|html|css|sh|md)$" | wc -l | tr -d ' ')
MODIFIED_PY=$(echo "$MODIFIED_FILES" | grep "\.py$" | wc -l | tr -d ' ')
MODIFIED_JS=$(echo "$MODIFIED_FILES" | grep "\.js$" | wc -l | tr -d ' ')
MODIFIED_HTML=$(echo "$MODIFIED_FILES" | grep "\.html$" | wc -l | tr -d ' ')
MODIFIED_CSS=$(echo "$MODIFIED_FILES" | grep "\.css$" | wc -l | tr -d ' ')
MODIFIED_SH=$(echo "$MODIFIED_FILES" | grep "\.sh$" | wc -l | tr -d ' ')
MODIFIED_MD=$(echo "$MODIFIED_FILES" | grep "\.md$" | wc -l | tr -d ' ')

# 生成摘要
SUMMARY="更新内容："
DETAILS=""

if [ "$MODIFIED_PY" -gt 0 ]; then
    DETAILS="${DETAILS}\n- 修改了 ${MODIFIED_PY} 个 Python 文件（后端逻辑）"
fi

if [ "$MODIFIED_JS" -gt 0 ]; then
    DETAILS="${DETAILS}\n- 修改了 ${MODIFIED_JS} 个 JavaScript 文件（前端功能）"
fi

if [ "$MODIFIED_HTML" -gt 0 ]; then
    DETAILS="${DETAILS}\n- 修改了 ${MODIFIED_HTML} 个 HTML 文件（页面结构）"
fi

if [ "$MODIFIED_CSS" -gt 0 ]; then
    DETAILS="${DETAILS}\n- 修改了 ${MODIFIED_CSS} 个 CSS 文件（样式）"
fi

if [ "$MODIFIED_SH" -gt 0 ]; then
    DETAILS="${DETAILS}\n- 修改了 ${MODIFIED_SH} 个脚本文件（部署/工具）"
fi

if [ "$MODIFIED_MD" -gt 0 ]; then
    DETAILS="${DETAILS}\n- 修改了 ${MODIFIED_MD} 个文档文件"
fi

# 显示摘要
echo -e "${BLUE}自动生成的更新摘要：${NC}"
echo -e "${DETAILS}"
echo ""

# 列出具体修改的文件
echo -e "${BLUE}修改的文件列表：${NC}"
echo "$MODIFIED_FILES" | while read file; do
    if [ -n "$file" ]; then
        echo "  - $file"
    fi
done
echo ""

# 第三步：询问是否添加自定义说明
echo -e "${YELLOW}是否添加自定义说明？（直接回车跳过，或输入说明）${NC}"
read -p "> " CUSTOM_MSG

if [ -n "$CUSTOM_MSG" ]; then
    COMMIT_MSG="$CUSTOM_MSG

$SUMMARY
$DETAILS

修改的文件：
$(echo "$MODIFIED_FILES" | sed 's/^/- /')"
else
    COMMIT_MSG="$SUMMARY
$DETAILS

修改的文件：
$(echo "$MODIFIED_FILES" | sed 's/^/- /')

提交时间: $(date '+%Y-%m-%d %H:%M:%S')"
fi

# 第四步：提交到本地
echo -e "${GREEN}[3/5] 提交到本地仓库...${NC}"
git add .
git commit -m "$COMMIT_MSG"
echo ""

# 第五步：推送到 GitHub
echo -e "${GREEN}[4/5] 推送到 GitHub...${NC}"
git push origin $(git branch --show-current)
echo ""

# 第六步：询问是否部署到服务器
echo -e "${GREEN}[5/5] 是否立即部署到服务器？${NC}"
echo -e "${YELLOW}输入 'y' 部署，直接回车跳过${NC}"
read -p "> " DEPLOY_NOW

if [ "$DEPLOY_NOW" = "y" ] || [ "$DEPLOY_NOW" = "Y" ]; then
    echo ""
    echo -e "${BLUE}开始部署到服务器...${NC}"
    ./deploy.sh
else
    echo ""
    echo -e "${YELLOW}已跳过部署。稍后可运行 ./deploy.sh 部署${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  推送完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
