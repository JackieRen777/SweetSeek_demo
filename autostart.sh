#!/bin/bash
# SweetSeek 开机自动启动管理
# 用法：
#   ./autostart.sh install    # 安装开机自动启动
#   ./autostart.sh uninstall  # 卸载开机自动启动
#   ./autostart.sh status     # 查看状态

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_FILE="$HOME/Library/LaunchAgents/com.sweetseek.server.plist"

# 显示使用帮助
show_help() {
    echo "用法: ./autostart.sh [命令]"
    echo ""
    echo "命令:"
    echo "  install    安装开机自动启动"
    echo "  uninstall  卸载开机自动启动"
    echo "  status     查看当前状态"
    echo ""
}

# 安装自动启动
install_autostart() {
    echo "📦 安装 SweetSeek 开机自动启动..."
    echo ""
    
    # 检查是否已安装
    if [ -f "$PLIST_FILE" ]; then
        echo "⚠️  已经安装过了"
        echo "   如需重新安装，请先运行: ./autostart.sh uninstall"
        exit 1
    fi
    
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
    launchctl load "$PLIST_FILE"
    
    if [ $? -eq 0 ]; then
        echo "✅ 安装成功！"
        echo ""
        echo "现在 SweetSeek 会在开机时自动启动"
        echo ""
        echo "管理命令："
        echo "  查看状态: ./autostart.sh status"
        echo "  卸载: ./autostart.sh uninstall"
    else
        echo "❌ 安装失败"
        rm "$PLIST_FILE"
        exit 1
    fi
}

# 卸载自动启动
uninstall_autostart() {
    echo "🗑️  卸载 SweetSeek 开机自动启动..."
    echo ""
    
    if [ -f "$PLIST_FILE" ]; then
        launchctl unload "$PLIST_FILE" 2>/dev/null
        rm "$PLIST_FILE"
        echo "✅ 卸载成功"
    else
        echo "⚠️  未找到自动启动配置"
    fi
}

# 查看状态
show_status() {
    echo "📊 SweetSeek 自动启动状态"
    echo ""
    
    if [ -f "$PLIST_FILE" ]; then
        echo "✅ 已安装开机自动启动"
        echo ""
        
        # 检查 LaunchAgent 状态
        if launchctl list | grep -q "com.sweetseek.server"; then
            echo "✅ LaunchAgent 已加载"
        else
            echo "⚠️  LaunchAgent 未加载"
        fi
        
        # 检查服务器是否运行
        if pgrep -f "python.*app.py" > /dev/null; then
            PID=$(pgrep -f "python.*app.py")
            echo "✅ 服务器正在运行 (PID: $PID)"
            
            # 测试 API
            if curl -s http://localhost:5001/api/stats > /dev/null 2>&1; then
                echo "✅ API 响应正常"
                echo ""
                echo "访问: http://localhost:5001"
            else
                echo "⚠️  API 无响应（可能正在启动）"
            fi
        else
            echo "❌ 服务器未运行"
        fi
    else
        echo "❌ 未安装开机自动启动"
        echo ""
        echo "安装: ./autostart.sh install"
    fi
}

# 主逻辑
case "$1" in
    install)
        install_autostart
        ;;
    uninstall)
        uninstall_autostart
        ;;
    status)
        show_status
        ;;
    *)
        show_help
        exit 1
        ;;
esac
