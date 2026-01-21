"""
Модуль для работы с базой данных метаданных синхронизации
"""
import sqlite3
import subprocess
import threading
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
    - markdown_path: TEXT - путь к сконвертированному MD файлу
    - created_at: TEXT - дата создания записи
    - updated_at: TEXT - дата обновления записи
    """

    def __init__(self, db_path: Path, auto_migrate: bool = True):
        """
        Инициализация подключения к БД

        :param db_path: Путь к файлу базы данных
        :param auto_migrate: Автоматически применять миграции Alembic
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Создаем lock для thread-safety
        self._lock = threading.Lock()

        # Проверяем существует ли БД
        db_exists = self.db_path.exists()

        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Применяем миграции если включено
        if auto_migrate:
            self._run_migrations(db_exists)

        self._init_database()

    def _run_migrations(self, db_exists: bool):
        """
        Применяет миграции Alembic

        :param db_exists: Существовала ли БД до инициализации
        """
        try:
            project_root = Path(__file__).parent.parent

            if not db_exists:
                # Новая БД - просто применяем все миграции
                logger.info("Инициализация новой БД через Alembic...")
                result = subprocess.run(
                    ['alembic', 'upgrade', 'head'],
                    cwd=str(project_root),
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    logger.error(f"Ошибка применения миграций: {result.stderr}")
                else:
                    logger.success("Миграции успешно применены")
            else:
                # Существующая БД - проверяем версию и применяем недостающие миграции
                # Сначала проверим есть ли таблица alembic_version
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
                )
                has_alembic_table = cursor.fetchone() is not None

                if not has_alembic_table:
                    # Первый запуск с Alembic на существующей БД
                    # Помечаем текущую версию без применения миграций
                    logger.info("Инициализация Alembic для существующей БД...")
                    result = subprocess.run(
                        ['alembic', 'stamp', 'head'],
                        cwd=str(project_root),
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        logger.error(f"Ошибка инициализации Alembic: {result.stderr}")
                    else:
                        logger.success("Alembic инициализирован для существующей БД")
                else:
                    # Применяем новые миграции если есть
                    result = subprocess.run(
                        ['alembic', 'upgrade', 'head'],
                        cwd=str(project_root),
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        logger.error(f"Ошибка применения миграций: {result.stderr}")
                    elif "Running upgrade" in result.stdout:
                        logger.success("Применены новые миграции")

        except Exception as e:
            logger.error(f"Ошибка работы с Alembic: {e}")
            logger.warning("Продолжаем работу без миграций")

    def _init_database(self):
        """
        Проверяет целостность БД

        Примечание: Создание таблиц и миграции управляются через Alembic.
        Этот метод используется только для проверок и логирования.
        """
        cursor = self.conn.cursor()

        # Проверяем существование таблицы files
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='files'"
        )
        table_exists = cursor.fetchone() is not None

        if not table_exists:
            logger.warning(
                "Таблица 'files' не найдена. "
                "Возможно, миграции Alembic не были применены."
            )
        else:
            logger.debug(f"База данных готова: {self.db_path}")

    def get_file_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Получает метаданные файла по пути

        :param file_path: Путь к файлу
        :return: Словарь с метаданными или None
        """
        with self._lock:
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
                          md5: str = "", is_empty: bool = False, markdown_path: str = ""):
        """
        Сохраняет или обновляет метаданные файла

        :param file_path: Путь к файлу
        :param size: Размер файла
        :param modified: Дата модификации
        :param md5: MD5 хеш
        :param is_empty: Флаг пустого файла
        :param markdown_path: Путь к MD файлу
        """
        with self._lock:
            cursor = self.conn.cursor()
            now = datetime.now().isoformat()

            # Проверяем существует ли запись (без вложенного lock - уже внутри)
            cursor.execute("SELECT 1 FROM files WHERE path = ?", (file_path,))
            existing = cursor.fetchone() is not None

            if existing:
                # Обновляем существующую запись
                cursor.execute("""
                    UPDATE files
                    SET size = ?, modified = ?, md5 = ?, last_sync = ?,
                        is_empty = ?, markdown_path = ?, updated_at = ?
                    WHERE path = ?
                """, (size, modified, md5, now, int(is_empty), markdown_path, now, file_path))
            else:
                # Создаем новую запись
                cursor.execute("""
                    INSERT INTO files
                    (path, size, modified, md5, last_sync, is_empty, markdown_path, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (file_path, size, modified, md5, now, int(is_empty), markdown_path, now, now))

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
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM files ORDER BY path")
            return [dict(row) for row in cursor.fetchall()]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Возвращает статистику по БД

        :return: Словарь со статистикой
        """
        with self._lock:
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

    def update_markdown_path(self, file_path: str, markdown_path: str):
        """
        Обновляет путь к MD файлу для файла

        :param file_path: Путь к исходному файлу
        :param markdown_path: Путь к MD файлу
        """
        with self._lock:
            cursor = self.conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                UPDATE files
                SET markdown_path = ?, updated_at = ?
                WHERE path = ?
            """, (markdown_path, now, file_path))
            self.conn.commit()

    def get_files_without_markdown(self) -> list:
        """
        Возвращает список файлов без конвертации в Markdown

        :return: Список словарей с метаданными файлов без MD
        """
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM files
                WHERE (markdown_path IS NULL OR markdown_path = '')
                AND is_empty = 0
                ORDER BY path
            """)
            return [dict(row) for row in cursor.fetchall()]

    def delete_file_metadata(self, file_path: str):
        """
        Удаляет метаданные файла

        :param file_path: Путь к файлу
        """
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM files WHERE path = ?", (file_path,))
            self.conn.commit()

    def update_transcription_status(self, file_path: str, status: str, operation_id: str = None,
                                   video_metadata: str = None):
        """
        Обновляет статус транскрибации видео

        :param file_path: Путь к файлу
        :param status: Статус (pending/in_progress/completed/failed)
        :param operation_id: ID операции в Yandex (опционально)
        :param video_metadata: JSON метаданные видео (опционально)
        """
        with self._lock:
            cursor = self.conn.cursor()
            now = datetime.now().isoformat()

            update_fields = ["transcription_status = ?", "updated_at = ?"]
            params = [status, now]

            if operation_id is not None:
                update_fields.append("transcription_operation_id = ?")
                params.append(operation_id)

            if video_metadata is not None:
                update_fields.append("video_metadata = ?")
                params.append(video_metadata)

            if status == 'in_progress':
                update_fields.append("transcription_started_at = ?")
                params.append(now)

            params.append(file_path)

            query = f"UPDATE files SET {', '.join(update_fields)} WHERE path = ?"
            cursor.execute(query, params)
            self.conn.commit()

    def get_pending_transcriptions(self) -> list:
        """
        Возвращает список файлов с незавершенной транскрибацией

        :return: Список словарей с метаданными файлов
        """
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM files
                WHERE transcription_status IN ('pending', 'in_progress')
                ORDER BY transcription_started_at
            """)
            return [dict(row) for row in cursor.fetchall()]

    def clear_all(self):
        """Очищает всю БД"""
        with self._lock:
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
