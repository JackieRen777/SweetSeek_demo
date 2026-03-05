#!/bin/bash

# SweetSeek 服务器部署辅助脚本
# 该脚本用于在服务器上自动创建持久化目录并配置权限
# 请以 root 权限或 sudo 执行此脚本

set -e

# 配置变量
DATA_DIR="/data/sweetseek_db"
USER_NAME="www" # 假设运行服务的用户是 www，请根据实际情况修改（如 root, ubuntu, nginx 等）
PROJECT_DIR="/www/wwwroot/sweetseek" # 项目根目录，请根据实际情况修改

echo "=================================================="
echo "SweetSeek 服务器部署助手"
echo "=================================================="

# 1. 创建持久化数据目录
echo "[1/4] 检查并创建数据目录: $DATA_DIR"
if [ ! -d "$DATA_DIR" ]; then
    mkdir -p "$DATA_DIR"
    echo "✅ 目录已创建"
else
    echo "ℹ️ 目录已存在"
fi

# 2. 设置目录权限
echo "[2/4] 设置目录权限 (Owner: $USER_NAME)"
# 检查用户是否存在
if id "$USER_NAME" &>/dev/null; then
    chown -R "$USER_NAME:$USER_NAME" "$DATA_DIR"
    chmod -R 755 "$DATA_DIR"
    echo "✅ 权限已更新"
else
    echo "⚠️ 用户 '$USER_NAME' 不存在，跳过权限设置。请手动执行: chown -R <your_user> $DATA_DIR"
fi

# 3. 检查并更新 .env 配置文件
ENV_FILE="$PROJECT_DIR/.env"
echo "[3/4] 检查配置文件: $ENV_FILE"

if [ -f "$ENV_FILE" ]; then
    echo "ℹ️ 发现 .env 文件，正在追加/更新配置..."
    
    # 备份
    cp "$ENV_FILE" "$ENV_FILE.bak.$(date +%s)"
    
    # 使用 grep 检查是否存在配置，不存在则追加
    if ! grep -q "CHROMA_DB_DIR=" "$ENV_FILE"; then
        echo "CHROMA_DB_DIR=$DATA_DIR" >> "$ENV_FILE"
        echo "➕ 已添加 CHROMA_DB_DIR"
    else
        # 简单的 sed 替换（注意：这可能需要根据实际情况调整）
        sed -i "s|CHROMA_DB_DIR=.*|CHROMA_DB_DIR=$DATA_DIR|g" "$ENV_FILE"
        echo "🔄 已更新 CHROMA_DB_DIR"
    fi
    
    if ! grep -q "EMBED_MODEL_NAME=" "$ENV_FILE"; then
        echo "EMBED_MODEL_NAME=BAAI/bge-small-zh-v1.5" >> "$ENV_FILE"
        echo "➕ 已添加 EMBED_MODEL_NAME"
    else
        sed -i "s|EMBED_MODEL_NAME=.*|EMBED_MODEL_NAME=BAAI/bge-small-zh-v1.5|g" "$ENV_FILE"
        echo "🔄 已更新 EMBED_MODEL_NAME"
    fi
    
    if ! grep -q "EMBED_MODEL_SOURCE=" "$ENV_FILE"; then
        echo "EMBED_MODEL_SOURCE=modelscope" >> "$ENV_FILE"
        echo "➕ 已添加 EMBED_MODEL_SOURCE"
    fi
    
    echo "✅ .env 配置已更新"
else
    echo "⚠️ 未找到 $ENV_FILE，请确保在项目根目录下执行或手动创建 .env 文件"
    echo "建议内容："
    echo "CHROMA_DB_DIR=$DATA_DIR"
    echo "EMBED_MODEL_NAME=BAAI/bge-small-zh-v1.5"
    echo "EMBED_MODEL_SOURCE=modelscope"
fi

# 4. 提示 Nginx 配置
echo "[4/4] Nginx 配置提醒"
echo "请手动检查 Nginx 配置，确保已添加 'proxy_buffering off;' 以支持流式响应。"
echo "参考配置文件: nginx_stream.conf"

echo ""
echo "=================================================="
echo "🎉 操作完成！"
echo "请重启您的后端服务以应用更改。"
echo "示例: sudo systemctl restart sweetseek-backend"
echo "=================================================="
