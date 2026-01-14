"""
Получение токена через сервисное приложение Яндекс 360
"""
import os
import requests
import json
from dotenv import load_dotenv


def get_app_token(admin_token, org_id, app_id, user_id):
    """Получает токен приложения для пользователя"""
    # Пробуем разные endpoints
    endpoints = [
        f"https://api360.yandex.net/security/v1/org/{org_id}/service_applications/{app_id}/tokens",
        f"https://api360.yandex.net/security/v1/org/{org_id}/service_applications/{app_id}/user_tokens",
        f"https://api360.yandex.net/admin/v1/org/{org_id}/service_applications/{app_id}/tokens",
    ]

    headers = {
        "Authorization": f"OAuth {admin_token}",
        "Content-Type": "application/json"
    }

    for url in endpoints:
        print(f"\nПопытка: {url}")

        # Пробуем POST
        data = {
            "userId": user_id
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            print(f"POST Статус: {response.status_code}")

            if response.status_code in [200, 201]:
                result = response.json()
                print(f"[OK] Успех!")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return result
            else:
                print(f"Ответ: {response.text}")

            # Пробуем GET
            response = requests.get(url, headers=headers, params={"userId": user_id})
            print(f"GET Статус: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"[OK] Успех!")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return result
            else:
                print(f"Ответ: {response.text}")

        except Exception as e:
            print(f"Ошибка: {e}")

    return None


def enable_app_for_user(admin_token, org_id, app_id, user_id):
    """Включает приложение для пользователя"""
    url = f"https://api360.yandex.net/security/v1/org/{org_id}/service_applications/{app_id}/users"
    headers = {
        "Authorization": f"OAuth {admin_token}",
        "Content-Type": "application/json"
    }
    data = {
        "userId": user_id
    }

    try:
        print(f"\nПодключение приложения {app_id} к пользователю {user_id}...")
        response = requests.post(url, headers=headers, json=data)
        print(f"Статус: {response.status_code}")

        if response.status_code in [200, 201, 204]:
            print("[OK] Приложение успешно подключено!")
            return True
        elif response.status_code == 409:
            print("[INFO] Приложение уже подключено")
            return True
        else:
            print(f"Ответ: {response.text}")
            return False

    except Exception as e:
        print(f"Ошибка: {e}")
        return False


def get_app_info(admin_token, org_id, app_id):
    """Получает информацию о приложении"""
    url = f"https://api360.yandex.net/security/v1/org/{org_id}/service_applications/{app_id}"
    headers = {
        "Authorization": f"OAuth {admin_token}",
        "Content-Type": "application/json"
    }

    try:
        print(f"\nПолучение информации о приложении {app_id}...")
        response = requests.get(url, headers=headers)
        print(f"Статус: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return data
        else:
            print(f"Ответ: {response.text}")
            return None

    except Exception as e:
        print(f"Ошибка: {e}")
        return None


def try_impersonation_token(admin_token, org_id, user_id):
    """Пытается получить токен для имперсонации пользователя"""
    url = f"https://api360.yandex.net/admin/v1/org/{org_id}/users/{user_id}/token"
    headers = {
        "Authorization": f"OAuth {admin_token}",
        "Content-Type": "application/json"
    }

    try:
        print(f"\nПопытка получить токен имперсонации для пользователя {user_id}...")
        response = requests.post(url, headers=headers)
        print(f"Статус: {response.status_code}")

        if response.status_code in [200, 201]:
            data = response.json()
            print("[OK] Токен получен!")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return data
        else:
            print(f"Ответ: {response.text}")
            return None

    except Exception as e:
        print(f"Ошибка: {e}")
        return None


def main():
    load_dotenv()

    admin_token = os.getenv("YANDEX_ADMIN_TOKEN")
    org_id = os.getenv("YANDEX_ORG_ID")
    app_id = "bdb90dee90fe49329c24535283606260"  # ID приложения с правами на диск
    user_id = "780891246"  # ID пользователя tn@imprice.ai

    if not admin_token or not org_id:
        print("[ERROR] Не найдены переменные окружения")
        return

    print("="*80)
    print("ПОЛУЧЕНИЕ ТОКЕНА ЧЕРЕЗ СЕРВИСНОЕ ПРИЛОЖЕНИЕ")
    print("="*80)
    print(f"Организация: {org_id}")
    print(f"Приложение: {app_id}")
    print(f"Пользователь: {user_id} (tn@imprice.ai)")
    print("="*80)

    # Получаем информацию о приложении
    app_info = get_app_info(admin_token, org_id, app_id)

    # Подключаем приложение к пользователю
    enabled = enable_app_for_user(admin_token, org_id, app_id, user_id)

    token_data = None
    if enabled:
        # Пытаемся получить токен приложения
        token_data = get_app_token(admin_token, org_id, app_id, user_id)

        if token_data:
            print("\n" + "="*80)
            print("[OK] ТОКЕН ПОЛУЧЕН!")
            print("="*80)
        else:
            print("\n[INFO] Не удалось получить токен через приложение")

    # Пытаемся получить токен имперсонации
    impersonation_token = try_impersonation_token(admin_token, org_id, user_id)

    if not token_data and not impersonation_token:
        print("\n" + "="*80)
        print("[INFO] ВОЗМОЖНЫЕ ВАРИАНТЫ:")
        print("="*80)
        print("1. API Яндекс 360 не поддерживает получение токенов для других пользователей")
        print("2. Используйте административный токен напрямую (он может иметь доступ к дискам всех пользователей)")
        print("3. Попросите пользователя tn@imprice.ai создать токен и расшарить папку")
        print("\nПопробуем использовать административный токен напрямую...")

        # Пробуем использовать административный токен для доступа к диску пользователя
        from get_user_token import list_user_folders

        print("\nПопытка доступа к диску с административным токеном...")
        folders = list_user_folders(admin_token)

        if folders:
            print("\n[OK] Административный токен работает для доступа к дискам!")


if __name__ == "__main__":
    main()
