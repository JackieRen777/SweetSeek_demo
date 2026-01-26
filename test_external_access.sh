#!/bin/bash
# 外部访问测试脚本

SERVER_IP="8.137.32.247"
PORT="5001"
BASE_URL="http://${SERVER_IP}:${PORT}"

echo "==================================="
echo "  SweetSeek 外部访问测试"
echo "==================================="
echo ""
echo "服务器: ${SERVER_IP}"
echo "端口: ${PORT}"
echo ""

# 测试1: 网络连通性
echo "【测试1】网络连通性"
echo -n "  Ping服务器... "
if ping -c 1 -W 2 ${SERVER_IP} > /dev/null 2>&1; then
    echo "✅ 成功"
else
    echo "❌ 失败"
fi

# 测试2: 端口开放
echo -n "  检查端口${PORT}... "
if nc -z -w 2 ${SERVER_IP} ${PORT} 2>/dev/null; then
    echo "✅ 开放"
else
    echo "❌ 关闭"
fi

echo ""

# 测试3: 健康检查
echo "【测试2】健康检查端点"
echo -n "  GET ${BASE_URL}/api/health... "
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" --max-time 5 ${BASE_URL}/api/health 2>/dev/null)
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n 1)
RESPONSE_BODY=$(echo "$HEALTH_RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ 成功 (HTTP $HTTP_CODE)"
    echo "  响应: $(echo $RESPONSE_BODY | python3 -m json.tool 2>/dev/null | head -5)"
else
    echo "❌ 失败 (HTTP $HTTP_CODE)"
fi

echo ""

# 测试4: 统计信息
echo "【测试3】统计信息端点"
echo -n "  GET ${BASE_URL}/api/stats... "
STATS_RESPONSE=$(curl -s -w "\n%{http_code}" --max-time 5 ${BASE_URL}/api/stats 2>/dev/null)
HTTP_CODE=$(echo "$STATS_RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ 成功 (HTTP $HTTP_CODE)"
else
    echo "❌ 失败 (HTTP $HTTP_CODE)"
fi

echo ""

# 测试5: 主页访问
echo "【测试4】主页访问"
echo -n "  GET ${BASE_URL}/... "
HOME_RESPONSE=$(curl -s -w "\n%{http_code}" --max-time 5 ${BASE_URL}/ 2>/dev/null)
HTTP_CODE=$(echo "$HOME_RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ 成功 (HTTP $HTTP_CODE)"
else
    echo "❌ 失败 (HTTP $HTTP_CODE)"
fi

echo ""
echo "==================================="
echo "  测试完成"
echo "==================================="
echo ""
echo "💡 提示:"
echo "  - 如果测试失败，请检查阿里云安全组配置"
echo "  - 确保端口5001已开放"
echo "  - 在浏览器中访问: ${BASE_URL}"
echo ""
