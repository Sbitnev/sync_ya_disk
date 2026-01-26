"""
Конвертер CSV файлов в Markdown
"""
from pathlib import Path
from io import StringIO
import pandas as pd
import chardet
from loguru import logger

from .base import FileConverter


class CSVConverter(FileConverter):
    """
    Конвертер CSV файлов в Markdown таблицы

    Использует pandas для чтения CSV и форматирования в markdown
    """

    def __init__(self, max_rows: int = None, max_columns: int = None):
        """
        :param max_rows: Максимальное количество строк для отображения (None = без ограничений)
        :param max_columns: Максимальное количество столбцов для отображения (None = без ограничений)
        """
        super().__init__(['.csv'])
        self.max_rows = max_rows
        self.max_columns = max_columns

    def _detect_encoding(self, input_path: Path) -> str:
        """
        Определяет кодировку файла с помощью chardet

        :param input_path: Путь к файлу
        :return: Определенная кодировка или 'utf-8' по умолчанию
        """
        try:
            # Читаем первые 100 КБ файла для определения кодировки
            with open(input_path, 'rb') as f:
                raw_data = f.read(100000)

            result = chardet.detect(raw_data)
            encoding = result['encoding']
            confidence = result['confidence']

            if encoding and confidence > 0.7:
                logger.debug(f"Определена кодировка {encoding} (уверенность: {confidence:.2f})")
                return encoding
            else:
                logger.debug(f"Низкая уверенность ({confidence:.2f}), используем utf-8")
                return 'utf-8'
        except Exception as e:
            logger.debug(f"Ошибка определения кодировки: {e}, используем utf-8")
            return 'utf-8'

    def _read_csv_manual_utf16(self, input_path: Path) -> pd.DataFrame:
        """
        Читает CSV файл с ручным определением UTF-16 кодировки (с и без BOM)

        Pandas не может правильно прочитать UTF-16 файлы без BOM,
        поэтому мы читаем байты вручную и декодируем их.

        :param input_path: Путь к файлу
        :return: DataFrame или None если не удалось
        """
        try:
            # Читаем файл как байты
            with open(input_path, 'rb') as f:
                raw_data = f.read()

            # Проверяем первые байты для определения кодировки
            if len(raw_data) < 2:
                return None

            # Пробуем разные варианты UTF-16
            encodings_to_try = []

            # Проверяем BOM (Byte Order Mark)
            if raw_data[:2] == b'\xff\xfe':
                # UTF-16 LE с BOM
                encodings_to_try.append(('utf-16-le', True))
                logger.debug("Обнаружен BOM для UTF-16 LE")
            elif raw_data[:2] == b'\xfe\xff':
                # UTF-16 BE с BOM
                encodings_to_try.append(('utf-16-be', True))
                logger.debug("Обнаружен BOM для UTF-16 BE")
            else:
                # Нет BOM - пробуем оба варианта
                # Для Windows чаще всего UTF-16 LE
                encodings_to_try.append(('utf-16-le', False))
                encodings_to_try.append(('utf-16-be', False))
                logger.debug("BOM не обнаружен, пробуем UTF-16 без BOM")

            # Пробуем каждую кодировку
            for encoding, has_bom in encodings_to_try:
                try:
                    # Декодируем байты в строку
                    if has_bom:
                        # Пропускаем BOM (первые 2 байта)
                        text = raw_data[2:].decode(encoding)
                    else:
                        text = raw_data.decode(encoding)

                    # Создаем StringIO для pandas
                    text_io = StringIO(text)

                    # Читаем CSV из строки
                    df = pd.read_csv(text_io)

                    logger.info(f"CSV успешно прочитан с кодировкой {encoding} (BOM: {has_bom})")
                    return df

                except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as e:
                    logger.debug(f"Не удалось прочитать с {encoding} (BOM: {has_bom}): {e}")
                    continue

            # Не удалось ни с одним вариантом
            return None

        except Exception as e:
            logger.debug(f"Ошибка при ручном чтении UTF-16: {e}")
            return None

    def convert(self, input_path: Path, output_path: Path) -> bool:
        """
        Конвертирует CSV в Markdown таблицу

        :param input_path: Путь к .csv файлу
        :param output_path: Путь к .md файлу
        :return: True если успешно
        """
        try:
            # Определяем кодировку с помощью chardet
            detected_encoding = self._detect_encoding(input_path)

            # Пробуем разные кодировки, начиная с определенной
            # Добавлены UTF-16 варианты без BOM (Little Endian и Big Endian)
            # ВАЖНО: не используем 'utf-16', потому что pandas требует BOM для него
            encodings = [
                detected_encoding,
                'utf-8',
                'utf-16-le',       # UTF-16 Little Endian без BOM (для Windows)
                'utf-16-be',       # UTF-16 Big Endian без BOM
                'cp1251',          # Windows Cyrillic
                'latin-1',         # ISO-8859-1
                'cp1252',          # Windows Latin
                'iso-8859-1'       # Latin-1
            ]
            # Удаляем дубликаты, сохраняя порядок
            encodings = list(dict.fromkeys(encodings))

            df = None
            used_encoding = None
            used_fallback = False

            # Первый проход: пробуем прочитать без errors='ignore'
            for encoding in encodings:
                try:
                    df = pd.read_csv(input_path, encoding=encoding)
                    used_encoding = encoding
                    logger.debug(f"CSV прочитан с кодировкой {encoding}")
                    break
                except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError, Exception) as e:
                    # Перехватываем также "UTF-16 stream does not start with BOM"
                    if "UTF-16" in str(e) and "BOM" in str(e):
                        logger.debug(f"Пропускаем {encoding} из-за проблемы с BOM")
                    continue

            # Второй проход: если не получилось, пробуем с errors='ignore'
            if df is None:
                logger.debug(f"Пробуем прочитать CSV с errors='ignore': {input_path.name}")
                for encoding in encodings:
                    try:
                        # Используем on_bad_lines='skip' для pandas >= 1.3
                        df = pd.read_csv(input_path, encoding=encoding, encoding_errors='ignore', on_bad_lines='skip')
                        used_encoding = encoding
                        used_fallback = True
                        logger.warning(f"CSV прочитан с кодировкой {encoding} и игнорированием ошибок")
                        break
                    except Exception as e:
                        # Перехватываем также "UTF-16 stream does not start with BOM"
                        if "UTF-16" in str(e) and "BOM" in str(e):
                            logger.debug(f"Пропускаем {encoding} из-за проблемы с BOM")
                        continue

            # Третий проход: пробуем ручное чтение UTF-16 без BOM
            if df is None:
                logger.debug(f"Пробуем ручное чтение UTF-16 без BOM: {input_path.name}")
                df = self._read_csv_manual_utf16(input_path)
                if df is not None:
                    used_encoding = 'utf-16 (manual)'
                    logger.info(f"CSV прочитан через ручное определение UTF-16")

            if df is None:
                logger.error(f"Не удалось прочитать CSV с доступными кодировками: {input_path.name}")
                return False

            # Получаем информацию о размере
            total_rows, total_cols = df.shape
            is_truncated_rows = self.max_rows is not None and total_rows > self.max_rows
            is_truncated_cols = self.max_columns is not None and total_cols > self.max_columns

            # Ограничиваем размер если необходимо
            df_display = df
            if is_truncated_rows:
                df_display = df_display.head(self.max_rows)

            if is_truncated_cols:
                df_display = df_display.iloc[:, :self.max_columns]

            # Создаем метаданные
            metadata = self._create_metadata(input_path, total_rows, total_cols, is_truncated_rows, is_truncated_cols)

            # Конвертируем в markdown
            markdown_table = df_display.to_markdown(index=False)

            # Если не получилось с to_markdown (может не быть установлено tabulate)
            if markdown_table is None:
                logger.warning("tabulate не установлен, используем fallback")
                markdown_table = self._dataframe_to_markdown_fallback(df_display)

            # Добавляем примечание если данные обрезаны
            truncation_note = ""
            if is_truncated_rows or is_truncated_cols:
                truncation_note = "\n\n---\n\n"
                if is_truncated_rows:
                    truncation_note += f"⚠️ Отображены первые {self.max_rows} из {total_rows} строк.\n\n"
                if is_truncated_cols:
                    truncation_note += f"⚠️ Отображены первые {self.max_columns} из {total_cols} столбцов.\n\n"

            # Формируем полный контент
            full_content = metadata + markdown_table + truncation_note

            # Сохраняем результат
            with open(output_path, 'w', encoding='utf-8') as md_file:
                md_file.write(full_content)

            return True

        except Exception as e:
            logger.error(f"Ошибка конвертации CSV {input_path.name}: {e}")
            return False

    def _create_metadata(self, input_path: Path, rows: int, cols: int,
                        truncated_rows: bool, truncated_cols: bool) -> str:
        """
        Создает метаданные для markdown файла

        :param input_path: Путь к исходному файлу
        :param rows: Количество строк
        :param cols: Количество столбцов
        :param truncated_rows: Обрезаны ли строки
        :param truncated_cols: Обрезаны ли столбцы
        :return: Строка с метаданными
        """
        metadata = f"""---
source_file: {input_path.name}
original_format: .csv
rows: {rows}
columns: {cols}
truncated: {truncated_rows or truncated_cols}
converted_by: CSVConverter
---

# {input_path.stem}

**Размер данных:** {rows} строк × {cols} столбцов

"""
        return metadata

    def _dataframe_to_markdown_fallback(self, df: pd.DataFrame) -> str:
        """
        Fallback метод для конвертации DataFrame в markdown если tabulate не установлен

        :param df: DataFrame для конвертации
        :return: Markdown строка
        """
        # Создаем заголовок
        header = "| " + " | ".join(str(col) for col in df.columns) + " |"
        separator = "|" + "|".join(["---" for _ in df.columns]) + "|"

        # Создаем строки
        rows = []
        for _, row in df.iterrows():
            row_str = "| " + " | ".join(str(val) for val in row) + " |"
            rows.append(row_str)

        # Собираем таблицу
        table = "\n".join([header, separator] + rows)
        return table
