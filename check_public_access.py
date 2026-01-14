"""
Проверка доступа к публичной папке через административный токен
"""
import os
import requests
from dotenv import load_dotenv


def check_public_folder_access(token, public_url):
    """
    Проверяет доступ к публичной папке

    Args:
        token: Токен доступа к API Яндекс.Диска
        public_url: URL публичной папки

    Returns:
        dict: Информация о папке или None в случае ошибки
    """
    # API endpoint для работы с публичными ресурсами
    url = "https://cloud-api.yandex.net/v1/disk/public/resources"
    headers = {
        "Authorization": f"OAuth {token}"
    }
    params = {
        "public_key": public_url,
        "limit": 20,  # Получим первые 20 элементов для проверки
        "fields": "name,type,public_key,owner,created,modified,size,_embedded.items.name,_embedded.items.type,_embedded.items.size"
    }

    try:
        print(f"Проверка доступа к: {public_url}")
        print("Отправка запроса к API...")

        response = requests.get(url, headers=headers, params=params)

        print(f"Статус ответа: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            return data
        elif response.status_code == 401:
            print("ОШИБКА: Токен недействителен или не авторизован")
            return None
        elif response.status_code == 404:
            print("ОШИБКА: Публичная папка не найдена или недоступна")
            return None
        elif response.status_code == 403:
            print("ОШИБКА: Доступ запрещен")
            return None
        else:
            print(f"ОШИБКА: {response.status_code}")
            print(f"Ответ сервера: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к API: {e}")
        return None


def format_size(size_bytes):
    """Форматирует размер в читаемый вид"""
    if size_bytes is None:
        return "Неизвестно"

    for unit in ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} ПБ"


def print_folder_info(data):
    """
    Выводит информацию о публичной папке

    Args:
        data: Данные папки из API
    """
    print("\n" + "="*80)
    print("ДОСТУП К ПУБЛИЧНОЙ ПАПКЕ ПОЛУЧЕН!")
    print("="*80 + "\n")

    print(f"Название: {data.get('name', 'Без названия')}")
    print(f"Тип: {data.get('type', 'Неизвестно')}")

    owner = data.get('owner', {})
    if owner:
        print(f"Владелец: {owner.get('display_name', 'Неизвестно')}")

    if 'created' in data:
        print(f"Создана: {data['created']}")
    if 'modified' in data:
        print(f"Изменена: {data['modified']}")

    size = data.get('size')
    if size:
        print(f"Размер: {format_size(size)}")

    # Проверяем содержимое папки
    embedded = data.get('_embedded', {})
    items = embedded.get('items', [])

    if items:
        print(f"\n{'='*80}")
        print(f"Содержимое папки (первые {len(items)} элементов):")
        print(f"{'='*80}\n")

        for i, item in enumerate(items, 1):
            item_type = "[DIR]" if item.get('type') == 'dir' else "[FILE]"
            item_name = item.get('name', 'Без имени')
            item_size = format_size(item.get('size')) if item.get('type') == 'file' else "папка"

            print(f"{i}. {item_type} {item_name} ({item_size})")
    else:
        print("\nПапка пустая или не содержит элементов")

    print("\n" + "="*80)


def try_save_to_disk(token, public_url):
    """
    Пытается сохранить публичную папку на свой диск

    Args:
        token: Токен доступа
        public_url: URL публичной папки

    Returns:
        bool: True если успешно, False если нет
    """
    url = "https://cloud-api.yandex.net/v1/disk/public/resources/save-to-disk"
    headers = {
        "Authorization": f"OAuth {token}"
    }
    params = {
        "public_key": public_url,
        "path": "/test_public_folder_access"  # Тестовый путь
    }

    try:
        print("\nПопытка сохранить папку на диск (для проверки прав)...")
        response = requests.post(url, headers=headers, params=params)

        if response.status_code == 201:
            print("[OK] Папка успешно сохранена! У токена есть права на сохранение.")
            # Удаляем тестовую папку
            delete_url = "https://cloud-api.yandex.net/v1/disk/resources"
            delete_params = {"path": "/test_public_folder_access", "permanently": "true"}
            requests.delete(delete_url, headers=headers, params=delete_params)
            print("     (тестовая папка удалена)")
            return True
        elif response.status_code == 409:
            print("[OK] Папка уже существует на диске (возможно, сохранена ранее)")
            return True
        elif response.status_code == 403:
            print("[ERROR] Владелец запретил сохранение папки на другие диски")
            return False
        else:
            print(f"[ERROR] Не удалось сохранить: {response.status_code}")
            print(f"        Ответ: {response.text}")
            return False

    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        return False


def main():
    load_dotenv()

    token = os.getenv("Token")

    if not token:
        print("ОШИБКА: Не найден токен в .env файле")
        return

    # URL публичной папки
    public_url = "https://disk.yandex.ru/d/_JeaJNmm6UeQVA"

    # Проверяем доступ
    folder_data = check_public_folder_access(token, public_url)

    if folder_data:
        print_folder_info(folder_data)

        # Пытаемся сохранить на диск
        can_save = try_save_to_disk(token, public_url)

        print("\n" + "="*80)
        print("ИТОГ:")
        print("="*80)
        print(f"[OK] Чтение публичной папки: ДА")
        print(f"[{'OK' if can_save else 'ERROR'}] Сохранение на диск: {'ДА' if can_save else 'НЕТ'}")
        print("="*80)
    else:
        print("\n" + "="*80)
        print("НЕТ ДОСТУПА К ПУБЛИЧНОЙ ПАПКЕ")
        print("="*80)


if __name__ == "__main__":
    main()
