from datetime import datetime, timedelta

from celery import shared_task
from celery.utils.log import get_task_logger

from irules_stats.celery import app
from park.views import (
    load_work_rules,
    load_yandex_driver_profiles,
    load_order,
    load_cars,
    load_transactions,
    process_dates_with_resume
)

logger = get_task_logger(__name__)


@app.task
def load_work_rules_celery():
    load_work_rules()


@app.task
def load_yandex_driver_profiles_celery():
    load_yandex_driver_profiles()


@app.task
def load_order_celery():
    load_order()


@app.task
def load_cars_celery():
    load_cars()


@app.task
def load_transactions_celery():
    load_transactions()


@app.task
def load_old_orders_celery():
    process_dates_with_resume()

