# запуск сервера celery
    celery -A report worker --loglevel=INFO
    celery -A report beat --loglevel=INFO

    ## один рабочий на все очереди
    celery -A report worker -l info -n kozlove_worker1 

# запуск celery в windows
    celery -A report worker -l info -P gevent
    celery -A report beat -l info
    celery -A report flower
    celery -A report flower --basic-auth=user:pwd

    watchmedo auto-restart -d dialog/ -p '*.py' -- celery -A fastpay worker --loglevel=info -P gevent


# settings
## redis
    REDIS_HOST = '0.0.0.0'
    REDIS_PORT = '6379'

## celery
    CELERY_BROKER_URL = 'redis://' + REDIS_HOST + ':' + REDIS_PORT + '/0'
    CELERY_BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 3600}
    CELERY_RESULT_BACKEND = 'redis://' + REDIS_HOST + ':' + REDIS_PORT + '/0'
    CELERY_ACCEPT_CONTENT = ['application/json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'

# celery.py
    import os
    from celery import Celery
    from celery.schedules import crontab

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fastpay.settings')

    app = Celery('fastpay')
    app.config_from_object('django.conf:settings', namespace='CELERY')
    app.autodiscover_tasks()

    # app.conf.beat_schedule = {
    #     'ak_name': {
    #         'task': 'main.tasks.<task_name>',
    #         'beat_schedule': crontab(minute='*/10')
    #     }
    # }

# главный __init__.py
    from .celery import app as celery_app

    __all__ = ('celery_app',)

# управление процессами
## активные процессы (в терминале)
    ps aux|grep 'celery worker'

## завершить процесс
    sudo kill -9 process_id

## завершить все процессы
    pkill -f "celery worker"

# Linux
## Узнать диск
    lsdk

## Сделать снэпшот
Подключиться по ssh к новому серверу, куда сохранится img
    ssh -p 22 root@193.124.117.38 -i ~/.ssh/rating "dd if=/dev/sda " | dd of=vps.img status=progress

## Развернуть снэпшот на новом сервере
Заходим на сервер на котором сохранен снэпшот и по ssh ставим на нужный vps
    dd if=vps.img | ssh root@ip_of_new_vps "dd of=/dev/sda"

# Очистка очереди Celery (общие методы)

    celery -A your_project_name purge -f