# SweetSeek 开发工作流程

## 🎯 核心原则
**永远先在本地测试，确认无误后再部署到服务器**

---

## 📝 标准开发流程

### 第一步：本地开发和测试

1. **启动本地服务器**
   ```bash
   # 在项目根目录
   python3 app.py
   ```

2. **访问本地网站**
   ```
   http://localhost:5001
   ```

3. **测试功能**
   - 测试新功能是否正常工作
   - 检查是否有错误
   - 验证前端显示是否正确
   - 查看控制台日志

4. **查看日志（如有问题）**
   ```bash
   tail -f logs/sweetseek.log
   ```

---

### 第二步：确认本地测试通过

✅ 检查清单：
- [ ] 功能正常工作
- [ ] 没有报错
- [ ] 前端显示正确
- [ ] References显示正常（如果涉及）
- [ ] 日志没有ERROR

---

### 第三步：提交代码到Git

```bash
# 查看修改的文件
git status

# 添加修改的文件
git add <文件名>
# 或添加所有修改
git add .

# 提交（使用规定的commit message）
git commit -m "修正结构逻辑错误"

# 推送到GitHub
git push origin RenJiaqi
```

---

### 第四步：部署到服务器

#### 方法一：手动部署（推荐，便于观察）

```bash
# 1. SSH连接服务器
ssh root@8.137.32.247

# 2. 进入项目目录
cd /www/wwwroot/FCN_SweetSeek

# 3. 拉取最新代码
git pull origin RenJiaqi

# 4. 重启应用
pkill -f "python3 app.py"
sleep 3
nohup python3 app.py > logs/app.log 2>&1 &

# 5. 验证服务运行
ps aux | grep "python3 app.py" | grep -v grep

# 6. 查看日志（确认启动成功）
tail -20 logs/sweetseek.log
```

#### 方法二：使用部署脚本

```bash
# 在服务器上运行
cd /www/wwwroot/FCN_SweetSeek
bash deploy.sh
```

---

### 第五步：线上验证

1. **访问线上网站**
   ```
   http://sweetseek.top
   ```

2. **强制刷新浏览器**
   - Mac: `Cmd + Shift + R`
   - Windows: `Ctrl + Shift + R`

3. **测试功能**
   - 重复本地测试的所有步骤
   - 确认功能正常

4. **如有问题，查看服务器日志**
   ```bash
   ssh root@8.137.32.247
   cd /www/wwwroot/FCN_SweetSeek
   tail -f logs/sweetseek.log
   ```

---

## 🚨 紧急回滚流程

如果线上出现严重问题：

```bash
# 1. SSH到服务器
ssh root@8.137.32.247
cd /www/wwwroot/FCN_SweetSeek

# 2. 回滚到上一个版本
git log --oneline -5  # 查看最近5次提交
git reset --hard <上一个正常的commit-id>

# 3. 重启应用
pkill -f "python3 app.py"
sleep 3
nohup python3 app.py > logs/app.log 2>&1 &

# 4. 验证
curl http://localhost:5001/api/health
```

---

## 📊 本地测试 vs 服务器环境

### 本地环境
- **地址**: http://localhost:5001
- **数据库**: 本地 `./chroma_db/`
- **日志**: 本地 `./logs/sweetseek.log`
- **优点**: 快速测试，不影响线上用户
- **缺点**: 环境可能与服务器略有差异

### 服务器环境
- **地址**: http://sweetseek.top
- **数据库**: `/www/wwwroot/FCN_SweetSeek/chroma_db/`
- **日志**: `/www/wwwroot/FCN_SweetSeek/logs/sweetseek.log`
- **优点**: 真实环境
- **缺点**: 影响线上用户，需谨慎

---

## 🔧 常用调试命令

### 本地调试

```bash
# 启动应用（前台运行，可看到实时输出）
python3 app.py

# 查看日志
tail -f logs/sweetseek.log

# 检查端口占用
lsof -i :5001

# 停止应用
pkill -f "python3 app.py"
```

### 服务器调试

```bash
# SSH连接
ssh root@8.137.32.247

# 查看应用状态
ps aux | grep "python3 app.py" | grep -v grep

# 查看实时日志
tail -f /www/wwwroot/FCN_SweetSeek/logs/sweetseek.log

# 健康检查
curl http://localhost:5001/api/health

# 重启应用
cd /www/wwwroot/FCN_SweetSeek
pkill -f "python3 app.py"
sleep 3
nohup python3 app.py > logs/app.log 2>&1 &
```

---

## 📝 开发建议

### ✅ 好的实践

1. **小步快跑**：每次只改一个功能，测试通过后再改下一个
2. **频繁提交**：功能测试通过就提交，便于回滚
3. **详细日志**：在关键位置添加日志，便于调试
4. **本地优先**：永远先在本地测试
5. **备份数据**：修改数据库前先备份

### ❌ 避免的做法

1. ❌ 直接在服务器上修改代码
2. ❌ 不测试就推送到服务器
3. ❌ 一次修改太多功能
4. ❌ 不查看日志就认为功能正常
5. ❌ 忘记重启服务器应用

---

## 🎯 快速参考

### 本地测试流程（2分钟）
```bash
python3 app.py
# 访问 http://localhost:5001
# 测试功能
# Ctrl+C 停止
```

### 部署到服务器流程（3分钟）
```bash
git add . && git commit -m "修正结构逻辑错误" && git push origin RenJiaqi
ssh root@8.137.32.247
cd /www/wwwroot/FCN_SweetSeek && git pull origin RenJiaqi
pkill -f "python3 app.py" && sleep 3 && nohup python3 app.py > logs/app.log 2>&1 &
# 访问 http://sweetseek.top 测试
```

---

## 📞 遇到问题时

1. **查看本地日志**: `tail -f logs/sweetseek.log`
2. **查看服务器日志**: `ssh root@8.137.32.247 "tail -f /www/wwwroot/FCN_SweetSeek/logs/sweetseek.log"`
3. **检查服务状态**: `curl http://localhost:5001/api/health`
4. **回滚代码**: `git reset --hard <commit-id>`

---

## 🎓 总结

记住这个黄金法则：
> **本地测试 ✅ → Git提交 → 服务器部署 → 线上验证**

永远不要跳过本地测试这一步！
