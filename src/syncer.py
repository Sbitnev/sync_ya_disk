"""
Синхронизатор личного диска пользователя Яндекс.Диска
"""
import time
import json
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
from .converters import (
    WordConverter, CSVConverter, ExcelConverter, PDFConverter,
    TextConverter, PowerPointConverter, HTMLConverter,
    ParquetConverter, RTFConverter, ArchiveConverter, VideoConverter
)


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
        # auto_migrate=False т.к. миграции применяются в main.py перед запуском
        self.db = MetadataDatabase(config.METADATA_DB_PATH, auto_migrate=False)
        self.metadata_lock = Lock()

        # Счетчик скачанных байт
        self.total_downloaded_bytes = 0
        self.download_lock = Lock()

        # Создаем директорию для загрузки
        self.download_dir.mkdir(exist_ok=True)

        # Единая HTTP-сессия для переиспользования соединений
        self.session = requests.Session()
        # Настройка connection pooling для оптимизации
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0  # Ретраи обрабатываем вручную в _request_with_retry
        )
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)

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

            # Text/Code конвертер
            self.text_converter = TextConverter() if config.CONVERT_TEXT_FILES else None

            # PowerPoint конвертер
            self.ppt_converter = PowerPointConverter() if config.CONVERT_POWERPOINT_FILES else None

            # HTML конвертер
            self.html_converter = HTMLConverter() if config.CONVERT_HTML_FILES else None

            # Parquet конвертер
            self.parquet_converter = ParquetConverter(
                max_rows=config.PARQUET_MAX_ROWS,
                max_columns=config.PARQUET_MAX_COLUMNS
            ) if config.CONVERT_PARQUET_FILES else None

            # RTF конвертер
            self.rtf_converter = RTFConverter() if config.CONVERT_RTF_FILES else None

            # Video конвертер (транскрибация через Yandex SpeechKit)
            self.video_converter = VideoConverter() if config.CONVERT_VIDEO_FILES else None

            # Archive конвертер (инициализируем последним, чтобы передать все остальные конвертеры)
            self.archive_converter = None
            if config.CONVERT_ARCHIVE_FILES:
                # Собираем список всех активных конвертеров
                available_converters = [
                    c for c in [
                        self.word_converter,
                        self.csv_converter,
                        self.excel_converter,
                        self.pdf_converter,
                        self.text_converter,
                        self.ppt_converter,
                        self.html_converter,
                        self.parquet_converter,
                        self.rtf_converter,
                        self.video_converter
                    ] if c is not None
                ]
                self.archive_converter = ArchiveConverter(
                    converters_registry=available_converters,
                    max_depth=config.ARCHIVE_MAX_DEPTH
                )

            # Список активных конвертеров
            self.converters = [
                c for c in [
                    self.word_converter,
                    self.csv_converter,
                    self.excel_converter,
                    self.pdf_converter,
                    self.text_converter,
                    self.ppt_converter,
                    self.html_converter,
                    self.parquet_converter,
                    self.rtf_converter,
                    self.video_converter,
                    self.archive_converter
                ] if c is not None
            ]
        else:
            self.converters = []

        # Список временных аудио файлов для удаления
        self.pending_audio_files = []

    def analyze_folders(self, all_files: list) -> dict:
        """
        Анализирует папки первого уровня: типы файлов, количество, размер

        :param all_files: Список всех файлов
        :return: Словарь с анализом по папкам
        """
        from collections import defaultdict

        folders_stats = defaultdict(lambda: {
            'total_size': 0,
            'file_count': 0,
            'file_types': defaultdict(int)
        })

        # Файлы в корне (без подпапок)
        root_folder = "(корневая папка)"

        for file_info in all_files:
            file_path = file_info['path']
            file_size = file_info['size']

            # Определяем папку первого уровня
            path_parts = file_path.split('/')
            if len(path_parts) > 1:
                folder_name = path_parts[0]
            else:
                folder_name = root_folder

            # Определяем тип файла по расширению
            file_ext = Path(file_path).suffix.lower()
            if not file_ext:
                file_ext = "(без расширения)"

            # Обновляем статистику
            folders_stats[folder_name]['total_size'] += file_size
            folders_stats[folder_name]['file_count'] += 1
            folders_stats[folder_name]['file_types'][file_ext] += 1

        return dict(folders_stats)

    def select_folders_interactive(self, folders_stats: dict) -> list:
        """
        Интерактивный выбор папок для синхронизации

        :param folders_stats: Статистика по папкам
        :return: Список выбранных папок
        """
        from src.config import format_size

        logger.info("=" * 70)
        logger.info("АНАЛИЗ ПАПОК ДЛЯ СИНХРОНИЗАЦИИ")
        logger.info("=" * 70)

        # Сортируем папки по размеру (по убыванию)
        sorted_folders = sorted(
            folders_stats.items(),
            key=lambda x: x[1]['total_size'],
            reverse=True
        )

        # Выводим список папок
        folder_names = []
        for idx, (folder_name, stats) in enumerate(sorted_folders, 1):
            folder_names.append(folder_name)

            # Форматируем информацию о папке
            size_str = format_size(stats['total_size'])
            file_count = stats['file_count']

            # Топ-5 типов файлов
            top_types = sorted(
                stats['file_types'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            types_str = ", ".join([f"{ext} ({count})" for ext, count in top_types])

            logger.info(f"{idx}. {folder_name}")
            logger.info(f"   Размер: {size_str}")
            logger.info(f"   Файлов: {file_count}")
            logger.info(f"   Типы: {types_str}")
            logger.info("")

        logger.info("=" * 70)
        logger.info("Выберите папки для синхронизации:")
        logger.info("  • Введите номера папок через запятую (например: 1,3,5)")
        logger.info("  • Или 'all' для синхронизации всех папок")
        logger.info("  • Или 'cancel' для отмены")
        logger.info("=" * 70)

        # Получаем выбор пользователя
        while True:
            try:
                user_input = input("\nВаш выбор: ").strip().lower()

                if user_input == 'cancel':
                    logger.warning("Синхронизация отменена пользователем")
                    return []

                if user_input == 'all':
                    logger.success(f"Выбраны все папки ({len(folder_names)})")
                    return folder_names

                # Парсим номера папок
                selected_indices = []
                for part in user_input.split(','):
                    part = part.strip()
                    if part.isdigit():
                        idx = int(part)
                        if 1 <= idx <= len(folder_names):
                            selected_indices.append(idx - 1)
                        else:
                            logger.error(f"Неверный номер: {idx}")
                            raise ValueError()
                    else:
                        logger.error(f"Неверный формат: {part}")
                        raise ValueError()

                if not selected_indices:
                    logger.error("Не выбрано ни одной папки")
                    raise ValueError()

                # Получаем имена выбранных папок
                selected_folders = [folder_names[i] for i in selected_indices]
                logger.success(f"Выбрано папок: {len(selected_folders)}")
                for folder in selected_folders:
                    logger.info(f"  • {folder}")

                return selected_folders

            except (ValueError, KeyboardInterrupt):
                logger.warning("Неверный ввод. Попробуйте еще раз.")
                continue

    def check_pending_transcriptions(self):
        """
        Проверяет и завершает незавершенные транскрибации из предыдущих запусков
        """
        if not config.VIDEO_CHECK_PENDING_ON_START or not self.video_converter:
            return

        logger.info("Проверка незавершенных транскрибаций...")
        import json

        pending = self.db.get_pending_transcriptions()
        if not pending:
            logger.info("Незавершенных транскрибаций нет")
            return

        logger.info(f"Найдено незавершенных транскрибаций: {len(pending)}")
        completed = 0
        failed = 0

        for record in pending:
            operation_id = record.get('transcription_operation_id')
            if not operation_id:
                continue

            file_path = record['path']
            logger.info(f"Проверка операции {operation_id} для {file_path}")

            # Проверяем статус
            status = self.video_converter.check_operation_status(operation_id)

            if status['done']:
                # Операция завершена
                if status['error']:
                    logger.error(f"Транскрибация завершилась с ошибкой: {file_path}")
                    self.db.update_transcription_status(file_path, 'failed')
                    failed += 1
                else:
                    # Сохраняем результат
                    try:
                        video_metadata = json.loads(record.get('video_metadata', '{}'))
                        relative_path = Path(file_path)
                        md_filename = relative_path.name + '.md'
                        md_path = self.markdown_dir / relative_path.parent / md_filename

                        if self.video_converter.save_transcription_result(operation_id, md_path, video_metadata):
                            # Обновляем БД
                            md_relative = str(md_path.relative_to(self.markdown_dir))
                            self.db.save_file_metadata(
                                file_path=file_path,
                                size=record['size'],
                                modified=record['modified'],
                                md5=record.get('md5', ''),
                                is_empty=False,
                                markdown_path=md_relative
                            )
                            self.db.update_transcription_status(file_path, 'completed')
                            logger.success(f"Транскрибация завершена: {file_path}")
                            completed += 1
                        else:
                            self.db.update_transcription_status(file_path, 'failed')
                            failed += 1
                    except Exception as e:
                        logger.error(f"Ошибка при сохранении результата транскрибации {file_path}: {e}")
                        self.db.update_transcription_status(file_path, 'failed')
                        failed += 1
            else:
                logger.info(f"Транскрибация еще в процессе: {file_path}")

        if completed > 0:
            logger.success(f"Завершено транскрибаций из предыдущих запусков: {completed}")
        if failed > 0:
            logger.warning(f"Транскрибаций завершились с ошибками: {failed}")

    def cleanup_pending_audio_files(self):
        """Удаляет временные аудио файлы после завершения синхронизации"""
        if not hasattr(self, 'pending_audio_files') or not self.pending_audio_files:
            return

        logger.info(f"Удаление временных аудио файлов: {len(self.pending_audio_files)}")
        for audio_path in self.pending_audio_files:
            try:
                if audio_path.exists():
                    audio_path.unlink()
                    logger.debug(f"Удален временный аудио: {audio_path.name}")
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл {audio_path}: {e}")

        self.pending_audio_files = []

    def wait_for_all_transcriptions(self):
        """
        Ждет завершения всех транскрибаций перед завершением синхронизации

        Периодически проверяет статус незавершенных транскрибаций
        и обрабатывает результаты по мере готовности
        """
        logger.info("=" * 70)
        logger.info("ОЖИДАНИЕ ЗАВЕРШЕНИЯ ТРАНСКРИБАЦИЙ")
        logger.info("=" * 70)

        while True:
            # Получаем список незавершенных транскрибаций
            pending = self.db.get_pending_transcriptions()

            if not pending:
                logger.success("Все транскрибации завершены!")
                logger.info("=" * 70)
                break

            logger.info(f"Незавершенных транскрибаций: {len(pending)}")

            # Проверяем статус каждой операции
            completed_count = 0
            for file_metadata in pending:
                file_path = file_metadata['path']
                operation_id = file_metadata.get('transcription_operation_id')

                if not operation_id:
                    logger.warning(f"Нет operation_id для {file_path}, пропускаем")
                    continue

                logger.info(f"Проверка операции {operation_id} для {file_path}")

                # Проверяем статус операции
                status = self.video_converter.check_operation_status(operation_id)

                if status['done']:
                    # Операция завершена
                    if status['error']:
                        logger.error(f"Транскрибация завершилась с ошибкой: {file_path}")
                        self.db.update_transcription_status(file_path, 'failed')
                        completed_count += 1
                    else:
                        # Сохраняем результат
                        try:
                            import json
                            video_metadata = json.loads(file_metadata.get('video_metadata', '{}'))
                            relative_path = Path(file_path)
                            md_filename = relative_path.name + '.md'
                            md_path = self.markdown_dir / relative_path.parent / md_filename

                            if self.video_converter.save_transcription_result(operation_id, md_path, video_metadata):
                                # Обновляем БД
                                md_relative = str(md_path.relative_to(self.markdown_dir))
                                self.db.update_markdown_path(file_path, md_relative)
                                self.db.update_transcription_status(file_path, 'completed')
                                logger.success(f"Транскрибация завершена: {file_path}")
                                completed_count += 1
                            else:
                                self.db.update_transcription_status(file_path, 'failed')
                                completed_count += 1
                        except Exception as e:
                            logger.error(f"Ошибка при сохранении результата транскрибации {file_path}: {e}")
                            self.db.update_transcription_status(file_path, 'failed')
                            completed_count += 1
                else:
                    logger.info(f"Транскрибация еще в процессе: {file_path}")

            if completed_count > 0:
                logger.success(f"Завершено транскрибаций: {completed_count}")

            # Проверяем снова есть ли незавершенные
            pending = self.db.get_pending_transcriptions()
            if not pending:
                logger.success("Все транскрибации завершены!")
                logger.info("=" * 70)
                break

            # Ждем перед следующей проверкой
            logger.info(f"Ожидание {config.VIDEO_CHECK_INTERVAL} сек перед следующей проверкой...")
            time.sleep(config.VIDEO_CHECK_INTERVAL)

    def _request_with_retry(self, method, url, max_retries=None, **kwargs):
        """Выполняет HTTP запрос с повторными попытками при ошибках"""
        max_retries = max_retries or config.MAX_RETRIES

        for attempt in range(max_retries):
            try:
                response = getattr(self.session, method)(url, timeout=config.REQUEST_TIMEOUT, **kwargs)
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
                status_code = e.response.status_code if e.response is not None else 'неизвестно'
                logger.error(f"HTTP ошибка {status_code}: {e}")
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

    def get_user_resources(self, path, limit=1000):
        """
        Получает ВСЕ ресурсы личного диска пользователя с поддержкой пагинации

        :param path: Путь к папке на диске (например, "/Клиенты")
        :param limit: Количество элементов на страницу (max 1000)
        :return: Данные ресурса со всеми элементами
        """
        url = "https://cloud-api.yandex.net/v1/disk/resources"
        headers = {"Authorization": f"OAuth {self.token_manager.token}"}

        all_items = []
        offset = 0
        total_fetched = 0

        # Пагинация для получения всех элементов
        while True:
            params = {
                "path": path,
                "limit": limit,
                "offset": offset
            }

            response = self._request_with_retry('get', url, headers=headers, params=params)
            if not response:
                # Ошибка уже залогирована в _request_with_retry
                break

            data = response.json()

            # Получаем элементы из ответа
            if '_embedded' in data and 'items' in data['_embedded']:
                items = data['_embedded']['items']
                all_items.extend(items)
                total_fetched += len(items)

                # Если получили меньше limit, это последняя страница
                if len(items) < limit:
                    if offset > 0:  # Если была пагинация
                        logger.debug(f"   Получено {total_fetched} элементов (пагинация)")
                    break

                offset += limit
            else:
                break

        # Возвращаем в том же формате, но со всеми элементами
        if all_items:
            return {
                '_embedded': {'items': all_items},
                'type': 'dir',
                'name': data.get('name', ''),
                'path': path
            }

        return None

    def get_all_files_recursive(self, path, relative_path="", folders_set=None, _processed_folders=None):
        """
        Рекурсивно получает все файлы из папки с параллельной обработкой вложенных папок

        :param path: Путь к папке на диске
        :param relative_path: Относительный путь для локального сохранения
        :param folders_set: Множество для сбора всех найденных папок
        :param _processed_folders: Счетчик обработанных папок
        :return: Список всех файлов
        """
        if folders_set is None:
            folders_set = set()

        if _processed_folders is None:
            _processed_folders = {'count': 0, 'lock': Lock()}

        files_list = []

        if relative_path:
            with _processed_folders['lock']:
                _processed_folders['count'] += 1
                if _processed_folders['count'] % 10 == 0:
                    logger.info(f"   Обработано папок: {_processed_folders['count']}")

        logger.debug(f"Получение содержимого: {path}")
        data = self.get_user_resources(path)

        if not data:
            logger.warning(f"Папка пропущена (нет доступа или пустая): {path}")
            return files_list

        if '_embedded' in data and 'items' in data['_embedded']:
            items = data['_embedded']['items']

            # Разделяем файлы и папки
            folders_to_process = []

            for item in items:
                item_name = item['name']
                item_type = item['type']
                item_path = f"{relative_path}/{item_name}" if relative_path else item_name
                full_path = f"{path}/{item_name}" if path != "/" else f"/{item_name}"

                if item_type == 'dir':
                    folders_set.add(item_path)
                    folders_to_process.append((full_path, item_path))
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

            # Параллельная обработка вложенных папок
            if folders_to_process:
                # Используем ThreadPoolExecutor для параллельной обработки
                with ThreadPoolExecutor(max_workers=config.FOLDER_SCAN_WORKERS) as executor:
                    futures = {
                        executor.submit(
                            self.get_all_files_recursive,
                            folder_path,
                            folder_rel_path,
                            folders_set,
                            _processed_folders
                        ): folder_path
                        for folder_path, folder_rel_path in folders_to_process
                    }

                    for future in as_completed(futures):
                        try:
                            nested_files = future.result()
                            files_list.extend(nested_files)
                        except Exception as e:
                            folder_path = futures[future]
                            logger.error(f"Ошибка при обработке папки {folder_path}: {e}")

        return files_list

    def _get_cache_path(self):
        """Возвращает путь к файлу кэша"""
        cache_dir = Path(config.METADATA_DIR)
        cache_dir.mkdir(exist_ok=True)
        return cache_dir / "files_list_cache.json"

    def _load_cached_files_list(self, max_age_seconds=300):
        """
        Загружает список файлов из кэша если он свежий

        :param max_age_seconds: Максимальный возраст кэша в секундах (по умолчанию 5 минут)
        :return: Кэшированный список файлов или None
        """
        cache_path = self._get_cache_path()

        if not cache_path.exists():
            return None

        # Проверяем возраст кэша
        cache_age = time.time() - cache_path.stat().st_mtime
        if cache_age > max_age_seconds:
            logger.debug(f"Кэш устарел ({cache_age:.0f} сек > {max_age_seconds} сек)")
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                logger.info(f"Использование кэша списка файлов (возраст: {cache_age:.0f} сек)")
                return cached_data.get('files'), cached_data.get('folders')
        except Exception as e:
            logger.warning(f"Не удалось загрузить кэш: {e}")
            return None

    def _save_files_list_to_cache(self, files_list, folders_set):
        """
        Сохраняет список файлов в кэш

        :param files_list: Список файлов
        :param folders_set: Множество папок
        """
        cache_path = self._get_cache_path()

        try:
            cached_data = {
                'files': files_list,
                'folders': list(folders_set),
                'timestamp': time.time(),
                'remote_path': self.remote_folder_path
            }

            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cached_data, f, ensure_ascii=False, indent=2)

            logger.debug(f"Список файлов сохранен в кэш: {len(files_list)} файлов, {len(folders_set)} папок")
        except Exception as e:
            logger.warning(f"Не удалось сохранить кэш: {e}")

    def is_video_file(self, filename):
        """Проверяет, является ли файл видео"""
        if not config.SKIP_VIDEO_FILES:
            return False

        file_ext = Path(filename).suffix.lower()
        return file_ext in config.VIDEO_EXTENSIONS

    def is_image_file(self, filename):
        """Проверяет, является ли файл изображением"""
        if not config.SKIP_IMAGE_FILES:
            return False

        file_ext = Path(filename).suffix.lower()
        return file_ext in config.IMAGE_EXTENSIONS

    def is_large_file(self, size):
        """Проверяет, является ли файл слишком большим"""
        if not config.SKIP_LARGE_FILES:
            return False

        return size > config.MAX_FILE_SIZE

    def should_create_empty_file(self, file_info):
        """
        Проверяет, нужно ли пропустить файл вместо скачивания

        :param file_info: Информация о файле
        :return: (should_skip, reason)
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

        # Проверяем изображения
        if self.is_image_file(file_info['name']):
            return True, "image"

        # Проверяем размер файла
        if self.is_large_file(file_info['size']):
            return True, "large"

        return False, None

    def download_file(self, file_info):
        """
        Скачивает файл с личного диска пользователя

        :param file_info: Информация о файле
        :return: True если файл обработан успешно, 'skipped' если пропущен
        """
        # Создаем путь для сохранения файла
        safe_path = sanitize_path(file_info['path'])
        local_path = self.download_dir / safe_path
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Проверяем, нужно ли пропустить файл
        should_skip, reason = self.should_create_empty_file(file_info)

        if should_skip:
            reason_text = {
                'video': 'видео',
                'image': 'изображение',
                'large': f'большой файл (>{format_size(config.MAX_FILE_SIZE)})',
                'total_limit': f'достигнут лимит {format_size(config.MAX_TOTAL_SIZE)}'
            }.get(reason, 'неизвестная причина')

            logger.info(f"Пропущено ({reason_text}): {file_info['path']} ({format_size(file_info['size'])})")
            return 'skipped'

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

    def should_convert_file(self, file_info: dict) -> bool:
        """
        Проверяет нужно ли конвертировать файл (кэширование)

        :param file_info: Информация о файле
        :return: True если нужно конвертировать, False если есть в кэше
        """
        # Получаем метаданные из БД
        db_record = self.db.get_file_metadata(file_info['path'])

        if not db_record:
            # Файла нет в БД - нужна конвертация
            return True

        # Проверяем есть ли уже MD файл
        if not db_record.get('markdown_path'):
            # MD файла нет - нужна конвертация
            return True

        # Проверяем изменился ли файл
        if (db_record.get('size') != file_info['size'] or
            db_record.get('modified') != file_info['modified']):
            # Файл изменился - нужна повторная конвертация
            logger.info(f"Файл изменился, требуется повторная конвертация: {file_info['path']}")
            return True

        # Проверяем существует ли MD файл физически
        md_path = self.markdown_dir / db_record['markdown_path']
        if not md_path.exists():
            # MD файл удален - нужна повторная конвертация
            logger.warning(f"MD файл удален, требуется повторная конвертация: {file_info['path']}")
            return True

        # Для видео проверяем статус транскрибации
        if db_record.get('transcription_status') == 'in_progress':
            logger.info(f"Транскрибация видео в процессе: {file_info['path']}")
            return False  # Не конвертируем, ждем завершения

        # Файл уже сконвертирован и не изменился - используем кэш
        logger.debug(f"Используется кэшированный MD: {file_info['path']}")
        return False

    def convert_file_to_markdown(self, local_path: Path, file_info: dict) -> str:
        """
        Конвертирует файл в Markdown если возможно

        :param local_path: Путь к локальному файлу
        :param file_info: Информация о файле
        :return: Относительный путь к MD файлу если успешно, пустая строка если нет
        """
        if not config.ENABLE_MARKDOWN_CONVERSION:
            return ""

        if not local_path.exists() or local_path.stat().st_size == 0:
            # Пустой файл - не конвертируем
            return ""

        # Проверяем кэш - может файл уже сконвертирован
        if not self.should_convert_file(file_info):
            # Файл уже сконвертирован, возвращаем путь из БД
            db_record = self.db.get_file_metadata(file_info['path'])
            if db_record and db_record.get('markdown_path'):
                return db_record['markdown_path']
            return ""

        # Проверяем, может ли кто-то из конвертеров обработать файл
        for converter in self.converters:
            if converter.can_convert(local_path):
                # Определяем расширение выходного файла
                # Для Excel и Parquet с включенным CSV режимом используем .csv
                # Для остальных используем .md
                file_ext = local_path.suffix.lower()

                # Проверяем, нужно ли сохранять как CSV
                use_csv = False
                if file_ext in ['.xlsx', '.xls', '.xlsm', '.xlsb']:
                    use_csv = hasattr(config, 'EXCEL_TO_CSV') and config.EXCEL_TO_CSV
                elif file_ext == '.parquet':
                    use_csv = hasattr(config, 'PARQUET_TO_CSV') and config.PARQUET_TO_CSV

                # Создаем путь для выходного файла
                # Сохраняем оригинальное расширение в имени, чтобы избежать конфликтов
                # Например: report.xlsx → report.xlsx.csv, report.pdf → report.pdf.md
                relative_path = local_path.relative_to(self.download_dir)
                output_extension = '.csv' if use_csv else '.md'
                md_filename = relative_path.name + output_extension
                md_path = self.markdown_dir / relative_path.parent / md_filename

                # Проверяем, это видео конвертер и включена ли асинхронность
                is_video = self.video_converter and converter == self.video_converter
                use_async = is_video and config.VIDEO_ASYNC_TRANSCRIPTION

                if use_async:
                    # Асинхронная обработка видео
                    operation_id, video_metadata, audio_path = self.video_converter.convert_async(local_path)

                    if operation_id:
                        # Сохраняем в БД статус "in_progress"
                        import json
                        self.db.update_transcription_status(
                            file_info['path'],
                            status='in_progress',
                            operation_id=operation_id,
                            video_metadata=json.dumps(video_metadata)
                        )

                        # Запоминаем аудио для удаления позже
                        if audio_path:
                            if not hasattr(self, 'pending_audio_files'):
                                self.pending_audio_files = []
                            self.pending_audio_files.append(audio_path)

                        logger.info(f"Видео отправлено на асинхронную транскрибацию: {file_info['path']}")
                        # Не возвращаем MD путь, так как транскрибация еще не завершена
                        return ""
                    else:
                        logger.error(f"Не удалось запустить асинхронную транскрибацию: {file_info['path']}")
                        return ""
                else:
                    # Синхронная конвертация (для всех файлов кроме видео, или если async отключен)
                    success = converter.convert_safe(local_path, md_path)

                    if not success:
                        return ""

                # Обработка успешной конвертации (только для синхронных)
                if not use_async:
                    logger.info(f"Конвертирован в MD: {file_info['path']}")

                    # Удаляем оригинал если настроено
                    if config.DELETE_ORIGINALS_AFTER_CONVERSION:
                        # Проверяем существует ли файл (может быть уже удален конвертером, например VideoConverter)
                        if not local_path.exists():
                            logger.debug(f"Оригинал уже удален: {file_info['path']}")
                        else:
                            import gc
                            # Принудительная сборка мусора для освобождения файловых дескрипторов
                            gc.collect()

                            # Пытаемся удалить с retry (особенно важно для Windows)
                            max_delete_attempts = 3
                            delete_delay = 0.5  # секунд

                            for attempt in range(max_delete_attempts):
                                try:
                                    time.sleep(delete_delay)  # Небольшая задержка перед попыткой
                                    local_path.unlink()
                                    logger.debug(f"Удален оригинал: {file_info['path']}")
                                    break
                                except PermissionError as e:
                                    if attempt < max_delete_attempts - 1:
                                        logger.warning(f"Файл заблокирован, попытка {attempt + 1}/{max_delete_attempts}: {file_info['path']}")
                                        time.sleep(delete_delay * (attempt + 1))
                                    else:
                                        logger.error(f"Не удалось удалить оригинал {file_info['path']} после {max_delete_attempts} попыток: {e}")
                                except Exception as e:
                                    logger.error(f"Ошибка при удалении оригинала {file_info['path']}: {e}")
                                    break

                    # Возвращаем относительный путь к MD файлу
                    md_relative = str(md_path.relative_to(self.markdown_dir))
                    return md_relative

                return ""

        # Файл не поддерживается конвертерами
        return ""

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

        # Проверяем метаданные из БД
        db_record = self.db.get_file_metadata(file_path)

        # Если это видео с транскрибацией в процессе, не скачиваем повторно
        if db_record and db_record.get('transcription_status') == 'in_progress':
            logger.debug(f"Видео с транскрибацией в процессе, пропускаем загрузку: {file_path}")
            return False

        # Если есть MD файл и исходный файл не изменился, не скачиваем
        if db_record and db_record.get('markdown_path'):
            md_path = self.markdown_dir / db_record['markdown_path']
            if md_path.exists():
                # Проверяем изменился ли файл
                if (db_record.get('size') == file_info['size'] and
                    db_record.get('modified') == file_info['modified']):
                    logger.debug(f"MD файл существует, исходный файл не изменился, пропускаем загрузку: {file_path}")
                    return False

        # Если файл есть в БД и не изменился (размер + дата), не скачиваем
        # Даже если локального файла нет (мог быть удален после обработки)
        if db_record:
            if (db_record.get('size') == file_info['size'] and
                db_record.get('modified') == file_info['modified']):
                logger.debug(f"Файл в БД не изменился, пропускаем загрузку: {file_path}")
                return False

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

        # Проверяем незавершенные транскрибации из предыдущих запусков
        self.check_pending_transcriptions()

        # Получаем список всех файлов и папок
        logger.info("Получение списка файлов...")

        # Пробуем загрузить из кэша если включено
        cached_result = None
        if config.ENABLE_FILES_CACHE:
            cached_result = self._load_cached_files_list(max_age_seconds=config.FILES_CACHE_LIFETIME)

        if cached_result:
            all_files, folders_list = cached_result
            folders_set = set(folders_list)
            logger.success(f"Использован кэш: {len(all_files)} файлов, {len(folders_set)} папок")
        else:
            # Получаем файлы с API
            folders_set = set()
            all_files = self.get_all_files_recursive(self.remote_folder_path, folders_set=folders_set)

            # Сохраняем в кэш если включено
            if config.ENABLE_FILES_CACHE and (all_files or folders_set):
                self._save_files_list_to_cache(all_files, folders_set)

        if not all_files and not folders_set:
            logger.warning("Файлы не найдены или произошла ошибка")
            return

        logger.info(f"Найдено файлов: {len(all_files)}")
        logger.info(f"Найдено папок: {len(folders_set)}")

        # Ручной выбор папок если включен MANUAL_MODE
        if config.MANUAL_MODE:
            # Анализируем папки
            folders_stats = self.analyze_folders(all_files)

            if not folders_stats:
                logger.warning("Не найдено папок для анализа")
                return

            # Интерактивный выбор
            selected_folders = self.select_folders_interactive(folders_stats)

            if not selected_folders:
                logger.warning("Синхронизация отменена - папки не выбраны")
                return

            # Фильтруем файлы по выбранным папкам
            root_folder = "(корневая папка)"
            filtered_files = []
            for file_info in all_files:
                file_path = file_info['path']
                path_parts = file_path.split('/')

                # Определяем папку первого уровня
                if len(path_parts) > 1:
                    folder_name = path_parts[0]
                else:
                    folder_name = root_folder

                # Добавляем файл если его папка выбрана
                if folder_name in selected_folders:
                    filtered_files.append(file_info)

            logger.success(f"После фильтрации осталось файлов: {len(filtered_files)}")
            all_files = filtered_files

            if not all_files:
                logger.warning("После фильтрации не осталось файлов")
                return

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
                should_skip, _ = self.should_create_empty_file(file_info)
                if not should_skip:
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
        image_count = 0
        large_file_count = 0
        limit_reached_count = 0
        converted_count = 0
        skipped_conversion_count = 0
        error_count = 0
        failed_files = []

        def process_file(file_info):
            nonlocal downloaded_count, updated_count, video_count, image_count, large_file_count, limit_reached_count, converted_count, skipped_conversion_count, error_count

            existing_metadata = self.db.get_file_metadata(file_info['path'])
            is_new = existing_metadata is None
            should_skip, reason = self.should_create_empty_file(file_info)

            download_result = self.download_file(file_info)

            # Обрабатываем пропущенные файлы
            if download_result == 'skipped':
                # Файл пропущен - НЕ сохраняем в БД для возможности повторной загрузки
                with self.metadata_lock:
                    if reason == 'video':
                        video_count += 1
                    elif reason == 'image':
                        image_count += 1
                    elif reason == 'large':
                        large_file_count += 1
                    elif reason == 'total_limit':
                        limit_reached_count += 1
                return (True, file_info['path'])

            # Обрабатываем успешно скачанные файлы
            if download_result:
                safe_path = sanitize_path(file_info['path'])
                local_path = self.download_dir / safe_path

                # Проверяем: это видео файл?
                is_video_file = self.video_converter and self.video_converter.can_convert(local_path)

                # Для видео сохраняем метаданные ДО конвертации
                # Это нужно для update_transcription_status в VideoConverter
                if is_video_file:
                    with self.metadata_lock:
                        self.db.save_file_metadata(
                            file_path=file_info['path'],
                            size=file_info['size'],
                            modified=file_info['modified'],
                            md5=file_info.get('md5', ''),
                            is_empty=False,
                            markdown_path=""  # Пока пусто, обновим после конвертации
                        )

                # Конвертируем файл в Markdown если возможно
                markdown_path = ""
                conversion_attempted = False

                # Проверяем: нужна ли конвертация?
                # Пропускаем если файл уже был сконвертирован и MD файл существует
                should_convert = True
                if existing_metadata and existing_metadata.get('markdown_path'):
                    # Проверяем существует ли MD файл
                    existing_md_path = self.markdown_dir / existing_metadata['markdown_path']
                    if existing_md_path.exists():
                        # MD файл существует - используем существующий путь
                        markdown_path = existing_metadata['markdown_path']
                        should_convert = False
                        skipped_conversion_count += 1
                        logger.debug(f"Конвертация пропущена (MD существует): {file_info['path']}")

                if should_convert:
                    # Конвертируем файл
                    conversion_attempted = True
                    markdown_path = self.convert_file_to_markdown(local_path, file_info)
                    if markdown_path:
                        converted_count += 1

                # Проверяем результат конвертации
                conversion_failed = conversion_attempted and not markdown_path and not is_video_file

                if conversion_failed:
                    # Конвертация провалилась для не-видео файла
                    # НЕ сохраняем в БД - это позволит повторить попытку при следующей синхронизации
                    logger.error(f"Ошибка конвертации {file_info['path']}: файл не добавлен в БД")
                    with self.metadata_lock:
                        error_count += 1

                    # Удаляем скачанный файл, чтобы освободить место
                    if local_path.exists():
                        try:
                            local_path.unlink()
                            logger.debug(f"Удален файл с ошибкой конвертации: {local_path}")
                        except Exception as e:
                            logger.warning(f"Не удалось удалить файл с ошибкой: {e}")

                    return (False, file_info['path'])

                # Для НЕ-видео файлов сохраняем в БД только после успешной конвертации
                if not is_video_file:
                    with self.metadata_lock:
                        self.db.save_file_metadata(
                            file_path=file_info['path'],
                            size=file_info['size'],
                            modified=file_info['modified'],
                            md5=file_info.get('md5', ''),
                            is_empty=False,
                            markdown_path=markdown_path  # Сохраняем результат конвертации
                        )

                # Обновляем markdown_path для видео если конвертация была успешной
                if is_video_file and markdown_path:
                    with self.metadata_lock:
                        self.db.update_markdown_path(file_info['path'], markdown_path)

                # Подсчитываем статистику
                with self.metadata_lock:
                    if is_new:
                        downloaded_count += 1
                    else:
                        updated_count += 1

                return (True, file_info['path'])
            else:
                # Ошибка загрузки - НЕ сохраняем в БД
                with self.metadata_lock:
                    error_count += 1
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
            failed_log = config.FAILED_DOWNLOADS_PATH
            failed_log.parent.mkdir(parents=True, exist_ok=True)
            with open(failed_log, 'w', encoding='utf-8') as f:
                f.write('\n'.join(failed_files))
            logger.warning(f"Список неудачно скачанных файлов сохранен в: {failed_log.absolute()}")

        # Итоговая статистика
        logger.info("=" * 70)
        logger.success("Синхронизация завершена!")
        logger.info("=" * 70)
        logger.info(f"Новых файлов скачано: {downloaded_count}")
        logger.info(f"Обновленных файлов: {updated_count}")
        logger.info(f"Видео (пропущено): {video_count}")
        logger.info(f"Изображения (пропущено): {image_count}")
        logger.info(f"Большие файлы >{format_size(config.MAX_FILE_SIZE)} (пропущено): {large_file_count}")
        logger.info(f"Достигнут лимит {format_size(config.MAX_TOTAL_SIZE)} (пропущено): {limit_reached_count}")
        logger.info(f"Пропущено (без изменений): {skipped_count}")
        if converted_count > 0:
            logger.info(f"Конвертировано в Markdown: {converted_count}")
        if skipped_conversion_count > 0:
            logger.info(f"Конвертация пропущена (MD существует): {skipped_conversion_count}")
        if deleted_local > 0:
            logger.warning(f"Удалено (отсутствуют на диске): {deleted_local}")
        if deleted_folders > 0:
            logger.warning(f"Удалено пустых папок: {deleted_folders}")
        if error_count > 0:
            logger.error(f"Ошибок при обработке: {error_count}")
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

        # Удаляем временные аудио файлы
        self.cleanup_pending_audio_files()

        # Ждем завершения всех транскрибаций если включено
        if config.VIDEO_WAIT_FOR_COMPLETION and config.CONVERT_VIDEO_FILES:
            self.wait_for_all_transcriptions()
