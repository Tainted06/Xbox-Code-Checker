"""
Актуальные User-Agent строки для имитации реальных браузеров
Обновлено: январь 2025
"""

import random
from typing import List

# Актуальные User-Agent строки (январь 2025)
USER_AGENTS: List[str] = [
    # Chrome 131 (Windows 10/11)
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
    
    # Chrome 130 (Windows 10/11)
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    
    # Chrome 129 (Windows 10/11)
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    
    # Firefox 133 (Windows)
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0',
    
    # Safari (macOS)
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15',
    
    # Chrome на macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    
    # Chrome на Linux
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    
    # Firefox на Linux
    'Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0',
    'Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0',
    
    # Opera
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/117.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 OPR/116.0.0.0',
    
    # Brave
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    
    # Vivaldi
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Vivaldi/7.0.3495.11',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Vivaldi/7.0.3495.6',
    
    # Yandex Browser
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 YaBrowser/24.12.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 YaBrowser/24.11.0.0 Safari/537.36',
    
    # Mobile Chrome (Android)
    'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
    
    # Mobile Safari (iOS)
    'Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1',
    
    # Samsung Internet
    'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/26.0 Chrome/131.0.0.0 Mobile Safari/537.36',
]

# Веса для разных типов браузеров (для более реалистичного распределения)
BROWSER_WEIGHTS = {
    'chrome_windows': 0.4,  # 40% - Chrome на Windows
    'chrome_other': 0.2,    # 20% - Chrome на других ОС
    'firefox': 0.15,        # 15% - Firefox
    'safari': 0.1,          # 10% - Safari
    'edge': 0.08,           # 8% - Edge
    'other': 0.07           # 7% - Остальные браузеры
}


def get_random_user_agent() -> str:
    """
    Возвращает случайный User-Agent из списка актуальных
    """
    return random.choice(USER_AGENTS)


def get_weighted_user_agent() -> str:
    """
    Возвращает User-Agent с учетом реального распределения браузеров
    """
    # Группируем User-Agent'ы по типам
    chrome_windows = [ua for ua in USER_AGENTS if 'Windows NT 10.0' in ua and 'Chrome/' in ua and 'Edg/' not in ua and 'OPR/' not in ua and 'YaBrowser/' not in ua and 'Vivaldi/' not in ua]
    chrome_other = [ua for ua in USER_AGENTS if 'Chrome/' in ua and 'Windows NT 10.0' not in ua and 'Edg/' not in ua and 'OPR/' not in ua and 'YaBrowser/' not in ua and 'Vivaldi/' not in ua]
    firefox = [ua for ua in USER_AGENTS if 'Firefox/' in ua]
    safari = [ua for ua in USER_AGENTS if 'Safari/' in ua and 'Chrome/' not in ua]
    edge = [ua for ua in USER_AGENTS if 'Edg/' in ua]
    other = [ua for ua in USER_AGENTS if ua not in chrome_windows + chrome_other + firefox + safari + edge]
    
    # Выбираем категорию на основе весов
    rand = random.random()
    if rand < BROWSER_WEIGHTS['chrome_windows']:
        return random.choice(chrome_windows) if chrome_windows else get_random_user_agent()
    elif rand < BROWSER_WEIGHTS['chrome_windows'] + BROWSER_WEIGHTS['chrome_other']:
        return random.choice(chrome_other) if chrome_other else get_random_user_agent()
    elif rand < BROWSER_WEIGHTS['chrome_windows'] + BROWSER_WEIGHTS['chrome_other'] + BROWSER_WEIGHTS['firefox']:
        return random.choice(firefox) if firefox else get_random_user_agent()
    elif rand < BROWSER_WEIGHTS['chrome_windows'] + BROWSER_WEIGHTS['chrome_other'] + BROWSER_WEIGHTS['firefox'] + BROWSER_WEIGHTS['safari']:
        return random.choice(safari) if safari else get_random_user_agent()
    elif rand < BROWSER_WEIGHTS['chrome_windows'] + BROWSER_WEIGHTS['chrome_other'] + BROWSER_WEIGHTS['firefox'] + BROWSER_WEIGHTS['safari'] + BROWSER_WEIGHTS['edge']:
        return random.choice(edge) if edge else get_random_user_agent()
    else:
        return random.choice(other) if other else get_random_user_agent()


def get_chrome_user_agent() -> str:
    """
    Возвращает только Chrome User-Agent (наиболее совместимый)
    """
    chrome_agents = [ua for ua in USER_AGENTS if 'Chrome/' in ua and 'Edg/' not in ua and 'OPR/' not in ua and 'YaBrowser/' not in ua and 'Vivaldi/' not in ua]
    return random.choice(chrome_agents) if chrome_agents else USER_AGENTS[0]


def get_desktop_user_agent() -> str:
    """
    Возвращает только десктопные User-Agent'ы
    """
    desktop_agents = [ua for ua in USER_AGENTS if 'Mobile' not in ua and 'Android' not in ua and 'iPhone' not in ua and 'iPad' not in ua]
    return random.choice(desktop_agents) if desktop_agents else USER_AGENTS[0]


def get_stable_user_agent() -> str:
    """
    Возвращает только самые стабильные Chrome User-Agent'ы для Windows
    """
    stable_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    ]
    return random.choice(stable_agents)


def get_legacy_user_agent() -> str:
    """
    Возвращает старый User-Agent для совместимости (если новые вызывают проблемы)
    """
    return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'


def get_compatible_user_agent() -> str:
    """
    Возвращает наиболее совместимый User-Agent (смесь старого и нового)
    """
    # 70% шанс использовать новый, 30% - старый проверенный
    if random.random() < 0.7:
        return get_stable_user_agent()
    else:
        return get_legacy_user_agent()


# Для обратной совместимости
def get_user_agent() -> str:
    """
    Основная функция для получения User-Agent
    По умолчанию возвращает взвешенный выбор
    """
    return get_weighted_user_agent()


if __name__ == "__main__":
    # Тестирование функций
    print("Случайный User-Agent:")
    print(get_random_user_agent())
    print("\nВзвешенный User-Agent:")
    print(get_weighted_user_agent())
    print("\nChrome User-Agent:")
    print(get_chrome_user_agent())
    print("\nДесктопный User-Agent:")
    print(get_desktop_user_agent())