"""
Сравнение размеров - только не-part файлы
"""
import sys
sys.path.append('.')
from compare_sizes import *


def main():
    print("=" * 100)
    print("СРАВНЕНИЕ РАЗМЕРОВ (БЕЗ PART-ФАЙЛОВ)")
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

        # Пропускаем part-файлы
        if original_name.startswith('part-') and '.parquet' in original_name:
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

    print(f"Успешно сопоставлено {len(comparisons)} файлов (без part-файлов)\n")

    # 6. Сортируем по коэффициенту увеличения
    comparisons_sorted = sorted(comparisons, key=lambda x: x['ratio'], reverse=True)

    # 7. Выводим ТОП-20
    print("=" * 100)
    print("ТОП-20 ФАЙЛОВ С НАИБОЛЬШИМ УВЕЛИЧЕНИЕМ РАЗМЕРА (БЕЗ PART-ФАЙЛОВ)")
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
    print("ОБЩАЯ СТАТИСТИКА (БЕЗ PART-ФАЙЛОВ)")
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

    print("=" * 100)


if __name__ == "__main__":
    main()
