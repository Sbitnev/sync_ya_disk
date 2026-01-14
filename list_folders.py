"""
Вывод всех папок в корне Яндекс.Диска организации
Использует административный токен для доступа к диску организации
"""
import os
import requests
from dotenv import load_dotenv


def get_root_folders(token):
    """
    Получает список всех папок в корневом каталоге диска

    Args:
        token: Токен доступа к API Яндекс.Диска

    Returns:
        list: Список папок с их метаданными
    """
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {
        "Authorization": f"OAuth {token}"
    }
    params = {
        "path": "/",  # Корневой каталог
        "limit": 1000,  # Максимальное количество элементов
        "fields": "_embedded.items.name,_embedded.items.type,_embedded.items.path,_embedded.items.created,_embedded.items.modified"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        items = data.get("_embedded", {}).get("items", [])

        # Фильтруем только папки (type == "dir")
        folders = [item for item in items if item.get("type") == "dir"]

        return folders

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Ответ сервера: {e.response.text}")
        return []


def print_folders(folders):
    """
    Красиво выводит список папок

    Args:
        folders: Список папок для вывода
    """
    if not folders:
        print("\nПапки не найдены или нет доступа к диску")
        return

    print(f"\n{'='*80}")
    print(f"Найдено папок в корневом каталоге: {len(folders)}")
    print(f"{'='*80}\n")

    for i, folder in enumerate(folders, 1):
        name = folder.get("name", "Без имени")
        path = folder.get("path", "")
        created = folder.get("created", "")
        modified = folder.get("modified", "")

        print(f"{i}. {name}")
        print(f"   Путь: {path}")
        if created:
            print(f"   Создана: {created}")
        if modified:
            print(f"   Изменена: {modified}")
        print()


def main():
    # Загружаем переменные окружения
    load_dotenv()

    token = os.getenv("Token")

    if not token:
        print("ОШИБКА: Не найден токен в .env файле")
        print("Убедитесь, что в .env есть строка: Token=ваш_токен")
        return

    print("Получение списка папок из корневого каталога...")

    folders = get_root_folders(token)
    print_folders(folders)

    # Дополнительная информация
    if folders:
        print(f"{'='*80}")
        print("Список имен папок (для копирования):")
        print(f"{'='*80}")
        for folder in folders:
            print(f"  - {folder.get('name')}")


if __name__ == "__main__":
    main()
