"""
Скрипт для поиска архивов в папке /Клиенты на Яндекс.Диске через API
"""
import requests
from pathlib import Path
from src import config
from src.token_manager import TokenManager

def find_archives():
    """Находит все архивы в папке /Клиенты"""

    # Инициализируем менеджер токенов
    token_manager = TokenManager(
        client_id=config.CLIENT_ID,
        client_secret=config.CLIENT_SECRET,
        user_id=config.USER_ID
    )

    print("[OK] Токен получен, начинаю поиск архивов...\n")

    # Расширения архивов
    archive_extensions = ['.zip', '.7z', '.rar', '.tar', '.gz', '.tgz', '.tar.gz']

    archives = []
    scanned_folders = [0]  # Используем список для изменяемого счетчика
    scanned_files = [0]

    def scan_folder(path):
        """Рекурсивно сканирует папку"""
        scanned_folders[0] += 1
        print(f"Сканирование [{scanned_folders[0]}]: {path}", flush=True)

        headers = {'Authorization': f'OAuth {token_manager.token}'}
        url = 'https://cloud-api.yandex.net/v1/disk/resources'

        params = {
            'path': path,
            'limit': 1000,
            'fields': '_embedded.items.name,_embedded.items.type,_embedded.items.path,_embedded.items.size'
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            items = data.get('_embedded', {}).get('items', [])

            for item in items:
                if item['type'] == 'dir':
                    # Рекурсивно сканируем подпапки
                    scan_folder(item['path'])
                else:
                    scanned_files[0] += 1
                    # Проверяем, является ли файл архивом
                    file_name = item['name'].lower()
                    if any(file_name.endswith(ext) for ext in archive_extensions):
                        archives.append({
                            'name': item['name'],
                            'path': item['path'],
                            'size': item.get('size', 0)
                        })
                        print(f"  Найден архив: {item['name']}", flush=True)

        except Exception as e:
            print(f"[WARN] Ошибка при сканировании {path}: {e}", flush=True)

    # Начинаем сканирование с папки /Клиенты
    base_path = config.REMOTE_FOLDER_PATH
    print(f"Сканирование папки: {base_path}\n")
    scan_folder(base_path)

    # Выводим результаты
    print(f"\n\nСканирование завершено!")
    print(f"Просканировано папок: {scanned_folders[0]}")
    print(f"Просканировано файлов: {scanned_files[0]}")
    print(f"Найдено архивов: {len(archives)}\n")

    if archives:
        print("=" * 100)

        # Группируем по расширениям
        by_extension = {}
        for archive in archives:
            ext = Path(archive['name']).suffix.lower()
            if ext not in by_extension:
                by_extension[ext] = []
            by_extension[ext].append(archive)

        # Выводим по типам
        for ext in sorted(by_extension.keys()):
            archives_list = by_extension[ext]
            total_size = sum(a['size'] for a in archives_list)
            print(f"\n{ext.upper()} архивы ({len(archives_list)} файлов, {format_size(total_size)}):")
            print("-" * 100)

            for archive in sorted(archives_list, key=lambda x: x['path']):
                size_str = format_size(archive['size'])
                print(f"    * {archive['path']}")
                print(f"     Размер: {size_str}")

        print("\n" + "=" * 100)
        print(f"\nВсего найдено: {len(archives)} архивов")

        # Сохраняем список в файл
        output_file = 'archives_list.txt'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("Список архивов в папке /Клиенты\n")
            f.write("=" * 100 + "\n\n")

            for ext in sorted(by_extension.keys()):
                archives_list = by_extension[ext]
                f.write(f"\n{ext.upper()} ({len(archives_list)} файлов):\n")
                f.write("-" * 100 + "\n")
                for archive in sorted(archives_list, key=lambda x: x['path']):
                    f.write(f"{archive['path']} ({format_size(archive['size'])})\n")

        print(f"\n[OK] Список сохранен в файл: {output_file}")
    else:
        print("[ERROR] Архивы не найдены")


def format_size(size):
    """Форматирует размер в читаемый вид"""
    for unit in ["Б", "КБ", "МБ", "ГБ"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} ТБ"


if __name__ == '__main__':
    print("=" * 100)
    print("ПОИСК АРХИВОВ НА ЯНДЕКС.ДИСКЕ")
    print("=" * 100)
    print()

    try:
        find_archives()
    except KeyboardInterrupt:
        print("\n\n[WARN] Поиск прерван пользователем")
    except Exception as e:
        print(f"\n\n[ERROR] Ошибка: {e}")
