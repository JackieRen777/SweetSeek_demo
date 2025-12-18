#!/bin/bash
# 安装开机自动启动

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_FILE="$HOME/Library/LaunchAgents/com.sweetseek.server.plist"

echo "📦 安装 SweetSeek 开机自动启动..."
echo ""

# 创建 LaunchAgent 配置
cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.sweetseek.server</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$PROJECT_DIR/.venv/bin/python3</string>
        <string>$PROJECT_DIR/app.py</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <false/>
    
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/autostart.log</string>
    
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/autostart.log</string>
</dict>
</plist>
EOF

# 加载配置
launchctl unload "$PLIST_FILE" 2>/dev/null
launchctl load "$PLIST_FILE"

if [ $? -eq 0 ]; then
    echo "✅ 安装成功！"
    echo ""
    echo "现在 SweetSeek 会在开机时自动启动"
    echo ""
    echo "管理命令："
    echo "  查看状态: launchctl list | grep sweetseek"
    echo "  停止服务: launchctl unload $PLIST_FILE"
    echo "  启动服务: launchctl load $PLIST_FILE"
    echo "  卸载自动启动: ./uninstall_autostart.sh"
else
    echo "❌ 安装失败"
    exit 1
fi
