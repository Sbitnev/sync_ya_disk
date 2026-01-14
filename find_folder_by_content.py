"""
Поиск папки на диске организации по содержимому
"""
import os
import requests
from dotenv import load_dotenv


def search_folders(token, folder_path="/"):
    """Ищет все папки в указанном пути"""
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {"Authorization": f"OAuth {token}"}
    params = {
        "path": folder_path,
        "limit": 1000,
        "fields": "_embedded.items.name,_embedded.items.type,_embedded.items.path"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            items = data.get("_embedded", {}).get("items", [])
            return [item for item in items if item.get("type") == "dir"]
        return []
    except Exception as e:
        print(f"Ошибка: {e}")
        return []


def get_folder_contents(token, folder_path):
    """Получает список подпапок в указанной папке"""
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {"Authorization": f"OAuth {token}"}
    params = {
        "path": folder_path,
        "limit": 100,
        "fields": "_embedded.items.name,_embedded.items.type"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            items = data.get("_embedded", {}).get("items", [])
            folders = [item.get("name") for item in items if item.get("type") == "dir"]
            return folders
        return []
    except Exception:
        return []


def main():
    load_dotenv()
    token = os.getenv("Token")

    if not token:
        print("Токен не найден")
        return

    # Ищем папки с характерными подпапками из публичной папки
    target_subfolders = ["DPD", "KDL", "SOKOLOV", "PiterOils"]

    print("="*80)
    print("Поиск папки по содержимому на диске организации")
    print("="*80)
    print(f"\nИщем папку, содержащую подпапки: {', '.join(target_subfolders)}")
    print("\nПроверка корневого каталога...")

    # Получаем папки в корне
    root_folders = search_folders(token, "/")

    print(f"Найдено папок в корне: {len(root_folders)}\n")

    for folder in root_folders:
        folder_name = folder.get("name")
        folder_path = folder.get("path")

        print(f"Проверка: {folder_name}")

        # Получаем содержимое папки
        subfolders = get_folder_contents(token, folder_path)

        # Проверяем, есть ли характерные подпапки
        matches = [sf for sf in target_subfolders if sf in subfolders]

        if len(matches) >= 3:  # Если найдено 3+ совпадения
            print(f"  [НАЙДЕНО!] Совпадений: {len(matches)}/{len(target_subfolders)}")
            print(f"  Путь: {folder_path}")
            print(f"  Подпапки ({len(subfolders)}): {', '.join(subfolders[:20])}")
            print()
        elif matches:
            print(f"  Частичное совпадение: {len(matches)}/{len(target_subfolders)}")
        else:
            print(f"  Нет совпадений")

    print("\n" + "="*80)


if __name__ == "__main__":
    main()
