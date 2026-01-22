# SweetSeek 部署问题排查指南

## 问题：推送代码后网站无法访问

### 根本原因分析

#### 1. 模型文件丢失
**原因：**
- 模型文件在 `.gitignore` 中被排除
- Git 推送时不包含 `models/` 目录
- 服务器拉取代码后，模型文件不存在

**症状：**
- 程序启动时卡住
- 日志显示尝试连接 HuggingFace
- 5001 端口没有监听

**解决方案：**
```bash
# 从本地上传模型文件到服务器（只需做一次）
scp -r models/models--BAAI--bge-small-zh-v1.5 root@8.137.32.247:/www/wwwroot/FCN_SweetSeek/models/
```

#### 2. 环境变量配置缺失
**原因：**
- `.env` 文件在 `.gitignore` 中被排除
- 服务器上的 `.env` 缺少离线模式配置
- 程序尝试从网络下载模型

**症状：**
- 日志显示 "Network is unreachable"
- 程序重试连接 HuggingFace
- 最终超时退出

**解决方案：**
```bash
# 在服务器上添加离线模式配置
ssh root@8.137.32.247
cd /www/wwwroot/FCN_SweetSeek
echo "HF_HUB_OFFLINE=1" >> .env
echo "TRANSFORMERS_OFFLINE=1" >> .env
```

#### 3. 进程管理问题
**原因：**
- 旧进程没有正确停止
- 新进程启动失败
- 端口被占用

**症状：**
- 多个 Python 进程同时运行
- 端口冲突
- 服务不稳定

**解决方案：**
```bash
# 彻底清理并重启
ssh root@8.137.32.247
cd /www/wwwroot/FCN_SweetSeek
pkill -f "python.*app.py"
sleep 2
source venv/bin/activate
nohup python app.py > logs/app.log 2>&1 &
```

---

## 预防措施

### 1. 使用完善的部署脚本

**推荐使用 `deploy-v2.sh`：**
```bash
./deploy-v2.sh "修改说明"
```

**功能：**
- ✅ 自动检查环境配置
- ✅ 自动修复 .env 文件
- ✅ 检查模型文件是否存在
- ✅ 正确停止和启动进程
- ✅ 验证部署是否成功

### 2. 首次部署检查清单

**在首次部署或重新部署时，确保：**

1. **模型文件已上传**
   ```bash
   ssh root@8.137.32.247 "ls -la /www/wwwroot/FCN_SweetSeek/models/models--BAAI--bge-small-zh-v1.5/snapshots/"
   ```
   应该看到模型文件（.safetensors 或 .bin）

2. **.env 文件配置正确**
   ```bash
   ssh root@8.137.32.247 "cat /www/wwwroot/FCN_SweetSeek/.env"
   ```
   应该包含：
   - `HF_HUB_OFFLINE=1`
   - `TRANSFORMERS_OFFLINE=1`
   - `DEEPSEEK_API_KEY=...`

3. **虚拟环境存在**
   ```bash
   ssh root@8.137.32.247 "ls -la /www/wwwroot/FCN_SweetSeek/venv/"
   ```

4. **日志目录存在**
   ```bash
   ssh root@8.137.32.247 "mkdir -p /www/wwwroot/FCN_SweetSeek/logs"
   ```

### 3. 部署后验证

**每次部署后，验证服务是否正常：**

1. **检查端口监听**
   ```bash
   ssh root@8.137.32.247 "netstat -tunlp | grep 5001"
   ```
   应该看到 Python 进程在监听 5001 端口

2. **检查进程状态**
   ```bash
   ssh root@8.137.32.247 "ps aux | grep 'python.*app.py' | grep -v grep"
   ```
   应该只有一个 Python 进程

3. **测试网站访问**
   ```bash
   curl -I http://8.137.32.247:5001
   ```
   应该返回 HTTP 200

4. **查看最新日志**
   ```bash
   ssh root@8.137.32.247 "tail -20 /www/wwwroot/FCN_SweetSeek/logs/app.log"
   ```
   应该看到 "Running on http://0.0.0.0:5001"

---

## 常见问题快速修复

### Q1: 部署后网站打不开

**快速修复：**
```bash
./restart-server.sh
```

或手动：
```bash
ssh root@8.137.32.247
cd /www/wwwroot/FCN_SweetSeek
pkill -f "python.*app.py"
source venv/bin/activate
nohup python app.py > logs/app.log 2>&1 &
sleep 5
netstat -tunlp | grep 5001
```

### Q2: 模型文件丢失

**快速修复：**
```bash
scp -r models/models--BAAI--bge-small-zh-v1.5 root@8.137.32.247:/www/wwwroot/FCN_SweetSeek/models/
./restart-server.sh
```

### Q3: .env 配置错误

**快速修复：**
```bash
scp .env root@8.137.32.247:/www/wwwroot/FCN_SweetSeek/
ssh root@8.137.32.247 "cd /www/wwwroot/FCN_SweetSeek && echo 'HF_HUB_OFFLINE=1' >> .env && echo 'TRANSFORMERS_OFFLINE=1' >> .env"
./restart-server.sh
```

### Q4: 多个进程冲突

**快速修复：**
```bash
ssh root@8.137.32.247 "pkill -9 -f 'python.*app.py'"
./restart-server.sh
```

---

## 最佳实践

### 1. 部署前检查
```bash
./check-deployment.sh
```

### 2. 使用完善的部署脚本
```bash
./deploy-v2.sh "修改说明"
```

### 3. 部署后验证
```bash
curl http://8.137.32.247:5001
```

### 4. 出问题时查看日志
```bash
ssh root@8.137.32.247 "tail -50 /www/wwwroot/FCN_SweetSeek/logs/app.log"
```

---

## 紧急回滚

如果部署后出现严重问题，可以回滚到上一个版本：

```bash
ssh root@8.137.32.247
cd /www/wwwroot/FCN_SweetSeek
git log --oneline -5  # 查看最近5次提交
git reset --hard HEAD~1  # 回滚到上一个版本
pkill -f "python.*app.py"
source venv/bin/activate
nohup python app.py > logs/app.log 2>&1 &
```

---

## 联系支持

如果问题仍然无法解决，请提供以下信息：

1. 错误日志：`tail -100 /www/wwwroot/FCN_SweetSeek/logs/app.log`
2. 进程状态：`ps aux | grep python`
3. 端口状态：`netstat -tunlp | grep 5001`
4. 环境配置：`cat /www/wwwroot/FCN_SweetSeek/.env`（隐藏 API 密钥）
