# SweetSeek 部署指南

# SweetSeek 部署指南

## 推荐工作流程

### 日常开发流程

1. **在本地修改代码**
   - 在 Kiro 中编辑文件
   - 本地测试功能
   - 修复 bug，添加新功能

2. **完成一个功能后推送**
   ```bash
   ./push.sh
   ```
   
   这个脚本会：
   - ✅ 自动检测修改的文件
   - ✅ 自动生成更新摘要
   - ✅ 列出修改的文件列表
   - ✅ 可选添加自定义说明
   - ✅ 推送到 GitHub
   - ✅ 询问是否立即部署到服务器

3. **部署到服务器（可选）**
   
   **方式1：推送时立即部署**
   - 在 `push.sh` 最后询问时输入 `y`
   
   **方式2：稍后手动部署**
   ```bash
   ./deploy-v2.sh
   ```

---

## 脚本说明

### 1. push.sh - 智能推送脚本（推荐）

**用途：** 完成功能开发后，推送代码到 GitHub

**功能：**
- 自动检测修改的文件
- 自动生成更新摘要（统计修改的文件类型和数量）
- 列出具体修改的文件
- 可选添加自定义说明
- 推送到 GitHub
- 询问是否立即部署

**使用：**
```bash
./push.sh
```

**示例输出：**
```
自动生成的更新摘要：
- 修改了 2 个 Python 文件（后端逻辑）
- 修改了 1 个 JavaScript 文件（前端功能）

修改的文件列表：
  - app.py
  - persistent_storage.py
  - static/main.js

是否添加自定义说明？（直接回车跳过，或输入说明）
> 修复了 ref 编号不匹配的问题

是否立即部署到服务器？
输入 'y' 部署，直接回车跳过
> y
```

---

### 2. deploy-v2.sh - 完善的部署脚本

**用途：** 将代码部署到服务器

**功能：**
- 从 GitHub 拉取最新代码
- 自动检查服务器环境
- 自动修复 .env 配置
- 检查模型文件是否存在
- 正确停止和启动进程
- 验证部署是否成功

**使用：**
```bash
./deploy-v2.sh
```

---

### 3. restart-server.sh - 快速重启服务

**用途：** 只重启服务器上的服务，不更新代码

**使用：**
```bash
./restart-server.sh
```

---

### 4. check-deployment.sh - 环境检查

**用途：** 检查服务器环境是否配置正确

**使用：**
```bash
./check-deployment.sh
```

---

## 使用场景

### 场景1：修复了一个 bug

```bash
# 1. 修改代码
# 2. 本地测试
# 3. 推送
./push.sh
# 输入自定义说明：修复了XXX bug
# 选择立即部署：y
```

### 场景2：添加了新功能

```bash
# 1. 开发新功能
# 2. 本地测试
# 3. 推送
./push.sh
# 输入自定义说明：添加了XXX功能
# 选择稍后部署：直接回车
# 4. 稍后部署
./deploy-v2.sh
```

### 场景3：只修改了文档

```bash
# 1. 修改 README.md 等文档
# 2. 推送
./push.sh
# 输入自定义说明：更新了文档
# 选择不部署：直接回车（文档修改不需要重启服务）
```

### 场景4：服务器出问题了

```bash
# 快速重启服务
./restart-server.sh
```

---

## 自动部署使用方法（旧版，不推荐）

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
pkill -f "python.*app.py"
source venv/bin/activate
nohup python app.py > logs/app.log 2>&1 &
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
