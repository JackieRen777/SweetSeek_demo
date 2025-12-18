# 🚀 如何启动 SweetSeek 服务器

## 问题
每次刷新网页显示"连接不到服务器"

## 原因
Flask 服务器没有自动启动，需要手动运行

---

## ✅ 解决方案

### 方法1：使用启动脚本（推荐）

```bash
# 1. 打开终端，进入项目目录
cd /Users/jackieren/Desktop/FCN_SweetSeek

# 2. 运行启动脚本
./start.sh
```

**等待提示**：
```
================================
🚀 Starting SweetSeek...
================================

服务器启动成功
访问地址: http://localhost:5001
```

### 方法2：后台运行

```bash
# 1. 启动后台服务
./start_server.sh

# 2. 检查状态
./check_server.sh

# 3. 停止服务
./stop_server.sh
```

### 方法3：手动启动

```bash
# 1. 激活虚拟环境
source .venv/bin/activate

# 2. 启动服务器
python3 app.py
```

---

## 📝 每日使用流程

### 第一次使用（每天）

1. **打开终端**
2. **进入项目目录**：
   ```bash
   cd /Users/jackieren/Desktop/FCN_SweetSeek
   ```
3. **启动服务器**：
   ```bash
   ./start.sh
   ```
4. **等待启动完成**（约10-30秒）
5. **打开浏览器**：访问 http://localhost:5001

### 使用完毕

- **方式A**：直接关闭终端（服务器会自动停止）
- **方式B**：按 `Ctrl + C` 停止服务器

---

## 🔍 故障排除

### 问题1：端口被占用

```bash
# 查找占用端口的进程
lsof -i :5001

# 停止进程
kill -9 <PID>
```

### 问题2：虚拟环境未激活

```bash
# 检查是否在虚拟环境中
which python3
# 应该显示：/Users/jackieren/Desktop/FCN_SweetSeek/.venv/bin/python3

# 如果不是，激活虚拟环境
source .venv/bin/activate
```

### 问题3：依赖缺失

```bash
# 重新安装依赖
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 💡 提示

### 快速启动（推荐）

创建一个桌面快捷方式：

1. 打开"自动操作"（Automator）
2. 创建"应用程序"
3. 添加"运行 Shell 脚本"
4. 输入：
   ```bash
   cd /Users/jackieren/Desktop/FCN_SweetSeek
   ./start.sh
   ```
5. 保存为"启动SweetSeek.app"
6. 双击即可启动

### 开机自动启动（高级）

如果你希望开机自动启动服务器，可以创建 LaunchAgent：

1. 创建配置文件：
   ```bash
   nano ~/Library/LaunchAgents/com.sweetseek.server.plist
   ```

2. 粘贴内容：
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
   <plist version="1.0">
   <dict>
       <key>Label</key>
       <string>com.sweetseek.server</string>
       <key>ProgramArguments</key>
       <array>
           <string>/Users/jackieren/Desktop/FCN_SweetSeek/start_server.sh</string>
       </array>
       <key>RunAtLoad</key>
       <true/>
       <key>KeepAlive</key>
       <false/>
   </dict>
   </plist>
   ```

3. 加载配置：
   ```bash
   launchctl load ~/Library/LaunchAgents/com.sweetseek.server.plist
   ```

---

## 📊 检查服务器状态

```bash
# 方式1：使用检查脚本
./check_server.sh

# 方式2：手动检查
curl http://localhost:5001/api/stats

# 方式3：查看进程
ps aux | grep "python.*app.py"
```

---

## 🎯 总结

**最简单的方法**：
1. 打开终端
2. `cd /Users/jackieren/Desktop/FCN_SweetSeek`
3. `./start.sh`
4. 等待启动完成
5. 访问 http://localhost:5001

**记住**：每次重启电脑或关闭终端后，都需要重新启动服务器！
