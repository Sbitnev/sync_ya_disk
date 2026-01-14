"""
Конвертер Excel файлов (.xlsx, .xls, .xlsm, .xlsb) в Markdown
"""
from pathlib import Path
import pandas as pd
from loguru import logger

from .base import FileConverter


class ExcelConverter(FileConverter):
    """
    Конвертер Excel файлов в Markdown

    Использует pandas для чтения Excel и форматирования в markdown
    Каждый лист Excel -> отдельная секция в Markdown
    """

    def __init__(self, max_rows: int = 1000, max_columns: int = 50, sheets_limit: int = 10):
        """
        :param max_rows: Максимальное количество строк на лист
        :param max_columns: Максимальное количество столбцов
        :param sheets_limit: Максимальное количество листов для конвертации
        """
        super().__init__(['.xlsx', '.xls', '.xlsm', '.xlsb'])
        self.max_rows = max_rows
        self.max_columns = max_columns
        self.sheets_limit = sheets_limit

    def convert(self, input_path: Path, output_path: Path) -> bool:
        """
        Конвертирует Excel файл в Markdown

        :param input_path: Путь к Excel файлу
        :param output_path: Путь к .md файлу
        :return: True если успешно
        """
        try:
            # Читаем все листы из Excel
            # Для .xls используем xlrd engine
            engine = 'openpyxl'
            if input_path.suffix.lower() == '.xls':
                engine = 'xlrd'
            elif input_path.suffix.lower() == '.xlsb':
                engine = 'pyxlsb'

            # Получаем список всех листов
            try:
                excel_file = pd.ExcelFile(input_path, engine=engine)
                sheet_names = excel_file.sheet_names
            except Exception as e:
                logger.error(f"Не удалось открыть Excel файл {input_path.name}: {e}")
                return False

            # Ограничиваем количество листов
            total_sheets = len(sheet_names)
            sheets_to_process = sheet_names[:self.sheets_limit]
            is_truncated_sheets = total_sheets > self.sheets_limit

            # Создаем метаданные
            metadata = self._create_metadata(input_path, total_sheets, is_truncated_sheets)

            # Конвертируем каждый лист
            all_content = [metadata]

            for i, sheet_name in enumerate(sheets_to_process, 1):
                try:
                    # Читаем лист
                    df = pd.read_excel(
                        input_path,
                        sheet_name=sheet_name,
                        engine=engine
                    )

                    # Пропускаем пустые листы
                    if df.empty:
                        logger.debug(f"Пропущен пустой лист: {sheet_name}")
                        continue

                    # Получаем информацию о размере
                    total_rows, total_cols = df.shape
                    is_truncated_rows = total_rows > self.max_rows
                    is_truncated_cols = total_cols > self.max_columns

                    # Ограничиваем размер
                    if is_truncated_rows:
                        df_display = df.head(self.max_rows)
                    else:
                        df_display = df

                    if is_truncated_cols:
                        df_display = df_display.iloc[:, :self.max_columns]

                    # Добавляем заголовок листа
                    sheet_header = f"\n## Лист {i}: {sheet_name}\n\n"
                    sheet_header += f"**Размер:** {total_rows} строк × {total_cols} столбцов\n\n"

                    # Конвертируем в markdown таблицу
                    markdown_table = df_display.to_markdown(index=False)

                    # Fallback если tabulate не установлен
                    if markdown_table is None:
                        logger.warning("tabulate не установлен, используем fallback")
                        markdown_table = self._dataframe_to_markdown_fallback(df_display)

                    # Добавляем примечание если данные обрезаны
                    truncation_note = ""
                    if is_truncated_rows or is_truncated_cols:
                        truncation_note = "\n\n"
                        if is_truncated_rows:
                            truncation_note += f"⚠️ Отображены первые {self.max_rows} из {total_rows} строк.\n\n"
                        if is_truncated_cols:
                            truncation_note += f"⚠️ Отображены первые {self.max_columns} из {total_cols} столбцов.\n\n"

                    # Собираем контент листа
                    sheet_content = sheet_header + markdown_table + truncation_note
                    all_content.append(sheet_content)

                except Exception as e:
                    logger.error(f"Ошибка при обработке листа '{sheet_name}': {e}")
                    # Продолжаем обработку других листов
                    all_content.append(f"\n## Лист {i}: {sheet_name}\n\n❌ Ошибка при конвертации листа: {str(e)}\n\n")

            # Добавляем примечание о необработанных листах
            if is_truncated_sheets:
                all_content.append(
                    f"\n---\n\n⚠️ Обработаны первые {self.sheets_limit} из {total_sheets} листов.\n"
                )

            # Сохраняем результат
            full_content = "\n".join(all_content)
            with open(output_path, 'w', encoding='utf-8') as md_file:
                md_file.write(full_content)

            return True

        except Exception as e:
            logger.error(f"Ошибка конвертации Excel {input_path.name}: {e}")
            return False

    def _create_metadata(self, input_path: Path, total_sheets: int, truncated: bool) -> str:
        """
        Создает метаданные для markdown файла

        :param input_path: Путь к исходному файлу
        :param total_sheets: Количество листов
        :param truncated: Обрезаны ли листы
        :return: Строка с метаданными
        """
        metadata = f"""---
source_file: {input_path.name}
original_format: {input_path.suffix}
total_sheets: {total_sheets}
sheets_truncated: {truncated}
converted_by: ExcelConverter
---

# {input_path.stem}

**Тип:** Excel документ
**Листов:** {total_sheets}

"""
        return metadata

    def _dataframe_to_markdown_fallback(self, df: pd.DataFrame) -> str:
        """
        Fallback метод для конвертации DataFrame в markdown

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
