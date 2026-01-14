"""
Скачивание файла из публичной папки через API
"""
import os
import requests
from dotenv import load_dotenv
from pathlib import Path


def get_public_folder_items(token, public_key, path=""):
    """Получает содержимое публичной папки или подпапки"""
    url = "https://cloud-api.yandex.net/v1/disk/public/resources"
    headers = {"Authorization": f"OAuth {token}"}
    params = {
        "public_key": public_key,
        "path": path,
        "limit": 1000,
        "fields": "_embedded.items.name,_embedded.items.type,_embedded.items.path,_embedded.items.size,_embedded.items.file"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            return data.get("_embedded", {}).get("items", [])
        else:
            print(f"Ошибка получения списка: {response.status_code}")
            print(response.text)
            return []
    except Exception as e:
        print(f"Ошибка: {e}")
        return []


def find_file_in_folder(token, public_key, folder_name, file_name):
    """Ищет файл в указанной подпапке"""
    print(f"Поиск подпапки '{folder_name}'...")

    # Получаем список папок в корне
    items = get_public_folder_items(token, public_key)

    target_folder = None
    for item in items:
        if item.get("type") == "dir" and item.get("name") == folder_name:
            target_folder = item
            break

    if not target_folder:
        print(f"Папка '{folder_name}' не найдена")
        return None

    print(f"Папка найдена: {target_folder.get('path')}")
    print(f"Поиск файла '{file_name}'...")

    # Получаем содержимое подпапки
    folder_path = target_folder.get("path")
    files = get_public_folder_items(token, public_key, folder_path)

    # Ищем нужный файл
    for file_item in files:
        if file_item.get("name") == file_name:
            print(f"Файл найден!")
            print(f"  Имя: {file_item.get('name')}")
            print(f"  Размер: {format_size(file_item.get('size'))}")
            print(f"  Путь: {file_item.get('path')}")
            return file_item

    print(f"Файл '{file_name}' не найден в папке '{folder_name}'")
    print(f"Найдено файлов в папке: {len([f for f in files if f.get('type') == 'file'])}")
    print("Доступные файлы:")
    for f in files[:10]:
        if f.get("type") == "file":
            print(f"  - {f.get('name')}")

    return None


def download_public_file(token, public_key, file_path, save_path):
    """Скачивает файл из публичной папки"""
    url = "https://cloud-api.yandex.net/v1/disk/public/resources/download"
    headers = {"Authorization": f"OAuth {token}"}
    params = {
        "public_key": public_key,
        "path": file_path
    }

    try:
        print(f"\nПолучение ссылки на скачивание...")
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            print(f"Ответ API: {data}")
            download_url = data.get("href")

            if not download_url:
                print("Не удалось получить ссылку на скачивание")
                print(f"Полный ответ: {data}")
                return False

            print(f"Ссылка получена: {download_url[:50]}...")
            print(f"Скачивание файла...")

            # Скачиваем файл
            file_response = requests.get(download_url, stream=True)

            if file_response.status_code == 200:
                # Создаём папку, если нужно
                save_path.parent.mkdir(parents=True, exist_ok=True)

                # Сохраняем файл
                total_size = int(file_response.headers.get('content-length', 0))
                downloaded = 0

                with open(save_path, 'wb') as f:
                    for chunk in file_response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                print(f"\rПрогресс: {progress:.1f}% ({format_size(downloaded)} / {format_size(total_size)})", end="")

                print(f"\n[OK] Файл успешно скачан: {save_path}")
                return True
            else:
                print(f"[ERROR] Ошибка скачивания: {file_response.status_code}")
                return False

        elif response.status_code == 403:
            print("[ERROR] Доступ запрещен - владелец не разрешает скачивание")
            print(f"Ответ: {response.text}")
            return False
        elif response.status_code == 404:
            print("[ERROR] Файл не найден")
            print(f"Ответ: {response.text}")
            return False
        else:
            print(f"[ERROR] Ошибка: {response.status_code}")
            print(f"Ответ: {response.text}")
            return False

    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        return False


def format_size(size):
    """Форматирует размер"""
    if size is None:
        return "Неизвестно"
    for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} ТБ"


def main():
    load_dotenv()
    token = os.getenv("Token")

    if not token:
        print("Токен не найден")
        return

    public_url = "https://disk.yandex.ru/d/_JeaJNmm6UeQVA"
    folder_name = "Юн.Индастриал"
    file_name = "UInd. Предварительное предложение.docx"

    print("="*80)
    print("СКАЧИВАНИЕ ФАЙЛА ИЗ ПУБЛИЧНОЙ ПАПКИ")
    print("="*80)
    print(f"Публичная папка: {public_url}")
    print(f"Подпапка: {folder_name}")
    print(f"Файл: {file_name}")
    print("="*80 + "\n")

    # Ищем файл
    file_info = find_file_in_folder(token, public_url, folder_name, file_name)

    if file_info:
        # Пытаемся скачать
        save_path = Path("test_downloads") / folder_name / file_name
        print(f"\nПопытка скачать в: {save_path}")

        success = download_public_file(
            token,
            public_url,
            file_info.get("path"),
            save_path
        )

        if success:
            print("\n" + "="*80)
            print("[OK] ФАЙЛ УСПЕШНО СКАЧАН!")
            print("="*80)
            print(f"Расположение: {save_path.absolute()}")
        else:
            print("\n" + "="*80)
            print("[ERROR] НЕ УДАЛОСЬ СКАЧАТЬ ФАЙЛ")
            print("="*80)
    else:
        print("\n" + "="*80)
        print("[ERROR] ФАЙЛ НЕ НАЙДЕН")
        print("="*80)


if __name__ == "__main__":
    main()
