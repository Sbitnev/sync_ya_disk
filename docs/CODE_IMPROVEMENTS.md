# Рекомендации по улучшению кода синхронизатора

## 1. Добавить проверку свободного места на диске

### Файл: `src/syncer.py`

Добавить метод проверки свободного места перед началом синхронизации:

```python
import shutil
from pathlib import Path

class YandexDiskUserSyncer:
    def check_disk_space(self, required_space_gb: float = 50) -> bool:
        """
        Проверяет наличие свободного места на диске

        :param required_space_gb: Минимально требуемое место в ГБ
        :return: True если места достаточно
        """
        download_path = Path(self.download_dir)

        # Получаем информацию о диске
        disk_usage = shutil.disk_usage(download_path)
        free_gb = disk_usage.free / (1024 ** 3)

        logger.info(f"Свободное место на диске: {free_gb:.2f} ГБ")

        if free_gb < required_space_gb:
            logger.error(
                f"Недостаточно места на диске! "
                f"Требуется минимум {required_space_gb} ГБ, "
                f"доступно {free_gb:.2f} ГБ"
            )
            return False

        return True

    def sync(self):
        """Запускает процесс синхронизации"""
        # Проверяем место на диске перед началом
        if not self.check_disk_space(config.MIN_FREE_SPACE_GB):
            raise RuntimeError("Недостаточно места на диске для синхронизации")

        # Остальной код синхронизации...
```

### Файл: `src/config.py`

Добавить настройку минимального места:

```python
# Минимальное свободное место на диске (ГБ)
MIN_FREE_SPACE_GB = int(os.getenv("MIN_FREE_SPACE_GB", "50"))
```

---

## 2. Улучшить обработку CSV с разными кодировками

### Файл: `src/converters/csv_converter.py`

Заменить текущую реализацию на более надежную:

```python
import chardet
import pandas as pd
from pathlib import Path
from typing import Optional


class CSVToMarkdownConverter:
    """Конвертер CSV файлов в Markdown с автоопределением кодировки"""

    @staticmethod
    def detect_encoding(file_path: Path, sample_size: int = 10000) -> str:
        """
        Определяет кодировку файла

        :param file_path: Путь к файлу
        :param sample_size: Размер образца для анализа (байт)
        :return: Название кодировки
        """
        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size)
            result = chardet.detect(raw_data)
            detected_encoding = result['encoding']
            confidence = result['confidence']

            logger.debug(
                f"Определена кодировка {detected_encoding} "
                f"с уверенностью {confidence:.2%}"
            )

            return detected_encoding

    @staticmethod
    def try_read_csv(file_path: Path, encoding: str) -> Optional[pd.DataFrame]:
        """
        Пытается прочитать CSV с указанной кодировкой

        :param file_path: Путь к файлу
        :param encoding: Кодировка
        :return: DataFrame или None при ошибке
        """
        try:
            # Пробуем разные разделители
            for sep in [',', ';', '\t', '|']:
                try:
                    df = pd.read_csv(
                        file_path,
                        encoding=encoding,
                        sep=sep,
                        on_bad_lines='skip',
                        low_memory=False
                    )
                    # Проверяем что файл распарсился нормально
                    if len(df.columns) > 1:
                        logger.debug(
                            f"CSV успешно прочитан с кодировкой {encoding} "
                            f"и разделителем '{sep}'"
                        )
                        return df
                except Exception:
                    continue
            return None
        except Exception as e:
            logger.debug(f"Не удалось прочитать с кодировкой {encoding}: {e}")
            return None

    def convert(self, csv_path: Path, max_rows: int = 1000) -> str:
        """
        Конвертирует CSV в Markdown

        :param csv_path: Путь к CSV файлу
        :param max_rows: Максимальное количество строк для конвертации
        :return: Markdown строка
        """
        # Определяем кодировку
        detected_encoding = self.detect_encoding(csv_path)

        # Список кодировок для попыток (в порядке приоритета)
        encodings_to_try = [
            detected_encoding,
            'utf-8',
            'utf-16',
            'utf-16-le',
            'utf-16-be',
            'cp1251',
            'latin1',
            'iso-8859-1',
        ]

        # Убираем дубликаты, сохраняя порядок
        encodings_to_try = list(dict.fromkeys(filter(None, encodings_to_try)))

        df = None
        used_encoding = None

        # Пробуем разные кодировки
        for encoding in encodings_to_try:
            df = self.try_read_csv(csv_path, encoding)
            if df is not None:
                used_encoding = encoding
                break

        if df is None:
            raise ValueError(
                f"Не удалось прочитать CSV файл {csv_path.name}. "
                f"Попробованы кодировки: {', '.join(encodings_to_try)}"
            )

        logger.info(
            f"CSV файл прочитан с кодировкой {used_encoding}. "
            f"Размер: {len(df)} строк, {len(df.columns)} столбцов"
        )

        # Ограничиваем количество строк
        if len(df) > max_rows:
            logger.warning(
                f"CSV файл содержит {len(df)} строк. "
                f"Будет показано только первые {max_rows}"
            )
            df = df.head(max_rows)

        # Формируем Markdown
        markdown = f"# {csv_path.name}\n\n"
        markdown += f"**Кодировка**: {used_encoding}\n"
        markdown += f"**Строк**: {len(df)}\n"
        markdown += f"**Столбцов**: {len(df.columns)}\n\n"

        # Добавляем таблицу
        markdown += df.to_markdown(index=False)

        return markdown
```

