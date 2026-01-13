"""
Скрипт для вывода списка всех файлов в публичной папке Яндекс Диска
"""
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

TOKEN = os.getenv('Token')


def get_all_files(public_url, path=None):
    """Рекурсивно получает все файлы из публичной папки"""
    api_url = "https://cloud-api.yandex.net/v1/disk/public/resources"
    headers = {'Authorization': f'OAuth {TOKEN}'} if TOKEN else {}

    params = {
        'public_key': public_url,
        'limit': 1000
    }
    if path:
        params['path'] = path

    try:
        response = requests.get(api_url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Ошибка при запросе {path or '/'}: {e}", file=sys.stderr)
        return []

    files = []
    folders = []

    if '_embedded' in data and 'items' in data['_embedded']:
        for item in data['_embedded']['items']:
            item_name = item['name']
            current_path = f"{path}/{item_name}" if path else f"/{item_name}"

            if item['type'] == 'dir':
                folders.append(current_path)
            else:
                files.append({
                    'path': current_path,
                    'name': item_name,
                    'size': item.get('size', 0),
                    'has_download_link': bool(item.get('file'))
                })

    # Рекурсивно обходим подпапки
    for folder in folders:
        files.extend(get_all_files(public_url, folder))

    return files


def format_size(size):
    """Форматирует размер в читаемый вид"""
    for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} ТБ"


def main():
    if not TOKEN:
        print("Предупреждение: Токен не найден в .env файле", file=sys.stderr)

    # Публичная ссылка
    public_url = "https://disk.yandex.ru/d/_JeaJNmm6UeQVA"

    # Можно указать конкретную подпапку через аргумент командной строки
    subfolder = None
    if len(sys.argv) > 1:
        subfolder = sys.argv[1]
        if not subfolder.startswith('/'):
            subfolder = '/' + subfolder

    print(f"Получение списка файлов из: {public_url}")
    if subfolder:
        print(f"Подпапка: {subfolder}")
    print("=" * 60)
    print()

    files = get_all_files(public_url, subfolder)

    if not files:
        print("Файлы не найдены или произошла ошибка")
        return

    # Сортируем по пути
    files.sort(key=lambda x: x['path'])

    # Статистика
    total_size = sum(f['size'] for f in files)
    with_links = sum(1 for f in files if f['has_download_link'])
    without_links = len(files) - with_links

    # Выводим список файлов
    print(f"{'Путь':<70} {'Размер':>12} {'Ссылка':>8}")
    print("-" * 92)

    for f in files:
        path_display = f['path'][:67] + '...' if len(f['path']) > 70 else f['path']
        size_str = format_size(f['size'])
        link_status = "+" if f['has_download_link'] else "-"
        print(f"{path_display:<70} {size_str:>12} {link_status:>8}")

    # Итоги
    print()
    print("=" * 60)
    print(f"Всего файлов: {len(files)}")
    print(f"Общий размер: {format_size(total_size)}")
    print(f"С прямой ссылкой: {with_links}")
    print(f"Без ссылки (не скачать через API): {without_links}")


if __name__ == "__main__":
    main()
