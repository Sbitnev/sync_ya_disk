import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import time
from loguru import logger

# Устанавливаем кодировку для консоли
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'ignore')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'ignore')

# Загружаем переменные окружения из .env файла
load_dotenv()

# Создаем папку для логов, если её нет
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Настройка логирования
logger.remove()  # Удаляем стандартный обработчик
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

# Конфигурация
DOWNLOAD_DIR = "downloaded_files"
METADATA_FILE = "sync_metadata.json"
TOKEN = os.getenv('Token')
LARGE_FILE_SIZE = 300 * 1024 * 1024  # 300 МБ в байтах
MAX_WORKERS = 5  # Количество потоков для параллельной загрузки
MAX_RETRIES = 3  # Максимальное количество попыток для сетевых запросов
RETRY_DELAY = 2  # Задержка между попытками в секундах


class YandexDiskSyncer:
    def __init__(self, public_url, download_dir=DOWNLOAD_DIR, skip_large_files=False, max_workers=MAX_WORKERS):
        """
        Инициализация синхронизатора Яндекс Диска

        :param public_url: Публичная ссылка на Яндекс Диск
        :param download_dir: Директория для скачивания файлов
        :param skip_large_files: Пропускать файлы больше 300 МБ (создавать пустые файлы)
        :param max_workers: Количество потоков для параллельной загрузки
        """
        self.public_url = public_url
        self.download_dir = Path(download_dir)
        self.metadata_file = Path(METADATA_FILE)
        self.token = TOKEN
        self.skip_large_files = skip_large_files
        self.max_workers = max_workers
        self.metadata = self.load_metadata()
        self.metadata_lock = Lock()  # Для безопасной работы с метаданными в многопоточном режиме

        # Создаем директорию для загрузки, если её нет
        self.download_dir.mkdir(exist_ok=True)

    @staticmethod
    def sanitize_filename(filename):
        """
        Удаляет или заменяет недопустимые символы в имени файла/папки для Windows

        :param filename: Исходное имя файла или папки
        :return: Безопасное имя файла
        """
        # Недопустимые символы в Windows: < > : " / \ | ? *
        invalid_chars = '<>:"/\\|?*'
        sanitized = filename

        # Заменяем недопустимые символы
        for char in invalid_chars:
            if char == '"':
                # Двойные кавычки заменяем на одинарные
                sanitized = sanitized.replace(char, "'")
            elif char in ['<', '>']:
                # Угловые скобки заменяем на круглые
                sanitized = sanitized.replace('<', '(').replace('>', ')')
            else:
                # Остальные заменяем на подчеркивание
                sanitized = sanitized.replace(char, '_')

        # Удаляем пробелы в начале и конце
        sanitized = sanitized.strip()

        # Если имя заканчивается точкой или пробелом, добавляем подчеркивание
        if sanitized.endswith('.') or sanitized.endswith(' '):
            sanitized += '_'

        return sanitized

    def sanitize_path(self, path):
        """
        Санитизирует полный путь, обрабатывая каждый компонент отдельно

        :param path: Путь с возможно недопустимыми символами
        :return: Безопасный путь
        """
        if not path:
            return path

        # Разбиваем путь на компоненты
        parts = path.split('/')
        # Санитизируем каждый компонент
        safe_parts = [self.sanitize_filename(part) for part in parts if part]
        # Собираем обратно
        return '/'.join(safe_parts)

    def _request_with_retry(self, method, url, max_retries=MAX_RETRIES, **kwargs):
        """
        Выполняет HTTP запрос с повторными попытками при ошибках

        :param method: HTTP метод ('get', 'post', и т.д.)
        :param url: URL для запроса
        :param max_retries: Максимальное количество попыток
        :param kwargs: Дополнительные параметры для requests
        :return: Response объект или None при неудаче
        """
        for attempt in range(max_retries):
            try:
                response = getattr(requests, method)(url, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Ошибка соединения (попытка {attempt + 1}/{max_retries})")
                    logger.debug(f"ConnectionError: {e}")
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                else:
                    logger.error(f"Не удалось установить соединение после {max_retries} попыток")
                    return None
            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Таймаут (попытка {attempt + 1}/{max_retries})")
                    logger.debug(f"Timeout: {e}")
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                else:
                    logger.error(f"Превышено время ожидания после {max_retries} попыток")
                    return None
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP ошибка: {e}")
                return None
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Ошибка запроса (попытка {attempt + 1}/{max_retries})")
                    logger.debug(f"RequestException: {e}")
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                else:
                    logger.error(f"Ошибка запроса после {max_retries} попыток: {e}")
                    return None
        return None

    def load_metadata(self):
        """Загружает метаданные о скачанных файлах"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_metadata(self):
        """Сохраняет метаданные о скачанных файлах"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    def get_public_resources(self, public_key, path=None):
        """
        Получает список ресурсов по публичной ссылке

        :param public_key: Публичная ссылка на ресурс
        :param path: Путь к подпапке относительно корня (опционально)
        :return: Данные ресурса
        """
        logger.debug(f"Запрос к API: public_key={public_key[:50]}..., path={path}")
        api_url = "https://cloud-api.yandex.net/v1/disk/public/resources"

        headers = {
            'Authorization': f'OAuth {self.token}'
        }

        params = {
            'public_key': public_key,
            'limit': 1000
        }

        # Добавляем путь, если он указан
        if path:
            params['path'] = path

        logger.debug(f"Отправка запроса к {api_url}")
        response = self._request_with_retry('get', api_url, headers=headers, params=params, timeout=30)
        logger.debug(f"Получен ответ: {response is not None}")
        if response:
            return response.json()
        else:
            logger.error(f"Не удалось получить ресурсы для: {public_key}")
            if path:
                logger.debug(f"Path: {path}")
            return None

    def get_all_files_recursive(self, public_key, relative_path="", folders_set=None, root_public_key=None, _processed_folders=None):
        """
        Рекурсивно получает все файлы из папки

        :param public_key: Публичная ссылка на ресурс
        :param relative_path: Относительный путь для локального сохранения
        :param folders_set: Множество для сбора всех найденных папок
        :param root_public_key: Корневая публичная ссылка (для использования path параметра)
        :param _processed_folders: Счетчик обработанных папок (для отображения прогресса)
        :return: Список всех файлов
        """
        if folders_set is None:
            folders_set = set()

        if _processed_folders is None:
            _processed_folders = {'count': 0}

        # Если это первый вызов, сохраняем корневую ссылку
        if root_public_key is None:
            root_public_key = public_key

        files_list = []

        # Для корневой папки используем public_key, для подпапок - path параметр
        if relative_path:
            _processed_folders['count'] += 1
            if _processed_folders['count'] % 10 == 0:
                logger.info(f"   Обработано папок: {_processed_folders['count']}")
            data = self.get_public_resources(root_public_key, path=f"/{relative_path}")
        else:
            logger.info("   Получение корневой папки...")
            data = self.get_public_resources(public_key)

        if not data:
            logger.warning(f"Не удалось получить данные для: {relative_path if relative_path else 'корневая папка'}")
            return files_list

        if '_embedded' in data and 'items' in data['_embedded']:
            items = data['_embedded']['items']

            for item in items:
                item_name = item['name']
                item_type = item['type']
                item_path = f"{relative_path}/{item_name}" if relative_path else item_name

                if item_type == 'dir':
                    # Рекурсивно обходим папку
                    folders_set.add(item_path)  # Добавляем папку в список
                    item_public_url = item.get('public_url', '')

                    if item_public_url:
                        # Если у подпапки есть собственный public_url, используем его
                        # (API вернет прямые ссылки на файлы)
                        nested_files = self.get_all_files_recursive(
                            public_key=item_public_url,
                            relative_path=item_path,
                            folders_set=folders_set,
                            root_public_key=root_public_key if root_public_key else item_public_url,
                            _processed_folders=_processed_folders
                        )
                        files_list.extend(nested_files)
                    else:
                        # Если нет public_url, используем path параметр
                        # (API может не вернуть прямые ссылки)
                        nested_files = self.get_all_files_recursive(
                            public_key=root_public_key,
                            relative_path=item_path,
                            folders_set=folders_set,
                            root_public_key=root_public_key,
                            _processed_folders=_processed_folders
                        )
                        files_list.extend(nested_files)
                else:
                    # Добавляем файл в список
                    file_info = {
                        'name': item_name,
                        'path': item_path,
                        'size': item.get('size', 0),
                        'modified': item.get('modified', ''),
                        'md5': item.get('md5', ''),
                        'file': item.get('file', ''),
                        'public_url': item.get('public_url', '')
                    }
                    files_list.append(file_info)

        return files_list

    def download_file(self, file_info, root_public_key=None):
        """
        Скачивает файл с Яндекс Диска (или создает пустой файл для видео/больших файлов)

        :param file_info: Информация о файле
        :param root_public_key: Корневая публичная ссылка (для файлов в подпапках)
        :return: True если файл скачан успешно
        """
        # Создаем путь для сохранения файла с санитизацией
        safe_path = self.sanitize_path(file_info['path'])
        local_path = self.download_dir / safe_path
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Проверяем, является ли файл видео
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg']
        file_ext = Path(file_info['name']).suffix.lower()

        if file_ext in video_extensions:
            # Создаем пустой файл для видео
            try:
                local_path.touch()
                logger.info(f"Пропущено видео (создан пустой файл): {file_info['path']} ({self.format_size(file_info['size'])})")
                return True
            except Exception as e:
                logger.error(f"Ошибка при создании пустого файла {file_info['path']}: {e}")
                return False

        # Проверяем размер файла, если включен флаг пропуска больших файлов
        if self.skip_large_files and file_info['size'] > LARGE_FILE_SIZE:
            # Создаем пустой файл для больших файлов
            try:
                local_path.touch()
                logger.info(f"Пропущен большой файл (создан пустой файл): {file_info['path']} ({self.format_size(file_info['size'])})")
                return True
            except Exception as e:
                logger.error(f"Ошибка при создании пустого файла {file_info['path']}: {e}")
                return False

        # Для обычных файлов - скачиваем
        # Проверяем, есть ли прямая ссылка на файл
        download_url = file_info.get('file')

        # Если нет прямой ссылки, получаем её через API
        if not download_url:
            # Используем root_public_key и path для файлов в подпапках
            file_public_url = file_info.get('public_url', '')
            if root_public_key and not file_public_url:
                # Файл в подпапке без собственного public_url
                download_url = self.get_download_link(root_public_key, path=f"/{file_info['path']}")
            elif file_public_url:
                # Файл имеет собственный public_url
                download_url = self.get_download_link(file_public_url)
            else:
                # Нет ни root_public_key, ни public_url
                logger.debug(f"Отладка: root_public_key={'есть' if root_public_key else 'нет'}, public_url={'есть' if file_public_url else 'нет'}")
                download_url = None

        if not download_url:
            logger.warning(f"Не удалось получить ссылку для скачивания: {file_info['path']}")
            return False

        # Скачиваем файл с retry
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(download_url, stream=True, timeout=30)
                response.raise_for_status()

                # Получаем размер файла
                total_size = int(response.headers.get('content-length', 0))

                # Сохраняем файл с прогресс-баром
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

                logger.success(f"Скачан: {file_info['path']} ({self.format_size(file_info['size'])})")
                return True

            except (requests.exceptions.RequestException, IOError) as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Ошибка при скачивании {file_info['path']} (попытка {attempt + 1}/{MAX_RETRIES})")
                    logger.debug(f"Download error: {e}")
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    # Удаляем частично скачанный файл
                    if local_path.exists():
                        local_path.unlink()
                    continue
                else:
                    logger.error(f"Не удалось скачать файл {file_info['path']} после {MAX_RETRIES} попыток")
                    if local_path.exists():
                        local_path.unlink()
                    return False

        return False

    def get_download_link(self, public_url, path=None):
        """
        Получает прямую ссылку на скачивание файла

        :param public_url: Публичная ссылка на файл
        :param path: Путь к файлу относительно корня (опционально)
        :return: URL для скачивания
        """
        if not public_url:
            return None

        api_url = "https://cloud-api.yandex.net/v1/disk/public/resources/download"

        headers = {
            'Authorization': f'OAuth {self.token}'
        }

        params = {
            'public_key': public_url
        }

        # Добавляем путь, если он указан
        if path:
            params['path'] = path

        response = self._request_with_retry('get', api_url, headers=headers, params=params, timeout=30)
        if response:
            data = response.json()
            href = data.get('href')
            if not href:
                logger.warning(f"API не вернул ссылку на скачивание")
                logger.debug(f"public_key: {public_url[:50]}...")
                if path:
                    logger.debug(f"path: {path}")
            return href
        else:
            return None

    def should_download(self, file_info):
        """
        Проверяет, нужно ли скачивать файл

        :param file_info: Информация о файле
        :return: True если файл нужно скачать
        """
        file_path = file_info['path']
        safe_path = self.sanitize_path(file_path)
        local_path = self.download_dir / safe_path

        # Если файл не существует локально, скачиваем
        if not local_path.exists():
            return True

        # Если нет метаданных о файле, скачиваем
        if file_path not in self.metadata:
            return True

        old_metadata = self.metadata[file_path]

        # Сравниваем по дате модификации
        if old_metadata.get('modified') != file_info['modified']:
            return True

        # Сравниваем по размеру
        if old_metadata.get('size') != file_info['size']:
            return True

        # Сравниваем по MD5 (если доступен)
        if file_info.get('md5') and old_metadata.get('md5') != file_info['md5']:
            return True

        return False

    def sync(self):
        """
        Основная функция синхронизации
        """
        logger.info(f"Начало синхронизации с: {self.public_url}")
        logger.info(f"Директория для скачивания: {self.download_dir.absolute()}")

        # Получаем список всех файлов и папок
        logger.info("Получение списка файлов...")
        folders_set = set()
        all_files = self.get_all_files_recursive(self.public_url, folders_set=folders_set)

        # Сохраняем корневой URL для использования при скачивании
        root_public_key = self.public_url

        if not all_files and not folders_set:
            logger.warning("Файлы не найдены или произошла ошибка")
            return

        logger.info(f"Найдено файлов: {len(all_files)}")
        logger.info(f"Найдено папок: {len(folders_set)}")

        # Создаем все папки, даже пустые
        logger.info("Создание структуры папок...")
        for folder_path in sorted(folders_set):
            safe_folder_path = self.sanitize_path(folder_path)
            folder_full_path = self.download_dir / safe_folder_path
            folder_full_path.mkdir(parents=True, exist_ok=True)
        logger.success(f"Создано папок: {len(folders_set)}")

        # Предварительная статистика
        logger.info("Анализ файлов для загрузки...")
        files_to_download = []
        total_download_size = 0
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg']

        for file_info in all_files:
            if self.should_download(file_info):
                files_to_download.append(file_info)
                file_ext = Path(file_info['name']).suffix.lower()
                is_video = file_ext in video_extensions
                is_large = self.skip_large_files and file_info['size'] > LARGE_FILE_SIZE

                # Учитываем размер только для реально скачиваемых файлов
                if not is_video and not is_large:
                    total_download_size += file_info['size']

        logger.info("=" * 60)
        logger.info("📊 Статистика загрузки:")
        logger.info(f"   Файлов к загрузке: {len(files_to_download)}")
        logger.info(f"   Общий объем: {self.format_size(total_download_size)}")
        logger.info(f"   Файлов уже скачано (пропущено): {len(all_files) - len(files_to_download)}")
        logger.info(f"   Потоков для загрузки: {self.max_workers}")
        logger.info("=" * 60)

        if not files_to_download:
            logger.success("Все файлы уже загружены!")
            return

        # Статистика для финального отчета
        downloaded_count = 0
        updated_count = 0
        skipped_count = len(all_files) - len(files_to_download)
        video_count = 0
        large_file_count = 0
        failed_files = []

        # Функция для обработки одного файла в отдельном потоке
        def process_file(file_info):
            nonlocal downloaded_count, updated_count, video_count, large_file_count

            file_ext = Path(file_info['name']).suffix.lower()
            is_video = file_ext in video_extensions
            is_large = self.skip_large_files and file_info['size'] > LARGE_FILE_SIZE
            is_new = file_info['path'] not in self.metadata

            download_result = self.download_file(file_info, root_public_key=root_public_key)

            if download_result:
                # Потокобезопасное обновление метаданных
                with self.metadata_lock:
                    self.metadata[file_info['path']] = {
                        'size': file_info['size'],
                        'modified': file_info['modified'],
                        'md5': file_info['md5'],
                        'last_sync': datetime.now().isoformat(),
                        'is_video': is_video,
                        'is_large': is_large
                    }

                    if is_video:
                        video_count += 1
                    elif is_large:
                        large_file_count += 1
                    elif is_new:
                        downloaded_count += 1
                    else:
                        updated_count += 1

                return (True, file_info['path'])
            else:
                return (False, file_info['path'])

        # Многопоточная загрузка файлов
        logger.info("Загрузка файлов...")
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Запускаем загрузку всех файлов
            futures = {executor.submit(process_file, file_info): file_info for file_info in files_to_download}

            # Отслеживаем прогресс
            with tqdm(total=len(files_to_download), desc="Общий прогресс", unit="файл") as pbar:
                for future in as_completed(futures):
                    success, file_path = future.result()
                    if not success:
                        failed_files.append(file_path)
                    pbar.update(1)

        # Сохраняем метаданные
        self.save_metadata()

        # Сохраняем список неудачных файлов
        if failed_files:
            failed_log = Path('failed_downloads.txt')
            with open(failed_log, 'w', encoding='utf-8') as f:
                f.write('\n'.join(failed_files))
            logger.warning(f"Список неудачно скачанных файлов сохранен в: {failed_log.absolute()}")

        # Итоговая статистика
        logger.info("=" * 60)
        logger.success("Синхронизация завершена!")
        logger.info("=" * 60)
        logger.info(f"Новых файлов скачано: {downloaded_count}")
        logger.info(f"Обновленных файлов: {updated_count}")
        logger.info(f"Видео (созданы пустые файлы): {video_count}")
        logger.info(f"Большие файлы >300МБ (созданы пустые файлы): {large_file_count}")
        logger.info(f"Пропущено (без изменений): {skipped_count}")
        if failed_files:
            logger.warning(f"Не удалось скачать: {len(failed_files)}")
        logger.info(f"Всего файлов: {len(all_files)}")

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

    # Публичная ссылка на Яндекс Диск
    public_url = "https://disk.yandex.ru/d/_JeaJNmm6UeQVA"

    # Создаем синхронизатор и запускаем синхронизацию
    # Установите skip_large_files=True, чтобы пропускать файлы больше 300 МБ
    syncer = YandexDiskSyncer(public_url, skip_large_files=True)
    syncer.sync()


if __name__ == "__main__":
    main()
