import json
import logging
import math
import time

from datetime import datetime

import pytz
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

URL_API_YANDEX = 'https://fleet-api.taxi.yandex.net'

# Получение профиля водителя (курьера) GET
URL_API_GET_PROFILE = '/v2/parks/contractors/driver-profile'

# Получение списка профилей водителей (курьеров) POST
URL_API_GET_DRIVER_PROFILES = '/v1/parks/driver-profiles/list'

# Получение списка заказов POST
URL_API_POST_ORDERS_LIST = '/v1/parks/orders/list'

# Получение списка транзакций по водителю
URL_API_POST_DRIVER_TRANSACTIONS_LIST = '/v2/parks/driver-profiles/transactions/list'

URL_API_POST_PARK_ORDERS_TRANSACTIONS_LIST = '/v2/parks/orders/transactions/list'

URL_API_POST_TRANSACTIONS_CATEGORIES_LIST = '/v2/parks/transactions/categories/list'

# Получение списка условий работы GET
URL_API_GET_WORK_RULES = '/v1/parks/driver-work-rules'

# Получение списка автомобилей POST (car_list)
URL_API_CARS_LIST_POST = '/v1/parks/cars/list'

# Получение списка категорий транзакций POST
URL_API_POST_TRANSACTION_CATEGORIES_LIST = '/v2/parks/transactions/categories/list'


def get_headers(park_id, api_key, client_id):
    """Заголовки"""
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Client-ID': client_id,
        'X-Park-ID': park_id,
        'X-API-Key': api_key,
        'X-Integrator-ID': settings.INTEGRATOR_ID,
        'X-Integrator-API-Key': settings.INTEGRATOR_API_KEY,
        'User-Agent': '',
        'Accept-Language': 'ru'
    }
    return headers


def get_total(park_id, api_key, client_id, URL):
    """Данные для получения общего количества"""
    data = {
        'fields': {
            'car': [],
            'current_status': []
        },
        'limit': 1,
        'offset': 0,
        'query': {
            'park': {
                'id': park_id
            },
        }
    }
    headers = get_headers(park_id, api_key, client_id)
    response = requests.request('POST', URL, headers=headers, json=data)
    if response.status_code == 200:
        json_response = response.json()
        # получили общее количество
        total = json_response.get('total')
        return total
    return None


