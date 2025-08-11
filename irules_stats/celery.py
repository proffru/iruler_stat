import os
from celery import Celery
from celery.schedules import crontab
from celery.utils.log import get_task_logger

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'irules_stats.settings')

app = Celery('irules')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.broker_connection_retry_on_startup = True
app.autodiscover_tasks()


# Настройки логирования
logger = get_task_logger(__name__)

app.conf.broker_transport_options = {
    'visibility_timeout': 1800,
}


# Исходный словарь
beat_schedule = {
    'Загрузка условий работы': {
        'task': 'park.tasks.load_work_rules_celery',
        'schedule': crontab(hour='*/1', minute=0)
    },
    'Загрузка профилей водителей': {
        'task': 'park.tasks.load_yandex_driver_profiles_celery',
        'schedule': crontab(minute='*/30')
    },
    'Загрузка автомобилей': {
        'task': 'park.tasks.load_cars_celery',
        'schedule': crontab(minute='*/45')
    },
    'Загрузка заказов': {
        'task': 'park.tasks.load_order_celery',
        'schedule': crontab(minute='*/30')
    },
    'Загрузка транзакций': {
        'task': 'park.tasks.load_transactions_celery',
        'schedule': crontab(minute='*/30')
    },
    'run_load_orders_once': {
        'task': 'park.tasks.run_load_orders',
        'schedule': crontab(minute=0, hour=0),  # например, запускать каждый день
        'one_off': True  # Celery Beat не умеет нативно, но можно отключить в коде
    },
}

app.conf.timezone = 'Europe/Moscow'
