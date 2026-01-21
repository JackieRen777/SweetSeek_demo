# SweetSeek 部署指南

## 环境要求

- Python 3.10+
- 至少 4GB RAM
- 至少 5GB 磁盘空间

## 本地部署

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd FCN_SweetSeek
```

### 2. 创建虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
chmod +x install.sh
./install.sh
```

或手动安装：

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制 `.env.production` 为 `.env` 并填入实际配置：

```bash
cp .env.production .env
nano .env  # 编辑配置
```

必须配置的项：
- `DEEPSEEK_API_KEY`: DeepSeek API密钥
- `DEEPSEEK_BASE_URL`: API地址
- `DEEPSEEK_MODEL`: 模型名称

### 5. 启动服务

```bash
python app.py
```

服务将在 `http://localhost:5001` 启动（可通过 `.env` 中的 `PORT` 修改）

## 生产环境部署

### 使用 Gunicorn（推荐）

1. 安装 Gunicorn：

```bash
pip install gunicorn
```

2. 启动服务：

```bash
gunicorn -w 4 -b 0.0.0.0:8080 app:app
```

参数说明：
- `-w 4`: 4个工作进程
- `-b 0.0.0.0:8080`: 绑定到所有接口的8080端口
- `app:app`: 模块名:应用名

### 使用 Docker

1. 构建镜像：

```bash
docker build -t sweetseek .
```

2. 运行容器：

```bash
docker run -d -p 8080:8080 \
  -e DEEPSEEK_API_KEY=your_key \
  -e PORT=8080 \
  -e DEBUG=False \
  -v $(pwd)/sweet_related_paper:/app/sweet_related_paper \
  -v $(pwd)/chroma_db:/app/chroma_db \
  sweetseek
```

### 使用 Nginx 反向代理

Nginx 配置示例：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 支持流式响应
        proxy_buffering off;
        proxy_cache off;
    }
}
```

## 云平台部署

### Vercel / Railway / Render

这些平台支持自动部署，只需：

1. 连接 GitHub 仓库
2. 设置环境变量（在平台控制台）
3. 平台会自动检测 `requirements.txt` 并安装依赖

### 阿里云 / 腾讯云

1. 购买云服务器（推荐 2核4G 以上）
2. 安装 Python 3.10+
3. 按照"生产环境部署"步骤操作
4. 配置防火墙开放端口
5. 使用 systemd 或 supervisor 管理进程

## 环境变量说明

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| DEEPSEEK_API_KEY | DeepSeek API密钥 | - | 是 |
| DEEPSEEK_BASE_URL | API地址 | https://api.siliconflow.cn/v1 | 是 |
| DEEPSEEK_MODEL | 模型名称 | deepseek-ai/DeepSeek-R1 | 是 |
| EMBED_MODEL_TYPE | 嵌入模型类型 | huggingface | 否 |
| EMBED_MODEL_NAME | 嵌入模型名称 | BAAI/bge-small-zh-v1.5 | 否 |
| HOST | 服务器地址 | 0.0.0.0 | 否 |
| PORT | 服务器端口 | 5001 | 否 |
| DEBUG | 调试模式 | True | 否 |

## 常见问题

### 1. 依赖安装失败

```bash
pip cache purge
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt --no-cache-dir
```

### 2. 内存不足

- 减少 `max_results` 参数（在 `app.py` 中）
- 使用更小的嵌入模型
- 增加服务器内存

### 3. 模型下载慢

设置 HuggingFace 镜像：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### 4. 端口被占用

修改 `.env` 中的 `PORT` 值

## 性能优化

1. **使用 Redis 缓存**：缓存查询结果
2. **使用 CDN**：加速静态资源
3. **启用 Gzip**：压缩响应
4. **增加工作进程**：根据 CPU 核心数调整
5. **使用负载均衡**：多实例部署

## 监控和日志

建议使用：
- **日志**: Loguru 或 Python logging
- **监控**: Prometheus + Grafana
- **错误追踪**: Sentry

## 安全建议

1. 不要在代码中硬编码 API 密钥
2. 使用 HTTPS（配置 SSL 证书）
3. 限制 API 请求频率
4. 定期更新依赖包
5. 使用防火墙限制访问

## 备份

定期备份以下目录：
- `chroma_db/`: 向量数据库
- `sweet_related_paper/`: 文献数据
- `.env`: 配置文件

## 更新

```bash
git pull
pip install -r requirements.txt --upgrade
python app.py
```