def get_park_info(park_id, api_key, client_id):
    """Информация о парке"""
    URL = URL_API_YANDEX + URL_API_GET_DRIVER_PROFILES
    try:
        park_id.encode('latin-1')
        api_key.encode('latin-1')
        client_id.encode('latin-1')
    except UnicodeEncodeError:
        logger.error('Данные по парку заполнены латиницей')
        # Если возникла ошибка UnicodeEncodeError, возвращаем ответ в формате JSON.
        response = {"message": "Вероятнее всего Вы ошиблись при вводе данных."}
        return json.dumps(response)

    # заголовки
    headers = get_headers(park_id, api_key, client_id)

    data = {
        'fields': {
            'account': [],
            'car': [],
            'current_status': [],
            'driver_profile': []
        },
        'limit': 1,
        'offset': 0,
        'query': {
            'park': {
                'id': park_id
            }
        }
    }

    response = requests.request('POST', URL, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['parks'][0]
    logger.error(response.text)
    return None


def get_profiles_list(park_id, api_key, client_id):
    """Получить список водителей (курьеров) парка"""
    URL = URL_API_YANDEX + URL_API_GET_DRIVER_PROFILES

    # заголовки
    headers = get_headers(park_id, api_key, client_id)

    # получили общее количество
    try:
        total = get_total(park_id, api_key, client_id, URL)
    except UnicodeEncodeError:
        return None

    if not total:
        return None

    limit = 1000
    offset = 0
    count_pages = math.ceil(total / limit)

    json_total = None
    for page in range(count_pages):
        count_profiles = total - (page * limit)
        if count_profiles > limit:
            count_profiles = limit

        data = {
            'limit': limit,
            'offset': offset,
            'query': {
                'park': {
                    'id': park_id,
                }
            },
            'sort_order': [
                {
                    'direction': 'desc',
                    'field': 'updated_at'
                }
            ]
        }
        offset += count_profiles

        response = requests.request('POST', URL, headers=headers, json=data)

        if response.status_code == 200:
            if not json_total:
                json_total = response.json()['driver_profiles']
            json_total += response.json()['driver_profiles']
        else:
            logger.error(f'Ошибка в обновлении списка водителей {response.status_code} {park_id}')

    return {
        'driver_profiles': json_total
    }


def post_orders_list(park_id, api_key, client_id, ended_at_from, ended_at_to):
    """Получение списка заказов с экспоненциальной задержкой при ошибке 429"""
    URL = URL_API_YANDEX + URL_API_POST_ORDERS_LIST

    # заголовки
    headers = get_headers(park_id, api_key, client_id)

    # Проверяем, являются ли ended_at_from и ended_at_to строками
    if isinstance(ended_at_from, str):
        ended_at_from_dt = datetime.strptime(ended_at_from, "%Y-%m-%d")
    else:
        ended_at_from_dt = ended_at_from  # Если это уже datetime, преобразование не нужно

    if isinstance(ended_at_to, str):
        ended_at_to_dt = datetime.strptime(ended_at_to, "%Y-%m-%d")
    else:
        ended_at_to_dt = ended_at_to  # Если это уже datetime, преобразование не нужно

    # Устанавливаем время и добавляем временную зону
    ended_at_from_dt = ended_at_from_dt.replace(hour=0, minute=0, second=0, tzinfo=pytz.timezone('Europe/Moscow'))
    ended_at_to_dt = ended_at_to_dt.replace(hour=23, minute=59, second=59, tzinfo=pytz.timezone('Europe/Moscow'))

    # Преобразуем в ISO 8601
    ended_at_from_iso = ended_at_from_dt.isoformat()
    ended_at_to_iso = ended_at_to_dt.isoformat()

    # получили общее количество
    limit = 500

    data = {
        'limit': limit,
        'query': {
            'park': {
                'id': park_id,
                'order': {
                    'ended_at': {
                        'from': ended_at_from_iso,
                        'to': ended_at_to_iso,
                    },
                }
            }
        }
    }

    json_total = []

    def make_request():
        nonlocal data, headers
        delay = 30  # начальная задержка 30 секунд
        max_attempts = 10  # максимальное количество попыток
        attempt = 0

        while attempt < max_attempts:
            response = requests.request('POST', URL, headers=headers, json=data)

            if response.status_code == 200:
                return response
            elif response.status_code == 429:
                attempt += 1
                logger.error(f'Ошибка 429. Попытка {attempt}. Ждем {delay} секунд. {park_id}')
                time.sleep(delay)
                delay *= 2  # удваиваем задержку
            else:
                logger.error(f'Ошибка загрузки заказов: {response.status_code} {response.text} {park_id}')
                return response

        logger.error(f'Превышено максимальное количество попыток ({max_attempts}) для парка {park_id}')
        return None

    # Первый запрос
    response = make_request()
    if response and response.status_code == 200:
        json_total = response.json().get('orders', [])

        # Обработка курсора
        while response.json().get('cursor'):

            cursor = {'cursor': response.json().get('cursor')}
            data.update(cursor)

            response = make_request()
            if response and response.status_code == 200:
                try:
                    json_total.extend(response.json().get('orders', []))
                except ValueError as e:
                    print("Ошибка декодирования JSON:", e)
                    print("Текст ответа:", response.text)
                    logger.error(f'Ошибка декодирования JSON: {e} {response.text}')
            else:
                break

    return {
        'orders': json_total
    }


def post_park_transactions_list(park_id, api_key, client_id, orders_ids):
    """Получение списка транзакций по заказу с экспоненциальной задержкой при ошибке 429"""
    URL = URL_API_YANDEX + URL_API_POST_PARK_ORDERS_TRANSACTIONS_LIST

    # заголовки
    headers = get_headers(park_id, api_key, client_id)

    # формируем запрос
    limit = 500

    data = {
        'limit': limit,
        'query': {
            'park': {
                'id': park_id,
                'order': {
                    'ids': orders_ids
                }
            }
        }
    }

    def make_request():
        nonlocal data, headers
        delay = 30  # начальная задержка 30 секунд
        max_attempts = 10  # максимальное количество попыток
        attempt = 0

        while attempt < max_attempts:
            response = requests.request('POST', URL, headers=headers, json=data)
            # print(response.text)

            if response.status_code == 200:
                return response
            elif response.status_code == 429:
                attempt += 1
                logger.error(
                    f'Ошибка 429 при запросе транзакций. Попытка {attempt}. Ждем {delay} сек. Park: {park_id}')
                time.sleep(delay)
                delay *= 2  # удваиваем задержку
            else:
                logger.error(
                    f'Ошибка загрузки транзакций: {response.status_code} {response.text} Park: {park_id}')
                return response

        logger.error(
            f'Превышено максимальное количество попыток ({max_attempts}) для транзакций заказа парк {park_id}')
        return None

    json_total = []
    response = make_request()

    if response and response.status_code == 200:
        try:
            json_total = response.json().get('transactions', [])

            # Обработка курсора
            while response.json().get('cursor'):

                cursor = {'cursor': response.json().get('cursor')}
                data.update(cursor)

                response = make_request()
                if response and response.status_code == 200:
                    try:
                        json_total.extend(response.json().get('transactions', []))
                    except ValueError as e:
                        print(f"Ошибка декодирования JSON для транзакций: {e}")
                        print("Текст ответа:", response.text)
                        logger.error(f'Ошибка декодирования JSON для транзакций: {e} {response.text} Order: {order_id}')
                else:
                    break
        except Exception as e:
            logger.error(f'Неожиданная ошибка при обработке транзакций: {e} Park: {park_id}')

    return {
        'transactions': json_total if json_total is not None else []
    }


def get_transaction_categories(park_id, api_key, client_id):
    """Получение списка категорий транзакций"""
    """Получение списка транзакций по водителю (курьеру)"""
    URL = URL_API_YANDEX + URL_API_POST_TRANSACTIONS_CATEGORIES_LIST

    headers = get_headers(park_id, api_key, client_id)

    data = {
        'query': {
            'park': {
                'id': park_id
            }
        }
    }

    response = requests.request('POST', URL, headers=headers, json=data)
    if response.status_code == 200:
        print(response.json())
        return response.json()
    return None


def get_driver_work_rules(park_id, api_key, client_id):
    """Получить список условий работы"""
    URL = URL_API_YANDEX + URL_API_GET_WORK_RULES

    # заголовки
    headers = get_headers(park_id, api_key, client_id)
    params = {'park_id': park_id}
    response = requests.request('GET', URL, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    return None


def post_car_list(park_id, api_key, client_id):
    """Получение списка автомобилей"""
    URL = URL_API_YANDEX + URL_API_CARS_LIST_POST

    # заголовки
    headers = get_headers(park_id, api_key, client_id)

    # получили общее количество
    total = get_total(park_id, api_key, client_id, URL)
    if not total:
        return None
    limit = 1000
    offset = 0
    count_pages = math.ceil(total / limit)

    json_total = None
    # для каждой страницы
    for page in range(count_pages):
        # количество автомобилей
        count_cars = total - (page * limit)
        if count_cars > limit:
            count_cars = limit

        data = {
            'limit': limit,
            'offset': offset,
            'query': {
                'park': {
                    'id': park_id,
                }
            }
        }
        offset += count_cars

        response = requests.request('POST', URL, headers=headers, json=data)
        if response.status_code == 200:
            if not json_total:
                json_total = response.json()['cars']
            json_total += response.json()['cars']

    return {
        'cars': json_total
    }


def post_transaction_categories_list(park_id, api_key, client_id):
    """Получение списка категорий транзакций"""
    URL = URL_API_YANDEX + URL_API_POST_TRANSACTION_CATEGORIES_LIST
    data = {
        'query': {
            'park': {
                'id': park_id,
            }
        }
    }
    # заголовки
    headers = get_headers(park_id, api_key, client_id)
    response = requests.request('POST', URL, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()
    return None