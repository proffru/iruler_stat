import json
import logging
import math
import time

from datetime import datetime

import pytz
import requests
import uuid
from django.conf import settings

from park.models import Park, Driver

logger = logging.getLogger(__name__)

URL_API_YANDEX = 'https://fleet-api.taxi.yandex.net'

ORIGINAL_URL = 'https://fleet.yandex.ru'

ORIGINAL_URL_KZ = 'https://fleet.yandex.kz'

# Получение профиля водителя (курьера) GET
URL_API_GET_PROFILE = '/v2/parks/contractors/driver-profile'

# Получение списка профилей водителей (курьеров) POST
URL_API_GET_DRIVER_PROFILES = '/v1/parks/driver-profiles/list'

# Получение списка заказов POST
URL_API_POST_ORDERS_LIST = '/v1/parks/orders/list'

# Получение списка транзакций по водителю
URL_API_POST_DRIVER_TRANSACTIONS_LIST = '/v2/parks/driver-profiles/transactions/list'

URL_API_POST_PARK_TRANSACTIONS_LIST = '/v2/parks/transactions/list'

URL_API_POST_TRANSACTIONS_CATEGORIES_LIST = '/v2/parks/transactions/categories/list'

# Создание транзакции на балансе водителя (курьера) POST
URL_API_CREATE_TRANSACTION = '/v3/parks/driver-profiles/transactions'

# Проверка статуса транзакции
URL_API_CHECK_TRANSACTION_STATUS = '/v3/parks/driver-profiles/transactions/status'


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


def post_orders_list(park_id, api_key, client_id, ended_at_from, ended_at_to, time_zone, driver_id=None):
    """Получение списка заказов"""
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
    ended_at_from_dt = ended_at_from_dt.replace(hour=0, minute=0, second=0, tzinfo=pytz.timezone(time_zone))
    ended_at_to_dt = ended_at_to_dt.replace(hour=23, minute=59, second=59, tzinfo=pytz.timezone(time_zone))

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
                    'statuses': [
                        'complete'
                    ]
                }
            }
        }
    }

    if driver_id:
        driver_data = {
            'driver_profile': {
                'id': driver_id
            }
        }
        data['query']['park'].update(driver_data)

    json_total = []
    response = requests.request('POST', URL, headers=headers, json=data)
    if response.status_code == 200:
        json_total = response.json()['orders']
        print(len(json_total))
        try:
            while response.json().get('cursor'):
                cursor = {
                    'cursor': response.json().get('cursor')
                }
                data.update(cursor)
                response = requests.request('POST', URL, headers=headers, json=data)
                try:
                    response.json()
                    json_total += response.json().get('orders')
                except ValueError as e:
                    print("Ошибка декодирования JSON:", e)
                    print("Текст ответа:", response.text)
                    logger.error(f'Ошибка декодирования JSON:, {e} {response.text}')
        except Exception as e:
            logger.error(f'ошибка загрузки заказов {response.text} {e} {park_id}')
    return {
        'orders': json_total
    }


def post_park_transactions_list(park_id, api_key, client_id, category_ids, ended_at_from, ended_at_to, time_zone):
    """Получение списка транзакций по водителю (курьеру)"""
    URL = URL_API_YANDEX + URL_API_POST_PARK_TRANSACTIONS_LIST

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
    ended_at_from_dt = ended_at_from_dt.replace(hour=0, minute=0, second=0, tzinfo=pytz.timezone(time_zone))
    ended_at_to_dt = ended_at_to_dt.replace(hour=23, minute=59, second=59, tzinfo=pytz.timezone(time_zone))

    # Преобразуем в ISO 8601
    ended_at_from_iso = ended_at_from_dt.isoformat()
    ended_at_to_iso = ended_at_to_dt.isoformat()

    # формируем запрос
    limit = 500

    data = {
        'limit': limit,
        'query': {
            'park': {
                'id': park_id,
                'transaction': {
                    'event_at': {
                        'from': ended_at_from_iso,
                        'to': ended_at_to_iso
                    },
                    'category_ids': [
                        category_ids
                    ]
                }
            }
        }
    }

    json_total = None
    response = requests.request('POST', URL, headers=headers, json=data)
    if response.status_code == 200:
        json_total = response.json()['transactions']
        # перебираем все порции заказов
        while response.json().get('cursor'):
            cursor = {
                'cursor': response.json().get('cursor')
            }
            data.update(cursor)
            response = requests.request('POST', URL, headers=headers, json=data)
            response.json()
            json_total += response.json()['transactions']
    return {'transactions': json_total}


def get_user_headers(park_id, refer):
    """Формируем заголовки для парсинга диспетчерской"""
    headers_list = {
        'Accept-Language': 'ru',
        'Content-Type': 'application/json; charset=utf-8',
        'Cookie': settings.SESSION,
        'Host': 'fleet.yandex.ru',
        'Origin': ORIGINAL_URL,
        'Referer': refer,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 YaBrowser/25.2.0.0 Safari/537.36',
        'X-Park-Id': park_id
    }
    return headers_list


