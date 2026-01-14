"""
Тестирование различных эндпоинтов Calendar API
"""
import os
import requests
import json
from dotenv import load_dotenv


def test_calendar_endpoints(admin_token, org_id):
    """Тестирует различные варианты Calendar API endpoints"""

    # Различные базовые URL для Calendar API
    base_urls = [
        "https://api.calendar.yandex.net",
        "https://calendar-api.yandex.net",
        "https://api360.yandex.net/calendar/v1",
        "https://api360.yandex.net/directory/v1",
    ]

    paths = [
        f"/org/{org_id}/events",
        f"/org/{org_id}/calendars",
        f"/events",
        f"/calendars",
    ]

    headers = {
        "Authorization": f"OAuth {admin_token}",
        "Content-Type": "application/json"
    }

    print("="*80)
    print("ТЕСТИРОВАНИЕ CALENDAR API ENDPOINTS")
    print("="*80 + "\n")

    working_endpoints = []

    for base_url in base_urls:
        for path in paths:
            url = base_url + path

            try:
                print(f"Тестирую: {url}")
                response = requests.get(url, headers=headers, timeout=5)
                print(f"  Статус: {response.status_code}")

                if response.status_code == 200:
                    print(f"  [OK] Работает!")
                    working_endpoints.append(url)
                    print(f"  Ответ: {response.text[:200]}")
                elif response.status_code == 401:
                    print(f"  [AUTH] Требуется авторизация")
                elif response.status_code == 403:
                    print(f"  [FORBIDDEN] Доступ запрещен")
                elif response.status_code == 404:
                    print(f"  [404] Не найден")
                else:
                    print(f"  Ответ: {response.text[:100]}")

            except requests.exceptions.Timeout:
                print(f"  [TIMEOUT] Превышено время ожидания")
            except Exception as e:
                print(f"  [ERROR] {e}")

            print()

    return working_endpoints


def check_calendar_docs_endpoint(admin_token, org_id):
    """Проверяет эндпоинты из официальной документации"""
    # Согласно документации Яндекс 360
    # https://yandex.ru/dev/api360/doc/ru/concepts/calendar

    endpoints = [
        {
            "url": f"https://api360.yandex.net/directory/v1/org/{org_id}/calendar/layers",
            "description": "Список календарей организации"
        },
        {
            "url": f"https://api360.yandex.net/directory/v1/org/{org_id}/calendar/events",
            "description": "События календаря организации"
        },
    ]

    headers = {
        "Authorization": f"OAuth {admin_token}",
        "Content-Type": "application/json"
    }

    print("="*80)
    print("ПРОВЕРКА ОФИЦИАЛЬНЫХ ЭНДПОИНТОВ")
    print("="*80 + "\n")

    for endpoint in endpoints:
        url = endpoint["url"]
        desc = endpoint["description"]

        print(f"{desc}")
        print(f"URL: {url}")

        try:
            response = requests.get(url, headers=headers)
            print(f"Статус: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"[OK] Успешно!")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                return True
            else:
                print(f"Ответ: {response.text}")

        except Exception as e:
            print(f"Ошибка: {e}")

        print()

    return False


def check_admin_token_scopes(admin_token):
    """Проверяет, какие права есть у административного токена"""
    url = "https://login.yandex.ru/info"
    headers = {
        "Authorization": f"OAuth {admin_token}"
    }

    try:
        print("="*80)
        print("ПРОВЕРКА ПРАВ АДМИНИСТРАТИВНОГО ТОКЕНА")
        print("="*80 + "\n")

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            print("[OK] Информация о токене получена:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return data
        else:
            print(f"Статус: {response.status_code}")
            print(f"Ответ: {response.text}")

    except Exception as e:
        print(f"Ошибка: {e}")

    return None


def main():
    load_dotenv()

    admin_token = os.getenv("YANDEX_ADMIN_TOKEN")
    org_id = os.getenv("YANDEX_ORG_ID")

    if not admin_token or not org_id:
        print("[ERROR] Не найдены переменные окружения")
        return

    # 1. Проверяем права токена
    token_info = check_admin_token_scopes(admin_token)

    # 2. Проверяем официальные эндпоинты
    has_calendar = check_calendar_docs_endpoint(admin_token, org_id)

    # 3. Тестируем различные варианты
    if not has_calendar:
        print("\n")
        working = test_calendar_endpoints(admin_token, org_id)

        if working:
            print("="*80)
            print(f"[OK] НАЙДЕНЫ РАБОЧИЕ ЭНДПОИНТЫ ({len(working)}):")
            print("="*80)
            for endpoint in working:
                print(f"  - {endpoint}")
        else:
            print("="*80)
            print("[INFO] НЕ НАЙДЕНЫ РАБОЧИЕ ЭНДПОИНТЫ")
            print("="*80)
            print("\nВозможные причины:")
            print("  1. Административный токен не имеет прав для Calendar API")
            print("  2. Calendar API требует отдельной активации в организации")
            print("  3. Используется другой формат API")
            print("\nРекомендация:")
            print("  - Проверьте документацию: https://yandex.ru/dev/api360/doc/ru/")
            print("  - Убедитесь, что Calendar включен в организации")


if __name__ == "__main__":
    main()
