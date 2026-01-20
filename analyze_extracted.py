"""
Анализ размера распакованных архивов
"""
from pathlib import Path
import re


def format_size(size_bytes):
    """Форматирует размер в читаемый вид"""
    for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} ТБ"


def parse_archives_list(file_path="archives_list.txt"):
    """Парсит список архивов и извлекает информацию"""
    archives = {}

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith("disk:/"):
                # Пример: disk:/Клиенты/ОКЕЙ/file.zip (37.5 МБ)
                match = re.search(r'disk:(/.*?)\s+\(([\d.]+)\s+(Б|КБ|МБ|ГБ|ТБ)\)', line)
                if match:
                    path = match.group(1)
                    size_value = float(match.group(2))
                    size_unit = match.group(3)

                    # Конвертируем в байты
                    multipliers = {'Б': 1, 'КБ': 1024, 'МБ': 1024**2, 'ГБ': 1024**3, 'ТБ': 1024**4}
                    size_bytes = size_value * multipliers.get(size_unit, 1)

                    filename = Path(path).name
                    archives[filename] = {
                        'original_path': path,
                        'size': size_bytes,
                        'size_str': f"{size_value} {size_unit}"
                    }

    return archives


def get_folder_size(folder_path):
    """Рекурсивно подсчитывает размер папки"""
    total_size = 0
    file_count = 0

    try:
        for item in folder_path.rglob("*"):
            if item.is_file():
                try:
                    total_size += item.stat().st_size
                    file_count += 1
                except (OSError, FileNotFoundError):
                    continue
    except Exception as e:
        print(f"Ошибка при обработке {folder_path}: {e}")

    return total_size, file_count


def analyze_extracted_folders(base_path="localdata/markdown_files"):
    """Анализирует распакованные архивы"""
    base = Path(base_path)

    if not base.exists():
        print(f"Папка {base} не найдена")
        return

    # Ищем папки с _extracted в названии
    extracted_folders = []

    for item in base.rglob("*"):
        if item.is_dir() and "_extracted" in item.name:
            size, file_count = get_folder_size(item)

            # Пытаемся найти соответствующий архив
            archive_name = item.name.replace("_extracted", "")

            extracted_folders.append({
                'path': item,
                'relative_path': item.relative_to(base),
                'name': item.name,
                'archive_name': archive_name,
                'size': size,
                'file_count': file_count
            })

    return extracted_folders


def main():
    print("=" * 100)
    print("АНАЛИЗ РАСПАКОВАННЫХ АРХИВОВ")
    print("=" * 100)
    print()

    # Читаем список исходных архивов
    print("Загрузка списка архивов...")
    archives = parse_archives_list()
    print(f"Найдено {len(archives)} архивов в списке\n")

    # Анализируем распакованные папки
    print("Поиск распакованных архивов...")
    extracted = analyze_extracted_folders()
    print(f"Найдено {len(extracted)} распакованных папок\n")

    if not extracted:
        print("Не найдено распакованных архивов (папок с '_extracted' в названии)")
        return

    # Сортируем по размеру
    extracted_sorted = sorted(extracted, key=lambda x: x['size'], reverse=True)

    # Выводим таблицу
    print("=" * 100)
    print("РАСПАКОВАННЫЕ АРХИВЫ (СОРТИРОВКА ПО РАЗМЕРУ)")
    print("=" * 100)
    print()
    print(f"{'№':<4} {'Размер распак.':<15} {'Файлов':<10} {'Имя архива':<50}")
    print("-" * 100)

    total_extracted_size = 0
    total_archive_size = 0
    matched_count = 0

    for idx, folder in enumerate(extracted_sorted, 1):
        size_str = format_size(folder['size'])
        archive_name = folder['archive_name'][:47] + "..." if len(folder['archive_name']) > 50 else folder['archive_name']

        print(f"{idx:<4} {size_str:<15} {folder['file_count']:<10} {archive_name}")

        total_extracted_size += folder['size']

        # Пытаемся найти размер исходного архива
        if folder['archive_name'] in archives:
            total_archive_size += archives[folder['archive_name']]['size']
            matched_count += 1

    print()
    print("=" * 100)
    print("ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 100)
    print()
    print(f"Всего распакованных папок: {len(extracted)}")
    print(f"Общий размер распакованных данных: {format_size(total_extracted_size)}")
    print(f"Всего файлов в распакованных папках: {sum(f['file_count'] for f in extracted):,}")
    print()

    if matched_count > 0 and total_archive_size > 0:
        print(f"Найдено соответствий с исходными архивами: {matched_count} из {len(extracted)}")
        print(f"Размер исходных архивов (для найденных): {format_size(total_archive_size)}")
        ratio = total_extracted_size / total_archive_size if total_archive_size > 0 else 0
        print(f"Коэффициент распаковки: {ratio:.2f}x (во сколько раз больше после распаковки)")
        print()

    # Топ-10 самых больших
    print("=" * 100)
    print("ТОП-10 САМЫХ БОЛЬШИХ РАСПАКОВАННЫХ АРХИВОВ")
    print("=" * 100)
    print()

    for idx, folder in enumerate(extracted_sorted[:10], 1):
        print(f"{idx}. {folder['name']}")
        print(f"   Размер: {format_size(folder['size'])}")
        print(f"   Файлов: {folder['file_count']:,}")
        print(f"   Путь: {folder['relative_path']}")

        # Проверяем исходный размер архива
        if folder['archive_name'] in archives:
            orig = archives[folder['archive_name']]
            ratio = folder['size'] / orig['size'] if orig['size'] > 0 else 0
            print(f"   Исходный архив: {orig['size_str']} -> {format_size(folder['size'])} ({ratio:.1f}x)")

        print()

    print("=" * 100)

    # Рекомендации
    print()
    print("РЕКОМЕНДАЦИИ:")
    print("-" * 100)
    print()

    if total_extracted_size > 1024**3:  # > 1 ГБ
        savings = total_extracted_size * 0.7  # примерно 70% можно сэкономить удалением распакованных
        print(f"1. Распакованные архивы занимают {format_size(total_extracted_size)}")
        print(f"   Если исходные архивы сохранены, можно удалить распакованные папки")
        print(f"   Потенциальная экономия: ~{format_size(savings)}")
        print()

    if matched_count < len(extracted):
        print(f"2. Не найдено исходных архивов для {len(extracted) - matched_count} распакованных папок")
        print(f"   Возможно, исходные архивы были удалены или переименованы")
        print()


if __name__ == "__main__":
    main()
