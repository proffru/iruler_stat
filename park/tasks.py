from datetime import datetime, timedelta

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


@shared_task
def run_load_orders():
    start_date = datetime(2025, 3, 30)
    end_date_limit = datetime(2025, 8, 15)
    delta_days = 1  # каждый раз увеличиваем интервал на 1 день

    current_start = start_date

    while current_start <= end_date_limit:
        current_end = current_start + timedelta(days=delta_days)
        if current_end > end_date_limit:
            current_end = end_date_limit

        print(f"Loading orders from {current_start} to {current_end}")
        logger.info(f'loading orders {current_start}')
        try:
            load_order(current_start.strftime("%Y-%m-%d"), current_end.strftime("%Y-%m-%d"))
        except Exception as e:
            logger.error(f"Error loading orders: {e}")
        # Следующий запуск — начинаем с конца предыдущего диапазона
        current_start = current_end
        delta_days += 1
