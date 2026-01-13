"""
Демонстрация логирования с loguru
"""
import sys
from pathlib import Path
from loguru import logger

# Создаем папку для логов
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Настройка логирования (как в main.py)
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO",
    colorize=True
)
logger.add(
    LOGS_DIR / "sync_ya_disk.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    compression="zip"
)

print("=" * 60)
print("ДЕМОНСТРАЦИЯ ЛОГИРОВАНИЯ С LOGURU")
print("=" * 60)
print()

# Разные уровни логирования
logger.debug("Это debug сообщение (не видно в консоли)")
logger.info("Начало синхронизации")
logger.info("Найдено файлов: 150")
logger.success("Создано папок: 42")
logger.warning("API не вернул ссылку на скачивание для некоторых файлов")
logger.success("Скачан: document.pdf (2.5 МБ)")
logger.info("Пропущено видео (создан пустой файл): video.mp4 (150.0 МБ)")
logger.error("Не удалось скачать файл после 3 попыток")
logger.success("Синхронизация завершена!")

print()
print("=" * 60)
print("Все сообщения также записаны в logs/sync_ya_disk.log")
print("=" * 60)
