import logging
import time

import pandas as pd
from datetime import datetime, timedelta

import pytz
from dateutil import parser
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.response import Response

from park.models import (
    Park,
    Driver,
    Order,
    Transaction,
    Account,
    DriverWorkRule,
    Car,
    DateProcessing,
)
from park.utils import (
    get_profiles_list,
    post_orders_list,
    post_park_transactions_list, get_driver_work_rules, post_car_list, post_transaction_categories_list,
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
                license = driver_profile.get('driver_license', None)

                # Добавляем поля водительского удостоверения только если license не None
                if license is not None:
                    driver.driver_license_number = license.get('normalized_number', '')
                    driver.driver_license_country = license.get('country', '')
                    driver.driver_license_issue_date = license.get('issue_date', None)
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
                        'work_status', 'created_date', 'account', 'work_rule',
                        'driver_license_number', 'driver_license_country',
                        'driver_license_issue_date', 'driver_license_expiration_date'
                    ]
                )
            except Exception as e:
                logger.error(f"{park} Ошибка в обновлении списка водителей: %s", e)

    return Response({'massage': 'Успешно обновлен список водителей'}, status=status.HTTP_200_OK)


def load_order(ended_at_from=None, ended_at_to=None):
    """Загрузка заказов"""
    batch_size = 100  # Задайте желаемый размер пакета

    qs = Park.objects.filter(is_active=True)

    for park in qs:
        client_id = park.client_id
        api_key = park.api_key
        park_id = park.park_id

        if not ended_at_from or not ended_at_to:
            # Получаем текущее время как объект datetime
            now = datetime.now(pytz.timezone('Europe/Moscow'))

            # Устанавливаем ended_at_from как "сейчас минус 2 часа"
            ended_at_from = now - timedelta(hours=2)

            # Устанавливаем ended_at_to как "сейчас"
            ended_at_to = now
        else:
            # Если даты заданы, парсим их и добавляем временную зону
            if isinstance(ended_at_from, str):
                ended_at_from = parse_datetime(ended_at_from).replace(tzinfo=pytz.timezone('Europe/Moscow'))
            if isinstance(ended_at_to, str):
                ended_at_to = parse_datetime(ended_at_to).replace(tzinfo=pytz.timezone('Europe/Moscow'))

        data = post_orders_list(
            park_id,
            api_key,
            client_id,
            ended_at_from,
            ended_at_to,
        )
        if not data or not data['orders']:
            continue

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

        # 1. Собираем все car_id из заказов
        car_ids = []
        for order in data['orders']:
            if isinstance(order, dict) and order.get('car'):
                car_ids.append(order['car']['id'])

        # 2. Получаем существующие автомобили одним запросом
        # Создаем словарь {car_id: car_object} для быстрого поиска
        existing_cars = {car.car_id: car for car in Car.objects.filter(car_id__in=car_ids)}

        orders_to_create = []

        for order_data in order_entries:
            # Проверяем наличие водителя и машины в базе
            driver = drivers_map.get(order_data['driver_profile']['id']) if order_data.get('driver_profile') else None
            car = existing_cars.get(order_data['car']['id']) if order_data.get('car') else None

            # Безопасное получение адреса назначения
            route_points = order_data.get('route_points', [])
            if route_points:  # Если есть точки маршрута
                last_point = route_points[-1]
                address_to = last_point['address']
                address_to_lat = float(last_point['lat'])
                address_to_lon = float(last_point['lon'])
            else:  # Если точек маршрута нет
                address_to = ''
                address_to_lat = 0.0
                address_to_lon = 0.0

            orders_to_create.append(Order(
                park=park,
                driver=driver,
                order_id=order_data['id'],
                short_id=order_data['short_id'],
                category=order_data.get('category', ''),
                created_at=order_data['created_at'],
                status=order_data['status'],
                payment_method=order_data.get('payment_method', ''),
                price=order_data.get('price', 0),
                address_from=order_data['address_from']['address'],
                address_from_lat=order_data['address_from']['lat'],
                address_from_lon=order_data['address_from']['lon'],
                address_to=address_to,
                address_to_lat=address_to_lat,
                address_to_lon=address_to_lon,
                mileage=order_data.get('mileage', 0),
                car=car,
                cancellation_description=order_data.get('cancellation_description', '')
            ))

        if orders_to_create:
            try:
                Order.objects.bulk_create(
                    orders_to_create,
                    batch_size=batch_size,
                    update_conflicts=True,
                    unique_fields=['order_id'],
                    update_fields=['status', 'price', 'short_id', 'category', 'mileage']
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


def load_cars(park=None):
    """Загрузить список автомобилей"""
    batch_size = 100

    qs = Park.objects.filter(is_active=True)
    # нужна выгрузка по конкретному парку
    if park:
        qs = qs.filter(profile__pk=park)

    cars_to_create = []

    for park_data in qs:
        client_id = park_data.client_id
        api_key = park_data.api_key
        park_id = park_data.park_id

        data = post_car_list(park_id, api_key, client_id)
        if data and data['cars']:
            # Словарь для устранения дубликатов car_id
            unique_cars = {}

            for car_data in data['cars']:
                # Преобразуем amenities в строку
                amenities_str = ', '.join(
                    item for sublist in car_data.get('amenities', [])
                    for item in sublist
                ) if car_data.get('amenities') else ''

                # Преобразуем категории в строку
                categories_str = ', '.join(
                    item for sublist in car_data.get('category', [])
                    for item in sublist
                ) if car_data.get('category') else ''

                car = Car(
                    park=park_data,
                    car_id=car_data['id'],
                    status=car_data.get('status'),
                    brand=car_data['brand'],
                    model=car_data['model'],
                    year=car_data['year'],
                    vin=car_data.get('vin', ''),
                    color=car_data.get('color', ''),
                    number=car_data.get('number', ''),
                    callsign=car_data.get('callsign', ''),
                    amenities=amenities_str,
                    category=categories_str,
                    registration_cert=car_data.get('registration_cert', ''),
                )
                # Убираем дубликаты: оставляем последнее значение
                unique_cars[car.car_id] = car

                # cars_to_create.append(car)

            # Добавляем только уникальные машины
            cars_to_create.extend(unique_cars.values())

        Car.objects.bulk_create(
            cars_to_create,
            batch_size=batch_size,
            update_conflicts=True,
            unique_fields=['car_id'],
            update_fields=['status']
        )

    return HttpResponse("Успешно обновлен список водителей", content_type="application/json; charset=utf-8")


def load_transactions():
    """Загрузка транзакций для определения корректности периодических списаний"""
    batch_size = 100

    qs = Park.objects.filter(is_active=True)

    transactions_to_create = []

    for park in qs:
        client_id = park.client_id
        api_key = park.api_key
        park_id = park.park_id
        print(park.name)

        # Предварительно выбираем активные заказы и формируем словарь по order_id
        active_orders = Order.objects.filter(
            load_transaction_complete=False,
            park=park,
        ).select_related('driver').values('order_id', 'pk', 'driver_id')[:100]

        # Словарь заказов по order_id
        orders_dict = {order['order_id']: order for order in active_orders}

        # Фильтруем только используемые заказы
        orders_ids = list(orders_dict.keys())

        if not orders_ids:
            continue

        # Запрашиваем транзакции по фильтрованному списку заказов
        data = post_park_transactions_list(
            park_id,
            api_key,
            client_id,
            orders_ids
        )

        if not data:
            continue

        transactions_entries = data.get('transactions', [])

        if not transactions_entries:
            # Ставим метку для выбранных заказов
            Order.objects.filter(pk__in=[order['pk'] for order in orders_dict.values()]).update(
                load_transaction_complete=True)

        # Обрабатываем каждую транзакцию
        for transaction_data in transactions_entries:
            order_id = transaction_data['order_id']
            order = orders_dict.get(order_id)

            if not order:
                continue  # пропускаем транзакцию, если соответствующего заказа нет

            # Формируем новую транзакцию
            transactions_to_create.append(Transaction(
                park=park,
                driver_id=order['driver_id'],  # Идентификатор водителя
                order_id=order['pk'],  # Идентификатор заказа
                transaction_id=transaction_data['id'],
                event_at=transaction_data['event_at'],
                category_id=transaction_data.get('category_id', ''),
                category_name=transaction_data.get('category_name', ''),
                group_id=transaction_data.get('group_id', ''),
                amount=float(transaction_data.get('amount', 0)),
                description=transaction_data.get('description', '')
            ))

        # Применяем массовые обновления
        if transactions_to_create:
            try:
                Transaction.objects.bulk_create(
                    transactions_to_create,
                    batch_size=batch_size,
                    update_conflicts=True,
                    unique_fields=['transaction_id'],
                    update_fields=['amount', 'group_id']
                )

                # Ставим метку для выбранных заказов
                Order.objects.filter(pk__in=[order['pk'] for order in orders_dict.values()]).update(
                    load_transaction_complete=True)

            except Exception as e:
                logger.error("Ошибка в добавлении транзакций: %s", e)

    return Response({'message': 'транзакции загружены'}, status=status.HTTP_200_OK)


def process_dates_with_resume():
    """
    Обрабатывает даты с возможностью продолжения с последней успешной даты
    """
    start_date = datetime.strptime('2025-07-25', '%Y-%m-%d').date()
    end_date = datetime.strptime('2025-08-30', '%Y-%m-%d').date()

    # Получаем или создаем запись
    processing_record, created = DateProcessing.objects.get_or_create(
        defaults={'last_processed_date': start_date - timedelta(days=1)}
    )

    current_date = processing_record.last_processed_date + timedelta(days=1)

    # Обрабатываем даты
    while current_date <= end_date:
        try:
            # Основная логика обработки
            load_order(
                current_date.strftime('%Y-%m-%d'),
                current_date.strftime('%Y-%m-%d')
            )

            # Обновляем последнюю дату
            processing_record.last_processed_date = current_date
            processing_record.save()

            logger.error(f"Успешно обработано: {current_date}")

        except Exception as e:
            logger.error(f"Ошибка при обработке даты {current_date}: {str(e)}")
            break

        current_date += timedelta(days=1)
