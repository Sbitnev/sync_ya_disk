"""
Скрипт для анализа расширений файлов в папке /Клиенты
"""
from collections import Counter
from pathlib import Path
from src.syncer import YandexDiskUserSyncer
from src.token_manager import TokenManager
from src import config


def analyze_extensions(files):
    """Анализирует расширения файлов"""
    extensions = []

    for file_info in files:
        name = file_info['name']
        # Получаем расширение
        ext = Path(name).suffix.lower()

        if ext:
            extensions.append(ext)
        else:
            extensions.append('(без расширения)')

    return Counter(extensions)


def format_size(size):
    """Форматирует размер в читаемый вид"""
    for unit in ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} ПБ"


def main():
    print("=" * 70)
    print("АНАЛИЗ РАСШИРЕНИЙ ФАЙЛОВ В ПАПКЕ /Клиенты")
    print("=" * 70)
    print()

    # Инициализируем менеджер токенов
    print("Получение токена...")
    token_manager = TokenManager(
        client_id=config.CLIENT_ID,
        client_secret=config.CLIENT_SECRET,
        user_id=config.USER_ID
    )

    # Инициализируем синхронизатор
    syncer = YandexDiskUserSyncer(
        token_manager=token_manager,
        remote_folder_path="/Клиенты",
        download_dir="temp_analysis"
    )

    # Получаем список всех файлов
    print("Сканирование папки /Клиенты (это может занять время)...")
    folders_set = set()
    all_files = syncer.get_all_files_recursive("/Клиенты", folders_set=folders_set)

    print(f"\nНайдено файлов: {len(all_files)}")
    print(f"Найдено папок: {len(folders_set)}")
    print()

    # Анализируем расширения
    extensions_counter = analyze_extensions(all_files)

    # Подсчитываем размеры по расширениям
    size_by_ext = {}
    for file_info in all_files:
        name = file_info['name']
        ext = Path(name).suffix.lower() or '(без расширения)'
        size_by_ext[ext] = size_by_ext.get(ext, 0) + file_info['size']

    # Сортируем по количеству файлов
    sorted_extensions = sorted(extensions_counter.items(), key=lambda x: x[1], reverse=True)

    print("=" * 70)
    print("СТАТИСТИКА ПО РАСШИРЕНИЯМ:")
    print("=" * 70)
    print(f"{'Расширение':<20} {'Количество':<15} {'Общий размер':<20}")
    print("-" * 70)

    total_count = 0
    total_size = 0

    for ext, count in sorted_extensions:
        size = size_by_ext.get(ext, 0)
        total_count += count
        total_size += size
        print(f"{ext:<20} {count:<15} {format_size(size):<20}")

    print("-" * 70)
    print(f"{'ВСЕГО':<20} {total_count:<15} {format_size(total_size):<20}")
    print("=" * 70)
    print()

    # Выводим все уникальные расширения списком
    print("ВСЕ НАЙДЕННЫЕ РАСШИРЕНИЯ:")
    unique_extensions = sorted([ext for ext in extensions_counter.keys() if ext != '(без расширения)'])
    print(", ".join(unique_extensions))

    if '(без расширения)' in extensions_counter:
        print(f"\nФайлов без расширения: {extensions_counter['(без расширения)']}")


if __name__ == "__main__":
    main()
