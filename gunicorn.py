from multiprocessing import cpu_count
from os import getenv

# Bind to 0.0.0.0 to allow external access
bind = f'0.0.0.0:{getenv("PORT", "8000")}'

# Timeout for requests (in seconds)
timeout = 120

# Maximum number of requests before worker restart
max_requests = 2000
max_requests_jitter = 200

# Number of workers = (2 * CPU) + 1 (recommended)
workers = int(getenv('WORKERS', (2 * cpu_count()) + 1))

# Worker class for async support
worker_class = 'sync'

# Keep-alive timeout
keepalive = 65

# Enable auto-reload during development
reload = True

# Application title
name = 'visa_doctors_web'

# Access log format
access_log_format = '%({x-forwarded-for}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Do not daemonize in Docker
daemon = False
