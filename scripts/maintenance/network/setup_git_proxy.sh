#!/bin/bash
# Git代理配置脚本

echo "=========================================="
echo "🔧 配置Git代理"
echo "=========================================="
echo ""

# 检测系统代理
PROXY_HOST=$(scutil --proxy | grep HTTPProxy | awk '{print $3}')
PROXY_PORT=$(scutil --proxy | grep HTTPPort | awk '{print $3}')

if [ -z "$PROXY_HOST" ] || [ -z "$PROXY_PORT" ]; then
    echo "❌ 未检测到系统代理设置"
    echo ""
    echo "请手动配置："
    echo "git config --global http.proxy http://127.0.0.1:7890"
    echo "git config --global https.proxy http://127.0.0.1:7890"
    exit 1
fi

PROXY_URL="http://${PROXY_HOST}:${PROXY_PORT}"

echo "检测到系统代理："
echo "  地址: $PROXY_HOST"
echo "  端口: $PROXY_PORT"
echo "  完整URL: $PROXY_URL"
echo ""

# 配置Git代理
echo "配置Git代理..."
git config --global http.proxy "$PROXY_URL"
git config --global https.proxy "$PROXY_URL"

# 只对GitHub使用代理（推荐）
echo ""
echo "配置GitHub专用代理..."
git config --global http.https://github.com.proxy "$PROXY_URL"
git config --global https.https://github.com.proxy "$PROXY_URL"

echo ""
echo "✅ Git代理配置完成！"
echo ""

# 显示当前配置
echo "当前Git代理配置："
echo "----------------------------------------"
git config --global --get http.proxy
git config --global --get https.proxy
git config --global --get http.https://github.com.proxy
git config --global --get https.https://github.com.proxy
echo "----------------------------------------"
echo ""

# 测试连接
echo "测试GitHub连接..."
if git ls-remote https://github.com/JackieRen777/SweetSeek_demo.git HEAD > /dev/null 2>&1; then
    echo "✅ GitHub连接成功！"
else
    echo "⚠️  GitHub连接测试失败，但代理已配置"
    echo "   请检查代理服务是否正常运行"
fi

echo ""
echo "=========================================="
echo "📋 常用命令"
echo "=========================================="
echo ""
echo "查看代理配置："
echo "  git config --global --get http.proxy"
echo ""
echo "取消代理配置："
echo "  git config --global --unset http.proxy"
echo "  git config --global --unset https.proxy"
echo ""
echo "只取消GitHub代理："
echo "  git config --global --unset http.https://github.com.proxy"
echo "  git config --global --unset https.https://github.com.proxy"
echo ""
