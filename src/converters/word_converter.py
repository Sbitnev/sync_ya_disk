"""
Конвертер Word документов (.docx, .doc) в Markdown
"""
import subprocess
from pathlib import Path
from loguru import logger

from .base import FileConverter
from .. import config


class WordConverter(FileConverter):
    """
    Конвертер Word документов в Markdown

    Использует mammoth для .docx или pandoc для .doc/.docx
    """

    def __init__(self):
        super().__init__(['.docx', '.doc'])
        self.has_mammoth = self._check_mammoth()
        self.has_pandoc = self._check_pandoc()

        if not self.has_mammoth and not self.has_pandoc:
            logger.warning("Ни mammoth, ни pandoc не найдены. Конвертация Word файлов недоступна.")

    def _check_mammoth(self) -> bool:
        """Проверяет наличие библиотеки mammoth"""
        try:
            import mammoth
            return True
        except ImportError:
            return False

    def _check_pandoc(self) -> bool:
        """Проверяет наличие pandoc в системе"""
        try:
            result = subprocess.run(
                ['pandoc', '--version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def convert(self, input_path: Path, output_path: Path) -> bool:
        """
        Конвертирует Word документ в Markdown

        :param input_path: Путь к .docx/.doc файлу
        :param output_path: Путь к .md файлу
        :return: True если успешно
        """
        # Для .docx пробуем mammoth, затем pandoc
        if input_path.suffix.lower() == '.docx':
            if self.has_mammoth:
                return self._convert_with_mammoth(input_path, output_path)
            elif self.has_pandoc:
                return self._convert_with_pandoc(input_path, output_path)

        # Для .doc используем только pandoc
        elif input_path.suffix.lower() == '.doc':
            if self.has_pandoc:
                return self._convert_with_pandoc(input_path, output_path)
            else:
                logger.error(f"Для конвертации .doc файлов требуется pandoc")
                return False

        logger.error(f"Невозможно сконвертировать {input_path}: нет доступных инструментов")
        return False

    def _convert_with_mammoth(self, input_path: Path, output_path: Path) -> bool:
        """
        Конвертация с использованием mammoth

        :param input_path: Путь к .docx файлу
        :param output_path: Путь к .md файлу
        :return: True если успешно
        """
        try:
            import mammoth

            # Проверяем, нужно ли заменять изображения на заглушки
            replace_images = hasattr(config, 'REPLACE_IMAGES_WITH_PLACEHOLDERS') and config.REPLACE_IMAGES_WITH_PLACEHOLDERS

            with open(input_path, 'rb') as docx_file:
                if replace_images:
                    # Используем конвертер с заменой изображений на заглушки
                    def convert_image(image):
                        return {"alt": "[Изображение удалено]"}

                    result = mammoth.convert_to_markdown(
                        docx_file,
                        convert_image=mammoth.images.img_element(convert_image)
                    )
                else:
                    result = mammoth.convert_to_markdown(docx_file)

                markdown_content = result.value

                # Добавляем метаданные
                metadata = self._create_metadata(input_path)
                full_content = metadata + markdown_content

                # Сохраняем результат
                with open(output_path, 'w', encoding='utf-8') as md_file:
                    md_file.write(full_content)

                # Логируем предупреждения от mammoth
                if result.messages:
                    for msg in result.messages:
                        logger.debug(f"Mammoth: {msg}")

                return True

        except Exception as e:
            logger.error(f"Ошибка mammoth конвертации {input_path.name}: {e}")
            return False

    def _convert_with_pandoc(self, input_path: Path, output_path: Path) -> bool:
        """
        Конвертация с использованием pandoc

        :param input_path: Путь к .docx/.doc файлу
        :param output_path: Путь к .md файлу
        :return: True если успешно
        """
        try:
            # Проверяем, нужно ли заменять изображения на заглушки
            replace_images = hasattr(config, 'REPLACE_IMAGES_WITH_PLACEHOLDERS') and config.REPLACE_IMAGES_WITH_PLACEHOLDERS

            # Формируем команду pandoc
            pandoc_cmd = [
                'pandoc',
                str(input_path),
                '-f', 'docx' if input_path.suffix.lower() == '.docx' else 'doc',
                '-t', 'markdown',
                '--wrap=none',  # Не переносить строки
                '-o', str(output_path)
            ]

            # Если НЕ заменяем изображения - извлекаем медиа
            if not replace_images:
                pandoc_cmd.insert(-2, '--extract-media')
                pandoc_cmd.insert(-2, str(output_path.parent / 'media'))

            # Запускаем pandoc
            result = subprocess.run(
                pandoc_cmd,
                capture_output=True,
                timeout=60,
                text=True
            )

            if result.returncode == 0:
                # Добавляем метаданные в начало файла
                self._prepend_metadata(output_path, input_path)
                return True
            else:
                logger.error(f"Pandoc ошибка: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout при конвертации {input_path.name}")
            return False
        except Exception as e:
            logger.error(f"Ошибка pandoc конвертации {input_path.name}: {e}")
            return False

    def _create_metadata(self, input_path: Path) -> str:
        """
        Создает метаданные для markdown файла

        :param input_path: Путь к исходному файлу
        :return: Строка с метаданными
        """
        metadata = f"""---
source_file: {input_path.name}
original_format: {input_path.suffix}
converted_by: WordConverter
---

# {input_path.stem}

"""
        return metadata

    def _prepend_metadata(self, md_path: Path, original_path: Path) -> None:
        """
        Добавляет метаданные в начало существующего markdown файла

        :param md_path: Путь к .md файлу
        :param original_path: Путь к оригинальному файлу
        """
        try:
            # Читаем существующий контент
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Создаем метаданные
            metadata = self._create_metadata(original_path)

            # Записываем метаданные + контент
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(metadata + content)

        except Exception as e:
            logger.error(f"Ошибка при добавлении метаданных: {e}")
