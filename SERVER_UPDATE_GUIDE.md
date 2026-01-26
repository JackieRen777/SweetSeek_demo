# 服务器代码更新指南

## 🎯 目标
更新阿里云服务器上的代码到最新版本（提交: 5dd4452 "修正结构逻辑错误"）

---

## 📋 方法1: 通过阿里云VNC（推荐）

### 步骤1: 登录阿里云控制台
1. 访问: https://ecs.console.aliyun.com
2. 登录你的阿里云账号
3. 找到实例列表

### 步骤2: 连接VNC
1. 找到你的ECS实例（FCN_SweetSeek相关）
2. 点击实例右侧的"远程连接"
3. 选择"VNC"
4. 输入VNC密码（如果首次使用，需要设置密码）

### 步骤3: 执行更新命令
在VNC终端中依次执行：

```bash
# 1. 进入项目目录
cd /www/wwwroot/FCN_SweetSeek

# 2. 检查当前状态
git status
git log --oneline -3

# 3. 拉取最新代码
git pull origin RenJiaqi

# 4. 检查更新内容
git log --oneline -3

# 5. 重启服务
./restart-server.sh

# 6. 等待几秒让服务启动
sleep 5

# 7. 验证服务
curl http://localhost:5001/api/health
```

### 步骤4: 验证更新
```bash
# 查看日志
tail -f logs/sweetseek.log

# 按 Ctrl+C 退出日志查看
```

---

## 📋 方法2: 通过SSH（如果SSH可用）

### 前提条件
- SSH端口22已开放
- 有SSH密钥或密码

### 执行命令
```bash
# 从本地连接到服务器
ssh root@8.137.32.247

# 进入项目目录
cd /www/wwwroot/FCN_SweetSeek

# 拉取最新代码
git pull origin RenJiaqi

# 重启服务
./restart-server.sh

# 验证
curl http://localhost:5001/api/health

# 退出SSH
exit
```

---

## ✅ 验证更新成功

### 在服务器上验证
```bash
# 1. 检查Git提交
cd /www/wwwroot/FCN_SweetSeek
git log --oneline -1
# 应该显示: 5dd4452 修正结构逻辑错误

# 2. 检查健康状态
curl http://localhost:5001/api/health
# 应该返回: {"status": "healthy", ...}

# 3. 检查日志
tail -20 logs/sweetseek.log
# 应该看到最新的启动日志
```

### 从本地验证
```bash
# 在本地电脑运行
./test_external_access.sh

# 或手动测试
curl http://8.137.32.247:5001/api/health
```

### 浏览器验证
访问: http://8.137.32.247:5001
- 主页应该正常加载
- 可以输入问题测试问答功能

---

## 🔧 故障排查

### 问题1: git pull 失败

**错误**: "error: Your local changes would be overwritten"

**解决**:
```bash
# 备份本地修改
git stash

# 拉取代码
git pull origin RenJiaqi

# 如需恢复本地修改
git stash pop
```

### 问题2: 服务无法启动

**检查**:
```bash
# 查看进程
ps aux | grep python | grep app.py

# 查看端口
netstat -tlnp | grep 5001

# 查看日志
tail -50 logs/sweetseek.log
```

**解决**:
```bash
# 停止旧进程
pkill -f "python.*app.py"

# 重新启动
./restart-server.sh
```

### 问题3: 健康检查返回404

**原因**: 代码可能没有更新成功

**解决**:
```bash
# 检查当前提交
git log --oneline -1

# 如果不是最新的，强制更新
git fetch origin
git reset --hard origin/RenJiaqi

# 重启服务
./restart-server.sh
```

---

## 📊 更新内容说明

本次更新包含以下改进：

### 新增功能
1. **日志系统**
   - 自动轮转（10MB/文件，保留5个备份）
   - 位置: `logs/sweetseek.log`

2. **错误处理**
   - 统一的API错误处理
   - 自动捕获异常

3. **性能监控**
   - 自动记录API执行时间
   - 超过10秒自动警告

4. **健康检查端点**
   - `GET /api/health`
   - 返回系统各组件状态

5. **前端增强**
   - 自动健康检查（每5分钟）
   - 友好的错误提示

### 修复问题
1. 修复了 `static/main.js` 中重复定义的函数
2. 清理了不必要的文件
3. 优化了代码结构

---

## 📞 需要帮助？

如果遇到问题：
1. 查看日志: `tail -f /www/wwwroot/FCN_SweetSeek/logs/sweetseek.log`
2. 检查进程: `ps aux | grep python`
3. 检查端口: `netstat -tlnp | grep 5001`

---

## ✅ 完成检查清单

更新完成后，确认以下项目：

- [ ] Git提交是最新的（5dd4452）
- [ ] 服务正在运行
- [ ] 健康检查返回 "healthy"
- [ ] 日志文件正常记录
- [ ] 外部可以访问 http://8.137.32.247:5001
- [ ] 问答功能正常工作

---

**创建时间**: 2026-01-26  
**目标提交**: 5dd4452 (修正结构逻辑错误)  
**服务器**: 8.137.32.247:5001
