"""
Синхронизатор личного диска пользователя Яндекс.Диска
"""
import time
import requests
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from loguru import logger

from . import config
from .utils import sanitize_path, format_size
from .database import MetadataDatabase
from .converters import WordConverter, CSVConverter, ExcelConverter, PDFConverter


class YandexDiskUserSyncer:
    """
    Синхронизатор личного диска пользователя Яндекс.Диска

    Использует Token Exchange для получения токена пользователя
    и синхронизирует указанную папку с локальной директорией.
    """

    def __init__(self, token_manager, remote_folder_path, download_dir=None):
        """
        Инициализация синхронизатора

        :param token_manager: Менеджер токенов (TokenManager)
        :param remote_folder_path: Путь к папке на диске пользователя (например, "/Клиенты")
        :param download_dir: Директория для скачивания файлов
        """
        self.token_manager = token_manager
        self.remote_folder_path = remote_folder_path
        self.download_dir = Path(download_dir or config.DOWNLOAD_DIR)

        # База данных для метаданных
        self.db = MetadataDatabase(config.METADATA_DB_PATH)
        self.metadata_lock = Lock()

        # Счетчик скачанных байт
        self.total_downloaded_bytes = 0
        self.download_lock = Lock()

        # Создаем директорию для загрузки
        self.download_dir.mkdir(exist_ok=True)

        # Конвертеры для Markdown
        self.markdown_dir = Path(config.MARKDOWN_OUTPUT_DIR)
        if config.ENABLE_MARKDOWN_CONVERSION:
            self.markdown_dir.mkdir(exist_ok=True)

            # Word конвертер
            self.word_converter = WordConverter() if config.CONVERT_WORD_FILES else None

            # CSV конвертер
            self.csv_converter = CSVConverter(
                max_rows=config.CSV_MAX_ROWS,
                max_columns=config.CSV_MAX_COLUMNS
            ) if config.CONVERT_CSV_FILES else None

            # Excel конвертер
            self.excel_converter = ExcelConverter(
                max_rows=config.EXCEL_MAX_ROWS,
                max_columns=config.EXCEL_MAX_COLUMNS,
                sheets_limit=config.EXCEL_MAX_SHEETS
            ) if config.CONVERT_EXCEL_FILES else None

            # PDF конвертер
            self.pdf_converter = PDFConverter(
                max_pages=config.PDF_MAX_PAGES
            ) if config.CONVERT_PDF_FILES else None

            # Список активных конвертеров
            self.converters = [
                c for c in [
                    self.word_converter,
                    self.csv_converter,
                    self.excel_converter,
                    self.pdf_converter
                ] if c is not None
            ]
        else:
            self.converters = []

    def _request_with_retry(self, method, url, max_retries=None, **kwargs):
        """Выполняет HTTP запрос с повторными попытками при ошибках"""
        max_retries = max_retries or config.MAX_RETRIES

        for attempt in range(max_retries):
            try:
                response = getattr(requests, method)(url, timeout=config.REQUEST_TIMEOUT, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Ошибка соединения (попытка {attempt + 1}/{max_retries})")
                    time.sleep(config.RETRY_DELAY * (attempt + 1))
                    continue
                else:
                    logger.error(f"Не удалось установить соединение после {max_retries} попыток")
                    return None
            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Таймаут (попытка {attempt + 1}/{max_retries})")
                    time.sleep(config.RETRY_DELAY * (attempt + 1))
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
                    time.sleep(config.RETRY_DELAY * (attempt + 1))
                    continue
                else:
                    logger.error(f"Ошибка запроса после {max_retries} попыток: {e}")
                    return None
        return None

    def get_user_resources(self, path):
        """
        Получает ресурсы личного диска пользователя

        :param path: Путь к папке на диске (например, "/Клиенты")
        :return: Данные ресурса
        """
        url = "https://cloud-api.yandex.net/v1/disk/resources"
        headers = {"Authorization": f"OAuth {self.token_manager.token}"}
        params = {"path": path, "limit": 1000}

        response = self._request_with_retry('get', url, headers=headers, params=params)
        if response:
            return response.json()
        else:
            logger.error(f"Не удалось получить ресурсы для: {path}")
            return None

    def get_all_files_recursive(self, path, relative_path="", folders_set=None, _processed_folders=None):
        """
        Рекурсивно получает все файлы из папки

        :param path: Путь к папке на диске
        :param relative_path: Относительный путь для локального сохранения
        :param folders_set: Множество для сбора всех найденных папок
        :param _processed_folders: Счетчик обработанных папок
        :return: Список всех файлов
        """
        if folders_set is None:
            folders_set = set()

        if _processed_folders is None:
            _processed_folders = {'count': 0}

        files_list = []

        if relative_path:
            _processed_folders['count'] += 1
            if _processed_folders['count'] % 10 == 0:
                logger.info(f"   Обработано папок: {_processed_folders['count']}")

        logger.debug(f"Получение содержимого: {path}")
        data = self.get_user_resources(path)

        if not data:
            logger.warning(f"Не удалось получить данные для: {path}")
            return files_list

        if '_embedded' in data and 'items' in data['_embedded']:
            items = data['_embedded']['items']

            for item in items:
                item_name = item['name']
                item_type = item['type']
                item_path = f"{relative_path}/{item_name}" if relative_path else item_name
                full_path = f"{path}/{item_name}" if path != "/" else f"/{item_name}"

                if item_type == 'dir':
                    # Рекурсивно обходим папку
                    folders_set.add(item_path)
                    nested_files = self.get_all_files_recursive(
                        path=full_path,
                        relative_path=item_path,
                        folders_set=folders_set,
                        _processed_folders=_processed_folders
                    )
                    files_list.extend(nested_files)
                else:
                    # Добавляем файл в список
                    file_info = {
                        'name': item_name,
                        'path': item_path,
                        'full_path': full_path,
                        'size': item.get('size', 0),
                        'modified': item.get('modified', ''),
                        'md5': item.get('md5', '')
                    }
                    files_list.append(file_info)

        return files_list

    def is_video_file(self, filename):
        """Проверяет, является ли файл видео"""
        if not config.SKIP_VIDEO_FILES:
            return False

        file_ext = Path(filename).suffix.lower()
        return file_ext in config.VIDEO_EXTENSIONS

    def is_large_file(self, size):
        """Проверяет, является ли файл слишком большим"""
        if not config.SKIP_LARGE_FILES:
            return False

        return size > config.MAX_FILE_SIZE

    def should_create_empty_file(self, file_info):
        """
        Проверяет, нужно ли создать пустой файл вместо скачивания

        :param file_info: Информация о файле
        :return: (should_create_empty, reason)
        """
        # Проверяем общий лимит загрузки
        if config.ENABLE_TOTAL_SIZE_LIMIT:
            with self.download_lock:
                if self.total_downloaded_bytes >= config.MAX_TOTAL_SIZE:
                    return True, "total_limit"

                # Проверяем, превысит ли загрузка этого файла лимит
                if self.total_downloaded_bytes + file_info['size'] > config.MAX_TOTAL_SIZE:
                    return True, "total_limit"

        # Проверяем видео
        if self.is_video_file(file_info['name']):
            return True, "video"

        # Проверяем размер файла
        if self.is_large_file(file_info['size']):
            return True, "large"

        return False, None

    def download_file(self, file_info):
        """
        Скачивает файл с личного диска пользователя или создает пустой файл

        :param file_info: Информация о файле
        :return: True если файл обработан успешно
        """
        # Создаем путь для сохранения файла
        safe_path = sanitize_path(file_info['path'])
        local_path = self.download_dir / safe_path
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Проверяем, нужно ли создать пустой файл
        should_create_empty, reason = self.should_create_empty_file(file_info)

        if should_create_empty:
            try:
                local_path.touch()
                reason_text = {
                    'video': 'видео',
                    'large': f'большой файл (>{format_size(config.MAX_FILE_SIZE)})',
                    'total_limit': f'достигнут лимит {format_size(config.MAX_TOTAL_SIZE)}'
                }.get(reason, 'неизвестная причина')

                logger.info(f"Пропущено ({reason_text}), создан пустой файл: {file_info['path']} ({format_size(file_info['size'])})")
                return True
            except Exception as e:
                logger.error(f"Ошибка при создании пустого файла {file_info['path']}: {e}")
                return False

        # Скачиваем файл
        # Шаг 1: Получаем ссылку на скачивание
        download_url = self.get_download_link(file_info['full_path'])

        if not download_url:
            logger.warning(f"Не удалось получить ссылку для скачивания: {file_info['path']}")
            return False

        # Шаг 2: Скачиваем файл с retry
        for attempt in range(config.MAX_RETRIES):
            try:
                response = requests.get(download_url, stream=True, timeout=config.REQUEST_TIMEOUT)
                response.raise_for_status()

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

                # Обновляем счетчик скачанных байт
                with self.download_lock:
                    self.total_downloaded_bytes += file_info['size']

                logger.success(f"Скачан: {file_info['path']} ({format_size(file_info['size'])})")
                return True

            except (requests.exceptions.RequestException, IOError) as e:
                if attempt < config.MAX_RETRIES - 1:
                    logger.warning(f"Ошибка при скачивании {file_info['path']} (попытка {attempt + 1}/{config.MAX_RETRIES})")
                    time.sleep(config.RETRY_DELAY * (attempt + 1))
                    if local_path.exists():
                        local_path.unlink()
                    continue
                else:
                    logger.error(f"Не удалось скачать файл {file_info['path']} после {config.MAX_RETRIES} попыток")
                    if local_path.exists():
                        local_path.unlink()
                    return False

        return False

    def convert_file_to_markdown(self, local_path: Path, file_info: dict) -> bool:
        """
        Конвертирует файл в Markdown если возможно

        :param local_path: Путь к локальному файлу
        :param file_info: Информация о файле
        :return: True если файл был сконвертирован, False если конвертация не требуется или не удалась
        """
        if not config.ENABLE_MARKDOWN_CONVERSION:
            return False

        if not local_path.exists() or local_path.stat().st_size == 0:
            # Пустой файл - не конвертируем
            return False

        # Проверяем, может ли кто-то из конвертеров обработать файл
        for converter in self.converters:
            if converter.can_convert(local_path):
                # Создаем путь для markdown файла
                relative_path = local_path.relative_to(self.download_dir)
                md_path = self.markdown_dir / relative_path.with_suffix('.md')

                # Конвертируем
                success = converter.convert_safe(local_path, md_path)

                if success:
                    logger.info(f"Конвертирован в MD: {file_info['path']}")

                    # Удаляем оригинал если настроено
                    if config.DELETE_ORIGINALS_AFTER_CONVERSION:
                        try:
                            local_path.unlink()
                            logger.debug(f"Удален оригинал: {file_info['path']}")
                        except Exception as e:
                            logger.error(f"Ошибка при удалении оригинала {file_info['path']}: {e}")

                return success

        # Файл не поддерживается конвертерами
        return False

    def get_download_link(self, path):
        """
        Получает прямую ссылку на скачивание файла с личного диска

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
        else:
            return None

    def should_download(self, file_info):
        """
        Проверяет, нужно ли скачивать файл

        :param file_info: Информация о файле
        :return: True если файл нужно скачать
        """
        file_path = file_info['path']
        safe_path = sanitize_path(file_path)
        local_path = self.download_dir / safe_path

        # Если файл не существует локально, скачиваем
        if not local_path.exists():
            return True

        # Проверяем через БД нужно ли обновлять файл
        return self.db.file_needs_update(
            file_path=file_path,
            size=file_info['size'],
            modified=file_info['modified'],
            md5=file_info.get('md5', '')
        )

    def cleanup_deleted_files(self, remote_files: list) -> tuple:
        """
        Удаляет файлы, которые отсутствуют на удаленном диске

        :param remote_files: Список файлов с удаленного диска
        :return: (количество удаленных файлов, количество удаленных записей из БД)
        """
        # Получаем пути всех файлов с удаленного диска
        remote_paths = {file_info['path'] for file_info in remote_files}

        # Получаем все файлы из БД
        db_files = self.db.get_all_files()

        deleted_local = 0
        deleted_db = 0

        for db_file in db_files:
            file_path = db_file['path']

            # Если файла нет на удаленном диске - удаляем
            if file_path not in remote_paths:
                # Удаляем локальный файл
                safe_path = sanitize_path(file_path)
                local_path = self.download_dir / safe_path

                if local_path.exists():
                    try:
                        local_path.unlink()
                        deleted_local += 1
                        logger.info(f"Удален локальный файл (отсутствует на диске): {file_path}")
                    except Exception as e:
                        logger.error(f"Ошибка при удалении файла {file_path}: {e}")

                # Удаляем запись из БД
                try:
                    self.db.delete_file_metadata(file_path)
                    deleted_db += 1
                except Exception as e:
                    logger.error(f"Ошибка при удалении метаданных {file_path}: {e}")

        return deleted_local, deleted_db

    def cleanup_empty_folders(self) -> int:
        """
        Удаляет пустые папки в локальной директории

        :return: количество удаленных папок
        """
        deleted_folders = 0

        # Получаем все папки и сортируем по глубине (от самых вложенных к корневым)
        all_dirs = [p for p in self.download_dir.rglob('*') if p.is_dir()]
        sorted_dirs = sorted(all_dirs, key=lambda p: len(p.parts), reverse=True)

        for dirpath in sorted_dirs:
            try:
                # Проверяем, пустая ли папка
                if not any(dirpath.iterdir()):
                    dirpath.rmdir()
                    deleted_folders += 1
                    relative_path = dirpath.relative_to(self.download_dir)
                    logger.info(f"Удалена пустая папка: {relative_path}")
            except OSError:
                # Папка не пустая или другая ошибка - пропускаем
                pass
            except Exception as e:
                logger.error(f"Ошибка при удалении папки {dirpath}: {e}")

        return deleted_folders

    def sync(self):
        """Основная функция синхронизации"""
        logger.info(f"Начало синхронизации папки: {self.remote_folder_path}")
        logger.info(f"Директория для скачивания: {self.download_dir.absolute()}")

        # Выводим информацию о конфигурации
        config.print_config_summary()

        # Получаем список всех файлов и папок
        logger.info("Получение списка файлов...")
        folders_set = set()
        all_files = self.get_all_files_recursive(self.remote_folder_path, folders_set=folders_set)

        if not all_files and not folders_set:
            logger.warning("Файлы не найдены или произошла ошибка")
            return

        logger.info(f"Найдено файлов: {len(all_files)}")
        logger.info(f"Найдено папок: {len(folders_set)}")

        # Очистка удаленных файлов
        logger.info("Проверка удаленных файлов...")
        deleted_local, deleted_db = self.cleanup_deleted_files(all_files)
        if deleted_local > 0 or deleted_db > 0:
            logger.warning(f"Удалено файлов, отсутствующих на диске: {deleted_local} (записей из БД: {deleted_db})")

        # Удаление пустых папок
        logger.info("Проверка пустых папок...")
        deleted_folders = self.cleanup_empty_folders()
        if deleted_folders > 0:
            logger.warning(f"Удалено пустых папок: {deleted_folders}")

        # Создаем структуру папок
        logger.info("Создание структуры папок...")
        for folder_path in sorted(folders_set):
            safe_folder_path = sanitize_path(folder_path)
            folder_full_path = self.download_dir / safe_folder_path
            folder_full_path.mkdir(parents=True, exist_ok=True)
        logger.success(f"Создано папок: {len(folders_set)}")

        # Анализ файлов для загрузки
        logger.info("Анализ файлов для загрузки...")
        files_to_download = []
        total_download_size = 0

        for file_info in all_files:
            if self.should_download(file_info):
                files_to_download.append(file_info)
                # Учитываем размер только для файлов, которые будем скачивать
                should_create_empty, _ = self.should_create_empty_file(file_info)
                if not should_create_empty:
                    total_download_size += file_info['size']

        logger.info("=" * 70)
        logger.info("Статистика загрузки:")
        logger.info(f"   Файлов к обработке: {len(files_to_download)}")
        logger.info(f"   Ожидаемый объем загрузки: {format_size(total_download_size)}")
        logger.info(f"   Файлов уже скачано (пропущено): {len(all_files) - len(files_to_download)}")
        logger.info(f"   Потоков для загрузки: {config.MAX_WORKERS}")
        logger.info("=" * 70)

        if not files_to_download:
            logger.success("Все файлы уже загружены!")
            return

        # Статистика для финального отчета
        downloaded_count = 0
        updated_count = 0
        skipped_count = len(all_files) - len(files_to_download)
        video_count = 0
        large_file_count = 0
        limit_reached_count = 0
        converted_count = 0
        failed_files = []

        def process_file(file_info):
            nonlocal downloaded_count, updated_count, video_count, large_file_count, limit_reached_count, converted_count

            is_new = self.db.get_file_metadata(file_info['path']) is None
            should_create_empty, reason = self.should_create_empty_file(file_info)

            download_result = self.download_file(file_info)

            if download_result:
                # Конвертируем файл в Markdown если возможно
                if not should_create_empty:
                    safe_path = sanitize_path(file_info['path'])
                    local_path = self.download_dir / safe_path
                    was_converted = self.convert_file_to_markdown(local_path, file_info)
                    if was_converted:
                        converted_count += 1

                # Сохраняем метаданные в БД
                with self.metadata_lock:
                    self.db.save_file_metadata(
                        file_path=file_info['path'],
                        size=file_info['size'],
                        modified=file_info['modified'],
                        md5=file_info.get('md5', ''),
                        is_empty=should_create_empty
                    )

                    if should_create_empty:
                        if reason == 'video':
                            video_count += 1
                        elif reason == 'large':
                            large_file_count += 1
                        elif reason == 'total_limit':
                            limit_reached_count += 1
                    elif is_new:
                        downloaded_count += 1
                    else:
                        updated_count += 1

                return (True, file_info['path'])
            else:
                return (False, file_info['path'])

        # Многопоточная загрузка
        logger.info("Загрузка файлов...")
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            futures = {executor.submit(process_file, file_info): file_info for file_info in files_to_download}

            with tqdm(total=len(files_to_download), desc="Общий прогресс", unit="файл") as pbar:
                for future in as_completed(futures):
                    success, file_path = future.result()
                    if not success:
                        failed_files.append(file_path)
                    pbar.update(1)

        # Сохраняем список неудачных файлов
        if failed_files:
            failed_log = Path('failed_downloads.txt')
            with open(failed_log, 'w', encoding='utf-8') as f:
                f.write('\n'.join(failed_files))
            logger.warning(f"Список неудачно скачанных файлов сохранен в: {failed_log.absolute()}")

        # Итоговая статистика
        logger.info("=" * 70)
        logger.success("Синхронизация завершена!")
        logger.info("=" * 70)
        logger.info(f"Новых файлов скачано: {downloaded_count}")
        logger.info(f"Обновленных файлов: {updated_count}")
        logger.info(f"Видео (созданы пустые файлы): {video_count}")
        logger.info(f"Большие файлы >{format_size(config.MAX_FILE_SIZE)} (созданы пустые файлы): {large_file_count}")
        logger.info(f"Достигнут лимит {format_size(config.MAX_TOTAL_SIZE)} (созданы пустые файлы): {limit_reached_count}")
        logger.info(f"Пропущено (без изменений): {skipped_count}")
        if converted_count > 0:
            logger.info(f"Конвертировано в Markdown: {converted_count}")
        if deleted_local > 0:
            logger.warning(f"Удалено (отсутствуют на диске): {deleted_local}")
        if deleted_folders > 0:
            logger.warning(f"Удалено пустых папок: {deleted_folders}")
        if failed_files:
            logger.warning(f"Не удалось скачать: {len(failed_files)}")
        logger.info(f"Всего файлов: {len(all_files)}")
        logger.info(f"Скачано данных: {format_size(self.total_downloaded_bytes)}")

        # Статистика из БД
        db_stats = self.db.get_statistics()
        logger.info("")
        logger.info("Статистика БД:")
        logger.info(f"   Всего записей: {db_stats['total_files']}")
        logger.info(f"   Реальных файлов: {db_stats['real_files']}")
        logger.info(f"   Пустых файлов: {db_stats['empty_files']}")
        logger.info(f"   Общий размер: {format_size(db_stats['total_size'])}")
        logger.info("=" * 70)
