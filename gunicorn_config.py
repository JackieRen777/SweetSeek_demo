# Gunicorn configuration file
import multiprocessing

bind = "127.0.0.1:5001"
# 双 RAG 系统初始化开销较大且使用进程内状态，固定 1 worker 可避免跨 worker 初始化状态不一致导致的间歇失败。
workers = 1
worker_class = "gevent"  # 使用 gevent 支持异步 (SSE流式输出需要)
# The production RAG indexes are large JSON stores. Their first load can take
# more than five minutes on the current ECS, so allow prewarm to finish.
timeout = 900
keepalive = 5

# 日志
accesslog = "/www/wwwlogs/sweetseek_gunicorn_access.log"
errorlog = "/www/wwwlogs/sweetseek_gunicorn_error.log"
loglevel = "info"

# 进程命名
proc_name = "sweetseek_backend"
