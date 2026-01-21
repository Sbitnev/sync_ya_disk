"""
Конфигурация для синхронизации Яндекс.Диска
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# === Учетные данные ===
# Административный токен для получения информации о пользователях
ADMIN_TOKEN = os.getenv("YANDEX_ADMIN_TOKEN")
ORG_ID = os.getenv("YANDEX_ORG_ID")

# Данные сервисного приложения для Token Exchange
CLIENT_ID = os.getenv("ClientID")
CLIENT_SECRET = os.getenv("Client_secret")

# ID или email пользователя, чей диск синхронизируем
USER_ID = os.getenv("USER_ID", "1130000057842996")
USER_EMAIL = os.getenv("USER_EMAIL", "tn@imprice.ai")

# === Пути ===
# Папка на диске пользователя для синхронизации
# Используется в run.py (основная синхронизация) и run_stash_download.py (полная выгрузка)
# Для тестов: "/Клиенты/SOKOLOV"
# Для продакшена: "/Клиенты"
# Для выгрузки всего диска: "/"
REMOTE_FOLDER_PATH = "/Клиенты"

# Базовая папка для всех данных (кроме логов)
LOCALDATA_DIR = Path("localdata")

# Локальная папка для скачивания
DOWNLOAD_DIR = LOCALDATA_DIR / "downloaded_files"

# База данных с метаданными о синхронизации
METADATA_DIR = LOCALDATA_DIR / "metadata"
METADATA_DB_PATH = METADATA_DIR / "sync_metadata.db"

# Файл с неудачными загрузками
FAILED_DOWNLOADS_PATH = LOCALDATA_DIR / "failed_downloads.txt"

# Папка для логов
LOGS_DIR = Path("logs")

# === Ограничения на файлы ===
# Пропускать видео файлы (не загружать и не обрабатывать)
SKIP_VIDEO_FILES = True

# Расширения видео файлов
VIDEO_EXTENSIONS = [
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".webm",
    ".flv",
    ".wmv",
    ".m4v",
    ".mpg",
    ".mpeg",
    ".3gp",
    ".ogv",
    ".vob",
    ".ts",
]

# Пропускать файлы изображений (не загружать и не обрабатывать)
SKIP_IMAGE_FILES = True

# Расширения файлов изображений
IMAGE_EXTENSIONS = [
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
    ".svg",
    ".webp",
    ".ico",
]

# Пропускать Parquet файлы (не загружать и не обрабатывать)
# Parquet - колоночный формат для BigData, увеличивается в 17-18 раз при конвертации в CSV
# Рекомендуется работать с ними напрямую через pandas/DuckDB
SKIP_PARQUET_FILES = True

# Расширения Parquet файлов
PARQUET_EXTENSIONS = [
    ".parquet",
]

# Максимальный размер файла для скачивания (в байтах)
# Файлы больше этого размера будут пропущены (создан пустой файл)
MAX_FILE_SIZE = 1024 * 1024 * 1024  # 1 Гб

# Максимальный размер для табличных файлов (CSV, Excel, Parquet)
# При обработке табличных данных используется минимум из MAX_FILE_SIZE и MAX_TABULAR_FILE_SIZE
# Это позволяет установить отдельный лимит для табличных данных
MAX_TABULAR_FILE_SIZE = 3 * 1024 * 1024  # 3 МБ

# Пропускать файлы больше MAX_FILE_SIZE
SKIP_LARGE_FILES = True

# Максимальный общий размер скачиваемых файлов (в байтах)
# После превышения все последующие файлы пропускаются (не скачиваются)
MAX_TOTAL_SIZE = 100 * 1024 * 1024 * 1024  # 100 ГБ

# Применять ограничение на общий размер
ENABLE_TOTAL_SIZE_LIMIT = True

# === Параметры синхронизации ===
# Режим ручного выбора папок для синхронизации
# Если включен, перед синхронизацией будет показан список папок с анализом
MANUAL_MODE = False

# Минимальное свободное место на диске (ГБ)
# Если места меньше, синхронизация будет остановлена
MIN_FREE_SPACE_GB = int(os.getenv("MIN_FREE_SPACE_GB", "5"))

# Паттерны файлов для пропуска (временные и служебные файлы)
SKIP_FILE_PATTERNS = [
    r'^~\$',            # Временные Office файлы (~$filename.docx)
    r'^~WRL.*\.tmp$',   # Временные Word файлы (~WRL1234.tmp)
    r'\.tmp$',          # Все .tmp файлы
    r'\.temp$',         # Временные файлы
    r'\.drawio$',       # Диаграммы Draw.io
    r'\.drawio\.bkp$',  # Резервные копии Draw.io
    r'\.drawio\.dtmp$', # Временные Draw.io
    r'\.mpp$',          # Microsoft Project (пока не поддерживается)
    r'^\.~',            # Скрытые временные файлы (.~lock)
    r'^\._',            # macOS временные файлы (._filename)
]

# Количество потоков для параллельной загрузки файлов
MAX_WORKERS = 5

# Количество потоков для полной выгрузки в stash (более агрессивная загрузка)
STASH_DOWNLOAD_WORKERS = 15

# Количество потоков для параллельного получения списка файлов из папок
# Увеличено для более быстрого сканирования структуры
FOLDER_SCAN_WORKERS = 20

# Максимальное количество попыток при ошибках сети
MAX_RETRIES = 3

# Задержка между попытками (секунды)
RETRY_DELAY = 2

# Таймаут для сетевых запросов (секунды)
REQUEST_TIMEOUT = 30

# Таймаут для операций сканирования папок (секунды)
# Меньше чем REQUEST_TIMEOUT т.к. запрос списка файлов быстрый
FOLDER_SCAN_TIMEOUT = 15

# Размер connection pool для HTTP сессии
HTTP_POOL_CONNECTIONS = 30
HTTP_POOL_MAXSIZE = 50

# Размер chunk для загрузки файлов (байты)
# Увеличенный размер chunk для более быстрой загрузки больших файлов
DOWNLOAD_CHUNK_SIZE = 1024 * 1024  # 1 МБ (было 8 КБ)

# === Кэширование ===
# Включить кэширование списка файлов (ускоряет повторные запуски)
ENABLE_FILES_CACHE = True

# Время жизни кэша списка файлов (секунды)
# После этого времени кэш считается устаревшим и обновляется
FILES_CACHE_LIFETIME = 300  # 5 минут

# === Токен ===
# Время жизни токена Token Exchange (секунды)
TOKEN_LIFETIME = 3600  # 1 час

# Обновлять токен за N секунд до истечения
TOKEN_REFRESH_BEFORE = 300  # 5 минут

# === Конвертация в Markdown ===
# Включить конвертацию файлов в Markdown
# Установите False чтобы полностью отключить конвертацию всех файлов
ENABLE_MARKDOWN_CONVERSION = True
# ENABLE_MARKDOWN_CONVERSION = False

# Папка для сохранения конвертированных markdown файлов
MARKDOWN_OUTPUT_DIR = LOCALDATA_DIR / "markdown_files"

# Конвертировать Word документы (.docx, .doc)
CONVERT_WORD_FILES = True
# Заменять изображения в документах на текстовые заглушки
REPLACE_IMAGES_WITH_PLACEHOLDERS = True

# Конвертировать CSV файлы
CONVERT_CSV_FILES = True

# Максимальное количество строк в CSV для отображения в markdown (None = без ограничений)
CSV_MAX_ROWS = None

# Максимальное количество столбцов в CSV для отображения (None = без ограничений)
CSV_MAX_COLUMNS = None

# Конвертировать Excel файлы (.xlsx, .xls, .xlsm, .xlsb) в CSV
CONVERT_EXCEL_FILES = True
EXCEL_TO_CSV = True  # Сохранять как CSV вместо Markdown

# Максимальное количество строк в Excel для отображения в markdown (None = без ограничений)
EXCEL_MAX_ROWS = None

# Максимальное количество столбцов в Excel для отображения (None = без ограничений)
EXCEL_MAX_COLUMNS = None

# Максимальное количество листов Excel для конвертации (None = без ограничений)
EXCEL_MAX_SHEETS = None

# Конвертировать PDF файлы
CONVERT_PDF_FILES = True

# Максимальное количество страниц PDF для конвертации
PDF_MAX_PAGES = 100

# Конвертировать текстовые файлы и код (.txt, .md, .py, .json, .xml, .avsc, .j2)
CONVERT_TEXT_FILES = True

# Конвертировать PowerPoint презентации (.pptx, .ppt)
CONVERT_POWERPOINT_FILES = True

# Конвертировать HTML файлы (.html, .htm)
CONVERT_HTML_FILES = True

# Конвертировать Parquet файлы (.parquet) в CSV
# ОТКЛЮЧЕНО: Parquet файлы увеличиваются в 17-18 раз при конвертации в CSV
# Рекомендуется работать с ними напрямую через pandas/DuckDB
CONVERT_PARQUET_FILES = False
PARQUET_TO_CSV = True  # Сохранять как CSV вместо Markdown

# Максимальное количество строк в Parquet для отображения в markdown (None = без ограничений)
PARQUET_MAX_ROWS = None

# Максимальное количество столбцов в Parquet для отображения (None = без ограничений)
PARQUET_MAX_COLUMNS = None

# Конвертировать RTF файлы (.rtf)
CONVERT_RTF_FILES = True

# Конвертировать архивы (.zip, .7z, .rar, .tar, .gz)
CONVERT_ARCHIVE_FILES = True

# Максимальная глубина вложенности архивов (защита от бесконечной рекурсии)
ARCHIVE_MAX_DEPTH = 10

# Конвертировать видео файлы в текст через транскрибацию
CONVERT_VIDEO_FILES = False  # Отключено: видео полностью пропускаются

# Максимальный размер видео для транскрибации (в байтах)
VIDEO_MAX_SIZE = 500 * 1024 * 1024  # 500 МБ

# Максимальное время ожидания транскрибации (секунды)
VIDEO_TRANSCRIPTION_TIMEOUT = 600  # 10 минут

# Асинхронная обработка видео
VIDEO_ASYNC_TRANSCRIPTION = (
    True  # Запускать транскрибацию асинхронно (не ждать завершения)
)

# Максимальное количество одновременных операций транскрибации
VIDEO_MAX_CONCURRENT_TRANSCRIPTIONS = 3  # Безопасный лимит для API

# Проверять незавершенные операции при запуске
VIDEO_CHECK_PENDING_ON_START = True  # Получать результаты из предыдущих запусков

# Ждать завершения всех транскрибаций перед завершением синхронизации
VIDEO_WAIT_FOR_COMPLETION = True  # Не завершать работу пока все видео не обработаются

# Интервал проверки статуса транскрибации (секунды)
VIDEO_CHECK_INTERVAL = 30  # Проверять каждые 30 секунд

# Удалять оригинальные файлы после конвертации
DELETE_ORIGINALS_AFTER_CONVERSION = (
    True  # Включено: оригиналы будут удалены после MD конвертации
)


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
        raise ValueError(
            "Ошибки конфигурации:\n" + "\n".join(f"  - {e}" for e in errors)
        )


def print_config_summary():
    """Выводит краткую информацию о конфигурации"""
    print("=" * 70)
    print("КОНФИГУРАЦИЯ СИНХРОНИЗАЦИИ")
    print("=" * 70)
    print(f"Пользователь: {USER_EMAIL} (ID: {USER_ID})")
    print(f"Удаленная папка: {REMOTE_FOLDER_PATH}")
    print(f"Локальная папка данных: {LOCALDATA_DIR}")
    print(f"Папка загрузок: {DOWNLOAD_DIR}")
    print()
    print("Ограничения:")
    print(f"  • Видео файлы: {'пропускать' if SKIP_VIDEO_FILES else 'скачивать'}")
    print(f"  • Файлы изображений: {'пропускать' if SKIP_IMAGE_FILES else 'скачивать'}")
    print(f"  • Parquet файлы: {'пропускать' if SKIP_PARQUET_FILES else 'скачивать'}")
    if SKIP_LARGE_FILES:
        # Показываем оба лимита если они различаются
        if MAX_FILE_SIZE != MAX_TABULAR_FILE_SIZE:
            tabular_limit = min(MAX_FILE_SIZE, MAX_TABULAR_FILE_SIZE)
            print(f"  • Большие файлы: пропускать (>{format_size(MAX_FILE_SIZE)})")
            print(f"  • Табличные файлы: пропускать (>{format_size(tabular_limit)})")
        else:
            print(f"  • Большие файлы (>{format_size(MAX_FILE_SIZE)}): пропускать")
    else:
        print(f"  • Большие файлы: скачивать")
    print(
        f"  • Общий лимит: {format_size(MAX_TOTAL_SIZE) if ENABLE_TOTAL_SIZE_LIMIT else 'нет'}"
    )
    print()
    print(f"Параллельных потоков загрузки: {MAX_WORKERS}")
    print(f"Параллельных потоков сканирования папок: {FOLDER_SCAN_WORKERS}")
    print(f"HTTP connection pool: {HTTP_POOL_CONNECTIONS}/{HTTP_POOL_MAXSIZE}")
    print(f"Режим ручного выбора папок: {'да' if MANUAL_MODE else 'нет'}")
    print()
    print("Конвертация в Markdown:")
    print(f"  • Включена: {'да' if ENABLE_MARKDOWN_CONVERSION else 'нет'}")
    if ENABLE_MARKDOWN_CONVERSION:
        print(f"  • Word документы: {'да' if CONVERT_WORD_FILES else 'нет'}")
        print(f"  • CSV файлы: {'да' if CONVERT_CSV_FILES else 'нет'}")
        print(f"  • Excel файлы: {'да' if CONVERT_EXCEL_FILES else 'нет'}")
        print(f"  • PDF файлы: {'да' if CONVERT_PDF_FILES else 'нет'}")
        print(f"  • Текстовые/код: {'да' if CONVERT_TEXT_FILES else 'нет'}")
        print(f"  • PowerPoint: {'да' if CONVERT_POWERPOINT_FILES else 'нет'}")
        print(f"  • HTML: {'да' if CONVERT_HTML_FILES else 'нет'}")
        print(f"  • Parquet: {'да' if CONVERT_PARQUET_FILES else 'нет'}")
        print(f"  • RTF: {'да' if CONVERT_RTF_FILES else 'нет'}")
        print(f"  • Archives: {'да' if CONVERT_ARCHIVE_FILES else 'нет'}")
        print(f"  • Видео (транскрибация): {'да' if CONVERT_VIDEO_FILES else 'нет'}")
        if CONVERT_VIDEO_FILES:
            print(f"    - Макс. размер: {format_size(VIDEO_MAX_SIZE)}")
            print(f"    - Таймаут: {VIDEO_TRANSCRIPTION_TIMEOUT}с")
            print(
                f"    - Асинхронная обработка: {'да' if VIDEO_ASYNC_TRANSCRIPTION else 'нет'}"
            )
            if VIDEO_ASYNC_TRANSCRIPTION:
                print(
                    f"    - Ждать завершения: {'да' if VIDEO_WAIT_FOR_COMPLETION else 'нет'}"
                )
                if VIDEO_WAIT_FOR_COMPLETION:
                    print(f"    - Интервал проверки: {VIDEO_CHECK_INTERVAL}с")
        print(f"  • Папка для MD: {MARKDOWN_OUTPUT_DIR}")
        print(
            f"  • Удалять оригиналы: {'да' if DELETE_ORIGINALS_AFTER_CONVERSION else 'нет'}"
        )
    print("=" * 70)


def format_size(size):
    """Форматирует размер в читаемый вид"""
    for unit in ["Б", "КБ", "МБ", "ГБ", "ТБ"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} ПБ"
