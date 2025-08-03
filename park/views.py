import logging

import pandas as pd
from datetime import datetime, timedelta

import pytz
from dateutil import parser
from django.http import HttpResponse
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.response import Response

from park.models import (
    Park,
    Driver,
    Order,
    Transaction, Account, DriverWorkRule,
)
from park.utils import (
    get_profiles_list,
    post_orders_list,
    post_park_transactions_list, get_driver_work_rules,
)

logger = logging.getLogger(__name__)


def load_work_rules(one_park_id=None):
    """Загрузить список условий работы"""
    batch_size = 100
    work_rules_to_create = []

    qs = Park.objects.filter(is_active=True)
    # нужна выгрузка по конкретному парку
    if one_park_id:
        qs = qs.filter(park_id=one_park_id)

    for park in qs:
        client_id = park.client_id
        api_key = park.api_key
        park_id = park.park_id

        data = get_driver_work_rules(park_id, api_key, client_id)

        if data:
            for rule in data['rules']:
                work_rules_to_create.append(
                    DriverWorkRule(
                        park=park,
                        work_rule_id=rule['id'],
                        is_enabled=rule['is_enabled'],
                        name=rule['name']
                    )
                )

            # Выполняем bulk_create после обработки всех правил для парка
            if work_rules_to_create:
                DriverWorkRule.objects.bulk_create(
                    work_rules_to_create,
                    batch_size=batch_size,
                    update_conflicts=True,
                    unique_fields=['park', 'work_rule_id'],
                    update_fields=['is_enabled', 'name']
                )
                work_rules_to_create = []  # Очищаем список для следующего парка

    return HttpResponse("Успешно обновлен список условий работы", content_type="application/json; charset=utf-8")


def load_yandex_driver_profiles():
    """Загрузить список водителей Яндекс такси"""
    batch_size = 100
    seen_drivers = set()

    qs = Park.objects.filter(is_active=True).prefetch_related('driver_park')

    for park in qs:
        client_id = park.client_id
        api_key = park.api_key
        park_id = park.park_id

        # ставим всем водителям статус уволен fired
        data = get_profiles_list(park_id, api_key, client_id)

        drivers_to_create = []
        accounts_to_create = []

        if data:
            for driver_data in data['driver_profiles']:
                driver_profile = driver_data['driver_profile']

                # извлекаем дату регистрации
                created_date_str = driver_profile['created_date']
                created_datetime = parser.parse(created_date_str)
                created_date = created_datetime.date()

                work_rule = driver_profile.get('work_rule_id', '')

                account_data = driver_data['accounts'][0]
                account = Account(
                    account_id=account_data['id'],
                    balance=account_data['balance'],
                    balance_limit=account_data.get('balance_limit', '0'),
                    currency=account_data['currency'],
                    account_type=account_data['type']
                )

                accounts_to_create.append(account)

                driver = Driver(
                    park=park,
                    driver_id=driver_profile['id'],
                    last_name=driver_profile['last_name'],
                    first_name=driver_profile.get('first_name', ''),
                    middle_name=driver_profile.get('middle_name', ''),
                    work_status=driver_profile['work_status'],
                    work_rule=DriverWorkRule.objects.filter(
                        park=park,
                        work_rule_id=work_rule
                    ).first() if work_rule else None,
                    account=account,
                    created_date=created_date
                )
                license = driver_data.get('driver_license', None)

                # Добавляем поля водительского удостоверения только если license не None
                if license is not None:
                    driver.driver_license_number = license.get('normalized_number', '')
                    driver.driver_license_country = license.get('country', '')
                    driver.issue_date = license.get('issue_date', None)
                    driver.driver_license_expiration_date = license.get('expiration_date', None)
                else:
                    # Явно устанавливаем None или пустые значения, если license отсутствует
                    driver.driver_license_number = ''
                    driver.driver_license_country = ''
                    driver.issue_date = None
                    driver.driver_license_expiration_date = None

                drivers_to_create.append(driver)

            # Обрабатываем только уникальные водители
            seen_account_ids = set()
            filtered_accounts = []
            for account in accounts_to_create:
                if account.account_id not in seen_account_ids:
                    filtered_accounts.append(account)
                    seen_account_ids.add(account.account_id)

            seen_driver_keys = set()
            filtered_drivers = []
            for driver in drivers_to_create:
                key = (driver.park.id, driver.driver_id)
                if key not in seen_driver_keys:
                    filtered_drivers.append(driver)
                    seen_driver_keys.add(key)

            try:
                # Сначала создаем аккаунты
                Account.objects.bulk_create(
                    filtered_accounts,
                    batch_size=batch_size,
                    update_conflicts=True,
                    unique_fields=['account_id'],
                    update_fields=['balance', 'balance_limit']
                )

                # Затем создаем водителей
                Driver.objects.bulk_create(
                    filtered_drivers,
                    batch_size=batch_size,
                    update_conflicts=True,
                    unique_fields=['park', 'driver_id'],
                    update_fields=[
                        'work_status', 'created_date', 'account', 'work_rule'
                    ]
                )
            except Exception as e:
                logger.error(f"{park} Ошибка в обновлении списка водителей: %s", e)

    return Response({'massage': 'Успешно обновлен список водителей'}, status=status.HTTP_200_OK)


