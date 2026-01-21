"""
Скрипт для выгрузки ВСЕХ файлов с Яндекс.Диска в папку stash/

Скачивает все файлы без фильтрации, конвертации и использования БД.
Просто полная выгрузка всего содержимого диска.
"""
import sys
import time
import json
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

        # Файл для сохранения прогресса
        self.progress_file = self.output_dir / ".download_progress.json"

        # Счетчики
        self.total_downloaded_bytes = 0
        self.download_lock = Lock()

        # Множество успешно загруженных файлов
        self.completed_files = self._load_progress()

        # Прогресс-бар для общего размера (будет создан в download_all)
        self.size_pbar = None

        # HTTP сессия
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0
        )
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)

    def _load_progress(self):
        """Загружает прогресс из файла"""
        if not self.progress_file.exists():
            return set()

        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                completed = set(data.get('completed_files', []))
                if completed:
                    logger.info(f"Загружен прогресс: {len(completed)} файлов уже скачано")
                return completed
        except Exception as e:
            logger.warning(f"Не удалось загрузить прогресс: {e}")
            return set()

    def _save_progress(self):
        """Сохраняет прогресс в файл"""
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'completed_files': list(self.completed_files),
                    'timestamp': time.time()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Не удалось сохранить прогресс: {e}")

    def _mark_completed(self, file_path):
        """Отмечает файл как завершенный"""
        with self.download_lock:
            self.completed_files.add(file_path)
            # Сохраняем прогресс каждые 10 файлов
            if len(self.completed_files) % 10 == 0:
                self._save_progress()

    def _request_with_retry(self, method, url, max_retries=3, context="", **kwargs):
        """Выполняет HTTP запрос с повторными попытками"""
        for attempt in range(max_retries):
            try:
                response = getattr(self.session, method)(url, timeout=30, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response is not None else 'неизвестно'
                try:
                    error_body = e.response.json() if e.response else {}
                    error_msg = error_body.get('message', str(e))
                except:
                    error_msg = str(e)
                logger.error(f"HTTP ошибка {status_code}{context}: {error_msg}")
                return None
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Ошибка запроса{context} (попытка {attempt + 1}/{max_retries})")
                    time.sleep(2 * (attempt + 1))
                    continue
                else:
                    logger.error(f"Ошибка{context} после {max_retries} попыток: {e}")
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

            response = self._request_with_retry('get', url, headers=headers, params=params, context=f" для папки: {path}")
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
        # Проверяем прогресс - может файл уже загружен
        if file_info['path'] in self.completed_files:
            logger.debug(f"Файл уже в списке завершенных: {file_info['path']}")
            return True

        # Создаем путь для сохранения
        safe_path = sanitize_path(file_info['path'])
        local_path = self.output_dir / safe_path
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Проверяем, существует ли файл уже
        if local_path.exists():
            existing_size = local_path.stat().st_size
            if existing_size == file_info['size']:
                logger.debug(f"Файл уже существует с правильным размером: {file_info['path']}")
                self._mark_completed(file_info['path'])
                return True
            else:
                # Файл частично загружен - удаляем
                logger.warning(f"Удаляем частично загруженный файл: {file_info['path']} ({format_size(existing_size)} из {format_size(file_info['size'])})")
                try:
                    local_path.unlink()
                except Exception as e:
                    logger.error(f"Не удалось удалить частично загруженный файл: {e}")
                    return False

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
                    # Отключаем индивидуальный прогресс-бар, чтобы не засорять вывод
                    # Общий прогресс-бар по размеру обновляется в реальном времени
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        # Обновляем общий прогресс-бар в реальном времени
                        if self.size_pbar:
                            with self.download_lock:
                                self.size_pbar.update(len(chunk))

                with self.download_lock:
                    self.total_downloaded_bytes += file_info['size']

                # Отмечаем файл как завершенный
                self._mark_completed(file_info['path'])

                # Используем debug вместо success, чтобы не засорять консоль с прогресс-барами
                logger.debug(f"Скачан: {file_info['path']} ({format_size(file_info['size'])})")
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

        logger.info(f"Найдено файлов на диске: {len(all_files)}")

        # Подсчитываем общий размер
        total_size = sum(f['size'] for f in all_files)
        logger.info(f"Общий размер: {format_size(total_size)}")

        # Фильтруем уже скачанные файлы и определяем новые
        files_to_download = []
        already_downloaded = 0
        already_downloaded_size = 0
        partial_files_count = 0
        partial_files_size = 0
        new_files_count = 0
        new_files_size = 0

        # Определяем файлы, которые были в предыдущем прогрессе
        all_file_paths = {f['path'] for f in all_files}

        # Находим новые файлы (которых не было в прогрессе)
        if self.completed_files:
            new_file_paths = all_file_paths - self.completed_files
            if new_file_paths:
                new_files_count = len(new_file_paths)
                new_files_size = sum(f['size'] for f in all_files if f['path'] in new_file_paths)

        for file_info in all_files:
            safe_path = sanitize_path(file_info['path'])
            local_path = self.output_dir / safe_path

            # Проверяем по прогрессу
            if file_info['path'] in self.completed_files:
                # Дополнительно проверяем существует ли файл локально
                if local_path.exists():
                    existing_size = local_path.stat().st_size
                    if existing_size == file_info['size']:
                        already_downloaded += 1
                        already_downloaded_size += file_info['size']
                        continue
                    else:
                        # Файл был в прогрессе, но локально поврежден - перезагрузим
                        logger.warning(f"Файл в прогрессе, но локально поврежден: {file_info['path']}")
                        partial_files_count += 1
                        partial_files_size += existing_size
                        files_to_download.append(file_info)
                        continue
                else:
                    # Файл был в прогрессе, но удален локально - перезагрузим
                    logger.warning(f"Файл в прогрессе, но удален локально: {file_info['path']}")
                    files_to_download.append(file_info)
                    continue

            # Проверяем локальный файл (для файлов не в прогрессе)
            if local_path.exists():
                existing_size = local_path.stat().st_size
                if existing_size == file_info['size']:
                    already_downloaded += 1
                    already_downloaded_size += file_info['size']
                    # Добавляем в прогресс
                    self._mark_completed(file_info['path'])
                    continue
                else:
                    # Частично загруженный файл
                    partial_files_count += 1
                    partial_files_size += existing_size

            files_to_download.append(file_info)

        # Информация о возобновлении и новых файлах
        if already_downloaded > 0 or new_files_count > 0:
            logger.info("=" * 70)
            if new_files_count > 0:
                logger.info("ОБНАРУЖЕНЫ НОВЫЕ ФАЙЛЫ НА ДИСКЕ")
            else:
                logger.info("ВОЗОБНОВЛЕНИЕ ЗАГРУЗКИ")
            logger.info("=" * 70)

            if already_downloaded > 0:
                logger.info(f"Уже скачано файлов: {already_downloaded}")
                logger.info(f"Размер скачанных файлов: {format_size(already_downloaded_size)}")

            if new_files_count > 0:
                logger.success(f"Новых файлов на диске: {new_files_count}")
                logger.success(f"Размер новых файлов: {format_size(new_files_size)}")

            if partial_files_count > 0:
                logger.warning(f"Поврежденных/частичных файлов: {partial_files_count} ({format_size(partial_files_size)})")
                logger.warning("Эти файлы будут удалены и загружены заново")

            logger.info("=" * 70)

        logger.info(f"Файлов к скачиванию: {len(files_to_download)}")
        remaining_size = sum(f['size'] for f in files_to_download)
        logger.info(f"Размер к скачиванию: {format_size(remaining_size)}")

        if not files_to_download:
            logger.success("Все файлы уже скачаны!")
            logger.info("При следующем запуске будут загружены только новые файлы с диска")
            return

        # Скачиваем файлы
        logger.info(f"Начинаем загрузку ({max_workers} потоков)...")
        logger.info("=" * 70)

        success_count = 0
        failed_count = 0
        failed_files = []

        # Создаем прогресс-бары
        with tqdm(
            total=remaining_size,
            desc="Размер загрузки",
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            position=0,
            colour='green'
        ) as size_pbar, \
        tqdm(
            total=len(files_to_download),
            desc="Файлы       ",
            unit="файл",
            position=1,
            colour='blue'
        ) as files_pbar:

            # Сохраняем ссылку на прогресс-бар размера
            self.size_pbar = size_pbar

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self.download_file, file_info): file_info
                    for file_info in files_to_download
                }

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

                    files_pbar.update(1)

            # Очищаем ссылку на прогресс-бар
            self.size_pbar = None

        # Небольшая пауза, чтобы увидеть завершенные прогресс-бары
        time.sleep(0.5)

        # Сохраняем финальный прогресс
        self._save_progress()

        # Итоговая статистика
        logger.info("=" * 70)
        logger.success("ВЫГРУЗКА ЗАВЕРШЕНА!")
        logger.info("=" * 70)

        # Статистика текущего сеанса
        logger.info("Текущий сеанс:")
        logger.info(f"  Успешно скачано: {success_count}")
        if new_files_count > 0 and success_count <= new_files_count:
            logger.info(f"  Новых файлов загружено: {success_count}/{new_files_count}")
        logger.info(f"  Ошибок: {failed_count}")
        logger.info(f"  Скачано данных: {format_size(self.total_downloaded_bytes)}")

        # Общая статистика
        logger.info("")
        logger.info("Общая статистика:")
        logger.info(f"  Всего файлов на диске: {len(all_files)}")
        logger.info(f"  Загружено локально: {already_downloaded + success_count}")
        logger.info(f"  Всего данных: {format_size(already_downloaded_size + self.total_downloaded_bytes)}")

        if new_files_count > 0:
            logger.info(f"  Новых файлов обнаружено: {new_files_count}")

        logger.info("=" * 70)

        if failed_files:
            failed_log = Path("stash_failed.txt")
            with open(failed_log, 'w', encoding='utf-8') as f:
                f.write('\n'.join(failed_files))
            logger.warning(f"Список неудачных файлов: {failed_log.absolute()}")
            logger.warning("При следующем запуске неудачные файлы будут загружены повторно")
        else:
            logger.success("Все файлы успешно загружены!")
            logger.info("Файл прогресса сохранен для инкрементальных обновлений")
            logger.info("При следующем запуске будут загружены только новые файлы")


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
