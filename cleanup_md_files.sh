#!/bin/bash
# 清理多余的Markdown文件

echo "=========================================="
echo "🧹 清理多余的Markdown文件"
echo "=========================================="
echo ""

# 归档目录
ARCHIVE_DIR=".archive/2026-02-03-md-cleanup"
mkdir -p "$ARCHIVE_DIR"

echo "📋 待清理的MD文件："
echo ""

# 立即删除的文件
IMMEDIATE_DELETE=(
    "CLEANUP_ANALYSIS.md"
    "CLEANUP_SUMMARY.md"
    "清理完成报告.md"
    "MD_FILES_ANALYSIS.md"
)

echo "【立即归档】"
for file in "${IMMEDIATE_DELETE[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    fi
done
echo ""

echo "【保留的核心文档】"
echo "  ✓ README.md - 项目主文档"
echo "  ✓ DEVELOPMENT_WORKFLOW.md - 开发流程指南"
echo "  ✓ 如何部署到服务器.md - 部署操作指南"
echo ""

read -p "确认清理？(y/N): " CONFIRM

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "❌ 已取消"
    exit 0
fi

echo ""
echo "移动文件到归档..."
MOVED=0

for file in "${IMMEDIATE_DELETE[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$ARCHIVE_DIR/"
        echo "  ✓ 已移动: $file"
        ((MOVED++))
    fi
done

echo ""
echo "=========================================="
echo "✅ 清理完成！"
echo "=========================================="
echo ""
echo "已移动 $MOVED 个文件到: $ARCHIVE_DIR"
echo ""
echo "保留的核心文档（3个）："
echo "  1. README.md"
echo "  2. DEVELOPMENT_WORKFLOW.md"
echo "  3. 如何部署到服务器.md"
echo ""
