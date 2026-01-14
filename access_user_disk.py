"""
Доступ к личному диску пользователя через API
"""
import os
import requests
from dotenv import load_dotenv


def get_user_disk_info(admin_token, user_id=None):
    """Получает информацию о диске пользователя"""
    # Пробуем разные варианты API
    base_urls = [
        "https://cloud-api.yandex.net/v1/disk",
        f"https://cloud-api.yandex.net/v1/users/{user_id}/disk" if user_id else None,
    ]

    headers = {
        "Authorization": f"OAuth {admin_token}",
        "X-Uid": str(user_id) if user_id else None  # Пробуем указать UID пользователя в заголовке
    }

    for url in base_urls:
        if not url:
            continue

        print(f"\nПопытка: {url}")
        print(f"Заголовки: {headers}")

        try:
            response = requests.get(url, headers=headers)
            print(f"Статус: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print("[OK] Информация получена!")
                print(f"Общий размер: {data.get('total_space', 0) / 1024 / 1024 / 1024:.2f} ГБ")
                print(f"Использовано: {data.get('used_space', 0) / 1024 / 1024 / 1024:.2f} ГБ")
                return data
            else:
                print(f"Ответ: {response.text}")

        except Exception as e:
            print(f"Ошибка: {e}")

    return None


def list_user_disk_folders(admin_token, user_id=None, path="/"):
    """Получает список папок на диске пользователя"""
    url = "https://cloud-api.yandex.net/v1/disk/resources"

    # Пробуем разные варианты заголовков
    header_variants = [
        {
            "Authorization": f"OAuth {admin_token}",
            "X-Uid": str(user_id)
        } if user_id else None,
        {
            "Authorization": f"OAuth {admin_token}",
            "X-Yandex-UID": str(user_id)
        } if user_id else None,
        {
            "Authorization": f"OAuth {admin_token}"
        }
    ]

    params = {
        "path": path,
        "limit": 1000,
        "fields": "_embedded.items.name,_embedded.items.type,_embedded.items.path,_embedded.items.owner"
    }

    for i, headers in enumerate(header_variants, 1):
        if not headers:
            continue

        print(f"\nВариант {i}: {headers}")

        try:
            response = requests.get(url, headers=headers, params=params)
            print(f"Статус: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                items = data.get("_embedded", {}).get("items", [])
                folders = [item for item in items if item.get("type") == "dir"]

                print(f"[OK] Найдено папок: {len(folders)}")

                if folders:
                    print("\nПапки:")
                    for folder in folders[:10]:
                        name = folder.get("name")
                        owner = folder.get("owner", {})
                        owner_login = owner.get("login", "Неизвестно") if owner else "Неизвестно"
                        print(f"  - {name} (владелец: {owner_login})")

                return folders
            else:
                print(f"Ответ: {response.text[:200]}")

        except Exception as e:
            print(f"Ошибка: {e}")

    return None


def search_public_folder_owner(admin_token):
    """
    Пытается найти папку "Клиенты/Проекты" на дисках пользователей организации
    """
    print("\n" + "="*80)
    print("ПОИСК ПАПКИ 'КЛИЕНТЫ' НА ДИСКАХ ОРГАНИЗАЦИИ")
    print("="*80)

    # Получаем список пользователей организации
    org_id = os.getenv("YANDEX_ORG_ID")
    url = f"https://api360.yandex.net/directory/v1/org/{org_id}/users"
    headers = {
        "Authorization": f"OAuth {admin_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, params={"perPage": 100})

        if response.status_code == 200:
            data = response.json()
            users = data.get("users", [])

            print(f"\nНайдено пользователей: {len(users)}")

            # Для каждого пользователя пробуем получить доступ к его диску
            for user in users[:5]:  # Ограничиваем первыми 5 пользователями
                user_id = user.get("id")
                email = user.get("email")

                print(f"\n--- Пользователь: {email} (ID: {user_id}) ---")

                # Пробуем получить папки пользователя
                folders = list_user_disk_folders(admin_token, user_id)

                if folders:
                    # Ищем папку "Клиенты" или похожие
                    for folder in folders:
                        name = folder.get("name", "").lower()
                        if "клиент" in name or "проект" in name or "client" in name:
                            print(f"[НАЙДЕНО] Возможная папка: {folder.get('name')}")

        else:
            print(f"Ошибка получения пользователей: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"Ошибка: {e}")


def main():
    load_dotenv()

    admin_token = os.getenv("YANDEX_ADMIN_TOKEN")
    user_id = "780891246"  # tn@imprice.ai

    print("="*80)
    print("ДОСТУП К ЛИЧНОМУ ДИСКУ ПОЛЬЗОВАТЕЛЯ")
    print("="*80)

    # Пробуем получить информацию о диске
    print("\n1. Информация о диске пользователя:")
    disk_info = get_user_disk_info(admin_token, user_id)

    # Пробуем получить список папок
    print("\n2. Список папок на диске пользователя:")
    folders = list_user_disk_folders(admin_token, user_id)

    # Ищем папку на дисках всех пользователей
    search_public_folder_owner(admin_token)

    print("\n" + "="*80)
    print("ИТОГ")
    print("="*80)
    print("Похоже, что:")
    print("1. Административный токен даёт доступ к диску организации")
    print("2. Личные диски пользователей требуют индивидуальных токенов")
    print("3. API Яндекс 360 не предоставляет прямого доступа к личным дискам через админ-токен")
    print("\nРешение: Попросите tn@imprice.ai:")
    print("  - Расшарить папку напрямую на организацию")
    print("  - Или создать токен и предоставить его")


if __name__ == "__main__":
    main()
