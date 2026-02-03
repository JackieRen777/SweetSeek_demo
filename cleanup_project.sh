#!/bin/bash
# 项目清理脚本
# 执行日期: 2026-02-03

echo "=========================================="
echo "🧹 SweetSeek 项目清理"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 创建归档目录
ARCHIVE_DIR=".archive/2026-02-03-cleanup"
echo -e "${BLUE}步骤 1/6: 创建归档目录${NC}"
mkdir -p "$ARCHIVE_DIR"
echo "✅ 创建目录: $ARCHIVE_DIR"
echo ""

# 待删除文件列表
echo -e "${BLUE}步骤 2/6: 准备待清理文件列表${NC}"
echo ""

# 类别1: 临时修复脚本
TEMP_FIX_SCRIPTS=(
    "fix_main_js.sh"
    "fix_metadata_paths.py"
    "diagnose_metadata.py"
    "fix_references_on_server.sh"
    "emergency_fix.sh"
    "quick_fix.sh"
)

# 类别2: 冗余文档
REDUNDANT_DOCS=(
    "FIX_REFERENCES_GUIDE.md"
    "DEPLOYMENT_GUIDE.md"
)

# 类别3: 临时文本文件
TEMP_TEXT_FILES=(
    "立即执行.txt"
    "SERVER_FIX_COMMANDS.txt"
    "UPDATE_COMMANDS.txt"
)

# 类别4: 备份文件
BACKUP_FILES=(
    "static/main.js.backup"
)

# 类别5: 可删除的脚本（经确认）
OPTIONAL_SCRIPTS=(
    "test_external_access.sh"
    "server_check.sh"
)

# 统计
TOTAL_FILES=0

echo -e "${YELLOW}📋 待清理文件清单：${NC}"
echo ""

echo "【临时修复脚本】(6个)"
for file in "${TEMP_FIX_SCRIPTS[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
        ((TOTAL_FILES++))
    else
        echo "  ✗ $file (不存在)"
    fi
done
echo ""

echo "【冗余文档】(2个)"
for file in "${REDUNDANT_DOCS[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
        ((TOTAL_FILES++))
    else
        echo "  ✗ $file (不存在)"
    fi
done
echo ""

echo "【临时文本文件】(3个)"
for file in "${TEMP_TEXT_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
        ((TOTAL_FILES++))
    else
        echo "  ✗ $file (不存在)"
    fi
done
echo ""

echo "【备份文件】(1个)"
for file in "${BACKUP_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
        ((TOTAL_FILES++))
    else
        echo "  ✗ $file (不存在)"
    fi
done
echo ""

echo "【可选脚本】(2个)"
for file in "${OPTIONAL_SCRIPTS[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
        ((TOTAL_FILES++))
    else
        echo "  ✗ $file (不存在)"
    fi
done
echo ""

echo -e "${GREEN}总计: $TOTAL_FILES 个文件待清理${NC}"
echo ""

# 确认
echo -e "${YELLOW}步骤 3/6: 确认清理操作${NC}"
echo -e "${RED}⚠️  这些文件将被移动到归档目录（保留7天）${NC}"
echo ""
read -p "确认继续？(y/N): " CONFIRM

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo ""
    echo -e "${YELLOW}❌ 已取消清理操作${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}步骤 4/6: 移动文件到归档目录${NC}"
echo ""

MOVED_COUNT=0

# 移动临时修复脚本
for file in "${TEMP_FIX_SCRIPTS[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$ARCHIVE_DIR/"
        echo "  ✓ 已移动: $file"
        ((MOVED_COUNT++))
    fi
done

# 移动冗余文档
for file in "${REDUNDANT_DOCS[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$ARCHIVE_DIR/"
        echo "  ✓ 已移动: $file"
        ((MOVED_COUNT++))
    fi
done

# 移动临时文本文件
for file in "${TEMP_TEXT_FILES[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$ARCHIVE_DIR/"
        echo "  ✓ 已移动: $file"
        ((MOVED_COUNT++))
    fi
