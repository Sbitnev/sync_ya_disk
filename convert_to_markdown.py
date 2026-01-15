"""
Скрипт для преобразования файлов из downloaded_files в Markdown
Работает с уже скачанными файлами, не требует подключения к Яндекс.Диску
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

from src import config
from src.database import MetadataDatabase
from src.converters import (
    WordConverter, CSVConverter, ExcelConverter, PDFConverter,
    TextConverter, PowerPointConverter, HTMLConverter,
    ParquetConverter, RTFConverter, ArchiveConverter
)


class MarkdownConverter:
    """Конвертер локальных файлов в Markdown"""

    def __init__(self, source_dir, output_dir, use_database=True):
        """
        :param source_dir: Папка с исходными файлами (downloaded_files)
        :param output_dir: Папка для markdown файлов (markdown_files)
        :param use_database: Использовать ли БД для отслеживания конвертированных файлов
        """
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.use_database = use_database

        # Создаем выходную папку
        self.output_dir.mkdir(exist_ok=True)

        # Подключаемся к БД если нужно
        if use_database:
            self.db = MetadataDatabase(config.METADATA_DB_PATH)
        else:
            self.db = None

        # Инициализируем конвертеры
        self.converters = []

        word_converter = WordConverter() if config.CONVERT_WORD_FILES else None
        csv_converter = CSVConverter(
            max_rows=config.CSV_MAX_ROWS,
            max_columns=config.CSV_MAX_COLUMNS
        ) if config.CONVERT_CSV_FILES else None
        excel_converter = ExcelConverter(
            max_rows=config.EXCEL_MAX_ROWS,
            max_columns=config.EXCEL_MAX_COLUMNS,
            sheets_limit=config.EXCEL_MAX_SHEETS
        ) if config.CONVERT_EXCEL_FILES else None
        pdf_converter = PDFConverter(
            max_pages=config.PDF_MAX_PAGES
        ) if config.CONVERT_PDF_FILES else None
        text_converter = TextConverter() if config.CONVERT_TEXT_FILES else None
        ppt_converter = PowerPointConverter() if config.CONVERT_POWERPOINT_FILES else None
        html_converter = HTMLConverter() if config.CONVERT_HTML_FILES else None
        parquet_converter = ParquetConverter(
            max_rows=config.PARQUET_MAX_ROWS,
            max_columns=config.PARQUET_MAX_COLUMNS
        ) if config.CONVERT_PARQUET_FILES else None
        rtf_converter = RTFConverter() if config.CONVERT_RTF_FILES else None

        # Собираем доступные конвертеры для Archive
        available_converters = [
            c for c in [
                word_converter, csv_converter, excel_converter,
                pdf_converter, text_converter, ppt_converter,
                html_converter, parquet_converter, rtf_converter
            ] if c is not None
        ]

        # Archive конвертер (инициализируем последним)
        archive_converter = None
        if config.CONVERT_ARCHIVE_FILES:
            archive_converter = ArchiveConverter(
                converters_registry=available_converters,
                max_depth=config.ARCHIVE_MAX_DEPTH
            )

        # Добавляем все конвертеры в список
        self.converters = [
            c for c in [
                word_converter, csv_converter, excel_converter,
                pdf_converter, text_converter, ppt_converter,
                html_converter, parquet_converter, rtf_converter,
                archive_converter
            ] if c is not None
        ]

        # Статистика
        self.stats = {
            'total_files': 0,
            'converted': 0,
            'skipped': 0,
            'errors': 0,
            'by_extension': {}
        }

    def get_converter_for_file(self, file_path):
        """Находит подходящий конвертер для файла"""
        for converter in self.converters:
            if converter.can_convert(file_path):
                return converter

        return None

    def convert_file(self, file_path, db_relative_path=None):
        """
        Конвертирует один файл в markdown

        :param file_path: Путь к исходному файлу
        :param db_relative_path: Относительный путь в БД (если используется БД)
        :return: Относительный путь к MD файлу если успешно, пустая строка если нет
        """
        # Получаем относительный путь от source_dir
        try:
            relative_path = file_path.relative_to(self.source_dir)
        except ValueError:
            if db_relative_path:
                relative_path = Path(db_relative_path)
            else:
                logger.error(f"Файл {file_path} не находится в {self.source_dir}")
                return ""

        # Формируем путь для markdown файла
        # Сохраняем расширение: file.docx -> file.docx.md
        md_filename = file_path.name + '.md'
        md_path = self.output_dir / relative_path.parent / md_filename

        # Создаем директорию если нужно
        md_path.parent.mkdir(parents=True, exist_ok=True)

        # Находим подходящий конвертер
        converter = self.get_converter_for_file(file_path)

        if not converter:
            return ""

        # Конвертируем
        try:
            success = converter.convert(file_path, md_path)
            if success:
                # Возвращаем относительный путь к MD файлу
                md_relative = str(md_path.relative_to(self.output_dir))
                return md_relative
            return ""
        except Exception as e:
            logger.error(f"Ошибка конвертации {file_path}: {e}")
            return ""

    def scan_files(self):
        """Сканирует файлы для конвертации - из БД или из папки"""
        if self.use_database and self.db:
            # Получаем файлы из БД без markdown_path
            logger.info("Поиск файлов без конвертации в БД...")
            db_files = self.db.get_files_without_markdown()
            logger.info(f"Найдено файлов в БД без MD: {len(db_files)}")

            convertible_files = []
            for file_record in db_files:
                file_path = self.source_dir / file_record['path']
                # Проверяем что файл существует и есть конвертер
                if file_path.exists() and file_path.is_file():
                    if self.get_converter_for_file(file_path):
                        convertible_files.append((file_path, file_record['path']))

            logger.info(f"Из них можно конвертировать: {len(convertible_files)}")
            return convertible_files

        else:
            # Сканируем папку напрямую (старый метод)
            logger.info(f"Сканирование папки: {self.source_dir}")

            all_files = []

            # Рекурсивно обходим все файлы
            for file_path in self.source_dir.rglob('*'):
                if file_path.is_file():
                    all_files.append(file_path)

            logger.info(f"Найдено файлов: {len(all_files)}")

            # Фильтруем только те, для которых есть конвертер
            convertible_files = []

            for file_path in all_files:
                if self.get_converter_for_file(file_path):
                    try:
                        relative_path = str(file_path.relative_to(self.source_dir))
                    except ValueError:
                        relative_path = file_path.name
                    convertible_files.append((file_path, relative_path))

            logger.info(f"Из них можно конвертировать: {len(convertible_files)}")

            return convertible_files

    def convert_all(self):
        """Конвертирует все файлы из source_dir"""
        # Сканируем файлы
        files = self.scan_files()
        self.stats['total_files'] = len(files)

        if not files:
            logger.warning("Нет файлов для конвертации")
            return

        # Конвертируем с прогресс-баром
        logger.info("Начинаем конвертацию...")

        for file_path, db_relative_path in tqdm(files, desc="Конвертация файлов"):
            extension = file_path.suffix.lower()

            # Обновляем статистику по расширениям
            if extension not in self.stats['by_extension']:
                self.stats['by_extension'][extension] = {
                    'total': 0,
                    'converted': 0,
                    'errors': 0
                }

            self.stats['by_extension'][extension]['total'] += 1

            # Конвертируем
            markdown_path = self.convert_file(file_path, db_relative_path)

            if markdown_path:
                self.stats['converted'] += 1
                self.stats['by_extension'][extension]['converted'] += 1

                # Обновляем БД если используем её
                if self.use_database and self.db:
                    try:
                        self.db.update_markdown_path(db_relative_path, markdown_path)
                    except Exception as e:
                        logger.error(f"Ошибка обновления БД для {db_relative_path}: {e}")
            else:
                self.stats['errors'] += 1
                self.stats['by_extension'][extension]['errors'] += 1

        # Выводим статистику
        self.print_stats()

    def print_stats(self):
        """Выводит статистику конвертации"""
        print("\n" + "=" * 70)
        print("СТАТИСТИКА КОНВЕРТАЦИИ")
        print("=" * 70)
        print(f"Всего файлов:       {self.stats['total_files']}")
        print(f"Успешно:            {self.stats['converted']} ({self.stats['converted'] / self.stats['total_files'] * 100:.1f}%)")
        print(f"Ошибки:             {self.stats['errors']}")
        print()

        # Статистика по расширениям
        if self.stats['by_extension']:
            print("По типам файлов:")
            print("-" * 70)
            print(f"{'Расширение':<15} {'Всего':>10} {'Успешно':>10} {'Ошибки':>10} {'%':>10}")
            print("-" * 70)

            for ext in sorted(self.stats['by_extension'].keys()):
                data = self.stats['by_extension'][ext]
                total = data['total']
                converted = data['converted']
                errors = data['errors']
                percentage = (converted / total * 100) if total > 0 else 0

                print(f"{ext:<15} {total:>10} {converted:>10} {errors:>10} {percentage:>9.1f}%")

        print("=" * 70)
        print(f"Результаты сохранены в: {self.output_dir}")
        print("=" * 70)


def main():
    """Главная функция"""
    print("=" * 70)
    print("КОНВЕРТАЦИЯ ФАЙЛОВ В MARKDOWN")
    print("=" * 70)
    print()

    # Проверяем, включена ли конвертация в конфиге
    if not config.ENABLE_MARKDOWN_CONVERSION:
        print("[!] ВНИМАНИЕ: ENABLE_MARKDOWN_CONVERSION = False в config.py")
        print("    Конвертация отключена в настройках!")
        print()
        response = input("Продолжить все равно? (да/нет): ").strip().lower()
        if response not in ['да', 'yes', 'y', 'д']:
            print("Отменено.")
            return
        print()

    # Пути
    source_dir = config.DOWNLOAD_DIR
    output_dir = config.MARKDOWN_OUTPUT_DIR

    print(f"Исходная папка:  {source_dir}")
    print(f"Выходная папка:  {output_dir}")
    print()

    # Проверяем, существует ли исходная папка
    if not Path(source_dir).exists():
        logger.error(f"Папка {source_dir} не существует!")
        logger.info("Сначала запустите синхронизацию: python run.py")
        return

    # Выводим настройки конвертации
    print("Включенные конвертеры:")
    converters_status = [
        ("Word (.docx, .doc)", config.CONVERT_WORD_FILES),
        ("CSV (.csv)", config.CONVERT_CSV_FILES),
        ("Excel (.xlsx, .xls, .xlsm, .xlsb)", config.CONVERT_EXCEL_FILES),
        ("PDF (.pdf)", config.CONVERT_PDF_FILES),
        ("Text/Code (.txt, .md, .py, .json, .xml, .avsc, .j2)", config.CONVERT_TEXT_FILES),
        ("PowerPoint (.pptx, .ppt)", config.CONVERT_POWERPOINT_FILES),
        ("HTML (.html, .htm)", config.CONVERT_HTML_FILES),
        ("Parquet (.parquet)", config.CONVERT_PARQUET_FILES),
        ("RTF (.rtf)", config.CONVERT_RTF_FILES),
        ("Archives (.zip, .7z, .rar, .tar, .gz)", config.CONVERT_ARCHIVE_FILES),
    ]

    for name, enabled in converters_status:
        status = "[OK]" if enabled else "[--]"
        print(f"  {status} {name}")
    print()

    # Создаем конвертер
    converter = MarkdownConverter(source_dir, output_dir)

    # Запускаем конвертацию
    converter.convert_all()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем.")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
        sys.exit(1)
