#!/bin/bash

# 部署前检查脚本
# 确保服务器环境配置正确

SERVER_IP="8.137.32.247"
SERVER_USER="root"
SERVER_PATH="/www/wwwroot/FCN_SweetSeek"

echo "========================================="
echo "  SweetSeek 部署环境检查"
echo "========================================="
echo ""

echo "正在检查服务器环境..."
echo "请输入服务器密码：Fcn509509"
echo ""

ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'

cd /www/wwwroot/FCN_SweetSeek

echo "1. 检查 .env 文件..."
if [ ! -f .env ]; then
    echo "❌ .env 文件不存在！"
    exit 1
fi

# 检查必要的环境变量
if ! grep -q "HF_HUB_OFFLINE=1" .env; then
    echo "⚠️  缺少 HF_HUB_OFFLINE=1，正在添加..."
    echo "HF_HUB_OFFLINE=1" >> .env
fi

if ! grep -q "TRANSFORMERS_OFFLINE=1" .env; then
    echo "⚠️  缺少 TRANSFORMERS_OFFLINE=1，正在添加..."
    echo "TRANSFORMERS_OFFLINE=1" >> .env
fi

echo "✅ .env 文件配置正确"
echo ""

echo "2. 检查模型文件..."
MODEL_PATH="models/models--BAAI--bge-small-zh-v1.5/snapshots"
if [ ! -d "$MODEL_PATH" ]; then
    echo "❌ 模型文件不存在！"
    echo "   需要从本地上传模型文件"
    exit 1
fi

MODEL_FILE=$(find $MODEL_PATH -name "*.safetensors" -o -name "pytorch_model.bin" | head -1)
if [ -z "$MODEL_FILE" ]; then
    echo "❌ 模型文件不完整！"
    exit 1
fi

echo "✅ 模型文件存在"
echo ""

echo "3. 检查虚拟环境..."
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在！"
    exit 1
fi

echo "✅ 虚拟环境存在"
echo ""

echo "4. 检查日志目录..."
if [ ! -d "logs" ]; then
    echo "⚠️  logs 目录不存在，正在创建..."
    mkdir -p logs
fi

echo "✅ 日志目录存在"
echo ""

echo "========================================="
echo "  环境检查完成！可以安全部署"
echo "========================================="

ENDSSH

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 服务器环境检查通过！"
    echo ""
else
    echo ""
    echo "❌ 服务器环境检查失败！请先修复问题。"
    echo ""
    exit 1
fi
