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
    'Загрузка профилей водителей': {
        'task': 'park.tasks.load_yandex_driver_profiles_celery',
        'schedule': crontab(minute='*/45')
    },
    'Загрузка заказов': {
        'task': 'park.tasks.load_order_celery',
        'schedule': crontab(minute='*/30')
    },
    'Загрузка транзакций периодических списаний': {
        'task': 'park.tasks.load_transactions_regular_charges_celery',
        'schedule': crontab(hour='*/3', minute='0')
    },
}

# Сортируем словарь по ключам (именам задач)
sorted_beat_schedule = dict(sorted(beat_schedule.items(), key=lambda x: x[0], reverse=True))

# Присваиваем отсортированный словарь в конфигурацию Celery
app.conf.beat_schedule = sorted_beat_schedule

app.conf.timezone = 'Europe/Moscow'
