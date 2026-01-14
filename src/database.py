"""
Модуль для работы с базой данных метаданных синхронизации
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger


class MetadataDatabase:
    """
    База данных для хранения метаданных файлов

    Структура таблицы files:
    - id: INTEGER PRIMARY KEY
    - path: TEXT UNIQUE - путь к файлу относительно корня синхронизации
    - size: INTEGER - размер файла в байтах
    - modified: TEXT - дата модификации файла на удаленном диске
    - md5: TEXT - MD5 хеш файла
    - last_sync: TEXT - дата последней синхронизации
    - is_empty: INTEGER - флаг пустого файла (0/1)
    - created_at: TEXT - дата создания записи
    - updated_at: TEXT - дата обновления записи
    """

    def __init__(self, db_path: Path):
        """
        Инициализация подключения к БД

        :param db_path: Путь к файлу базы данных
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_database()

    def _init_database(self):
        """Создает таблицы если их нет"""
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                size INTEGER NOT NULL,
                modified TEXT NOT NULL,
                md5 TEXT,
                last_sync TEXT NOT NULL,
                is_empty INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Создаем индексы для быстрого поиска
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_files_path ON files(path)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_files_modified ON files(modified)
        """)

        self.conn.commit()
        logger.debug(f"База данных инициализирована: {self.db_path}")

    def get_file_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Получает метаданные файла по пути

        :param file_path: Путь к файлу
        :return: Словарь с метаданными или None
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM files WHERE path = ?",
            (file_path,)
        )
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def save_file_metadata(self, file_path: str, size: int, modified: str,
                          md5: str = "", is_empty: bool = False):
        """
        Сохраняет или обновляет метаданные файла

        :param file_path: Путь к файлу
        :param size: Размер файла
        :param modified: Дата модификации
        :param md5: MD5 хеш
        :param is_empty: Флаг пустого файла
        """
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        # Проверяем существует ли запись
        existing = self.get_file_metadata(file_path)

        if existing:
            # Обновляем существующую запись
            cursor.execute("""
                UPDATE files
                SET size = ?, modified = ?, md5 = ?, last_sync = ?,
                    is_empty = ?, updated_at = ?
                WHERE path = ?
            """, (size, modified, md5, now, int(is_empty), now, file_path))
        else:
            # Создаем новую запись
            cursor.execute("""
                INSERT INTO files
                (path, size, modified, md5, last_sync, is_empty, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (file_path, size, modified, md5, now, int(is_empty), now, now))

        self.conn.commit()

    def file_needs_update(self, file_path: str, size: int, modified: str, md5: str = "") -> bool:
        """
        Проверяет, нужно ли обновлять файл

        :param file_path: Путь к файлу
        :param size: Размер файла
        :param modified: Дата модификации
        :param md5: MD5 хеш
        :return: True если файл нужно обновить
        """
        metadata = self.get_file_metadata(file_path)

        if not metadata:
            # Файла нет в БД - нужно скачать
            return True

        # Проверяем изменения
        if metadata['size'] != size:
            return True

        if metadata['modified'] != modified:
            return True

        if md5 and metadata['md5'] and metadata['md5'] != md5:
            return True

        return False

    def get_all_files(self) -> list:
        """
        Возвращает список всех файлов в БД

        :return: Список словарей с метаданными
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM files ORDER BY path")
        return [dict(row) for row in cursor.fetchall()]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Возвращает статистику по БД

        :return: Словарь со статистикой
        """
        cursor = self.conn.cursor()

        # Общее количество файлов
        cursor.execute("SELECT COUNT(*) as count FROM files")
        total_files = cursor.fetchone()['count']

        # Количество пустых файлов
        cursor.execute("SELECT COUNT(*) as count FROM files WHERE is_empty = 1")
        empty_files = cursor.fetchone()['count']

        # Общий размер
        cursor.execute("SELECT SUM(size) as total_size FROM files WHERE is_empty = 0")
        result = cursor.fetchone()
        total_size = result['total_size'] if result['total_size'] else 0

        return {
            'total_files': total_files,
            'empty_files': empty_files,
            'real_files': total_files - empty_files,
            'total_size': total_size
        }

    def delete_file_metadata(self, file_path: str):
        """
        Удаляет метаданные файла

        :param file_path: Путь к файлу
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM files WHERE path = ?", (file_path,))
        self.conn.commit()

    def clear_all(self):
        """Очищает всю БД"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM files")
        self.conn.commit()
        logger.warning("База данных очищена")

    def close(self):
        """Закрывает соединение с БД"""
        if self.conn:
            self.conn.close()
            logger.debug("Соединение с БД закрыто")

    def __enter__(self):
        """Поддержка context manager"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Закрытие при выходе из context manager"""
        self.close()
