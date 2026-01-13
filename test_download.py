"""
Тестовый скрипт для проверки скачивания файлов из подпапок Яндекс Диска
Пробует разные методы получения ссылок для скачивания
"""
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

TOKEN = os.getenv('Token')
PUBLIC_URL = "https://disk.yandex.ru/d/_JeaJNmm6UeQVA"
OUTPUT_DIR = Path("test_downloads")


def get_files_from_folder(public_url, folder_path, limit=10):
    """Получает список файлов из папки"""
    api_url = "https://cloud-api.yandex.net/v1/disk/public/resources"
    headers = {'Authorization': f'OAuth {TOKEN}'} if TOKEN else {}

    params = {
        'public_key': public_url,
        'path': folder_path,
        'limit': limit
    }

    try:
        response = requests.get(api_url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        files = []
        if '_embedded' in data and 'items' in data['_embedded']:
            for item in data['_embedded']['items']:
                if item['type'] == 'file':
                    files.append({
                        'name': item['name'],
                        'path': item['path'],
                        'size': item.get('size', 0),
                        'file': item.get('file'),  # Прямая ссылка из метаданных
                        'public_url': item.get('public_url')
                    })

        return files
    except Exception as e:
        print(f"Ошибка получения списка: {e}")
        return []


def try_download_methods(file_info, public_url):
    """Пробует разные методы получения ссылки для скачивания"""
    download_api = "https://cloud-api.yandex.net/v1/disk/public/resources/download"
    headers = {'Authorization': f'OAuth {TOKEN}'} if TOKEN else {}

    methods = []

    # Метод 1: Прямая ссылка из метаданных
    if file_info.get('file'):
        methods.append(('Прямая ссылка из метаданных', file_info['file']))

    # Метод 2: Через download API с path
    try:
        params = {
            'public_key': public_url,
            'path': file_info['path']
        }
        resp = requests.get(download_api, headers=headers, params=params, timeout=30)
        if resp.ok:
            href = resp.json().get('href')
            if href:
                methods.append(('Download API (path)', href))
            else:
                methods.append(('Download API (path)', 'ПУСТОЙ href'))
    except Exception as e:
        methods.append(('Download API (path)', f'ОШИБКА: {e}'))

    # Метод 3: Через public_url файла (если есть)
    if file_info.get('public_url'):
        try:
            params = {'public_key': file_info['public_url']}
            resp = requests.get(download_api, headers=headers, params=params, timeout=30)
            if resp.ok:
                href = resp.json().get('href')
                if href:
                    methods.append(('Download API (public_url)', href))
        except Exception as e:
            methods.append(('Download API (public_url)', f'ОШИБКА: {e}'))

    # Метод 4: Без токена (публичный доступ)
    try:
        params = {
            'public_key': public_url,
            'path': file_info['path']
        }
        resp = requests.get(download_api, params=params, timeout=30)
        if resp.ok:
            href = resp.json().get('href')
            if href:
                methods.append(('Без токена', href))
    except Exception as e:
        pass

    return methods


def download_file(url, output_path):
    """Скачивает файл по ссылке"""
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return True
    except Exception as e:
        return False


def main():
    if not TOKEN:
        print("ОШИБКА: Токен не найден в .env файле")
        return

    # Папка для проверки (можно изменить через аргумент)
    folder = "/Юн.Индастриал"
    if len(sys.argv) > 1:
        folder = sys.argv[1]
        if not folder.startswith('/'):
            folder = '/' + folder

    print("=" * 80)
    print(f"ТЕСТИРОВАНИЕ СКАЧИВАНИЯ ФАЙЛОВ")
    print(f"Папка: {folder}")
    print(f"Публичная ссылка: {PUBLIC_URL}")
    print("=" * 80)
    print()

    # Получаем список файлов
    print("Получение списка файлов...")
    files = get_files_from_folder(PUBLIC_URL, folder, limit=10)

    if not files:
        print("Файлы не найдены")
        return

    print(f"Найдено файлов: {len(files)}")
    print()

    # Очищаем папку для тестов
    if OUTPUT_DIR.exists():
        import shutil
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Тестируем каждый файл
    success_count = 0

    for i, file_info in enumerate(files, 1):
        print("=" * 80)
        print(f"[{i}/{len(files)}] Файл: {file_info['name']}")
        print(f"Размер: {file_info['size']} байт")
        print(f"Path: {file_info['path']}")
        print()

        # Пробуем разные методы
        methods = try_download_methods(file_info, PUBLIC_URL)

        print(f"Найдено методов получения ссылки: {len(methods)}")
        for method_name, result in methods:
            print(f"  - {method_name}: ", end='')
            if result.startswith('http'):
                print(f"OK (ссылка получена)")
                print(f"    URL: {result[:60]}...")
            else:
                print(result)

        # Пробуем скачать
        download_success = False
        used_method = None

        for method_name, result in methods:
            if result.startswith('http'):
                print(f"\nПопытка скачивания через: {method_name}")
                output_path = OUTPUT_DIR / file_info['name']
                if download_file(result, output_path):
                    file_size = output_path.stat().st_size
                    print(f"[OK] УСПЕХ! Скачано: {file_size} байт")
                    print(f"  Сохранено: {output_path}")
                    download_success = True
                    used_method = method_name
                    success_count += 1
                    break
                else:
                    print(f"[ERROR] ОШИБКА при скачивании")

        if not download_success:
            print(f"\n[FAIL] НЕ УДАЛОСЬ СКАЧАТЬ - нет рабочих ссылок")

        print()

    # Итоги
    print("=" * 80)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    print(f"Всего файлов: {len(files)}")
    print(f"Успешно скачано: {success_count}")
    print(f"Не удалось скачать: {len(files) - success_count}")
    print()

    if success_count > 0:
        print(f"Скачанные файлы находятся в папке: {OUTPUT_DIR.absolute()}")
    else:
        print("К сожалению, ни один файл не удалось скачать через API")


if __name__ == "__main__":
    main()
