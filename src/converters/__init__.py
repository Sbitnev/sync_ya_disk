"""
Модуль для конвертации различных форматов файлов в Markdown
"""
from .base import FileConverter
from .word_converter import WordConverter
from .csv_converter import CSVConverter

__all__ = ['FileConverter', 'WordConverter', 'CSVConverter']
