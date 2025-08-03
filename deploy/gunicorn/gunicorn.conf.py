import multiprocessing

bind = '127.0.0.1:8000'
workers = multiprocessing.cpu_count() * 2 + 1
user = 'root'
group = 'root'
pidfile = '/run/gunicorn.pid'
accesslog = '/home/logs/gunicorn/access.log'
errorlog = '/home/logs/gunicorn/error.log'
loglevel = 'info'
timeout = 600