# SweetSeek 部署指南

## 自动部署使用方法

### 方法1：完整部署（推荐）

```bash
./deploy.sh "修改了XXX功能"
```

这会自动完成：
1. ✅ 提交本地修改到 Git
2. ✅ 推送到远程仓库
3. ✅ 连接服务器拉取最新代码
4. ✅ 自动重启服务

### 方法2：快速部署

```bash
./quick-deploy.sh
```

使用默认提交信息快速部署。

### 方法3：只推送代码（不部署）

```bash
git add .
git commit -m "修改说明"
git push
```

然后手动登录服务器更新：
```bash
ssh root@8.137.32.247
cd /www/wwwroot/FCN_SweetSeek
git pull
supervisorctl restart sweetseek
```

---

## 服务器信息

- **IP**: 8.137.32.247
- **项目路径**: /www/wwwroot/FCN_SweetSeek
- **访问地址**: http://8.137.32.247:5001
- **域名**（备案后）: http://sweetseek.top

---

## 常见问题

### Q: 部署失败怎么办？

**A: 检查以下几点：**
1. 确认能 SSH 连接到服务器：`ssh root@8.137.32.247`
2. 确认服务器上有 Git 仓库：`ssh root@8.137.32.247 "cd /www/wwwroot/FCN_SweetSeek && git status"`
3. 查看错误信息，根据提示解决

### Q: 如何查看服务器日志？

**A: 登录服务器查看：**
```bash
ssh root@8.137.32.247
cd /www/wwwroot/FCN_SweetSeek
tail -f logs/app.log
```

### Q: 如何手动重启服务？

**A: 使用 Supervisor：**
```bash
ssh root@8.137.32.247 "supervisorctl restart sweetseek"
```

或者在宝塔面板中重启。

### Q: 修改了 .env 文件怎么办？

**A: .env 文件不会被 Git 追踪（在 .gitignore 中），需要手动更新：**
```bash
scp .env root@8.137.32.247:/www/wwwroot/FCN_SweetSeek/
ssh root@8.137.32.247 "supervisorctl restart sweetseek"
```

---

## 开发工作流

### 日常开发流程

1. **在本地修改代码**
   - 在 Kiro 中编辑文件
   - 本地测试功能

2. **部署到服务器**
   ```bash
   ./deploy.sh "添加了XXX功能"
   ```

3. **验证部署**
   - 访问 http://8.137.32.247:5001
   - 测试新功能是否正常

4. **如果有问题**
   - 查看服务器日志
   - 修复问题
   - 重新部署

### 紧急回滚

如果部署后发现严重问题，可以回滚到上一个版本：

```bash
# 在服务器上
ssh root@8.137.32.247
cd /www/wwwroot/FCN_SweetSeek
git log --oneline  # 查看提交历史
git reset --hard HEAD~1  # 回滚到上一个版本
supervisorctl restart sweetseek
```

---

## 注意事项

1. ⚠️ **不要提交敏感信息**
   - API 密钥在 .env 中，不会被提交
   - 不要在代码中硬编码密钥

2. ⚠️ **大文件不要提交**
   - PDF 文献文件已在 .gitignore 中排除
   - 模型文件已在 .gitignore 中排除

3. ⚠️ **备案期间**
   - 域名解析保持关闭
   - 只能通过 IP 访问
   - 代码可以正常更新

4. ✅ **备案完成后**
   - 启用域名解析
   - 就可以用 sweetseek.top 访问了

---

## 技术栈

- **后端**: Python 3.9 + Flask
- **向量数据库**: ChromaDB
- **嵌入模型**: BGE-small-zh-v1.5
- **LLM**: DeepSeek-R1 (via SiliconFlow)
- **部署**: 阿里云轻量应用服务器
- **进程管理**: Supervisor
- **Web服务器**: Nginx (宝塔面板)

---

## 联系方式

如有问题，请联系项目维护者。
