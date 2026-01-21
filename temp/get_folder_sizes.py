"""Получить размеры папок в localdata"""
import os
from pathlib import Path


def get_folder_size(folder_path):
    """Рекурсивно подсчитывает размер папки"""
    total_size = 0
    file_count = 0

    try:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                    file_count += 1
                except (OSError, FileNotFoundError):
                    continue
    except Exception as e:
        print(f"Ошибка при обработке {folder_path}: {e}")

    return total_size, file_count


def format_size(size_bytes):
    """Форматирует размер в читаемый вид"""
    for unit in ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} ПБ"


def main():
    localdata = Path("localdata")

    if not localdata.exists():
        print("Папка localdata не найдена")
        return

    print("=" * 80)
    print("РАЗМЕРЫ ПАПОК В LOCALDATA")
    print("=" * 80)
    print()

    # Собираем информацию о всех подпапках
    folders_info = []

    for item in localdata.iterdir():
        if item.is_dir():
            size, count = get_folder_size(item)
            folders_info.append({
                'name': item.name,
                'size': size,
                'count': count
            })

    # Сортируем по размеру
    folders_info.sort(key=lambda x: x['size'], reverse=True)

    # Выводим таблицу
    print(f"{'Папка':<40} {'Размер':<15} {'Файлов':<10}")
    print("-" * 80)

    total_size = 0
    total_files = 0

    for info in folders_info:
        print(f"{info['name']:<40} {format_size(info['size']):<15} {info['count']:<10,}")
        total_size += info['size']
        total_files += info['count']

    print("-" * 80)
    print(f"{'ИТОГО:':<40} {format_size(total_size):<15} {total_files:<10,}")
    print()

    # Дополнительная информация
    print("=" * 80)
    print("ДЕТАЛЬНАЯ ИНФОРМАЦИЯ")
    print("=" * 80)
    print()

    for info in folders_info:
        size_gb = info['size'] / (1024**3)
        avg_size = info['size'] / info['count'] if info['count'] > 0 else 0
        print(f"{info['name']}:")
        print(f"  Размер: {format_size(info['size'])} ({size_gb:.2f} ГБ)")
        print(f"  Файлов: {info['count']:,}")
        print(f"  Средний размер файла: {format_size(avg_size)}")
        print()


if __name__ == "__main__":
    main()
