#!/bin/bash
# 食品AI科研问答系统 - Git部署脚本

echo "🚀 开始部署到Git仓库..."
echo ""

# 检查是否已初始化Git
if [ ! -d ".git" ]; then
    echo "📝 初始化Git仓库..."
    git init
    echo "✅ Git初始化完成"
else
    echo "✅ Git仓库已存在"
fi

# 添加所有文件
echo ""
echo "📦 添加文件到Git..."
git add .

# 查看状态
echo ""
echo "📊 当前状态："
git status --short

# 提交
echo ""
read -p "📝 请输入提交说明（默认：初始提交）: " commit_msg
commit_msg=${commit_msg:-"初始提交：食品AI科研问答系统"}

git commit -m "$commit_msg"
echo "✅ 提交完成"

# 询问远程仓库
echo ""
echo "🌐 选择Git平台："
echo "  1. GitHub（国际）"
echo "  2. Gitee（国内推荐）"
echo "  3. 跳过（稍后手动添加）"
read -p "请选择 [1-3]: " choice

case $choice in
    1)
        echo ""
        read -p "📝 请输入GitHub用户名: " username
        read -p "📝 请输入仓库名（默认：food-ai-research-qa）: " repo_name
        repo_name=${repo_name:-"food-ai-research-qa"}
        
        remote_url="https://github.com/$username/$repo_name.git"
        
        # 检查是否已有远程仓库
        if git remote | grep -q "origin"; then
            echo "⚠️  远程仓库已存在，更新URL..."
            git remote set-url origin $remote_url
        else
            git remote add origin $remote_url
        fi
        
        echo ""
        echo "🔗 远程仓库已设置: $remote_url"
        echo ""
        read -p "是否立即推送到GitHub？[y/N]: " push_now
        
        if [[ $push_now =~ ^[Yy]$ ]]; then
            echo "📤 推送到GitHub..."
            git branch -M main
            git push -u origin main
            echo "✅ 推送完成！"
            echo ""
            echo "🎉 项目地址: https://github.com/$username/$repo_name"
        else
            echo "💡 稍后手动推送："
            echo "   git branch -M main"
            echo "   git push -u origin main"
        fi
        ;;
        
    2)
        echo ""
        read -p "📝 请输入Gitee用户名: " username
        read -p "📝 请输入仓库名（默认：food-ai-research-qa）: " repo_name
        repo_name=${repo_name:-"food-ai-research-qa"}
        
        remote_url="https://gitee.com/$username/$repo_name.git"
        
        # 检查是否已有远程仓库
        if git remote | grep -q "origin"; then
            echo "⚠️  远程仓库已存在，更新URL..."
            git remote set-url origin $remote_url
        else
            git remote add origin $remote_url
        fi
        
        echo ""
        echo "🔗 远程仓库已设置: $remote_url"
        echo ""
        read -p "是否立即推送到Gitee？[y/N]: " push_now
        
        if [[ $push_now =~ ^[Yy]$ ]]; then
            echo "📤 推送到Gitee..."
            git push -u origin master
            echo "✅ 推送完成！"
            echo ""
            echo "🎉 项目地址: https://gitee.com/$username/$repo_name"
        else
            echo "💡 稍后手动推送："
            echo "   git push -u origin master"
        fi
        ;;
        
    3)
        echo ""
        echo "💡 跳过远程仓库设置"
        echo "💡 稍后可以手动添加："
        echo "   git remote add origin <仓库地址>"
        echo "   git push -u origin main"
        ;;
        
    *)
        echo "❌ 无效选择"
        ;;
esac

echo ""
echo "=" * 60
echo "✅ 部署完成！"
echo ""
echo "📋 后续操作："
echo "  1. 在GitHub/Gitee创建仓库（如果还没创建）"
echo "  2. 推送代码（如果还没推送）"
echo "  3. 分享仓库链接给别人"
echo ""
echo "📖 详细说明：查看 Git使用指南.md"
echo "=" * 60