def get_regular_charges(park_id):
    """Загрузить периодические списания"""
    URL = f'{ORIGINAL_URL}/api/v1/regular-charges/list'
    refer = f'{ORIGINAL_URL}/contractors?segment=churn&park_id={park_id}'

    headers = get_user_headers(park_id, refer)
    if not headers:
        return None

    # получили количество записей
    payload = {
        'date_type': 'date_from',
        'limit': 1,
        'page': 1
    }

    response = requests.request("POST", URL, headers=headers, json=payload)
    if response.status_code != 200:
        logger.error(f'get_regular_charges - не получаю список периодических списаний, нужно обновить сессию {park_id}')
        return None
    try:
        total = response.json()['pagination']['total']
    except Exception:
        return None

    # собираем весь отчет
    limit = 100
    if limit > total:
        limit = total
    if total >= limit:
        # подсчитываем количество страниц
        count_pages = math.ceil(total / limit)

        json_total = []

        for page in range(count_pages):
            page += 1
            payload = {
                'date_type': 'date_from',
                'limit': limit,
                'page': page
            }
            response = requests.request("POST", URL, headers=headers, json=payload)
            if response.status_code == 200:
                json_total += response.json()['regular_charges']
        return {
            'regular_charges': json_total
        }
    return None


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


def yandex_payment(driver_id, amount, description):
    """Проведения платежей"""
    logger.info(f"Yandex payment STARTED for driver_id={driver_id}, amount={amount}")
    URL = URL_API_YANDEX + URL_API_CREATE_TRANSACTION

    try:
        driver = Driver.objects.select_related('park').get(driver_id=driver_id)
        park = driver.park
    except Exception as e:
        logger.error(f'ошибка загрузки водителя и ошибка загрузки парка {e}')
        return False

    headers = get_headers(park.park_id, park.api_key, park.client_id)

    max_retries = 2
    retry_count = 0

    transaction_id = None
    created_at = None
    status = None
    version = None
    status_description = None
    status_code = 0

    token = str(uuid.uuid4())
    x_token = {
        "X-Idempotency-Token": token
    }
    headers.update(x_token)

    post_data = {
        'park_id': park.park_id,
        'contractor_profile_id': driver_id,
        'amount': str(amount),
        'description': description,
        'data': {
            'kind': 'payout',
            'fee_amount': '0'
        }
    }

    while retry_count < max_retries:
        if retry_count > 0:
            time.sleep(1)

        try:
            response = requests.post(
                URL,
                headers=headers,
                json=post_data
            )
            response.raise_for_status()
        except (requests.RequestException, ValueError) as e:
            retry_count += 1
            continue

        if response.status_code != 200:
            print("Ошибка при запросе:", response.text)
            return {
                'status': 'fail',
                'transaction': None
            }

        json_data = response.json()
        print("Yandex response text:", response.text)

        # Сохраняем данные вне зависимости от статуса
        transaction_id = json_data.get("id")
        created_at = json_data.get("created_at")
        status = json_data.get("status")
        version = json_data.get("version")
        status_description = json_data.get('status_description')

        # Если статус не in_progress — можно выходить
        if status != "in_progress":
            break

        retry_count += 1

    # сохраняем транзакцию
    transaction = PaymentStatus.objects.create(
        park=park,
        driver=driver,
        transaction_id=transaction_id,
        created_at=created_at,
        status=status,
        version=version,
        status_description=status_description,
        amount=amount,
        status_code=status_code
    )

    if status is None:
        return {
            'status': 'fail',
            'transaction': None
        }

    return {
        'status': status,
        'transaction': transaction
    }


def payment_status(transaction_id, driver_id):
    """Статус транзакции"""
    URL = URL_API_YANDEX + URL_API_CHECK_TRANSACTION_STATUS

    try:
        driver = Driver.objects.select_related('park').get(driver_id=driver_id)
        park = driver.park
    except Exception as e:
        logger.error(f'ошибка загрузки водителя и ошибка загрузки парка {e}')
        return False

    params = {
        'id': transaction_id,
        'contractor_profile_id': driver_id,
        'park_id': park.park_id,
        'version': 1
    }

    headers = get_headers(park.park_id, park.api_key, park.client_id)

    response = requests.get(
        URL,
        headers=headers,
        params=params
    )

    print("Yandex response text:", response.text)

    if response.status_code == 200:
        json_data = response.json()

        # Извлекаем данные
        transaction_id = json_data.get('id')
        status = json_data['version_info']['status']
        version = json_data['version_info']['version']

        # сохраняем транзакцию
        obj, updated =PaymentStatus.objects.update_or_create(
            park=park,
            driver=driver,
            transaction_id=transaction_id,
            version=version,
            defaults={
                'status': status
            }
        )
        if updated:
            return {
                'status': status,
                'transaction': obj
            }

    return {
        'status': None,
        'transaction': None
    }


def get_active_drivers(park_id, driver_type, total=None):
    """Загрузить периодические списания"""
    refer = f'{ORIGINAL_URL}/contractors?segment=active&employment_type=selfemployed&park_id={park_id}'

    headers = get_user_headers(park_id, refer)
    if not headers:
        return None

    if total:
        URL = f'{ORIGINAL_URL}/api/fleet/contractor-profiles-manager/v1/segments/count'
        payload = {}
    else:
        URL = f'{ORIGINAL_URL}/api/fleet/contractor-profiles-manager/v1/active/count'

        # получили количество записей
        if driver_type == 'selfemployed':
            payload = {
                'query': {
                    'employment_type': 'selfemployed'
                }
            }
        else:
            payload = {
                'query': {
                    'employment_type': 'individual_entrepreneur'
                }
            }

    response = requests.request("POST", URL, headers=headers, json=payload)
    print(response.text)
    if response.status_code != 200:
        logger.error(f'get_active_drivers - не получаю список периодических списаний, нужно обновить сессию {park_id}')
        return None
    try:
        if total:
            total = response.json()['active']
            return total
        else:
            stages = response.json()['stages']['all']
            return stages
    except Exception:
        return None
