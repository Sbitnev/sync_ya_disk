"""
Быстрый анализ файла errors.log
Показывает статистику по типам ошибок
"""
from pathlib import Path
from collections import defaultdict
import re


def analyze_errors(log_file: Path = Path("logs/errors.log")):
    """Анализирует файл с ошибками"""

    if not log_file.exists():
        print(f"❌ Файл {log_file} не найден")
        return

    # Счетчики
    error_types = defaultdict(int)
    total_errors = 0
    errors_by_file = defaultdict(list)

    # Читаем файл
    print(f"📖 Читаю файл: {log_file}")
    print("=" * 80)

    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if 'ERROR' not in line:
                continue

            total_errors += 1

            # Извлекаем тип ошибки
            # Примеры:
            # "Не удалось скачать файл..."
            # "Ошибка конвертации..."
            # "HTTP ошибка 400..."
            # "Критическая ошибка..."

            # Ошибки скачивания
            if 'Не удалось скачать файл' in line:
                match = re.search(r'Не удалось скачать файл (.+?) после', line)
                if match:
                    filename = match.group(1)
                    error_types['Ошибки скачивания'] += 1
                    errors_by_file['Ошибки скачивания'].append(filename)

            # Ошибки конвертации
            elif 'Ошибка конвертации' in line:
                match = re.search(r'Ошибка конвертации (.+?):', line)
                if match:
                    filename = match.group(1)
                    error_types['Ошибки конвертации'] += 1
                    errors_by_file['Ошибки конвертации'].append(filename)

                # Детализация по типам конвертации
                if 'UTF-16' in line:
                    error_types['  └─ CSV с неправильной кодировкой'] += 1
                elif '.tmp' in line or '~$' in line or '~WRL' in line:
                    error_types['  └─ Временные файлы Office'] += 1
                elif '.drawio' in line:
                    error_types['  └─ Draw.io файлы'] += 1
                elif '.mpp' in line:
                    error_types['  └─ Microsoft Project файлы'] += 1
                elif '.m4a' in line:
                    error_types['  └─ Аудио файлы'] += 1

            # HTTP ошибки
            elif 'HTTP ошибка' in line:
                match = re.search(r'HTTP ошибка (\d+)', line)
                if match:
                    status_code = match.group(1)
                    error_types[f'HTTP {status_code} ошибки'] += 1

            # Критические ошибки
            elif 'Критическая ошибка' in line:
                error_types['Критические ошибки'] += 1

            # Прочие ошибки
            else:
                error_types['Прочие ошибки'] += 1

    # Выводим результаты
    print(f"\n📊 СТАТИСТИКА ПО ОШИБКАМ\n")
    print(f"Всего ошибок: {total_errors}")
    print()

    if error_types:
        print("Типы ошибок:")
        print("-" * 80)

        # Сортируем по количеству
        sorted_types = sorted(error_types.items(), key=lambda x: x[1], reverse=True)

        for error_type, count in sorted_types:
            percentage = (count / total_errors * 100) if total_errors > 0 else 0
            print(f"{error_type:<50} {count:>6} ({percentage:>5.1f}%)")

        # Топ проблемных файлов
        print("\n" + "=" * 80)
        print("📁 ТОП-10 ПРОБЛЕМНЫХ ФАЙЛОВ\n")

        for category, files in errors_by_file.items():
            if not files:
                continue

            print(f"\n{category}:")
            # Считаем частоту
            from collections import Counter
            file_counts = Counter(files)
            top_files = file_counts.most_common(10)

            for filename, count in top_files:
                print(f"  {count:>2}x  {filename}")

    print("\n" + "=" * 80)

    # Рекомендации
    print("\n💡 РЕКОМЕНДАЦИИ:\n")

    if error_types.get('  └─ Временные файлы Office', 0) > 0:
        print("• Добавьте временные Office файлы в исключения (см. CODE_IMPROVEMENTS.md)")

    if error_types.get('  └─ CSV с неправильной кодировкой', 0) > 0:
        print("• Улучшите обработку CSV кодировок (см. CODE_IMPROVEMENTS.md)")

    if error_types.get('  └─ Draw.io файлы', 0) > 0:
        print("• Draw.io файлы не поддерживаются - добавьте в исключения")

    if error_types.get('Критические ошибки', 0) > 0:
        print("• ⚠️  ВНИМАНИЕ: Обнаружены критические ошибки! Проверьте лог детально.")

    if error_types.get('Ошибки скачивания', 0) > 10:
        print("• Много ошибок скачивания - проверьте сетевое подключение")

    if error_types.get('HTTP 400 ошибки', 0) > 0:
        print("• HTTP 400 ошибки - проблема с именами файлов (см. CODE_IMPROVEMENTS.md)")

    print()


if __name__ == "__main__":
    analyze_errors()
