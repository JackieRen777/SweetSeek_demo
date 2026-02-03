#!/bin/bash
# 清理前验证脚本 - 确保系统功能正常

echo "=========================================="
echo "🔍 清理前系统验证"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0

# 测试1: 检查核心Python文件
echo "【测试 1/8】检查核心Python文件"
CORE_FILES=(
    "app.py"
    "persistent_storage.py"
    "metadata_storage.py"
    "pdf_metadata_extractor.py"
    "query_expander.py"
    "evidence_ranker.py"
    "incremental_indexer.py"
)

for file in "${CORE_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file"
    else
        echo -e "  ${RED}✗${NC} $file (缺失)"
        ((FAIL_COUNT++))
    fi
done
((PASS_COUNT++))
echo ""

# 测试2: 检查核心脚本
echo "【测试 2/8】检查核心脚本"
CORE_SCRIPTS=(
    "deploy.sh"
    "deploy_to_server.sh"
    "test_local.sh"
    "rebuild-index.sh"
    "restart-server.sh"
)

for file in "${CORE_SCRIPTS[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file"
    else
        echo -e "  ${RED}✗${NC} $file (缺失)"
        ((FAIL_COUNT++))
    fi
done
((PASS_COUNT++))
echo ""

# 测试3: 检查配置文件
echo "【测试 3/8】检查配置文件"
CONFIG_FILES=(
    ".env"
    "requirements.txt"
    "nginx_sweetseek.conf"
)

for file in "${CONFIG_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file"
    else
        echo -e "  ${RED}✗${NC} $file (缺失)"
        ((FAIL_COUNT++))
    fi
done
((PASS_COUNT++))
echo ""

# 测试4: 检查前端文件
echo "【测试 4/8】检查前端文件"
FRONTEND_FILES=(
    "frontend/index.html"
    "frontend/search.html"
    "frontend/about.html"
    "static/main.js"
    "static/search.js"
    "static/style.css"
)

for file in "${FRONTEND_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file"
    else
        echo -e "  ${RED}✗${NC} $file (缺失)"
        ((FAIL_COUNT++))
    fi
done
((PASS_COUNT++))
echo ""

# 测试5: 检查数据库目录
echo "【测试 5/8】检查数据库目录"
if [ -d "chroma_db" ]; then
    echo -e "  ${GREEN}✓${NC} chroma_db/ 存在"
    if [ -f "chroma_db/metadata.json" ]; then
        METADATA_COUNT=$(python3 -c "import json; print(len(json.load(open('chroma_db/metadata.json'))))" 2>/dev/null)
        echo -e "  ${GREEN}✓${NC} metadata.json (包含 $METADATA_COUNT 个文件)"
    else
        echo -e "  ${RED}✗${NC} metadata.json 缺失"
        ((FAIL_COUNT++))
    fi
    ((PASS_COUNT++))
else
    echo -e "  ${RED}✗${NC} chroma_db/ 不存在"
    ((FAIL_COUNT++))
fi
echo ""

# 测试6: Python语法检查
echo "【测试 6/8】Python语法检查"
SYNTAX_ERROR=0
for file in "${CORE_FILES[@]}"; do
    if [ -f "$file" ]; then
        if python3 -m py_compile "$file" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} $file 语法正确"
        else
            echo -e "  ${RED}✗${NC} $file 语法错误"
            SYNTAX_ERROR=1
            ((FAIL_COUNT++))
        fi
    fi
done

if [ $SYNTAX_ERROR -eq 0 ]; then
    ((PASS_COUNT++))
fi
echo ""

# 测试7: 检查Git状态
echo "【测试 7/8】检查Git状态"
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Git仓库正常"
    BRANCH=$(git branch --show-current)
    echo -e "  ${GREEN}✓${NC} 当前分支: $BRANCH"
    
    if git diff --quiet && git diff --cached --quiet; then
        echo -e "  ${GREEN}✓${NC} 没有未提交的更改"
    else
        echo -e "  ${YELLOW}⚠${NC}  有未提交的更改"
    fi
    ((PASS_COUNT++))
else
    echo -e "  ${RED}✗${NC} Git仓库异常"
    ((FAIL_COUNT++))
fi
echo ""

# 测试8: 尝试启动应用（快速测试）
echo "【测试 8/8】应用启动测试"
echo "  启动Flask应用进行快速测试..."

# 检查端口是否被占用
if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "  ${YELLOW}⚠${NC}  端口5001已被占用，跳过启动测试"
    echo -e "  ${GREEN}✓${NC} 应用可能正在运行"
    ((PASS_COUNT++))
else
    # 尝试启动（后台，5秒后关闭）
    timeout 5 python3 app.py > /tmp/sweetseek_test.log 2>&1 &
    APP_PID=$!
    sleep 3
    
    if ps -p $APP_PID > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} 应用启动成功"
        kill $APP_PID 2>/dev/null
        ((PASS_COUNT++))
    else
        echo -e "  ${RED}✗${NC} 应用启动失败"
        echo "  查看日志: /tmp/sweetseek_test.log"
        ((FAIL_COUNT++))
    fi
fi
echo ""

# 总结
echo "=========================================="
echo "📊 验证结果"
echo "=========================================="
echo ""
echo -e "通过测试: ${GREEN}$PASS_COUNT${NC}"
echo -e "失败测试: ${RED}$FAIL_COUNT${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✅ 所有测试通过，可以安全执行清理！${NC}"
    echo ""
    echo "执行清理："
    echo "  bash cleanup_project.sh"
    echo ""
    exit 0
else
    echo -e "${RED}❌ 有 $FAIL_COUNT 个测试失败，请先修复问题！${NC}"
    echo ""
    exit 1
fi
