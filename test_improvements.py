"""
Тестовый скрипт для демонстрации улучшений
"""
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from main import YandexDiskSyncer

load_dotenv()

print("="*60)
print("ТЕСТ УЛУЧШЕННОГО СКРИПТА ВЫГРУЗКИ")
print("="*60)
print("\n✨ Новые возможности:")
print("  • Многопоточная загрузка (5 потоков)")
print("  • Автоматический retry при ошибках (до 3 попыток)")
print("  • Предварительная статистика по объему и количеству файлов")
print("  • Улучшенные прогресс-бары")
print("  • Пропуск больших файлов >300 МБ")
print("\n" + "="*60 + "\n")

public_url = "https://disk.yandex.ru/d/_JeaJNmm6UeQVA"

# Создаем синхронизатор с настройками
syncer = YandexDiskSyncer(
    public_url,
    download_dir="test_download_improved",
    skip_large_files=True,
    max_workers=5  # 5 параллельных потоков
)

# Запускаем синхронизацию
syncer.sync()

print("\n" + "="*60)
print("✓ ТЕСТ ЗАВЕРШЕН")
print("="*60)
