# 修复文献显示问题

## 问题描述
文献引用显示为 "Unknown N/A"，无法显示正确的文献标题、期刊等信息。

## 根本原因
向量数据库（chroma_db）是在本地Mac上构建的，存储的是绝对路径：
```
/Users/jackieren/Desktop/FCN_SweetSeek/sweet_related_paper/papers/xxx.pdf
```

而元数据存储（metadata.json）使用的是相对路径：
```
sweet_related_paper/papers/xxx.pdf
```

当系统尝试匹配路径获取元数据时，因为路径格式不同而失败，导致所有文献显示为 "Unknown N/A"。

## 解决方案
在服务器上重建向量索引，使用服务器的正确路径。

### 方法一：使用自动脚本（推荐）

1. 推送修复脚本到服务器：
```bash
./push.sh
```

2. SSH登录服务器：
```bash
ssh root@8.137.32.247
```

3. 进入项目目录：
```bash
cd /www/wwwroot/FCN_SweetSeek
```

4. 运行重建脚本：
```bash
chmod +x rebuild-index.sh
./rebuild-index.sh
```

5. 等待几分钟后测试

### 方法二：手动操作

SSH登录服务器后执行：
```bash
cd /www/wwwroot/FCN_SweetSeek

# 停止服务
pkill -f "python.*app.py"

# 删除旧索引
rm -rf chroma_db

# 启动服务（自动重建索引）
source venv/bin/activate
nohup python app.py > logs/app.log 2>&1 &

# 监控进度
tail -f logs/app.log
```

## 验证修复
1. 等待索引重建完成（日志中会显示"索引构建完成"）
2. 访问 http://8.137.32.247:5001
3. 提问任意问题
4. 检查右侧 References 面板是否显示正确的文献信息

## 后续清理
修复成功后，可以删除调试代码（app.py 中的 print 语句）：
- 第313行
- 第718-719行
- 第725-727行

这些调试语句可以在下次更新时移除。
