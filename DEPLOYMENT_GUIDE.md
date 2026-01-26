# 阿里云部署和外部访问配置指南

## 📋 部署步骤

### 1. 登录阿里云控制台

访问: https://ecs.console.aliyun.com

### 2. 配置安全组规则

确保以下端口开放：
- **5001** - SweetSeek应用端口
- **22** - SSH端口（如需远程连接）

#### 操作步骤：
1. 进入ECS实例管理页面
2. 找到你的实例（FCN_SweetSeek）
3. 点击"安全组" → "配置规则"
4. 添加入方向规则：
   - 端口范围: 5001/5001
   - 授权对象: 0.0.0.0/0
   - 协议类型: TCP
   - 优先级: 1

### 3. 通过VNC连接服务器

1. 在阿里云控制台找到实例
2. 点击"远程连接" → "VNC"
3. 输入VNC密码

### 4. 部署代码

```bash
# 进入项目目录
cd /www/wwwroot/FCN_SweetSeek

# 拉取最新代码
git pull origin RenJiaqi

# 检查环境
source .venv/bin/activate
cat .env | grep DEEPSEEK

# 重启服务
./restart-server.sh
```

### 5. 验证部署

#### 本地验证（在服务器上）
```bash
curl http://localhost:5001/api/health
```

#### 外部访问验证
```bash
# 从本地电脑测试
curl http://8.137.32.247:5001/api/health
```

浏览器访问:
- http://8.137.32.247:5001

## 🔍 测试清单

### 网络连通性测试
- [ ] 能否ping通服务器IP: `ping 8.137.32.247`
- [ ] 端口是否开放: `telnet 8.137.32.247 5001`
- [ ] 健康检查端点: `curl http://8.137.32.247:5001/api/health`

### 服务响应速度测试
```bash
# 测试响应时间
time curl http://8.137.32.247:5001/api/health

# 测试统计信息
time curl http://8.137.32.247:5001/api/stats
```

### 功能完整性测试
- [ ] 主页加载: http://8.137.32.247:5001
- [ ] 健康检查: http://8.137.32.247:5001/api/health
- [ ] 统计信息: http://8.137.32.247:5001/api/stats
- [ ] 问答功能: 在Web界面输入问题测试
- [ ] 文献搜索: http://8.137.32.247:5001/search.html
- [ ] 日志记录: 检查 `/www/wwwroot/FCN_SweetSeek/logs/sweetseek.log`

## 🔧 故障排查

### 问题1: 无法外部访问

**检查安全组**:
```bash
# 在阿里云控制台检查安全组规则
# 确保5001端口已开放
```

**检查防火墙**:
```bash
# 在服务器上
sudo firewall-cmd --list-ports
sudo firewall-cmd --add-port=5001/tcp --permanent
sudo firewall-cmd --reload
```

**检查服务状态**:
```bash
# 检查进程
ps aux | grep python | grep app.py

# 检查端口
netstat -tlnp | grep 5001
```

### 问题2: 服务未启动

```bash
cd /www/wwwroot/FCN_SweetSeek
./restart-server.sh

# 查看日志
tail -f logs/sweetseek.log
```

### 问题3: Git拉取失败

```bash
# 检查Git状态
git status

# 如有冲突，先备份本地修改
git stash

# 拉取代码
git pull origin RenJiaqi

# 恢复本地修改（如需要）
git stash pop
```

## 📊 性能监控

### 查看系统资源
```bash
# CPU和内存
top

# 磁盘使用
df -h

# 网络连接
netstat -an | grep 5001
```

### 查看应用日志
```bash
# 实时日志
tail -f /www/wwwroot/FCN_SweetSeek/logs/sweetseek.log

# 错误日志
grep ERROR /www/wwwroot/FCN_SweetSeek/logs/sweetseek.log

# 性能日志
grep "执行时间" /www/wwwroot/FCN_SweetSeek/logs/sweetseek.log
```

## ✅ 验收标准

### 必须通过
- [ ] 外部可以访问 http://8.137.32.247:5001
- [ ] 健康检查返回 "status": "healthy"
- [ ] 问答功能正常工作
- [ ] 日志正常记录

### 性能要求
- [ ] 健康检查响应时间 < 1秒
- [ ] 统计信息响应时间 < 2秒
- [ ] 问答功能响应时间 < 3分钟

### 稳定性要求
- [ ] 连续运行24小时无崩溃
- [ ] 无ERROR级别日志（除正常的API错误）

## 📞 支持信息

- 服务器IP: 8.137.32.247
- 应用端口: 5001
- 项目路径: /www/wwwroot/FCN_SweetSeek
- 日志路径: /www/wwwroot/FCN_SweetSeek/logs/sweetseek.log

---

**创建时间**: 2026-01-26
**最后更新**: 2026-01-26
