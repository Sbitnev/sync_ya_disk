"""
Скрипт для обработки файлов из stash/ в Markdown
Работает с уже скачанными файлами, не требует подключения к Яндекс.Диску

Использует настройки из src/config.py:
- SKIP_VIDEO_FILES - пропускать ли видео
- SKIP_IMAGE_FILES - пропускать ли изображения
- SKIP_PARQUET_FILES - пропускать ли parquet
- MAX_FILE_SIZE - максимальный размер файла для обработки
- ENABLE_MARKDOWN_CONVERSION - включена ли конвертация
"""
import sys
from pathlib import Path
from tqdm import tqdm
from loguru import logger

# Настройка логирования
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)
logger.add(
    "stash_processing.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="DEBUG",
    rotation="10 MB"
)

from src import config
from src.converters import (
    WordConverter, CSVConverter, ExcelConverter, PDFConverter,
    TextConverter, PowerPointConverter, HTMLConverter,
    ParquetConverter, RTFConverter, ArchiveConverter
)
from src.utils import format_size


class StashProcessor:
    """Обработчик файлов из stash/ в Markdown"""

    def __init__(self, source_dir="stash", output_dir="stash_markdown", apply_filters=True):
        """
        :param source_dir: Папка с скачанными файлами (stash)
        :param output_dir: Папка для markdown файлов (stash_markdown)
        :param apply_filters: Применять ли фильтры из config (видео, изображения, размер)
        """
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.apply_filters = apply_filters

        if not self.source_dir.exists():
            raise ValueError(f"Папка {source_dir} не найдена. Сначала запустите run_stash_download.py")

        # Создаем выходную папку
        self.output_dir.mkdir(exist_ok=True)

        # Инициализируем конвертеры в зависимости от настроек
        self.converters = []

        if config.ENABLE_MARKDOWN_CONVERSION:
            if config.CONVERT_WORD_FILES:
                self.converters.append(WordConverter())
            if config.CONVERT_CSV_FILES:
                self.converters.append(CSVConverter())
            if config.CONVERT_EXCEL_FILES:
                self.converters.append(ExcelConverter())
            if config.CONVERT_PDF_FILES:
                self.converters.append(PDFConverter())
            if config.CONVERT_TEXT_FILES:
                self.converters.append(TextConverter())
            if config.CONVERT_POWERPOINT_FILES:
                self.converters.append(PowerPointConverter())
            if config.CONVERT_HTML_FILES:
                self.converters.append(HTMLConverter())
            if config.CONVERT_PARQUET_FILES:
                self.converters.append(ParquetConverter())
            if config.CONVERT_RTF_FILES:
                self.converters.append(RTFConverter())
            if config.CONVERT_ARCHIVES:
                self.converters.append(ArchiveConverter())

        # Статистика
        self.stats = {
            'total_files': 0,
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'skipped_by_filter': 0,
            'skipped_no_converter': 0,
            'already_exists': 0
        }

    def should_skip_file(self, file_path: Path) -> tuple[bool, str]:
        """
        Проверяет, нужно ли пропустить файл согласно фильтрам

        :return: (should_skip, reason)
        """
        if not self.apply_filters:
            return False, ""

        file_size = file_path.stat().st_size
        ext = file_path.suffix.lower()

        # Проверяем размер файла
        if config.SKIP_LARGE_FILES and file_size > config.MAX_FILE_SIZE:
            return True, f"Слишком большой файл ({format_size(file_size)})"

        # Проверяем видео
        if config.SKIP_VIDEO_FILES and ext in config.VIDEO_EXTENSIONS:
            return True, "Видео файл"

        # Проверяем изображения
        if config.SKIP_IMAGE_FILES and ext in config.IMAGE_EXTENSIONS:
            return True, "Файл изображения"

        # Проверяем parquet
        if config.SKIP_PARQUET_FILES and ext in config.PARQUET_EXTENSIONS:
            return True, "Parquet файл"

        return False, ""

    def get_output_path(self, source_file: Path) -> Path:
        """Получает путь для выходного markdown файла"""
        relative_path = source_file.relative_to(self.source_dir)
        md_path = self.output_dir / relative_path.with_suffix('.md')
        return md_path

    def process_file(self, file_path: Path) -> bool:
        """
        Обрабатывает один файл

        :return: True если успешно обработан
        """
        # Проверяем фильтры
        should_skip, reason = self.should_skip_file(file_path)
        if should_skip:
            logger.debug(f"Пропущен: {file_path.name} ({reason})")
            self.stats['skipped_by_filter'] += 1
            return False

        # Получаем путь для выходного файла
        output_path = self.get_output_path(file_path)

        # Проверяем, не существует ли уже
        if output_path.exists():
            # Проверяем время модификации
            source_mtime = file_path.stat().st_mtime
            output_mtime = output_path.stat().st_mtime

            if output_mtime >= source_mtime:
                logger.debug(f"Уже существует: {file_path.name}")
                self.stats['already_exists'] += 1
                return False

        # Ищем подходящий конвертер
        converter = None
        for conv in self.converters:
            if conv.can_convert(str(file_path)):
                converter = conv
                break

        if not converter:
            logger.debug(f"Нет конвертера для: {file_path.name}")
            self.stats['skipped_no_converter'] += 1
            return False

        # Конвертируем
        try:
            # Создаем директорию для выходного файла
            output_path.parent.mkdir(parents=True, exist_ok=True)

            success = converter.convert(str(file_path), str(output_path))

            if success:
                logger.success(f"Обработан: {file_path.name} → {output_path.name}")
                self.stats['processed'] += 1
                return True
            else:
                logger.warning(f"Не удалось обработать: {file_path.name}")
                self.stats['errors'] += 1
                return False

        except Exception as e:
            logger.error(f"Ошибка при обработке {file_path.name}: {e}")
            self.stats['errors'] += 1
            return False

    def process_all(self):
        """Обрабатывает все файлы из stash/"""
        logger.info("=" * 70)
        logger.info("ОБРАБОТКА ФАЙЛОВ ИЗ STASH В MARKDOWN")
        logger.info("=" * 70)
        logger.info(f"Источник: {self.source_dir.absolute()}")
        logger.info(f"Назначение: {self.output_dir.absolute()}")
        logger.info(f"Применять фильтры: {'Да' if self.apply_filters else 'Нет'}")
        logger.info(f"Конвертация включена: {'Да' if config.ENABLE_MARKDOWN_CONVERSION else 'Нет'}")

        if not config.ENABLE_MARKDOWN_CONVERSION:
            logger.error("Конвертация в Markdown отключена в config.py (ENABLE_MARKDOWN_CONVERSION)")
            return

        if not self.converters:
            logger.error("Не настроены конвертеры. Проверьте CONVERT_*_FILES в config.py")
            return

        logger.info(f"Активных конвертеров: {len(self.converters)}")
        logger.info("=" * 70)

        # Получаем список всех файлов
        logger.info("Сканирование файлов...")
        all_files = list(self.source_dir.rglob("*"))
        all_files = [f for f in all_files if f.is_file()]

        self.stats['total_files'] = len(all_files)

        if not all_files:
            logger.warning("Файлы не найдены в папке stash/")
            return

        logger.info(f"Найдено файлов: {len(all_files)}")
        logger.info("Начинаем обработку...")
        logger.info("=" * 70)

        # Обрабатываем файлы с прогресс-баром
        for file_path in tqdm(all_files, desc="Обработка файлов", unit="файл"):
            self.process_file(file_path)

        # Итоговая статистика
        logger.info("=" * 70)
        logger.success("ОБРАБОТКА ЗАВЕРШЕНА!")
        logger.info("=" * 70)
        logger.info(f"Всего файлов: {self.stats['total_files']}")
        logger.info(f"Обработано: {self.stats['processed']}")
        logger.info(f"Уже существовали: {self.stats['already_exists']}")
        logger.info(f"Пропущено (фильтры): {self.stats['skipped_by_filter']}")
        logger.info(f"Пропущено (нет конвертера): {self.stats['skipped_no_converter']}")
        logger.info(f"Ошибок: {self.stats['errors']}")
        logger.info("=" * 70)

        # Выводим детали фильтрации если применялась
        if self.apply_filters:
            logger.info("")
            logger.info("Примененные фильтры:")
            logger.info(f"  • Видео: {'пропускать' if config.SKIP_VIDEO_FILES else 'обрабатывать'}")
            logger.info(f"  • Изображения: {'пропускать' if config.SKIP_IMAGE_FILES else 'обрабатывать'}")
            logger.info(f"  • Parquet: {'пропускать' if config.SKIP_PARQUET_FILES else 'обрабатывать'}")
            logger.info(f"  • Макс. размер: {format_size(config.MAX_FILE_SIZE) if config.SKIP_LARGE_FILES else 'без ограничений'}")


def main():
    """Главная функция"""
    # Валидация конфигурации
    try:
        config.validate_config()
    except ValueError as e:
        logger.error(str(e))
        return 1

    # Создаем процессор и запускаем обработку
    try:
        processor = StashProcessor(
            source_dir="stash",
            output_dir="stash_markdown",
            apply_filters=True  # Применяем фильтры из config.py
        )
        processor.process_all()
        return 0
    except KeyboardInterrupt:
        logger.warning("Обработка прервана пользователем")
        return 130
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
