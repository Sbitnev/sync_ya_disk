"""
Конфигурация для синхронизации Яндекс.Диска
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# === Учетные данные ===
# Административный токен для получения информации о пользователях
ADMIN_TOKEN = os.getenv('YANDEX_ADMIN_TOKEN')
ORG_ID = os.getenv('YANDEX_ORG_ID')

# Данные сервисного приложения для Token Exchange
CLIENT_ID = os.getenv('ClientID')
CLIENT_SECRET = os.getenv('Client_secret')

# ID или email пользователя, чей диск синхронизируем
USER_ID = os.getenv('USER_ID', '1130000057842996')
USER_EMAIL = os.getenv('USER_EMAIL', 'tn@imprice.ai')

# === Пути ===
# Папка на диске пользователя для синхронизации
REMOTE_FOLDER_PATH = "/Клиенты"

# Локальная папка для скачивания
DOWNLOAD_DIR = "downloaded_files"

# Файл с метаданными о синхронизации
METADATA_FILE = "sync_metadata.json"

# Папка для логов
LOGS_DIR = Path("logs")

# === Ограничения на файлы ===
# Пропускать видео файлы (создавать пустые)
SKIP_VIDEO_FILES = True

# Расширения видео файлов
VIDEO_EXTENSIONS = [
    '.mp4', '.avi', '.mov', '.mkv', '.webm',
    '.flv', '.wmv', '.m4v', '.mpg', '.mpeg',
    '.3gp', '.ogv', '.vob', '.ts'
]

# Максимальный размер файла для скачивания (в байтах)
# Файлы больше этого размера будут пропущены (создан пустой файл)
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 МБ

# Пропускать файлы больше MAX_FILE_SIZE
SKIP_LARGE_FILES = True

# Максимальный общий размер скачиваемых файлов (в байтах)
# После превышения все файлы создаются пустыми
MAX_TOTAL_SIZE = 10 * 1024 * 1024 * 1024  # 10 ГБ

# Применять ограничение на общий размер
ENABLE_TOTAL_SIZE_LIMIT = True

# === Параметры синхронизации ===
# Количество потоков для параллельной загрузки
MAX_WORKERS = 5

# Максимальное количество попыток при ошибках сети
MAX_RETRIES = 3

# Задержка между попытками (секунды)
RETRY_DELAY = 2

# Таймаут для сетевых запросов (секунды)
REQUEST_TIMEOUT = 30

# === Токен ===
# Время жизни токена Token Exchange (секунды)
TOKEN_LIFETIME = 3600  # 1 час

# Обновлять токен за N секунд до истечения
TOKEN_REFRESH_BEFORE = 300  # 5 минут


def validate_config():
    """Проверяет наличие обязательных настроек"""
    errors = []

    if not CLIENT_ID:
        errors.append("CLIENT_ID не найден в .env")

    if not CLIENT_SECRET:
        errors.append("CLIENT_SECRET не найден в .env")

    if not USER_ID and not USER_EMAIL:
        errors.append("USER_ID или USER_EMAIL должен быть указан")

    if errors:
        raise ValueError("Ошибки конфигурации:\n" + "\n".join(f"  - {e}" for e in errors))


def print_config_summary():
    """Выводит краткую информацию о конфигурации"""
    print("=" * 70)
    print("КОНФИГУРАЦИЯ СИНХРОНИЗАЦИИ")
    print("=" * 70)
    print(f"Пользователь: {USER_EMAIL} (ID: {USER_ID})")
    print(f"Удаленная папка: {REMOTE_FOLDER_PATH}")
    print(f"Локальная папка: {DOWNLOAD_DIR}")
    print()
    print("Ограничения:")
    print(f"  • Видео файлы: {'пропускать' if SKIP_VIDEO_FILES else 'скачивать'}")
    print(f"  • Большие файлы (>{format_size(MAX_FILE_SIZE)}): {'пропускать' if SKIP_LARGE_FILES else 'скачивать'}")
    print(f"  • Общий лимит: {format_size(MAX_TOTAL_SIZE) if ENABLE_TOTAL_SIZE_LIMIT else 'нет'}")
    print()
    print(f"Параллельных потоков: {MAX_WORKERS}")
    print("=" * 70)


def format_size(size):
    """Форматирует размер в читаемый вид"""
    for unit in ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} ПБ"
