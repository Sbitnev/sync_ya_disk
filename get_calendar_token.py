"""
Получение токена для доступа к календарю через Admin API
"""
import os
import requests
import json
from dotenv import load_dotenv


def create_service_token(admin_token, org_id, app_id, user_id):
    """Создает токен сервисного приложения для пользователя"""
    # Пробуем разные варианты endpoint'ов
    endpoints = [
        f"https://api360.yandex.net/security/v1/org/{org_id}/service_applications/{app_id}/service_tokens",
        f"https://api360.yandex.net/admin/v1/org/{org_id}/service_applications/{app_id}/tokens",
        f"https://api360.yandex.net/directory/v1/org/{org_id}/service_applications/{app_id}/tokens",
    ]

    headers = {
        "Authorization": f"OAuth {admin_token}",
        "Content-Type": "application/json"
    }

    for url in endpoints:
        print(f"\nПопытка создания токена: {url}")

        # POST запрос
        data = {
            "userId": str(user_id)
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            print(f"POST Статус: {response.status_code}")
            print(f"Ответ: {response.text[:500]}")

            if response.status_code in [200, 201]:
                result = response.json()
                print("\n[OK] Токен создан!")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return result

        except Exception as e:
            print(f"Ошибка: {e}")

    return None


def generate_app_token(admin_token, org_id, app_id, user_id):
    """Генерирует токен приложения для пользователя"""
    url = f"https://api360.yandex.net/security/v1/org/{org_id}/service_applications/{app_id}/app_passwords"
    headers = {
        "Authorization": f"OAuth {admin_token}",
        "Content-Type": "application/json"
    }
    data = {
        "userId": str(user_id),
        "name": "Calendar API Access"
    }

    try:
        print(f"\nГенерация app password...")
        print(f"URL: {url}")
        response = requests.post(url, headers=headers, json=data)
        print(f"Статус: {response.status_code}")
        print(f"Ответ: {response.text[:500]}")

        if response.status_code in [200, 201]:
            result = response.json()
            print("\n[OK] App password создан!")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return result

    except Exception as e:
        print(f"Ошибка: {e}")

    return None


def get_admin_impersonation_token(admin_token, org_id, user_id, scopes):
    """Пытается получить токен от имени администратора"""
    url = f"https://api360.yandex.net/admin/v1/org/{org_id}/tokens/impersonation"
    headers = {
        "Authorization": f"OAuth {admin_token}",
        "Content-Type": "application/json"
    }
    data = {
        "userId": str(user_id),
        "scopes": scopes
    }

    try:
        print(f"\nПолучение токена имперсонации...")
        response = requests.post(url, headers=headers, json=data)
        print(f"Статус: {response.status_code}")
        print(f"Ответ: {response.text}")

        if response.status_code in [200, 201]:
            result = response.json()
            print("\n[OK] Токен имперсонации получен!")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return result

    except Exception as e:
        print(f"Ошибка: {e}")

    return None


def try_calendar_api_directly(admin_token, org_id, user_id):
    """Пробует напрямую обратиться к Calendar API с админ токеном"""
    url = f"https://api360.yandex.net/calendar/v1/users/{user_id}/events"

    headers_variants = [
        {
            "Authorization": f"OAuth {admin_token}",
            "X-Org-ID": str(org_id)
        },
        {
            "Authorization": f"OAuth {admin_token}",
            "X-UID": str(user_id)
        },
        {
            "Authorization": f"OAuth {admin_token}"
        }
    ]

    for i, headers in enumerate(headers_variants, 1):
        print(f"\nВариант {i}: Прямой запрос к Calendar API")
        print(f"Headers: {headers}")

        try:
            response = requests.get(url, headers=headers)
            print(f"Статус: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print("[OK] Доступ к календарю есть!")
                print(f"События: {len(data.get('events', []))}")
                return True
            else:
                print(f"Ответ: {response.text[:200]}")

        except Exception as e:
            print(f"Ошибка: {e}")

    return False


def list_all_service_apps(admin_token, org_id):
    """Получает подробную информацию о всех сервисных приложениях"""
    url = f"https://api360.yandex.net/security/v1/org/{org_id}/service_applications"
    headers = {
        "Authorization": f"OAuth {admin_token}",
        "Content-Type": "application/json"
    }

    try:
        print("Получение списка всех сервисных приложений...")
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            apps = data.get("applications", [])

            print(f"\n[OK] Найдено приложений: {len(apps)}\n")

            for app in apps:
                app_id = app.get("id")
                scopes = app.get("scopes", [])

                print(f"Приложение ID: {app_id}")
                print(f"Права: {', '.join(scopes)}")

                # Пробуем получить детальную информацию о приложении
                detail_url = f"https://api360.yandex.net/security/v1/org/{org_id}/service_applications/{app_id}"
                detail_response = requests.get(detail_url, headers=headers)

                if detail_response.status_code == 200:
                    detail = detail_response.json()
                    print(f"Детали: {json.dumps(detail, indent=2, ensure_ascii=False)}")

                print()

            return apps
        else:
            print(f"Ошибка: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"Ошибка: {e}")

    return []


def main():
    load_dotenv()

    admin_token = os.getenv("YANDEX_ADMIN_TOKEN")
    org_id = os.getenv("YANDEX_ORG_ID")
    calendar_app_id = "69687b2f4722452fae8b875ed3559ec3"
    user_id = "1130000057842996"  # tn@imprice.ai

    print("="*80)
    print("ПОЛУЧЕНИЕ ТОКЕНА ДЛЯ ДОСТУПА К КАЛЕНДАРЮ")
    print("="*80)
    print(f"Организация: {org_id}")
    print(f"Приложение Calendar: {calendar_app_id}")
    print(f"Пользователь: tn@imprice.ai (ID: {user_id})")
    print("="*80)

    # Получаем детальную информацию о приложениях
    apps = list_all_service_apps(admin_token, org_id)

    # Пробуем создать токен сервисного приложения
    token_data = create_service_token(admin_token, org_id, calendar_app_id, user_id)

    if not token_data:
        # Пробуем app password
        token_data = generate_app_token(admin_token, org_id, calendar_app_id, user_id)

    if not token_data:
        # Пробуем токен имперсонации
        token_data = get_admin_impersonation_token(admin_token, org_id, user_id, ["calendar:all"])

    # Пробуем напрямую обратиться к Calendar API
    print("\n" + "="*80)
    print("ПРЯМОЙ ДОСТУП К CALENDAR API")
    print("="*80)

    has_access = try_calendar_api_directly(admin_token, org_id, user_id)

    print("\n" + "="*80)
    print("ИТОГ")
    print("="*80)

    if token_data:
        print("[OK] Токен успешно получен!")
        token = token_data.get("token") or token_data.get("password") or token_data.get("access_token")
        if token:
            print(f"\nТокен: {token}")
            print(f"\nСохраните его в .env:")
            print(f"CALENDAR_TOKEN={token}")
    elif has_access:
        print("[OK] Административный токен работает для Calendar API!")
        print(f"\nИспользуйте существующий токен: YANDEX_ADMIN_TOKEN")
    else:
        print("[INFO] Не удалось получить токен для календаря")
        print("\nВозможные причины:")
        print("  1. API не поддерживает создание токенов для календаря")
        print("  2. Административный токен уже имеет нужные права")
        print("  3. Нужен другой метод авторизации")


if __name__ == "__main__":
    main()
