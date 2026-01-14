"""
Вывод всех папок пользователя tn@imprice.ai
"""
import os
import requests
from dotenv import load_dotenv


def list_user_folders(token, path="/"):
    """Получает список папок на диске пользователя"""
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {"Authorization": f"OAuth {token}"}
    params = {
        "path": path,
        "limit": 1000,
        "fields": "_embedded.items.name,_embedded.items.type,_embedded.items.path,_embedded.items.created,_embedded.items.modified,_embedded.items.size"
    }

    try:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            items = data.get("_embedded", {}).get("items", [])
            folders = [item for item in items if item.get("type") == "dir"]
            return folders
        else:
            print(f"[ERROR] Ошибка: {response.status_code}")
            print(f"Ответ: {response.text}")
            return []

    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        return []


def format_size(size):
    """Форматирует размер"""
    if size is None or size == 0:
        return ""
    for unit in ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} ПБ"


def main():
    load_dotenv()

    # Используем полученный токен
    token = "2.1130000057842996.997486.1768381487.1768377887976.1.0.11609667.BSFzzc69Js6_ATwI.E98i9pzJ3MdPQcY7o23pdFoLvgwPKSyzcwj_QFeIg91zeNfXtZyIMijTGQJArg.cm377ZoGRhNjmX04cOlvgw"

    print("="*80)
    print("ПАПКИ НА ДИСКЕ ПОЛЬЗОВАТЕЛЯ TN@IMPRICE.AI")
    print("="*80)
    print()

    # Получаем папки в корне
    folders = list_user_folders(token, "/")

    if not folders:
        print("[INFO] Папки не найдены")
        return

    print(f"Всего папок в корне: {len(folders)}\n")

    for i, folder in enumerate(folders, 1):
        name = folder.get("name", "Без имени")
        path = folder.get("path", "")
        created = folder.get("created", "")

        print(f"{i}. {name}")
        print(f"   Путь: {path}")
        if created:
            print(f"   Создана: {created[:10]}")
        print()

    print("="*80)
    print("СПИСОК ИМЕН ПАПОК (для копирования):")
    print("="*80)
    for folder in folders:
        print(f"  - {folder.get('name')}")


if __name__ == "__main__":
    main()
