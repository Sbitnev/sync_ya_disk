"""
Модуль для конвертации различных форматов файлов в Markdown
"""
from .base import FileConverter
from .word_converter import WordConverter
from .csv_converter import CSVConverter
from .excel_converter import ExcelConverter
from .pdf_converter import PDFConverter

__all__ = ['FileConverter', 'WordConverter', 'CSVConverter', 'ExcelConverter', 'PDFConverter']
