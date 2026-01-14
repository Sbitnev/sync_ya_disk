"""
Базовый класс для конвертации файлов в Markdown
"""
from abc import ABC, abstractmethod
from pathlib import Path
from loguru import logger


class FileConverter(ABC):
    """
    Абстрактный базовый класс для конвертеров файлов
    """

    def __init__(self, supported_extensions: list):
        """
        :param supported_extensions: Список поддерживаемых расширений (например, ['.docx', '.doc'])
        """
        self.supported_extensions = [ext.lower() for ext in supported_extensions]

    def can_convert(self, file_path: Path) -> bool:
        """
        Проверяет, может ли конвертер обработать данный файл

        :param file_path: Путь к файлу
        :return: True если файл может быть конвертирован
        """
        return file_path.suffix.lower() in self.supported_extensions

    @abstractmethod
    def convert(self, input_path: Path, output_path: Path) -> bool:
        """
        Конвертирует файл в Markdown

        :param input_path: Путь к исходному файлу
        :param output_path: Путь к результирующему .md файлу
        :return: True если конвертация успешна, False иначе
        """
        pass

    def convert_safe(self, input_path: Path, output_path: Path) -> bool:
        """
        Безопасная конвертация с обработкой ошибок

        :param input_path: Путь к исходному файлу
        :param output_path: Путь к результирующему .md файлу
        :return: True если конвертация успешна, False иначе
        """
        try:
            if not input_path.exists():
                logger.error(f"Файл не найден: {input_path}")
                return False

            if not self.can_convert(input_path):
                logger.warning(f"Файл {input_path.suffix} не поддерживается конвертером {self.__class__.__name__}")
                return False

            # Создаем директорию для выходного файла
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Выполняем конвертацию
            success = self.convert(input_path, output_path)

            if success:
                logger.debug(f"Конвертация успешна: {input_path.name} → {output_path.name}")
            else:
                logger.warning(f"Конвертация не удалась: {input_path.name}")

            return success

        except Exception as e:
            logger.error(f"Ошибка при конвертации {input_path.name}: {e}")
            return False

    def get_markdown_path(self, original_path: Path, markdown_root: Path) -> Path:
        """
        Генерирует путь для markdown файла на основе оригинального пути

        :param original_path: Путь к оригинальному файлу
        :param markdown_root: Корневая директория для markdown файлов
        :return: Путь к .md файлу
        """
        # Заменяем расширение на .md
        relative_path = original_path.relative_to(original_path.parent)
        md_filename = relative_path.stem + '.md'
        return markdown_root / original_path.parent.name / md_filename
