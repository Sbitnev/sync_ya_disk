"""
Топ-20 самых больших файлов в markdown_files
"""
from pathlib import Path


def format_size(size_bytes):
    """Форматирует размер в читаемый вид"""
    for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} ТБ"


def get_top_files(folder_path="localdata/markdown_files", top_n=20):
    """Получить топ-N самых больших файлов"""
    folder = Path(folder_path)

    if not folder.exists():
        print(f"Папка {folder} не найдена")
        return

    # Собираем все файлы
    all_files = []
    for file_path in folder.rglob("*"):
        if file_path.is_file():
            try:
                size = file_path.stat().st_size
                rel_path = file_path.relative_to(folder)
                all_files.append({
                    'path': str(rel_path),
                    'size': size,
                    'ext': file_path.suffix.lower()
                })
            except Exception:
                pass

    # Сортируем по размеру
    top_files = sorted(all_files, key=lambda x: x['size'], reverse=True)[:top_n]

    # Выводим результат
    print("=" * 100)
    print(f"ТОП-{top_n} САМЫХ БОЛЬШИХ ФАЙЛОВ В MARKDOWN_FILES")
    print("=" * 100)
    print()
    print(f"{'№':<4} {'Размер':<12} {'Байт':<15} {'Тип':<8} {'Путь'}")
    print("-" * 100)

    for idx, file_info in enumerate(top_files, 1):
        size_str = format_size(file_info['size'])
        bytes_str = f"{file_info['size']:,}"
        ext_str = file_info['ext'] if file_info['ext'] else 'нет'
        path_str = file_info['path']

        print(f"{idx:<4} {size_str:<12} {bytes_str:<15} {ext_str:<8} {path_str}")

    print()
    print("=" * 100)

    # Итого
    total_size = sum(f['size'] for f in top_files)
    print(f"Суммарный размер топ-{top_n}: {format_size(total_size)}")
    print()


if __name__ == "__main__":
    get_top_files()
