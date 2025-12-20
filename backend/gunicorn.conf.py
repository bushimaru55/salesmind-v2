"""
Gunicorn configuration file for SalesMind Django application
"""
import multiprocessing
import os

# サーバーソケット
# bind は entrypoint.sh で --bind オプションとして指定される
backlog = 2048

# ワーカープロセス
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# ロギング
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# プロセス名
proc_name = "salesmind"

# サーバーメカニクス
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL（必要に応じて設定）
# keyfile = None
# certfile = None

# パフォーマンス
preload_app = True
max_requests = 1000
max_requests_jitter = 100

