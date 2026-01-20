"""
Конвертер CSV файлов в Markdown
"""
from pathlib import Path
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
            encodings = [detected_encoding, 'utf-8', 'cp1251', 'latin-1', 'utf-16']
            # Удаляем дубликаты, сохраняя порядок
            encodings = list(dict.fromkeys(encodings))

            df = None

            for encoding in encodings:
                try:
                    df = pd.read_csv(input_path, encoding=encoding)
                    logger.debug(f"CSV прочитан с кодировкой {encoding}")
                    break
                except (UnicodeDecodeError, pd.errors.ParserError):
                    continue

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
