"""
Модуль для конвертации различных форматов файлов в Markdown
"""
from .base import FileConverter
from .word_converter import WordConverter
from .csv_converter import CSVConverter
from .excel_converter import ExcelConverter
from .pdf_converter import PDFConverter
from .text_converter import TextConverter
from .powerpoint_converter import PowerPointConverter
from .html_converter import HTMLConverter
from .parquet_converter import ParquetConverter
from .rtf_converter import RTFConverter
from .archive_converter import ArchiveConverter
from .video_converter import VideoConverter

__all__ = [
    'FileConverter',
    'WordConverter',
    'CSVConverter',
    'ExcelConverter',
    'PDFConverter',
    'TextConverter',
    'PowerPointConverter',
    'HTMLConverter',
    'ParquetConverter',
    'RTFConverter',
    'ArchiveConverter',
    'VideoConverter'
]
