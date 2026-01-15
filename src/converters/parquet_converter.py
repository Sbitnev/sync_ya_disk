"""
Конвертер Parquet файлов в Markdown
"""
from pathlib import Path
from .base import FileConverter


class ParquetConverter(FileConverter):
    """
    Конвертер для Apache Parquet файлов
    Поддерживает: .parquet
    """

    def __init__(self, max_rows: int = None, max_columns: int = None):
        super().__init__(['.parquet'])
        self.max_rows = max_rows
        self.max_columns = max_columns
        self.has_pandas = self._check_pandas()
        self.has_pyarrow = self._check_pyarrow()

    def _check_pandas(self) -> bool:
        """Проверяет доступность pandas"""
        try:
            import pandas as pd
            return True
        except ImportError:
            return False

    def _check_pyarrow(self) -> bool:
        """Проверяет доступность pyarrow"""
        try:
            import pyarrow
            return True
        except ImportError:
            return False

    def convert(self, input_path: Path, output_path: Path) -> bool:
        """
        Конвертирует Parquet в Markdown

        :param input_path: Путь к исходному файлу
        :param output_path: Путь для сохранения markdown файла
        :return: True если конвертация успешна
        """
        if not self.has_pandas:
            print(f"pandas не установлен. Установите: pip install pandas")
            return False

        if not self.has_pyarrow:
            print(f"pyarrow не установлен. Установите: pip install pyarrow")
            return False

        try:
            return self._convert_with_pandas(input_path, output_path)
        except Exception as e:
            print(f"Ошибка при конвертации {input_path}: {e}")
            return False

    def _convert_with_pandas(self, input_path: Path, output_path: Path) -> bool:
        """Конвертирует с помощью pandas"""
        import pandas as pd

        try:
            # Читаем parquet файл
            df = pd.read_parquet(input_path)

            # Создаем директорию для выходного файла
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                # Информация о данных
                total_rows = len(df)
                total_columns = len(df.columns)
                rows_truncated = self.max_rows is not None and total_rows > self.max_rows
                columns_truncated = self.max_columns is not None and total_columns > self.max_columns

                # YAML заголовок
                f.write("---\n")
                f.write(f"source_file: {input_path.name}\n")
                f.write(f"original_format: .parquet\n")
                f.write(f"total_rows: {total_rows}\n")
                f.write(f"total_columns: {total_columns}\n")
                f.write(f"rows_truncated: {rows_truncated}\n")
                f.write(f"columns_truncated: {columns_truncated}\n")
                f.write(f"converted_by: ParquetConverter\n")
                f.write("---\n\n")

                # Заголовок
                f.write(f"# {input_path.stem}\n\n")
                f.write(f"**Тип:** Apache Parquet данные\n")
                f.write(f"**Строк:** {total_rows:,}\n")
                f.write(f"**Столбцов:** {total_columns}\n\n")

                # Предупреждения об обрезке
                if rows_truncated or columns_truncated:
                    f.write("⚠️ **Внимание:**\n")
                    if rows_truncated:
                        f.write(f"- Отображены только первые {self.max_rows:,} строк из {total_rows:,}\n")
                    if columns_truncated:
                        f.write(f"- Отображены только первые {self.max_columns} столбцов из {total_columns}\n")
                    f.write("\n")

                # Информация о столбцах
                f.write("## Структура данных\n\n")
                f.write("| Столбец | Тип данных | Не-null |\n")
                f.write("|---------|------------|--------|\n")
                cols_to_show = df.columns if self.max_columns is None else df.columns[:self.max_columns]
                for col in cols_to_show:
                    dtype = str(df[col].dtype)
                    non_null = df[col].count()
                    f.write(f"| {col} | {dtype} | {non_null:,} |\n")
                f.write("\n")

                # Ограничиваем данные
                row_slice = slice(None) if self.max_rows is None else slice(self.max_rows)
                col_slice = slice(None) if self.max_columns is None else slice(self.max_columns)
                df_limited = df.iloc[row_slice, col_slice]

                # Конвертируем в markdown таблицу
                f.write("## Данные\n\n")

                # Используем табулятор если доступен
                try:
                    from tabulate import tabulate
                    markdown_table = tabulate(df_limited, headers='keys', tablefmt='pipe', showindex=False)
                    f.write(markdown_table)
                    f.write("\n")
                except ImportError:
                    # Fallback на простой markdown
                    f.write(df_limited.to_markdown(index=False))
                    f.write("\n")

            return True

        except Exception as e:
            print(f"Ошибка pandas: {e}")
            return False
