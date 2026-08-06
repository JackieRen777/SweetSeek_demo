#!/bin/bash
# 域名部署脚本

echo "=========================================="
echo "  SweetSeek 域名部署脚本"
echo "=========================================="
echo ""

# 检查是否提供了域名参数
if [ -z "$1" ]; then
    echo "❌ 错误：请提供域名"
    echo "用法: ./deploy_domain.sh your-domain.com"
    exit 1
fi

DOMAIN=$1
CONF_FILE="nginx_sweetseek.conf"
NGINX_CONF_DIR="/www/server/panel/vhost/nginx"
TARGET_CONF="${NGINX_CONF_DIR}/${DOMAIN}.conf"

echo "域名: $DOMAIN"
echo "配置文件: $TARGET_CONF"
echo ""

# 1. 检查配置文件是否存在
if [ ! -f "$CONF_FILE" ]; then
    echo "❌ 错误：找不到配置文件 $CONF_FILE"
    exit 1
fi

# 2. 替换域名占位符
echo "【1】生成配置文件..."
sed "s/YOUR_DOMAIN_HERE/$DOMAIN/g" "$CONF_FILE" > "/tmp/sweetseek_${DOMAIN}.conf"
echo "✅ 配置文件已生成"
echo ""

# 3. 复制到Nginx配置目录
echo "【2】安装配置文件..."
cp "/tmp/sweetseek_${DOMAIN}.conf" "$TARGET_CONF"
echo "✅ 配置文件已安装到: $TARGET_CONF"
echo ""

# 4. 测试Nginx配置
echo "【3】测试Nginx配置..."
nginx -t
if [ $? -eq 0 ]; then
    echo "✅ Nginx配置测试通过"
else
    echo "❌ Nginx配置测试失败"
    echo "正在回滚..."
    rm -f "$TARGET_CONF"
    exit 1
fi
echo ""

# 5. 重载Nginx
echo "【4】重载Nginx..."
systemctl reload nginx
if [ $? -eq 0 ]; then
    echo "✅ Nginx已重载"
else
    echo "❌ Nginx重载失败"
    exit 1
fi
echo ""

# 6. 检查Flask应用是否运行
echo "【5】检查Flask应用..."
if pgrep -f "python.*app.py" > /dev/null; then
    echo "✅ Flask应用正在运行"
else
    echo "⚠️  Flask应用未运行，正在启动..."
    cd /www/wwwroot/FCN_SweetSeek
    nohup python app.py > /dev/null 2>&1 &
    sleep 2
    if pgrep -f "python.*app.py" > /dev/null; then
        echo "✅ Flask应用已启动"
    else
        echo "❌ Flask应用启动失败"
    fi
fi
echo ""

echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "📝 下一步操作："
echo "1. 确保域名 $DOMAIN 已解析到服务器IP: 8.136.8.223"
echo "2. 在浏览器访问: http://$DOMAIN"
echo "3. 如需配置HTTPS，运行: certbot --nginx -d $DOMAIN"
echo ""
echo "🔍 测试命令："
echo "  curl -I http://$DOMAIN"
echo "  curl http://$DOMAIN/api/health"
echo ""
