"""
Получение токена пользователя через token exchange
"""
import os
import requests
from dotenv import load_dotenv


def get_user_token_by_uid(client_id, client_secret, user_id):
    """Получает токен пользователя по UID через token exchange"""
    url = "https://oauth.yandex.ru/token"

    data = {
        'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
        'client_id': client_id,
        'client_secret': client_secret,
        'subject_token': str(user_id),
        'subject_token_type': 'urn:yandex:params:oauth:token-type:uid'
    }

    try:
        print("="*80)
        print("ПОЛУЧЕНИЕ ТОКЕНА ЧЕРЕЗ TOKEN EXCHANGE (UID)")
        print("="*80)
        print(f"Client ID: {client_id}")
        print(f"User ID: {user_id}")
        print(f"URL: {url}")
        print()

        response = requests.post(url, data=data)

        print(f"Статус: {response.status_code}")
        print(f"Ответ: {response.text}")
        print()

        if response.status_code == 200:
            result = response.json()
            token = result.get('access_token')

            if token:
                print("[OK] ТОКЕН УСПЕШНО ПОЛУЧЕН!")
                print(f"Access Token: {token}")
                print(f"Token Type: {result.get('token_type', 'Bearer')}")

                if 'expires_in' in result:
                    print(f"Expires in: {result['expires_in']} секунд")

                return token
            else:
                print("[ERROR] Токен не найден в ответе")
                return None
        else:
            print(f"[ERROR] Не удалось получить токен")
            return None

    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_user_token_by_email(client_id, client_secret, user_email):
    """Получает токен пользователя по email через token exchange"""
    url = "https://oauth.yandex.ru/token"

    data = {
        'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
        'client_id': client_id,
        'client_secret': client_secret,
        'subject_token': user_email,
        'subject_token_type': 'urn:yandex:params:oauth:token-type:email'
    }

    try:
        print("="*80)
        print("ПОЛУЧЕНИЕ ТОКЕНА ЧЕРЕЗ TOKEN EXCHANGE (EMAIL)")
        print("="*80)
        print(f"Client ID: {client_id}")
        print(f"User Email: {user_email}")
        print(f"URL: {url}")
        print()

        response = requests.post(url, data=data)

        print(f"Статус: {response.status_code}")
        print(f"Ответ: {response.text}")
        print()

        if response.status_code == 200:
            result = response.json()
            token = result.get('access_token')

            if token:
                print("[OK] ТОКЕН УСПЕШНО ПОЛУЧЕН!")
                print(f"Access Token: {token}")
                print(f"Token Type: {result.get('token_type', 'Bearer')}")

                if 'expires_in' in result:
                    print(f"Expires in: {result['expires_in']} секунд")

                return token
            else:
                print("[ERROR] Токен не найден в ответе")
                return None
        else:
            print(f"[ERROR] Не удалось получить токен")
            return None

    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_token_with_disk(token):
    """Тестирует токен на доступ к диску"""
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {
        "Authorization": f"OAuth {token}"
    }
    params = {
        "path": "/",
        "limit": 10
    }

    try:
        print("\n" + "="*80)
        print("ТЕСТИРОВАНИЕ ТОКЕНА НА ДОСТУП К ДИСКУ")
        print("="*80)

        response = requests.get(url, headers=headers, params=params)

        print(f"Статус: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            items = data.get("_embedded", {}).get("items", [])
            folders = [item for item in items if item.get("type") == "dir"]

            print(f"[OK] Доступ к диску есть!")
            print(f"Найдено папок: {len(folders)}")

            if folders:
                print("\nПапки:")
                for folder in folders:
                    print(f"  - {folder.get('name')}")

            return True
        else:
            print(f"[ERROR] Нет доступа к диску")
            print(f"Ответ: {response.text}")
            return False

    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        return False


def main():
    load_dotenv()

    client_id = os.getenv("ClientID")
    client_secret = os.getenv("Client_secret")
    user_id = "1130000057842996"  # tn@imprice.ai
    user_email = "tn@imprice.ai"

    if not client_id or not client_secret:
        print("[ERROR] Не найдены ClientID или Client_secret в .env")
        return

    # Попытка 1: Получение токена по UID
    token = get_user_token_by_uid(client_id, client_secret, user_id)

    if not token:
        # Попытка 2: Получение токена по Email
        token = get_user_token_by_email(client_id, client_secret, user_email)

    if token:
        # Тестируем токен
        works = test_token_with_disk(token)

        if works:
            print("\n" + "="*80)
            print("[OK] ТОКЕН РАБОТАЕТ!")
            print("="*80)
            print(f"\nСохраните токен в .env:")
            print(f"USER_TOKEN={token}")

            # Пробуем получить доступ к папке "Клиенты"
            print("\n" + "="*80)
            print("ПРОВЕРКА ДОСТУПА К ПАПКЕ 'КЛИЕНТЫ'")
            print("="*80)

            url = "https://cloud-api.yandex.net/v1/disk/resources"
            headers = {"Authorization": f"OAuth {token}"}
            params = {"path": "/Клиенты", "limit": 100}

            response = requests.get(url, headers=headers, params=params)
            print(f"Статус: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                items = data.get("_embedded", {}).get("items", [])
                print(f"[OK] ДОСТУП К ПАПКЕ 'КЛИЕНТЫ' ЕСТЬ!")
                print(f"Найдено подпапок: {len(items)}")

                for i, item in enumerate(items[:10], 1):
                    print(f"  {i}. {item.get('name')}")
            else:
                print(f"[INFO] Папка 'Клиенты' не найдена или нет доступа")
                print(f"Ответ: {response.text[:200]}")
    else:
        print("\n" + "="*80)
        print("[ERROR] НЕ УДАЛОСЬ ПОЛУЧИТЬ ТОКЕН")
        print("="*80)
        print("\nВозможные причины:")
        print("  1. CLIENT_ID/CLIENT_SECRET не подходят для token exchange")
        print("  2. Сервисное приложение не активировано для пользователя")
        print("  3. У приложения нет прав на token exchange")


if __name__ == "__main__":
    main()