done

# 移动备份文件
for file in "${BACKUP_FILES[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$ARCHIVE_DIR/"
        echo "  ✓ 已移动: $file"
        ((MOVED_COUNT++))
    fi
done

# 移动可选脚本
for file in "${OPTIONAL_SCRIPTS[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$ARCHIVE_DIR/"
        echo "  ✓ 已移动: $file"
        ((MOVED_COUNT++))
    fi
done

echo ""
echo -e "${GREEN}✅ 已移动 $MOVED_COUNT 个文件到归档目录${NC}"
echo ""

# 更新 .gitignore
echo -e "${BLUE}步骤 5/6: 更新 .gitignore${NC}"
if ! grep -q "^\.archive/" .gitignore 2>/dev/null; then
    echo ".archive/" >> .gitignore
    echo "✅ 已添加 .archive/ 到 .gitignore"
else
    echo "✓ .gitignore 已包含 .archive/"
fi
echo ""

# 创建清理日志
echo -e "${BLUE}步骤 6/6: 创建清理日志${NC}"
LOG_FILE="$ARCHIVE_DIR/CLEANUP_LOG.txt"
cat > "$LOG_FILE" << EOF
========================================
SweetSeek 项目清理日志
========================================

清理时间: $(date '+%Y-%m-%d %H:%M:%S')
归档目录: $ARCHIVE_DIR
清理文件数: $MOVED_COUNT

清理文件列表:
$(ls -lh "$ARCHIVE_DIR" | tail -n +2)

保留期限: 7天 (至 2026-02-10)
恢复方法: mv .archive/2026-02-03-cleanup/<文件名> ./

注意事项:
1. 所有文件在Git历史中仍可恢复
2. 归档文件保留7天观察期
3. 2026-02-10后可永久删除归档目录
4. 清理后需验证系统功能正常

========================================
EOF

echo "✅ 清理日志已保存: $LOG_FILE"
echo ""

# 显示归档内容
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 清理完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}归档目录内容：${NC}"
ls -lh "$ARCHIVE_DIR"
echo ""

echo -e "${YELLOW}📋 后续操作：${NC}"
echo ""
echo "1. 验证系统功能："
echo "   bash test_local.sh"
echo ""
echo "2. 提交清理记录："
echo "   git add ."
echo "   git commit -m \"清理冗余文件：移除临时修复脚本和过时文档\""
echo "   git push origin RenJiaqi"
echo ""
echo "3. 部署到服务器："
echo "   bash deploy_to_server.sh"
echo ""
echo "4. 恢复文件（如需要）："
echo "   mv $ARCHIVE_DIR/<文件名> ./"
echo ""
echo "5. 永久删除归档（2026-02-10后）："
echo "   rm -rf .archive/"
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}保留的核心文件：${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "核心应用 (7个):"
echo "  ✓ app.py"
echo "  ✓ persistent_storage.py"
echo "  ✓ metadata_storage.py"
echo "  ✓ pdf_metadata_extractor.py"
echo "  ✓ query_expander.py"
echo "  ✓ evidence_ranker.py"
echo "  ✓ incremental_indexer.py"
echo ""
echo "核心文档 (3个):"
echo "  ✓ README.md"
echo "  ✓ DEVELOPMENT_WORKFLOW.md"
echo "  ✓ 如何部署到服务器.md"
echo ""
echo "核心脚本 (7个):"
echo "  ✓ deploy.sh"
echo "  ✓ deploy_to_server.sh"
echo "  ✓ deploy_domain.sh"
echo "  ✓ test_local.sh"
echo "  ✓ rebuild-index.sh"
echo "  ✓ restart-server.sh"
echo "  ✓ push.sh"
echo ""
echo "重要工具 (1个):"
echo "  ✓ fix_vector_db_paths.py (可能需要在服务器再次运行)"
echo ""
