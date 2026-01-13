"""
Синхронизация с Яндекс Диском через библиотеку yadisk
Скачивает файлы через сохранение публичной папки на свой диск
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
    LOGS_DIR / "yadisk_sync.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    compression="zip"
)

# Конфигурация
TOKEN = os.getenv('Token')
PUBLIC_URL = "https://disk.yandex.ru/d/_JeaJNmm6UeQVA"
DOWNLOAD_DIR = Path("yadisk_downloads")
TEMP_DISK_PATH = "disk:/YaDisk_Sync_Temp"


class YaDiskDownloader:
    def __init__(self, token, download_dir=DOWNLOAD_DIR):
        """Инициализация загрузчика"""
        self.token = token
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)

        # Создаем клиент без Client ID (работает только для чтения с токеном)
        self.client = yadisk.YaDisk(token=token)

    def check_connection(self):
        """Проверяет соединение и токен"""
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

    def save_public_to_disk(self, public_url, disk_path):
        """Сохраняет публичную папку на свой диск"""
        try:
            logger.info(f"Сохранение публичной папки на диск: {disk_path}")

            # Удаляем старую копию если есть
            if self.client.exists(disk_path):
                logger.info(f"Удаление старой копии: {disk_path}")
                self.client.remove(disk_path, permanently=True)

            # Сохраняем публичную папку
            result = self.client.save_to_disk(public_url, save_path=disk_path)

            # Проверяем, асинхронная ли операция
            if hasattr(result, 'href'):
                logger.info("Операция выполняется асинхронно, ожидание...")
                # Ждем завершения операции
                operation = self.client.get_operation_status(result.href)
                while operation.status == "in-progress":
                    import time
                    time.sleep(1)
                    operation = self.client.get_operation_status(result.href)

                if operation.status == "success":
                    logger.success(f"Папка сохранена на диск: {disk_path}")
                else:
                    logger.error(f"Операция не удалась: {operation.status}")
                    return False
            else:
                logger.success(f"Папка сохранена на диск: {disk_path}")
            return True

        except yadisk.exceptions.ForbiddenError:
            logger.error("Владелец запретил сохранение папки на другие диски")
            return False
        except Exception as e:
            logger.error(f"Ошибка при сохранении: {e}")
            return False

    def download_from_disk(self, disk_path, local_path, progress=True):
        """Рекурсивно скачивает папку со своего диска"""
        local_path = Path(local_path)
        local_path.mkdir(parents=True, exist_ok=True)

        try:
            # Получаем содержимое папки
            items = list(self.client.listdir(disk_path))

            logger.info(f"Найдено элементов: {len(items)}")

            for item in items:
                item_disk_path = f"{disk_path}/{item.name}"
                item_local_path = local_path / item.name

                if item.type == "dir":
                    # Рекурсивно обрабатываем подпапку
                    logger.info(f"Обработка папки: {item.name}")
                    self.download_from_disk(item_disk_path, item_local_path, progress)
                else:
                    # Скачиваем файл
                    self.download_file(item_disk_path, item_local_path, item.size)

        except Exception as e:
            logger.error(f"Ошибка при обходе {disk_path}: {e}")

    def download_file(self, disk_path, local_path, file_size):
        """Скачивает один файл с прогресс-баром"""
        try:
            logger.info(f"Скачивание: {local_path.name} ({self.format_size(file_size)})")

            with tqdm(
                total=file_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                desc=local_path.name[:30],
                leave=False
            ) as pbar:
                def callback(monitor):
                    pbar.update(monitor.bytes_read - pbar.n)

                self.client.download(disk_path, str(local_path), progress=callback)

            logger.success(f"Скачан: {local_path.name} ({self.format_size(file_size)})")

        except Exception as e:
            logger.error(f"Ошибка скачивания {local_path.name}: {e}")

    def download_public_folder(self, public_url, subfolder=None):
        """
        Основной метод: сохраняет публичную папку на диск и скачивает

        :param public_url: Публичная ссылка на папку
        :param subfolder: Конкретная подпапка для скачивания (опционально)
        """
        logger.info("=" * 60)
        logger.info("Начало синхронизации с Яндекс.Диском (yadisk)")
        logger.info("=" * 60)
        logger.info(f"Публичная ссылка: {public_url}")

        if subfolder:
            logger.info(f"Подпапка: {subfolder}")
            full_url = f"{public_url}:/{subfolder}"
            temp_path = f"{TEMP_DISK_PATH}/{subfolder}"
            local_path = self.download_dir / subfolder
        else:
            full_url = public_url
            temp_path = TEMP_DISK_PATH
            local_path = self.download_dir

        logger.info(f"Локальная папка: {local_path.absolute()}")
        logger.info("")

        # Шаг 1: Сохраняем на свой диск
        logger.info("Шаг 1: Сохранение публичной папки на ваш диск...")
        if not self.save_public_to_disk(full_url, temp_path):
            logger.error("Не удалось сохранить папку на диск")
            logger.info("")
            logger.info("Возможные причины:")
            logger.info("  1. Владелец запретил 'Сохранение на диск'")
            logger.info("  2. Недостаточно места на диске")
            logger.info("  3. Проблемы с токеном")
            logger.info("")
            logger.info("Попробуйте другие решения из SOLUTIONS.md")
            return False

        logger.info("")

        # Шаг 2: Скачиваем со своего диска
        logger.info("Шаг 2: Скачивание файлов с вашего диска...")
        self.download_from_disk(temp_path, local_path)

        logger.info("")

        # Шаг 3: Очистка временной папки
        logger.info("Шаг 3: Удаление временной копии с диска...")
        try:
            self.client.remove(TEMP_DISK_PATH, permanently=True)
            logger.success("Временная копия удалена")
        except Exception as e:
            logger.warning(f"Не удалось удалить временную копию: {e}")

        logger.info("")
        logger.info("=" * 60)
        logger.success("Синхронизация завершена!")
        logger.info("=" * 60)
        logger.info(f"Файлы сохранены в: {local_path.absolute()}")

        return True

    @staticmethod
    def format_size(size):
        """Форматирует размер файла в читаемый вид"""
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

    # Создаем загрузчик
    downloader = YaDiskDownloader(TOKEN)

    # Проверяем соединение
    if not downloader.check_connection():
        return

    logger.info("")

    # Можно указать конкретную подпапку через аргумент
    subfolder = None
    if len(sys.argv) > 1:
        subfolder = sys.argv[1]

    # Скачиваем
    success = downloader.download_public_folder(PUBLIC_URL, subfolder)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
