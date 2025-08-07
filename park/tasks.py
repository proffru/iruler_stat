from celery import shared_task
from celery.utils.log import get_task_logger

from park.views import (
    load_work_rules,
    load_yandex_driver_profiles,
    load_order,
    load_cars,
    load_transactions
)

logger = get_task_logger(__name__)


@shared_task()
def load_work_rules_celery():
    load_work_rules()


@shared_task()
def load_yandex_driver_profiles_celery():
    load_yandex_driver_profiles()


@shared_task()
def load_order_celery():
    load_order()


@shared_task()
def load_cars_celery():
    load_cars()


@shared_task()
def load_transactions_celery():
    load_transactions()
