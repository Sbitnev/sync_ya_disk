"""Анализ результатов синхронизации из логов"""
import re
from pathlib import Path

def analyze_sync_log():
    log_file = Path("logs/sync_ya_disk.log")

    if not log_file.exists():
        print(f"Файл {log_file} не найден")
        return

    # Счетчики
    downloaded = 0
    converted = 0
    skipped_video = 0
    skipped_images = 0
    errors = 0

    # Читаем лог
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if 'SUCCESS' in line and ('Скачан:' in line or 'скачан' in line.lower()):
                downloaded += 1
            elif 'Конвертирован в MD:' in line:
                converted += 1
            elif 'Пропущено (видео):' in line:
                skipped_video += 1
            elif 'Пропущено (изображение):' in line or 'Пропущено (картинка):' in line:
                skipped_images += 1
            elif 'ERROR' in line:
                errors += 1

    # Выводим результаты
    print("=" * 80)
    print("АНАЛИЗ РЕЗУЛЬТАТОВ СИНХРОНИЗАЦИИ")
    print("=" * 80)
    print(f"Скачано файлов: {downloaded}")
    print(f"Конвертировано в Markdown: {converted}")
    print(f"Пропущено видео: {skipped_video}")
    print(f"Пропущено изображений: {skipped_images}")
    print(f"Ошибок: {errors}")
    print()

    # Читаем статистику из file_statistics.txt
    stats_file = Path("file_statistics.txt")
    if stats_file.exists():
        with open(stats_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Ищем строку "Всего файлов:"
            match = re.search(r'Всего файлов:\s*(\d+)', content)
            if match:
                total_files = int(match.group(1))
                print(f"Всего файлов на Яндекс.Диске: {total_files}")
                print(f"Успешно синхронизировано: {downloaded} из {total_files} ({downloaded/total_files*100:.1f}%)")
                print(f"Не синхронизировано: {total_files - downloaded} файлов")

    print("=" * 80)

    # Проверяем наличие базы данных
    db_file = Path("localdata/metadata/sync_metadata.db")
    if db_file.exists():
        print(f"\nБаза данных метаданных: {db_file}")
        print(f"Размер БД: {db_file.stat().st_size / 1024 / 1024:.2f} МБ")

if __name__ == "__main__":
    analyze_sync_log()