def load_order(ended_at_from=None, ended_at_to=None):
    """Загрузка заказов"""
    batch_size = 200  # Задайте желаемый размер пакета

    qs = Park.objects.filter(is_active=True)

    for park in qs:
        client_id = park.client_id
        api_key = park.api_key
        park_id = park.park_id
        time_zone = park.time_zone

        if not ended_at_from or not ended_at_to:
            # Получаем текущее время как объект datetime
            now = datetime.now(pytz.timezone(time_zone))

            # Устанавливаем ended_at_from как "сейчас минус 2 часа"
            ended_at_from = now - timedelta(hours=2)

            # Устанавливаем ended_at_to как "сейчас"
            ended_at_to = now
        else:
            # Если даты заданы, парсим их и добавляем временную зону
            if isinstance(ended_at_from, str):
                ended_at_from = parse_datetime(ended_at_from).replace(tzinfo=pytz.timezone(time_zone))
            if isinstance(ended_at_to, str):
                ended_at_to = parse_datetime(ended_at_to).replace(tzinfo=pytz.timezone(time_zone))

        data = post_orders_list(
            park_id,
            api_key,
            client_id,
            ended_at_from,
            ended_at_to,
            time_zone
        )

        if not data:
            return

        order_entries = data.get('orders', [])

        # Получаем все уникальные driver_id
        driver_ids = list({order['driver_profile']['id'] for order in order_entries})

        # Разбиваем на части по 200
        drivers_batch_size = 200
        drivers_map = {}

        for i in range(0, len(driver_ids), drivers_batch_size):
            batch = driver_ids[i:i + drivers_batch_size]
            drivers_map.update(
                {d.driver_id: d for d in Driver.objects.filter(driver_id__in=batch)}
            )

        orders_to_create = []

        for order_data in order_entries:
            driver = drivers_map.get(order_data['driver_profile']['id'])
            if not driver:
                continue

            orders_to_create.append(Order(
                park=park,
                driver=driver,
                order_id=order_data['id'],
                order_category=order_data['category'],
                ended_at=order_data['ended_at'],
                price=order_data['price'],
            ))

        if orders_to_create:
            try:
                Order.objects.bulk_create(
                    orders_to_create,
                    batch_size=batch_size,
                    ignore_conflicts=True,
                )
            except Exception as e:
                logger.error("Ошибка в добавлении заказов: %s", e)

    return Response({'massage': 'заказы загружены'}, status=status.HTTP_200_OK)


def load_park_data_from_file():
    """Загрузить id парков из эксель"""
    # Укажите путь к вашему Excel файлу
    file_path = 'park_list.xlsx'

    # Чтение Excel файла
    df = pd.read_excel(file_path)

    # Проход по всем строкам и вывод значений
    for index, row in df.iterrows():
        park = row['park_id']
        key = row['api_key']
        client = row['client_id']
        Park.objects.get_or_create(
            park_id=park,
            defaults={
                'api_key': key,
                'client_id': client
            }
        )
        print(f"Park: {park}, Key: {key}, Client: {client}")


def load_transactions_regular_charges(ended_at_from=None, ended_at_to=None):
    """Загрузка транзакций для определения корректности периодических списаний"""
    category_ids = 'partner_service_recurring_payment'
    batch_size = 200  # Задайте желаемый размер пакета

    qs = Park.objects.filter(is_active=True)

    transactions_to_create = []

    for park in qs:
        client_id = park.client_id
        api_key = park.api_key
        park_id = park.park_id
        time_zone = park.time_zone
        tz_info = pytz.timezone(time_zone) if time_zone else pytz.UTC

        # Обработка временных диапазонов
        if not ended_at_from or not ended_at_to:
            now = datetime.now(tz_info)
            ended_at_from = now - timedelta(days=1)
            ended_at_to = now
        else:
            # Если даты — строки, парсим их
            if isinstance(ended_at_from, str):
                ended_at_from = parse_datetime(ended_at_from)
            if isinstance(ended_at_to, str):
                ended_at_to = parse_datetime(ended_at_to)

            # Приводим к нужному часовому поясу
            ended_at_from = ended_at_from.astimezone(tz_info)
            ended_at_to = ended_at_to.astimezone(tz_info)

        data = post_park_transactions_list(
            park_id,
            api_key,
            client_id,
            category_ids,
            ended_at_from,
            ended_at_to,
            time_zone
        )

        if not data:
            return

        transactions_entries = data.get('transactions', [])

        if not transactions_entries:
            continue

        # Получаем все уникальные driver_id
        driver_ids = list({transactions['driver_profile_id'] for transactions in transactions_entries})

        # Загружаем всех водителей одним запросом
        drivers_map = {d.driver_id: d for d in Driver.objects.filter(driver_id__in=driver_ids)}

        for transaction_data in transactions_entries:
            driver = drivers_map.get(transaction_data['driver_profile_id'])
            if not driver:
                continue

            transactions_to_create.append(Transaction(
                park=park,
                driver=driver,
                transaction_id=transaction_data['id'],
                event_at=transaction_data['event_at'],
                category_id=transaction_data['category_id'],
                category_name=transaction_data['category_name'],
                amount=transaction_data['amount'],
                description=transaction_data['description']
            ))

        if transactions_to_create:
            try:
                Transaction.objects.bulk_create(
                    transactions_to_create,
                    batch_size=batch_size,
                    ignore_conflicts=True,
                    unique_fields=['park', 'transaction_id'],
                    update_fields=['amount'],
                )
            except Exception as e:
                logger.error("Ошибка в добавлении транзакций: %s", e)

    return Response({'massage': 'транзакции загружены'}, status=status.HTTP_200_OK)
