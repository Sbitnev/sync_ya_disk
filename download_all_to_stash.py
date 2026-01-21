"""
Скрипт для выгрузки ВСЕХ файлов с Яндекс.Диска в папку stash/

Скачивает все файлы без фильтрации, конвертации и использования БД.
Просто полная выгрузка всего содержимого диска.
"""
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Устанавливаем кодировку для консоли Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'ignore')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'ignore')

# Загружаем переменные окружения
load_dotenv()

# Импортируем необходимые модули
from src import config
from src.token_manager import TokenManager
from src.utils import sanitize_path, format_size


class StashDownloader:
    """Загрузчик всех файлов с Яндекс.Диска в stash/"""

    def __init__(self, token_manager, output_dir="stash"):
        self.token_manager = token_manager
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Счетчики
        self.total_downloaded_bytes = 0
        self.download_lock = Lock()

        # HTTP сессия
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0
        )
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)

    def _request_with_retry(self, method, url, max_retries=3, **kwargs):
        """Выполняет HTTP запрос с повторными попытками"""
        for attempt in range(max_retries):
            try:
                response = getattr(self.session, method)(url, timeout=30, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Ошибка запроса (попытка {attempt + 1}/{max_retries})")
                    time.sleep(2 * (attempt + 1))
                    continue
                else:
                    logger.error(f"Ошибка после {max_retries} попыток: {e}")
                    return None
        return None

    def get_user_resources(self, path, limit=1000):
        """
        Получает ресурсы с диска с поддержкой пагинации

        :param path: Путь к папке на диске
        :param limit: Количество элементов на страницу
        :return: Данные ресурса
        """
        url = "https://cloud-api.yandex.net/v1/disk/resources"
        headers = {"Authorization": f"OAuth {self.token_manager.token}"}

        all_items = []
        offset = 0

        while True:
            params = {
                "path": path,
                "limit": limit,
                "offset": offset
            }

            response = self._request_with_retry('get', url, headers=headers, params=params)
            if not response:
                break

            data = response.json()

            if '_embedded' in data and 'items' in data['_embedded']:
                items = data['_embedded']['items']
                all_items.extend(items)

                if len(items) < limit:
                    break

                offset += limit
            else:
                break

        if all_items:
            return {
                '_embedded': {'items': all_items},
                'type': 'dir',
                'name': data.get('name', ''),
                'path': path
            }

        return None

    def get_all_files_recursive(self, path="/", relative_path=""):
        """
        Рекурсивно получает все файлы с диска

        :param path: Путь на диске
        :param relative_path: Относительный путь для локального сохранения
        :return: Список всех файлов
        """
        files_list = []
        folders_to_process = []

        logger.debug(f"Сканирование: {path}")
        data = self.get_user_resources(path)

        if not data:
            logger.warning(f"Папка пропущена: {path}")
            return files_list

        if '_embedded' in data and 'items' in data['_embedded']:
            items = data['_embedded']['items']

            for item in items:
                item_name = item['name']
                item_type = item['type']
                item_path = f"{relative_path}/{item_name}" if relative_path else item_name
                full_path = f"{path}/{item_name}" if path != "/" else f"/{item_name}"

                if item_type == 'dir':
                    folders_to_process.append((full_path, item_path))
                else:
                    file_info = {
                        'name': item_name,
                        'path': item_path,
                        'full_path': full_path,
                        'size': item.get('size', 0),
                        'modified': item.get('modified', ''),
                        'md5': item.get('md5', '')
                    }
                    files_list.append(file_info)

            # Обрабатываем вложенные папки
            for folder_path, folder_rel_path in folders_to_process:
                nested_files = self.get_all_files_recursive(folder_path, folder_rel_path)
                files_list.extend(nested_files)

        return files_list

    def get_download_link(self, path):
        """
        Получает ссылку на скачивание файла

        :param path: Путь к файлу на диске
        :return: URL для скачивания
        """
        url = "https://cloud-api.yandex.net/v1/disk/resources/download"
        headers = {"Authorization": f"OAuth {self.token_manager.token}"}
        params = {"path": path}

        response = self._request_with_retry('get', url, headers=headers, params=params)
        if response:
            data = response.json()
            return data.get('href')
        return None

    def download_file(self, file_info):
        """
        Скачивает файл

        :param file_info: Информация о файле
        :return: True если успешно
        """
        # Создаем путь для сохранения
        safe_path = sanitize_path(file_info['path'])
        local_path = self.output_dir / safe_path
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Проверяем, существует ли файл уже
        if local_path.exists():
            existing_size = local_path.stat().st_size
            if existing_size == file_info['size']:
                logger.debug(f"Файл уже существует: {file_info['path']}")
                return True

        # Получаем ссылку на скачивание
        download_url = self.get_download_link(file_info['full_path'])

        if not download_url:
            logger.warning(f"Не удалось получить ссылку: {file_info['path']}")
            return False

        # Скачиваем файл
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(download_url, stream=True, timeout=30)
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))

                with open(local_path, 'wb') as f:
                    with tqdm(
                        total=total_size,
                        unit='B',
                        unit_scale=True,
                        unit_divisor=1024,
                        desc=file_info['name'][:30],
                        leave=False
                    ) as pbar:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            pbar.update(len(chunk))

                with self.download_lock:
                    self.total_downloaded_bytes += file_info['size']

                logger.success(f"Скачан: {file_info['path']} ({format_size(file_info['size'])})")
                return True

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Ошибка при скачивании (попытка {attempt + 1}/{max_retries})")
                    time.sleep(2 * (attempt + 1))
                    if local_path.exists():
                        local_path.unlink()
                    continue
                else:
                    logger.error(f"Не удалось скачать {file_info['path']}: {e}")
                    if local_path.exists():
                        local_path.unlink()
                    return False

        return False

    def download_all(self, max_workers=5):
        """
        Скачивает все файлы с диска

        :param max_workers: Количество параллельных загрузок
        """
        logger.info("=" * 70)
        logger.info("ВЫГРУЗКА ВСЕХ ФАЙЛОВ С ЯНДЕКС.ДИСКА В STASH/")
        logger.info("=" * 70)
        logger.info(f"Директория для скачивания: {self.output_dir.absolute()}")

        # Получаем список всех файлов
        logger.info("Получение списка файлов с диска...")
        all_files = self.get_all_files_recursive("/")

        if not all_files:
            logger.warning("Файлы не найдены")
            return

        logger.info(f"Найдено файлов: {len(all_files)}")

        # Подсчитываем общий размер
        total_size = sum(f['size'] for f in all_files)
        logger.info(f"Общий размер: {format_size(total_size)}")

        # Фильтруем уже скачанные файлы
        files_to_download = []
        for file_info in all_files:
            safe_path = sanitize_path(file_info['path'])
            local_path = self.output_dir / safe_path

            if local_path.exists():
                existing_size = local_path.stat().st_size
                if existing_size == file_info['size']:
                    continue

            files_to_download.append(file_info)

        logger.info(f"Файлов к скачиванию: {len(files_to_download)}")
        logger.info(f"Уже скачано: {len(all_files) - len(files_to_download)}")

        if not files_to_download:
            logger.success("Все файлы уже скачаны!")
            return

        # Скачиваем файлы
        logger.info(f"Начинаем загрузку ({max_workers} потоков)...")
        logger.info("=" * 70)

        success_count = 0
        failed_count = 0
        failed_files = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.download_file, file_info): file_info
                for file_info in files_to_download
            }

            with tqdm(total=len(files_to_download), desc="Общий прогресс", unit="файл") as pbar:
                for future in as_completed(futures):
                    file_info = futures[future]
                    try:
                        if future.result():
                            success_count += 1
                        else:
                            failed_count += 1
                            failed_files.append(file_info['path'])
                    except Exception as e:
                        logger.error(f"Ошибка обработки {file_info['path']}: {e}")
                        failed_count += 1
                        failed_files.append(file_info['path'])

                    pbar.update(1)

        # Итоговая статистика
        logger.info("=" * 70)
        logger.success("ВЫГРУЗКА ЗАВЕРШЕНА!")
        logger.info("=" * 70)
        logger.info(f"Успешно скачано: {success_count}")
        logger.info(f"Ошибок: {failed_count}")
        logger.info(f"Уже было скачано: {len(all_files) - len(files_to_download)}")
        logger.info(f"Всего файлов: {len(all_files)}")
        logger.info(f"Скачано данных: {format_size(self.total_downloaded_bytes)}")
        logger.info("=" * 70)

        if failed_files:
            failed_log = Path("stash_failed.txt")
            with open(failed_log, 'w', encoding='utf-8') as f:
                f.write('\n'.join(failed_files))
            logger.warning(f"Список неудачных файлов: {failed_log.absolute()}")


def setup_logging():
    """Настройка логирования"""
    logger.remove()

    # Логирование в консоль
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
        colorize=True
    )

    # Логирование в файл
    logger.add(
        "stash_download.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days"
    )


def main():
    """Главная функция"""
    setup_logging()

    # Валидация конфигурации
    try:
        config.validate_config()
    except ValueError as e:
        logger.error(str(e))
        return 1

    # Создаем менеджер токенов
    logger.info("Инициализация менеджера токенов...")
    try:
        token_manager = TokenManager(
            client_id=config.CLIENT_ID,
            client_secret=config.CLIENT_SECRET,
            user_id=config.USER_ID,
            token_lifetime=config.TOKEN_LIFETIME,
            refresh_before=config.TOKEN_REFRESH_BEFORE
        )
    except Exception as e:
        logger.error(f"Ошибка при создании менеджера токенов: {e}")
        return 1

    # Создаем загрузчик и запускаем выгрузку
    try:
        downloader = StashDownloader(token_manager, output_dir="stash")
        downloader.download_all(max_workers=5)
        return 0
    except KeyboardInterrupt:
        logger.warning("Выгрузка прервана пользователем")
        return 130
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