### Обновить `requirements.txt`:

```
chardet>=5.2.0
```

---

## 3. Добавить санитизацию имен файлов

### Файл: `src/utils.py`

Добавить функцию для очистки имен файлов:

```python
import re
from pathlib import Path


def sanitize_filename(filename: str, replacement: str = '_') -> str:
    """
    Очищает имя файла от запрещенных символов

    :param filename: Исходное имя файла
    :param replacement: Символ для замены запрещенных символов
    :return: Очищенное имя файла
    """
    # Запрещенные символы в Windows и других ОС
    forbidden_chars = r'[<>:"/\\|?*\x00-\x1f]'

    # Заменяем запрещенные символы
    clean_name = re.sub(forbidden_chars, replacement, filename)

    # Убираем точки в начале и конце
    clean_name = clean_name.strip('. ')

    # Ограничиваем длину (Windows имеет лимит 255 символов)
    if len(clean_name) > 255:
        name, ext = os.path.splitext(clean_name)
        max_name_length = 255 - len(ext)
        clean_name = name[:max_name_length] + ext

    return clean_name


def sanitize_path(path: str) -> str:
    """
    Очищает путь, применяя санитизацию к каждой части

    :param path: Исходный путь
    :return: Очищенный путь
    """
    parts = Path(path).parts
    clean_parts = [sanitize_filename(part) for part in parts]
    return str(Path(*clean_parts))
```

### Использование в `src/syncer.py`:

```python
from src.utils import sanitize_filename, sanitize_path

def download_file(self, file_info: dict):
    remote_path = file_info['path']

    # Очищаем локальный путь
    clean_relative_path = sanitize_path(file_info['relative_path'])
    local_path = self.download_dir / clean_relative_path

    # Остальной код...
```

---

## 4. Улучшить систему повторных попыток

### Файл: `src/api_client.py`

Добавить экспоненциальную задержку:

```python
import time
from typing import Callable, Any


def retry_with_backoff(
    func: Callable,
    max_retries: int = 5,
    initial_delay: float = 1,
    max_delay: float = 60,
    backoff_factor: float = 2
) -> Any:
    """
    Выполняет функцию с экспоненциальной задержкой при ошибках

    :param func: Функция для выполнения
    :param max_retries: Максимальное количество попыток
    :param initial_delay: Начальная задержка (секунды)
    :param max_delay: Максимальная задержка (секунды)
    :param backoff_factor: Множитель для увеличения задержки
    :return: Результат функции
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e

            if attempt < max_retries - 1:
                # Вычисляем задержку
                current_delay = min(delay * (backoff_factor ** attempt), max_delay)

                logger.warning(
                    f"Попытка {attempt + 1}/{max_retries} не удалась: {e}. "
                    f"Повтор через {current_delay:.1f}с..."
                )

                time.sleep(current_delay)
            else:
                logger.error(
                    f"Все {max_retries} попыток исчерпаны. "
                    f"Последняя ошибка: {e}"
                )

    raise last_exception


class YandexDiskAPIClient:
    def download_file(self, url: str, local_path: Path):
        """Скачивает файл с повторными попытками"""

        def _download():
            response = self.session.get(
                url,
                stream=True,
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()

            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

        # Используем retry с экспоненциальной задержкой
        retry_with_backoff(
            _download,
            max_retries=config.MAX_RETRIES,
            initial_delay=config.RETRY_DELAY
        )
```

### Файл: `src/config.py`

Добавить настройки:

```python
# Настройки повторных попыток
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))
RETRY_DELAY = float(os.getenv("RETRY_DELAY", "1"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "60"))
```

---

## 5. Добавить фильтрацию временных файлов

### Файл: `src/config.py`

Добавить паттерны исключений:

```python
# Паттерны файлов для пропуска
SKIP_FILE_PATTERNS = [
    r'^~\$',            # Временные Office файлы (~$filename)
    r'^~WRL.*\.tmp$',   # Временные Word файлы
    r'\.tmp$',          # Все .tmp файлы
    r'\.temp$',         # Временные файлы
    r'\.drawio\.bkp$',  # Резервные копии Draw.io
    r'\.drawio\.dtmp$', # Временные Draw.io
    r'\.mpp$',          # Microsoft Project (пока не поддерживается)
    r'^\.~',            # Скрытые временные файлы
    r'^\._',            # macOS временные файлы
]
```

### Файл: `src/syncer.py`

Добавить проверку:

