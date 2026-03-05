# SweetSeek 部署与持久化指南

本指南旨在解决服务器部署中常见的“每次都要重新构建索引”以及“流式响应失效”的问题。

## 1. 核心问题：数据持久化

SweetSeek 使用 ChromaDB 存储向量索引。如果每次部署都覆盖了代码目录，或者使用了临时容器而没有挂载数据卷，索引数据就会丢失，导致系统启动时需要重新扫描所有 PDF 构建索引。

### 解决方案：使用独立的数据目录

我们建议在服务器上创建一个独立于代码的目录来存储 ChromaDB 数据。

#### 步骤 1：创建数据目录
在服务器上执行：
```bash
# 创建数据存储目录
sudo mkdir -p /data/sweetseek_db
# 确保运行服务的用户有权限写入
sudo chown -R $USER:$USER /data/sweetseek_db
```

#### 步骤 2：配置环境变量
在项目根目录的 `.env` 文件中添加（或修改）：

```bash
# 指定 ChromaDB 存储路径（绝对路径）
CHROMA_DB_DIR=/data/sweetseek_db

# 推荐使用的 Embedding 模型（CPU 环境下平衡速度与效果）
EMBED_MODEL_NAME=BAAI/bge-small-zh-v1.5
# 使用 ModelScope 加速国内下载
EMBED_MODEL_SOURCE=modelscope
```

**注意**：一旦配置了持久化路径，首次启动时会构建索引。之后只要不删除 `/data/sweetseek_db`，重启服务或更新代码后，系统会直接加载现有索引，**无需重建**。

---

## 2. Docker 部署（推荐）

如果您使用 Docker，请务必挂载数据卷。

`docker-compose.yml` 示例：

```yaml
version: '3.8'

services:
  sweetseek-backend:
    build: .
    ports:
      - "5001:5001"
    environment:
      - CHROMA_DB_DIR=/app/chroma_db  # 容器内路径
      - EMBED_MODEL_SOURCE=modelscope
    volumes:
      # 【关键】将宿主机的持久化目录挂载到容器内
      - /data/sweetseek_db:/app/chroma_db
      # 挂载 PDF 数据目录（可选）
      - ./sweet_related_paper:/app/sweet_related_paper
    restart: always
```

---

## 3. 解决“不能流式问答” (Nginx 配置)

如果通过 Nginx 反向代理访问服务，Nginx 默认会缓冲响应，导致流式输出（SSE）失效，变成一次性返回。

### 修改 Nginx 配置

在 Nginx 配置文件（通常位于 `/etc/nginx/sites-available/default` 或 `/etc/nginx/nginx.conf`）的 `location` 块中添加 `proxy_buffering off;`。

示例配置：

```nginx
server {
    listen 80;
    server_name sweetseek.top;

    location /api/ {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # 【关键】关闭缓冲，启用流式响应
        proxy_buffering off;
        
        # 增加超时时间，防止长文本生成中断
        proxy_read_timeout 300s;
    }

    # 其他配置...
}
```

修改后重启 Nginx：
```bash
sudo nginx -t  # 检查配置语法
sudo systemctl reload nginx
```

---

## 4. 关于 Embedding 模型选择

### 当前配置
*   **模型**: `BAAI/bge-small-zh-v1.5`
*   **维度**: 512
*   **优势**: 速度快（CPU推理延迟低），中文语义理解能力强，足以支撑 3000+ 篇文献的检索。
*   **适用场景**: 无 GPU 的服务器，追求响应速度。

### 升级方案（如果未来需要）
如果您有 GPU 服务器，或者希望追求极致效果，可以切换到 `BAAI/bge-m3`：
1.  修改 `.env`: `EMBED_MODEL_NAME=BAAI/bge-m3`
2.  **重要**: 由于维度从 512 变为 1024，必须删除旧的 `/data/sweetseek_db` 目录，让系统重新构建索引。

---

## 5. 故障排查

如果遇到 `Collection expecting embedding with dimension of 512, got 1024` 错误：
*   **原因**: 当前代码配置的模型维度与数据库中已有的索引维度不一致。
*   **解决**: 
    1.  确认 `.env` 中的模型配置是否正确。
    2.  如果确认要更换模型，请手动删除持久化目录（如 `/data/sweetseek_db`），然后重启服务重建索引。
