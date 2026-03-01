# Gunicorn configuration file
import multiprocessing

bind = "127.0.0.1:5001"
workers = 2  # 根据服务器CPU核心数调整: 2 * cores + 1
worker_class = "gevent"  # 使用 gevent 支持异步 (SSE流式输出需要)
timeout = 300
keepalive = 5

# 日志
accesslog = "/www/wwwlogs/sweetseek_gunicorn_access.log"
errorlog = "/www/wwwlogs/sweetseek_gunicorn_error.log"
loglevel = "info"

# 进程命名
proc_name = "sweetseek_backend"
