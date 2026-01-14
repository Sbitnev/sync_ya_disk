"""
Доступ к диску пользователя tn@imprice.ai
"""
import os
import requests
from dotenv import load_dotenv


def list_folders_with_uid(admin_token, user_id):
    """Получает папки с указанием UID пользователя"""
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {
        "Authorization": f"OAuth {admin_token}",
        "X-Uid": str(user_id)
    }
    params = {
        "path": "/",
        "limit": 1000,
        "fields": "_embedded.items.name,_embedded.items.type,_embedded.items.path,_embedded.items.public_url,_embedded.items.public_key,_embedded.items.owner"
    }

    try:
        print(f"Получение папок для пользователя {user_id}...")
        response = requests.get(url, headers=headers, params=params)

        print(f"Статус: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            items = data.get("_embedded", {}).get("items", [])
            folders = [item for item in items if item.get("type") == "dir"]

            print(f"\n[OK] Найдено папок: {len(folders)}\n")

            for i, folder in enumerate(folders, 1):
                name = folder.get("name")
                path = folder.get("path")
                public_url = folder.get("public_url")
                public_key = folder.get("public_key")
                owner = folder.get("owner", {})

                print(f"{i}. {name}")
                print(f"   Путь: {path}")

                if owner:
                    print(f"   Владелец: {owner.get('login', 'Неизвестно')}")

                if public_url:
                    print(f"   Публичная ссылка: {public_url}")

                if public_key:
                    # Проверяем, совпадает ли с нашей целевой папкой
                    target_key = "bNTp52Q+YweSHhqx02ejDjpfggJx49cgALFn0JHUhswQWLskVnK/47Nry/5PmKVjDqZvSgIch5AN9ddz7ydViQ=="
                    if public_key == target_key:
                        print(f"   *** ЭТО НАША ЦЕЛЕВАЯ ПАПКА! ***")

                print()

            return folders
        else:
            print(f"Ошибка: {response.status_code}")
            print(f"Ответ: {response.text}")
            return None

    except Exception as e:
        print(f"Ошибка: {e}")
        return None


def check_folder_access(admin_token, user_id, folder_path):
    """Проверяет доступ к конкретной папке пользователя"""
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {
        "Authorization": f"OAuth {admin_token}",
        "X-Uid": str(user_id)
    }
    params = {
        "path": folder_path,
        "limit": 100,
        "fields": "_embedded.items.name,_embedded.items.type,name,path,type,public_url"
    }

    try:
        print(f"\nПроверка доступа к папке: {folder_path}")
        response = requests.get(url, headers=headers, params=params)

        print(f"Статус: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Доступ есть!")
            print(f"  Имя: {data.get('name')}")
            print(f"  Тип: {data.get('type')}")
            print(f"  Публичная: {data.get('public_url', 'Нет')}")

            items = data.get("_embedded", {}).get("items", [])
            if items:
                print(f"  Содержимое ({len(items)} элементов):")
                for item in items[:10]:
                    item_type = "[DIR]" if item.get("type") == "dir" else "[FILE]"
                    print(f"    {item_type} {item.get('name')}")

            return True
        elif response.status_code == 404:
            print(f"[INFO] Папка не найдена")
            return False
        else:
            print(f"Ошибка: {response.status_code}")
            print(f"Ответ: {response.text}")
            return False

    except Exception as e:
        print(f"Ошибка: {e}")
        return False


def main():
    load_dotenv()

    admin_token = os.getenv("YANDEX_ADMIN_TOKEN")
    user_id = "1130000057842996"  # ID tn@imprice.ai

    print("="*80)
    print("ДОСТУП К ДИСКУ ПОЛЬЗОВАТЕЛЯ TN@IMPRICE.AI")
    print("="*80)
    print(f"User ID: {user_id}")
    print("="*80 + "\n")

    # Получаем список папок
    folders = list_folders_with_uid(admin_token, user_id)

    if folders:
        # Ищем папку "Клиенты" или "Проекты"
        for folder in folders:
            name = folder.get("name", "").lower()
            if "клиент" in name or "проект" in name:
                print(f"\n[НАЙДЕНО] Возможная целевая папка: {folder.get('name')}")
                print(f"Путь: {folder.get('path')}")

                # Проверяем доступ к подпапкам
                check_folder_access(admin_token, user_id, folder.get("path"))

        # Пробуем прямой доступ к папке "Клиенты"
        print("\n" + "="*80)
        print("ПРЯМАЯ ПРОВЕРКА ПАПКИ 'КЛИЕНТЫ'")
        print("="*80)
        check_folder_access(admin_token, user_id, "/Клиенты")

    print("\n" + "="*80)
    print("ИТОГ")
    print("="*80)


if __name__ == "__main__":
    main()