```python
import re
from src import config


def should_skip_file(file_path: str) -> bool:
    """
    Проверяет, нужно ли пропустить файл по паттернам

    :param file_path: Путь к файлу
    :return: True если файл нужно пропустить
    """
    filename = Path(file_path).name

    for pattern in config.SKIP_FILE_PATTERNS:
        if re.search(pattern, filename, re.IGNORECASE):
            logger.debug(f"Файл {filename} пропущен по паттерну {pattern}")
            return True

    return False


class YandexDiskUserSyncer:
    def sync(self):
        # ... получение списка файлов ...

        # Фильтруем файлы
        files_to_sync = [
            f for f in all_files
            if not should_skip_file(f['path'])
        ]

        skipped_count = len(all_files) - len(files_to_sync)
        if skipped_count > 0:
            logger.info(
                f"Пропущено {skipped_count} временных/служебных файлов"
            )

        # Продолжаем синхронизацию с отфильтрованным списком
        # ...
```

---

## 6. Улучшить логирование

### Файл: `src/syncer.py`

Добавить сводку по ошибкам:

```python
from collections import defaultdict


class SyncStatistics:
    """Класс для сбора статистики синхронизации"""

    def __init__(self):
        self.downloaded = 0
        self.converted = 0
        self.skipped_video = 0
        self.skipped_images = 0
        self.errors_by_type = defaultdict(list)
        self.failed_files = []

    def add_error(self, error_type: str, file_path: str, message: str):
        """Добавляет информацию об ошибке"""
        self.errors_by_type[error_type].append({
            'file': file_path,
            'message': message
        })
        self.failed_files.append(file_path)

    def print_summary(self):
        """Выводит сводку по синхронизации"""
        logger.info("=" * 80)
        logger.info("СВОДКА ПО СИНХРОНИЗАЦИИ")
        logger.info("=" * 80)
        logger.info(f"Скачано файлов: {self.downloaded}")
        logger.info(f"Конвертировано в Markdown: {self.converted}")
        logger.info(f"Пропущено видео: {self.skipped_video}")
        logger.info(f"Пропущено изображений: {self.skipped_images}")

        if self.errors_by_type:
            logger.info(f"\nОШИБКИ ПО КАТЕГОРИЯМ:")
            for error_type, errors in self.errors_by_type.items():
                logger.info(f"  {error_type}: {len(errors)}")

            # Выводим первые 5 ошибок каждого типа
            logger.info(f"\nПРИМЕРЫ ОШИБОК:")
            for error_type, errors in self.errors_by_type.items():
                logger.info(f"\n  {error_type}:")
                for error in errors[:5]:
                    logger.info(f"    - {error['file']}: {error['message']}")

        logger.info("=" * 80)


class YandexDiskUserSyncer:
    def __init__(self, ...):
        # ...
        self.stats = SyncStatistics()

    def sync(self):
        try:
            # ... процесс синхронизации ...
            pass
        finally:
            # Всегда выводим сводку в конце
            self.stats.print_summary()
```

---

## 7. Мониторинг в процессе синхронизации

### Файл: `src/syncer.py`

Добавить периодическую проверку места на диске:

```python
import shutil
from datetime import datetime, timedelta


class YandexDiskUserSyncer:
    def __init__(self, ...):
        # ...
        self.last_disk_check = datetime.now()
        self.disk_check_interval = timedelta(minutes=5)

    def check_disk_space_during_sync(self):
        """Проверяет место на диске в процессе синхронизации"""
        now = datetime.now()

        # Проверяем каждые 5 минут
        if now - self.last_disk_check < self.disk_check_interval:
            return

        self.last_disk_check = now

        disk_usage = shutil.disk_usage(self.download_dir)
        free_gb = disk_usage.free / (1024 ** 3)

        logger.info(f"💾 Свободно на диске: {free_gb:.2f} ГБ")

        # Предупреждение при низком месте
        if free_gb < config.MIN_FREE_SPACE_GB:
            logger.warning(
                f"⚠️ ВНИМАНИЕ: Осталось мало места на диске ({free_gb:.2f} ГБ)! "
                f"Рекомендуется остановить синхронизацию."
            )

        # Критическое предупреждение
        if free_gb < 10:
            raise RuntimeError(
                f"Критически мало места на диске ({free_gb:.2f} ГБ)! "
                f"Синхронизация остановлена."
            )

    def download_and_process_file(self, file_info: dict):
        """Скачивает и обрабатывает файл"""
        # Проверяем место перед скачиванием
        self.check_disk_space_during_sync()

        # ... остальной код ...
```

---

## Итоговый чеклист изменений

### Высокий приоритет (внедрить сразу)
- [x] Проверка свободного места перед началом
- [ ] Фильтрация временных файлов
- [ ] Улучшенная обработка CSV кодировок
- [ ] Санитизация имен файлов

### Средний приоритет (на этой неделе)
- [ ] Экспоненциальная задержка при ошибках
- [ ] Улучшенное логирование и сводка
- [ ] Мониторинг места в процессе синхронизации

### Низкий приоритет (можно отложить)
- [ ] Поддержка Draw.io
- [ ] Поддержка Microsoft Project
- [ ] Система уведомлений

---

**Документ создан**: 20 января 2026
