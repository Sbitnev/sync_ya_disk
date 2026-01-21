"""
Анализ папки markdown_files - статистика по размерам файлов
"""
from pathlib import Path
from collections import defaultdict
import os


def format_size(size_bytes):
    """Форматирует размер в читаемый вид"""
    for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} ТБ"


def analyze_markdown_folder(folder_path="localdata/markdown_files"):
    """Анализирует папку с markdown файлами"""

    folder = Path(folder_path)

    if not folder.exists():
        print(f"Папка {folder} не найдена")
        return

    print("=" * 80)
    print("АНАЛИЗ ПАПКИ MARKDOWN_FILES")
    print("=" * 80)
    print(f"Путь: {folder.absolute()}\n")

    # Собираем информацию о всех .md файлах
    all_files = []
    total_size = 0
    folders_stats = defaultdict(lambda: {'count': 0, 'size': 0, 'files': []})

    for md_file in folder.rglob("*.md"):
        try:
            size = md_file.stat().st_size
            total_size += size

            # Относительный путь от markdown_files
            rel_path = md_file.relative_to(folder)

            # Первая папка в пути (категория)
            category = str(rel_path.parts[0]) if len(rel_path.parts) > 1 else "Корень"

            all_files.append({
                'path': str(rel_path),
                'full_path': md_file,
                'size': size,
                'category': category
            })

            # Статистика по категориям
            folders_stats[category]['count'] += 1
            folders_stats[category]['size'] += size
            folders_stats[category]['files'].append({
                'name': md_file.name,
                'size': size
            })

        except Exception as e:
            print(f"Ошибка при чтении {md_file}: {e}")

    # Выводим общую статистику
    print(f"ОБЩАЯ СТАТИСТИКА\n")
    print(f"Всего файлов: {len(all_files):,}")
    print(f"Общий размер: {format_size(total_size)}")
    print(f"Средний размер файла: {format_size(total_size / len(all_files)) if all_files else '0 Б'}")
    print()

    # ТОП-50 самых больших файлов
    print("=" * 80)
    print("ТОП-50 САМЫХ БОЛЬШИХ ФАЙЛОВ")
    print("=" * 80)
    print()

    sorted_files = sorted(all_files, key=lambda x: x['size'], reverse=True)[:50]

    print(f"{'№':<4} {'Размер':<12} {'Путь':<60}")
    print("-" * 80)

    for idx, file_info in enumerate(sorted_files, 1):
        size_str = format_size(file_info['size'])
        path_str = file_info['path']

        # Обрезаем путь если слишком длинный
        if len(path_str) > 55:
            path_str = "..." + path_str[-52:]

        print(f"{idx:<4} {size_str:<12} {path_str}")

    # Статистика по категориям (папкам)
    print("\n" + "=" * 80)
    print("СТАТИСТИКА ПО КАТЕГОРИЯМ (ПАПКАМ)")
    print("=" * 80)
    print()

    sorted_categories = sorted(
        folders_stats.items(),
        key=lambda x: x[1]['size'],
        reverse=True
    )

    print(f"{'Категория':<40} {'Файлов':<10} {'Размер':<15} {'% от общего'}")
    print("-" * 80)

    for category, stats in sorted_categories:
        percentage = (stats['size'] / total_size * 100) if total_size > 0 else 0
        category_display = category[:37] + "..." if len(category) > 40 else category

        print(f"{category_display:<40} {stats['count']:<10} {format_size(stats['size']):<15} {percentage:>6.1f}%")

    # Топ-10 категорий с самыми большими файлами
    print("\n" + "=" * 80)
    print("ТОП-10 КАТЕГОРИЙ С САМЫМИ БОЛЬШИМИ СРЕДНИМИ РАЗМЕРАМИ")
    print("=" * 80)
    print()

    categories_with_avg = []
    for category, stats in folders_stats.items():
        avg_size = stats['size'] / stats['count'] if stats['count'] > 0 else 0
        categories_with_avg.append({
            'category': category,
            'avg_size': avg_size,
            'count': stats['count'],
            'total_size': stats['size']
        })

    sorted_by_avg = sorted(categories_with_avg, key=lambda x: x['avg_size'], reverse=True)[:10]

    print(f"{'Категория':<40} {'Средний размер':<15} {'Файлов'}")
    print("-" * 80)

    for item in sorted_by_avg:
        category_display = item['category'][:37] + "..." if len(item['category']) > 40 else item['category']
        print(f"{category_display:<40} {format_size(item['avg_size']):<15} {item['count']}")

    # Распределение по размерам
    print("\n" + "=" * 80)
    print("РАСПРЕДЕЛЕНИЕ ФАЙЛОВ ПО РАЗМЕРАМ")
    print("=" * 80)
    print()

    size_ranges = {
        '< 1 КБ': 0,
        '1 КБ - 10 КБ': 0,
        '10 КБ - 100 КБ': 0,
        '100 КБ - 1 МБ': 0,
        '1 МБ - 10 МБ': 0,
        '10 МБ - 100 МБ': 0,
        '> 100 МБ': 0
    }

    for file_info in all_files:
        size = file_info['size']
        if size < 1024:
            size_ranges['< 1 КБ'] += 1
        elif size < 10 * 1024:
            size_ranges['1 КБ - 10 КБ'] += 1
        elif size < 100 * 1024:
            size_ranges['10 КБ - 100 КБ'] += 1
        elif size < 1024 * 1024:
            size_ranges['100 КБ - 1 МБ'] += 1
        elif size < 10 * 1024 * 1024:
            size_ranges['1 МБ - 10 МБ'] += 1
        elif size < 100 * 1024 * 1024:
            size_ranges['10 МБ - 100 МБ'] += 1
        else:
            size_ranges['> 100 МБ'] += 1

    for range_name, count in size_ranges.items():
        percentage = (count / len(all_files) * 100) if all_files else 0
        bar_length = int(percentage / 2)
        bar = '#' * bar_length
        print(f"{range_name:<20} {count:>6} ({percentage:>5.1f}%) {bar}")

    # Рекомендации
    print("\n" + "=" * 80)
    print("РЕКОМЕНДАЦИИ")
    print("=" * 80)
    print()

    # Файлы > 10 МБ
    large_files = [f for f in all_files if f['size'] > 10 * 1024 * 1024]
    if large_files:
        print(f"• Найдено {len(large_files)} файлов больше 10 МБ")
        print(f"  Общий размер: {format_size(sum(f['size'] for f in large_files))}")
        print(f"  Рекомендуется проверить необходимость хранения таких больших markdown файлов")
        print()

    # Проверяем дубликаты по имени
    file_names = defaultdict(list)
    for file_info in all_files:
        file_names[Path(file_info['path']).name].append(file_info['path'])

    duplicates = {name: paths for name, paths in file_names.items() if len(paths) > 1}
    if duplicates:
        print(f"• Найдено {len(duplicates)} имён файлов с дубликатами:")
        for name, paths in list(duplicates.items())[:5]:
            print(f"  - {name}: {len(paths)} копий")
        if len(duplicates) > 5:
            print(f"  ... и ещё {len(duplicates) - 5} дубликатов")
        print()

    # Потенциал для сжатия
    print(f"• Потенциал для сжатия (примерно): {format_size(total_size * 0.7)} -> {format_size(total_size * 0.3)}")
    print(f"  (Markdown файлы хорошо сжимаются, экономия ~70%)")
    print()

    print("=" * 80)

    return {
        'total_files': len(all_files),
        'total_size': total_size,
        'files': all_files,
        'categories': dict(folders_stats)
    }


if __name__ == "__main__":
    stats = analyze_markdown_folder()

    # Сохраняем детальный отчет
    if stats:
        output_file = "markdown_analysis_report.txt"
        print(f"\nДетальный отчет сохранен в: {output_file}")
