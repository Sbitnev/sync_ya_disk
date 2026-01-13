"""
Прямое скачивание файлов из публичной папки через yadisk
Работает только для файлов с public_url
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import yadisk
from tqdm import tqdm
from loguru import logger

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO",
    colorize=True
)
logger.add(
    LOGS_DIR / "yadisk_direct.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    compression="zip"
)

# Конфигурация
TOKEN = os.getenv('Token')
PUBLIC_URL = "https://disk.yandex.ru/d/_JeaJNmm6UeQVA"
DOWNLOAD_DIR = Path("yadisk_direct_downloads")


class YaDiskDirectDownloader:
    def __init__(self, token, download_dir=DOWNLOAD_DIR):
        """Инициализация загрузчика"""
        self.token = token
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.client = yadisk.YaDisk(token=token)

        self.stats = {
            'total': 0,
            'downloaded': 0,
            'skipped_no_url': 0,
            'failed': 0
        }

    def check_connection(self):
        """Проверяет соединение"""
        try:
            if self.client.check_token():
                logger.info("Токен действителен")
                return True
            else:
                logger.error("Токен недействителен")
                return False
        except Exception as e:
            logger.error(f"Ошибка проверки токена: {e}")
            return False

    def get_all_files_recursive(self, public_key, path=""):
        """Рекурсивно получает список всех файлов"""
        files = []

        try:
            # Получаем метаданные
            if path:
                meta = self.client.get_public_meta(public_key, path=path)
            else:
                meta = self.client.get_public_meta(public_key)

            # Обрабатываем содержимое
            if hasattr(meta, 'embedded') and meta.embedded:
                for item in meta.embedded.items:
                    item_path = f"{path}/{item.name}" if path else item.name

                    if item.type == "dir":
                        # Рекурсивно обходим папку
                        files.extend(self.get_all_files_recursive(public_key, item_path))
                    else:
                        # Добавляем файл
                        files.append({
                            'name': item.name,
                            'path': item_path,
                            'size': item.size if hasattr(item, 'size') else 0,
                            'public_url': item.public_url if hasattr(item, 'public_url') else None,
                            'file': item.file if hasattr(item, 'file') else None
                        })
        except Exception as e:
            logger.error(f"Ошибка при обходе {path}: {e}")

        return files

    def download_file(self, file_info):
        """Скачивает один файл"""
        local_path = self.download_dir / file_info['path']
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Проверяем, есть ли прямая ссылка
        if file_info.get('file'):
            try:
                logger.info(f"Скачивание: {file_info['name']} (прямая ссылка)")

                with tqdm(
                    total=file_info['size'],
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=file_info['name'][:30],
                    leave=False
                ) as pbar:
                    import requests
                    response = requests.get(file_info['file'], stream=True)
                    response.raise_for_status()

                    with open(local_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            pbar.update(len(chunk))

                logger.success(f"Скачан: {file_info['name']}")
                self.stats['downloaded'] += 1
                return True
            except Exception as e:
                logger.error(f"Ошибка скачивания {file_info['name']}: {e}")
                self.stats['failed'] += 1
                return False

        # Пробуем через public_url
        elif file_info.get('public_url'):
            try:
                logger.info(f"Скачивание: {file_info['name']} (public_url)")

                with tqdm(
                    total=file_info['size'],
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=file_info['name'][:30],
                    leave=False
                ) as pbar:
                    def callback(monitor):
                        pbar.update(monitor.bytes_read - pbar.n)

                    self.client.download_public(
                        file_info['public_url'],
                        str(local_path),
                        progress=callback
                    )

                logger.success(f"Скачан: {file_info['name']}")
                self.stats['downloaded'] += 1
                return True
            except Exception as e:
                logger.error(f"Ошибка скачивания {file_info['name']}: {e}")
                self.stats['failed'] += 1
                return False
        else:
            logger.warning(f"Пропущен (нет ссылки): {file_info['name']}")
            self.stats['skipped_no_url'] += 1
            return False

    def download_public_folder(self, public_url):
        """Скачивает все доступные файлы из публичной папки"""
        logger.info("=" * 60)
        logger.info("Прямое скачивание через yadisk")
        logger.info("=" * 60)
        logger.info(f"Публичная ссылка: {public_url}")
        logger.info(f"Локальная папка: {self.download_dir.absolute()}")
        logger.info("")

        # Получаем список файлов
        logger.info("Получение списка файлов...")
        files = self.get_all_files_recursive(public_url)

        self.stats['total'] = len(files)
        logger.info(f"Найдено файлов: {len(files)}")
        logger.info("")

        if not files:
            logger.warning("Файлы не найдены")
            return

        # Скачиваем файлы
        logger.info("Начало скачивания...")
        for file_info in files:
            self.download_file(file_info)

        # Итоги
        logger.info("")
        logger.info("=" * 60)
        logger.info("СТАТИСТИКА")
        logger.info("=" * 60)
        logger.info(f"Всего файлов: {self.stats['total']}")
        logger.info(f"Скачано: {self.stats['downloaded']}")
        logger.info(f"Пропущено (нет ссылки): {self.stats['skipped_no_url']}")
        logger.info(f"Ошибки: {self.stats['failed']}")

        if self.stats['downloaded'] > 0:
            logger.success(f"Файлы сохранены в: {self.download_dir.absolute()}")

    @staticmethod
    def format_size(size):
        """Форматирует размер"""
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} ТБ"


def main():
    """Главная функция"""
    if not TOKEN:
        logger.error("Токен не найден в .env файле")
        return

    downloader = YaDiskDirectDownloader(TOKEN)

    if not downloader.check_connection():
        return

    logger.info("")
    downloader.download_public_folder(PUBLIC_URL)


if __name__ == "__main__":
    main()
