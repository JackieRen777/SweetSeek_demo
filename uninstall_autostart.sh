#!/bin/bash
# 卸载开机自动启动

PLIST_FILE="$HOME/Library/LaunchAgents/com.sweetseek.server.plist"

echo "🗑️  卸载 SweetSeek 开机自动启动..."

if [ -f "$PLIST_FILE" ]; then
    launchctl unload "$PLIST_FILE" 2>/dev/null
    rm "$PLIST_FILE"
    echo "✅ 卸载成功"
else
    echo "⚠️  未找到自动启动配置"
fi
