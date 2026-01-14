"""
Получение токена пользователя через административный API Яндекс 360
"""
import os
import requests
import json
from dotenv import load_dotenv


def get_service_applications(admin_token, org_id):
    """Получает список доступных сервисных приложений"""
    url = f"https://api360.yandex.net/security/v1/org/{org_id}/service_applications"
    headers = {
        "Authorization": f"OAuth {admin_token}",
        "Content-Type": "application/json"
    }

    try:
        print("Получение списка доступных приложений...")
        response = requests.get(url, headers=headers)

        print(f"Статус: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("\n" + "="*80)
            print("ДОСТУПНЫЕ СЕРВИСНЫЕ ПРИЛОЖЕНИЯ:")
            print("="*80)
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return data
        else:
            print(f"Ошибка: {response.status_code}")
            print(f"Ответ: {response.text}")
            return None

    except Exception as e:
        print(f"Ошибка: {e}")
        return None


def create_user_token(admin_token, org_id, user_id, scopes):
    """Создает токен для пользователя с указанными правами"""
    url = f"https://api360.yandex.net/security/v1/org/{org_id}/user_tokens"
    headers = {
        "Authorization": f"OAuth {admin_token}",
        "Content-Type": "application/json"
    }
    data = {
        "userId": user_id,
        "scopes": scopes
    }

    try:
        print(f"\nСоздание токена для пользователя {user_id}...")
        print(f"Права: {', '.join(scopes)}")

        response = requests.post(url, headers=headers, json=data)

        print(f"Статус: {response.status_code}")

        if response.status_code in [200, 201]:
            result = response.json()
            print("\n[OK] Токен успешно создан!")
            return result
        else:
            print(f"[ERROR] Ошибка создания токена: {response.status_code}")
            print(f"Ответ: {response.text}")
            return None

    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        return None


def get_user_id_by_email(admin_token, org_id, email):
    """Получает ID пользователя по email"""
    url = f"https://api360.yandex.net/directory/v1/org/{org_id}/users"
    headers = {
        "Authorization": f"OAuth {admin_token}",
        "Content-Type": "application/json"
    }
    params = {
        "email": email
    }

    try:
        print(f"Поиск пользователя {email}...")
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            users = data.get("users", [])

            if users:
                user = users[0]
                user_id = user.get("id")
                print(f"[OK] Пользователь найден: ID={user_id}")
                return user_id
            else:
                print(f"[ERROR] Пользователь не найден")
                return None
        else:
            print(f"[ERROR] Ошибка: {response.status_code}")
            print(f"Ответ: {response.text}")
            return None

    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        return None


def list_user_folders(user_token):
    """Выводит список папок на диске пользователя"""
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {
        "Authorization": f"OAuth {user_token}"
    }
    params = {
        "path": "/",
        "limit": 1000,
        "fields": "_embedded.items.name,_embedded.items.type,_embedded.items.path,_embedded.items.created,_embedded.items.modified"
    }

    try:
        print("\nПолучение списка папок на диске пользователя...")
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            items = data.get("_embedded", {}).get("items", [])
            folders = [item for item in items if item.get("type") == "dir"]

            print("\n" + "="*80)
            print(f"ПАПКИ НА ДИСКЕ ПОЛЬЗОВАТЕЛЯ (всего: {len(folders)}):")
            print("="*80 + "\n")

            for i, folder in enumerate(folders, 1):
                name = folder.get("name", "Без имени")
                path = folder.get("path", "")
                created = folder.get("created", "")

                print(f"{i}. {name}")
                print(f"   Путь: {path}")
                if created:
                    print(f"   Создана: {created}")
                print()

            return folders
        else:
            print(f"[ERROR] Ошибка: {response.status_code}")
            print(f"Ответ: {response.text}")
            return None

    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        return None


def main():
    load_dotenv()

    admin_token = os.getenv("YANDEX_ADMIN_TOKEN")
    org_id = os.getenv("YANDEX_ORG_ID")
    target_email = "tn@imprice.ai"

    if not admin_token or not org_id:
        print("[ERROR] Не найдены YANDEX_ADMIN_TOKEN или YANDEX_ORG_ID в .env")
        return

    print("="*80)
    print("ПОЛУЧЕНИЕ ТОКЕНА ПОЛЬЗОВАТЕЛЯ ЧЕРЕЗ ADMIN API")
    print("="*80)
    print(f"Организация: {org_id}")
    print(f"Целевой пользователь: {target_email}")
    print("="*80 + "\n")

    # Шаг 1: Получаем список приложений
    apps = get_service_applications(admin_token, org_id)

    if not apps:
        print("\n[ERROR] Не удалось получить список приложений")
        # Продолжаем без списка приложений

    # Шаг 2: Получаем ID пользователя
    user_id = get_user_id_by_email(admin_token, org_id, target_email)

    if not user_id:
        print("\n[ERROR] Не удалось найти пользователя")
        return

    # Шаг 3: Создаем токен с правами на чтение диска
    # Пробуем разные варианты прав
    scopes_options = [
        ["cloud_api:disk.read", "cloud_api:disk.write"],
        ["yadisk:disk.read", "yadisk:disk.write"],
        ["disk:read", "disk:write"],
    ]

    user_token_data = None
    for scopes in scopes_options:
        user_token_data = create_user_token(admin_token, org_id, user_id, scopes)
        if user_token_data:
            break

    if not user_token_data:
        print("\n[ERROR] Не удалось создать токен пользователя")
        print("\nВозможные причины:")
        print("  1. У администратора нет прав на создание токенов пользователей")
        print("  2. API Яндекс 360 не поддерживает создание токенов для диска")
        print("  3. Неправильный формат запроса или scope")
        return

    # Получаем токен из ответа
    user_token = user_token_data.get("token")

    if not user_token:
        print("\n[ERROR] Токен не найден в ответе")
        print(f"Полный ответ: {user_token_data}")
        return

    print(f"\n[OK] Токен получен: {user_token[:20]}...")

    # Сохраняем токен в переменную окружения
    print(f"\nСохраните токен в .env:")
    print(f"USER_TOKEN={user_token}")

    # Шаг 4: Используем токен для получения списка папок
    folders = list_user_folders(user_token)

    if folders:
        print("\n" + "="*80)
        print("[OK] УСПЕШНО ПОЛУЧЕН ДОСТУП К ДИСКУ ПОЛЬЗОВАТЕЛЯ!")
        print("="*80)


if __name__ == "__main__":
    main()
