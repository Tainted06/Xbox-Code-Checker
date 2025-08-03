"""
Расширенные заголовки браузера для лучшей маскировки
"""

import random
from typing import Dict, List

# Различные варианты Accept заголовков
ACCEPT_HEADERS = [
    'application/json, text/javascript, */*; q=0.01',
    'application/json, text/plain, */*',
    'application/json, application/xml, text/plain, text/html, *.*',
    '*/*',
    'application/json',
]

# Различные варианты Accept-Language
ACCEPT_LANGUAGE_HEADERS = [
    'en-US,en;q=0.9',
    'en-US,en;q=0.9,ru;q=0.8',
    'en-US,en;q=0.8',
    'en-US,en;q=0.9,ru;q=0.8,de;q=0.7',
    'ru-RU,ru;q=0.9,en;q=0.8',
    'ru,en-US;q=0.9,en;q=0.8',
]

# Различные варианты Accept-Encoding
ACCEPT_ENCODING_HEADERS = [
    'gzip, deflate, br',
    'gzip, deflate, br, zstd',
    'gzip, deflate',
    'gzip, deflate, br, compress',
]

# Sec-CH-UA заголовки для разных браузеров
SEC_CH_UA_HEADERS = [
    '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    '"Not_A Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
    '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
    '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
]

# Sec-CH-UA-Platform заголовки
SEC_CH_UA_PLATFORM_HEADERS = [
    '"Windows"',
    '"macOS"',
    '"Linux"',
]

# DNT (Do Not Track) заголовки
DNT_HEADERS = ['1', '0', None]  # None означает отсутствие заголовка

# Sec-GPC заголовки
SEC_GPC_HEADERS = ['1', '0', None]


def get_random_headers() -> Dict[str, str]:
    """
    Генерирует случайный набор заголовков браузера
    """
    headers = {
        'accept': random.choice(ACCEPT_HEADERS),
        'accept-encoding': random.choice(ACCEPT_ENCODING_HEADERS),
        'accept-language': random.choice(ACCEPT_LANGUAGE_HEADERS),
        'origin': 'https://www.microsoft.com',
        'referer': 'https://www.microsoft.com/',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'sec-ch-ua': random.choice(SEC_CH_UA_HEADERS),
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': random.choice(SEC_CH_UA_PLATFORM_HEADERS),
        'connection': 'keep-alive',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
    }
    
    # Добавляем опциональные заголовки
    dnt = random.choice(DNT_HEADERS)
    if dnt is not None:
        headers['dnt'] = dnt
    
    sec_gpc = random.choice(SEC_GPC_HEADERS)
    if sec_gpc is not None:
        headers['sec-gpc'] = sec_gpc
    
    # Иногда добавляем upgrade-insecure-requests
    if random.random() < 0.3:
        headers['upgrade-insecure-requests'] = '1'
    
    return headers


def get_chrome_headers() -> Dict[str, str]:
    """
    Генерирует заголовки, характерные для Chrome (консервативная версия)
    """
    return {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.8',
        'origin': 'https://www.microsoft.com',
        'referer': 'https://www.microsoft.com/',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'sec-gpc': '1',
        'connection': 'keep-alive',
    }


def get_firefox_headers() -> Dict[str, str]:
    """
    Генерирует заголовки, характерные для Firefox
    """
    return {
        'accept': 'application/json, text/plain, */*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.5',
        'origin': 'https://www.microsoft.com',
        'referer': 'https://www.microsoft.com/',
        'connection': 'keep-alive',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'te': 'trailers',
    }


def get_safari_headers() -> Dict[str, str]:
    """
    Генерирует заголовки, характерные для Safari
    """
    return {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'origin': 'https://www.microsoft.com',
        'referer': 'https://www.microsoft.com/',
        'connection': 'keep-alive',
        'cache-control': 'no-cache',
    }


def get_headers_for_user_agent(user_agent: str) -> Dict[str, str]:
    """
    Возвращает подходящие заголовки для конкретного User-Agent (консервативная версия)
    """
    # Всегда используем Chrome-подобные заголовки для лучшей совместимости
    return get_chrome_headers()


def get_conservative_headers() -> Dict[str, str]:
    """
    Возвращает консервативные заголовки, максимально близкие к оригинальным
    """
    return {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.8',
        'origin': 'https://www.microsoft.com',
        'referer': 'https://www.microsoft.com/',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'sec-gpc': '1',
        'connection': 'keep-alive'
    }


# Дополнительные заголовки для специальных случаев
ADDITIONAL_HEADERS = {
    'x-requested-with': 'XMLHttpRequest',
    'x-ms-client-request-id': lambda: f"{random.randint(10000000, 99999999)}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-{random.randint(100000000000, 999999999999)}",
}


def add_random_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Добавляет случайные дополнительные заголовки
    """
    # Иногда добавляем X-Requested-With
    if random.random() < 0.2:
        headers['x-requested-with'] = ADDITIONAL_HEADERS['x-requested-with']
    
    # Иногда добавляем X-MS-Client-Request-ID
    if random.random() < 0.1:
        headers['x-ms-client-request-id'] = ADDITIONAL_HEADERS['x-ms-client-request-id']()
    
    return headers