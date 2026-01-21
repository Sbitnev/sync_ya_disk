"""
Сравнение размеров исходных и преобразованных файлов
"""
from pathlib import Path
from collections import defaultdict
import sqlite3


def format_size(size_bytes):
    """Форматирует размер в читаемый вид"""
    for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} ТБ"


def get_original_files_from_db(db_path="localdata/metadata/sync_metadata.db"):
    """Получить информацию об исходных файлах из БД"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Получаем все файлы с их размерами
        cursor.execute("""
            SELECT path, size, markdown_path
            FROM files
            WHERE size > 0
        """)

        files = {}
        for row in cursor.fetchall():
            path, size, markdown_path = row

            # Извлекаем имя файла из пути
            name = Path(path).name if path else ""

            files[path] = {
                'name': name,
                'size': size,
                'markdown_path': markdown_path
            }

        conn.close()
        return files
    except Exception as e:
        print(f"Ошибка при чтении БД: {e}")
        import traceback
        traceback.print_exc()
        return {}


def get_converted_files_size(base_path="localdata/markdown_files"):
    """Получить размеры всех преобразованных файлов"""
    base = Path(base_path)

    if not base.exists():
        return {}

    files_map = {}

    # Собираем все файлы
    for file_path in base.rglob("*"):
        if file_path.is_file():
            try:
                size = file_path.stat().st_size
                rel_path = file_path.relative_to(base)

                # Сохраняем с разными ключами для поиска
                files_map[str(rel_path)] = size
                files_map[file_path.name] = size

            except Exception:
                pass

    return files_map


def group_part_files(base_path="localdata/markdown_files"):
    """Группирует part-файлы по их базовому имени"""
    base = Path(base_path)

    if not base.exists():
        return {}

    groups = defaultdict(lambda: {'files': [], 'total_size': 0})

    for file_path in base.rglob("part-*.csv"):
        if file_path.is_file():
            try:
                size = file_path.stat().st_size

                # Извлекаем базовое имя группы (все part-файлы из одной папки)
                parent = file_path.parent
                group_key = str(parent.relative_to(base))

                groups[group_key]['files'].append(file_path.name)
                groups[group_key]['total_size'] += size

            except Exception:
                pass

    return groups


def group_extracted_files(base_path="localdata/markdown_files"):
    """Группирует файлы из _extracted папок с их архивами"""
    base = Path(base_path)

    if not base.exists():
        return {}

    groups = {}

    for folder in base.rglob("*_extracted"):
        if folder.is_dir():
            # Получаем имя архива
            archive_name = folder.name.replace("_extracted", "")

            # Считаем общий размер всех файлов в папке
            total_size = 0
            file_count = 0

            for file_path in folder.rglob("*"):
                if file_path.is_file():
                    try:
                        total_size += file_path.stat().st_size
                        file_count += 1
                    except Exception:
                        pass

            groups[archive_name] = {
                'total_size': total_size,
                'file_count': file_count,
                'path': str(folder.relative_to(base))
            }

    return groups


def find_converted_size(original_name, markdown_path, converted_files, extracted_groups, part_groups):
    """Найти размер преобразованного файла/группы файлов"""

    # 0. Используем прямой путь из БД, если есть
    if markdown_path and markdown_path in converted_files:
        return converted_files[markdown_path], 'db_path'

    # 1. Проверяем архивы (_extracted)
    if original_name in extracted_groups:
        return extracted_groups[original_name]['total_size'], 'archive'

    # 2. Проверяем прямое совпадение
    if original_name in converted_files:
        return converted_files[original_name], 'direct'

    # 3. Проверяем с .md расширением
    md_name = original_name + '.md'
    if md_name in converted_files:
        return converted_files[md_name], 'converted'

    # 4. Проверяем без расширения
    name_no_ext = Path(original_name).stem
    if name_no_ext in converted_files:
        return converted_files[name_no_ext], 'no_ext'

    return None, None


def main():
    print("=" * 100)
    print("СРАВНЕНИЕ РАЗМЕРОВ ИСХОДНЫХ И ПРЕОБРАЗОВАННЫХ ФАЙЛОВ")
    print("=" * 100)
    print()

    # 1. Получаем исходные файлы из БД
    print("Загрузка информации об исходных файлах из БД...")
    original_files = get_original_files_from_db()
    print(f"Найдено {len(original_files)} исходных файлов\n")

    if not original_files:
        print("Не удалось загрузить данные из БД")
        return

    # 2. Получаем преобразованные файлы
    print("Анализ преобразованных файлов...")
    converted_files = get_converted_files_size()
    print(f"Найдено {len(converted_files)} преобразованных файлов\n")

    # 3. Группируем _extracted папки
    print("Анализ распакованных архивов...")
    extracted_groups = group_extracted_files()
    print(f"Найдено {len(extracted_groups)} распакованных архивов\n")

    # 4. Группируем part-файлы
    print("Анализ part-файлов...")
    part_groups = group_part_files()
    print(f"Найдено {len(part_groups)} групп part-файлов\n")

    # 5. Сравниваем размеры
    print("Сравнение размеров...")
    comparisons = []

    for path, info in original_files.items():
        original_name = info['name']
        original_size = info['size']
        markdown_path = info.get('markdown_path')

        if original_size == 0:
            continue

        # Ищем преобразованный файл
        converted_size, match_type = find_converted_size(
            original_name,
            markdown_path,
            converted_files,
            extracted_groups,
            part_groups
        )

        if converted_size is not None and converted_size > 0:
            ratio = converted_size / original_size
            increase = converted_size - original_size

            comparisons.append({
                'name': original_name,
                'original_size': original_size,
                'converted_size': converted_size,
                'ratio': ratio,
                'increase': increase,
                'match_type': match_type
            })

    print(f"Успешно сопоставлено {len(comparisons)} файлов\n")

    # 6. Сортируем по коэффициенту увеличения
    comparisons_sorted = sorted(comparisons, key=lambda x: x['ratio'], reverse=True)

    # 7. Выводим ТОП-20
    print("=" * 100)
    print("ТОП-20 ФАЙЛОВ С НАИБОЛЬШИМ УВЕЛИЧЕНИЕМ РАЗМЕРА")
    print("=" * 100)
    print()
    print(f"{'№':<4} {'Коэфф.':<8} {'Исходный':<15} {'Преобразов.':<15} {'Имя файла':<40}")
    print("-" * 100)

    for idx, item in enumerate(comparisons_sorted[:20], 1):
        name = item['name'][:37] + "..." if len(item['name']) > 40 else item['name']

        print(f"{idx:<4} {item['ratio']:<8.1f}x "
              f"{format_size(item['original_size']):<15} "
              f"{format_size(item['converted_size']):<15} "
              f"{name}")

    print()
    print("=" * 100)
    print("ДЕТАЛЬНАЯ ИНФОРМАЦИЯ ПО ТОП-10")
    print("=" * 100)
    print()

    for idx, item in enumerate(comparisons_sorted[:10], 1):
        print(f"{idx}. {item['name']}")
        print(f"   Исходный размер: {format_size(item['original_size'])}")
        print(f"   После преобразования: {format_size(item['converted_size'])}")
        print(f"   Увеличение: {format_size(item['increase'])} ({item['ratio']:.1f}x)")
        print(f"   Тип сопоставления: {item['match_type']}")
        print()

    # 8. Статистика
    print("=" * 100)
    print("ОБЩАЯ СТАТИСТИКА")
    print("=" * 100)
    print()

    total_original = sum(c['original_size'] for c in comparisons)
    total_converted = sum(c['converted_size'] for c in comparisons)
    avg_ratio = sum(c['ratio'] for c in comparisons) / len(comparisons) if comparisons else 0

    print(f"Файлов сопоставлено: {len(comparisons)}")
    print(f"Общий размер исходных: {format_size(total_original)}")
    print(f"Общий размер преобразованных: {format_size(total_converted)}")
    print(f"Общее увеличение: {format_size(total_converted - total_original)} ({(total_converted/total_original):.2f}x)")
    print(f"Средний коэффициент увеличения: {avg_ratio:.2f}x")
    print()

    # Распределение по коэффициенту
    ranges = {
        '< 1x (сжатие)': 0,
        '1-2x': 0,
        '2-5x': 0,
        '5-10x': 0,
        '10-50x': 0,
        '> 50x': 0
    }

    for c in comparisons:
        ratio = c['ratio']
        if ratio < 1:
            ranges['< 1x (сжатие)'] += 1
        elif ratio < 2:
            ranges['1-2x'] += 1
        elif ratio < 5:
            ranges['2-5x'] += 1
        elif ratio < 10:
            ranges['5-10x'] += 1
        elif ratio < 50:
            ranges['10-50x'] += 1
        else:
            ranges['> 50x'] += 1

    print("Распределение по коэффициенту увеличения:")
    print("-" * 100)
    for range_name, count in ranges.items():
        percentage = (count / len(comparisons) * 100) if comparisons else 0
        bar = '#' * int(percentage / 2)
        print(f"{range_name:<20} {count:>6} ({percentage:>5.1f}%) {bar}")

    print()
    print("=" * 100)


if __name__ == "__main__":
    main()
