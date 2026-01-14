"""
Конвертер текстовых файлов и кода в Markdown
"""
from pathlib import Path
from .base import FileConverter


class TextConverter(FileConverter):
    """
    Конвертер для текстовых файлов и кода
    Поддерживает: .txt, .md, .py, .json, .xml, .avsc, .j2
    """

    # Маппинг расширений к языкам для подсветки синтаксиса
    LANGUAGE_MAP = {
        '.py': 'python',
        '.json': 'json',
        '.xml': 'xml',
        '.avsc': 'json',  # Avro Schema это JSON
        '.j2': 'jinja2',
        '.txt': 'text',
        '.md': 'markdown'
    }

    def __init__(self):
        super().__init__(['.txt', '.md', '.py', '.json', '.xml', '.avsc', '.j2'])

    def convert(self, input_path: Path, output_path: Path) -> bool:
        """
        Конвертирует текстовый файл или код в Markdown

        :param input_path: Путь к исходному файлу
        :param output_path: Путь для сохранения markdown файла
        :return: True если конвертация успешна
        """
        try:
            # Читаем содержимое с различными кодировками
            content = self._read_with_fallback(input_path)

            if content is None:
                return False

            # Создаем директорию для выходного файла
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Определяем язык для подсветки синтаксиса
            extension = input_path.suffix.lower()
            language = self.LANGUAGE_MAP.get(extension, 'text')

            # Формируем markdown
            with open(output_path, 'w', encoding='utf-8') as f:
                # YAML заголовок с метаданными
                f.write("---\n")
                f.write(f"source_file: {input_path.name}\n")
                f.write(f"original_format: {extension}\n")
                f.write(f"language: {language}\n")
                f.write(f"size_bytes: {input_path.stat().st_size}\n")
                f.write(f"converted_by: TextConverter\n")
                f.write("---\n\n")

                # Заголовок
                f.write(f"# {input_path.stem}\n\n")
                f.write(f"**Тип:** {self._get_file_type_name(extension)}\n")
                f.write(f"**Формат:** {extension}\n\n")

                # Для .md файлов - вставляем содержимое как есть
                if extension == '.md':
                    f.write("## Содержимое\n\n")
                    f.write(content)
                else:
                    # Для остальных - оборачиваем в code block
                    f.write("## Содержимое\n\n")
                    f.write(f"```{language}\n")
                    f.write(content)
                    if not content.endswith('\n'):
                        f.write('\n')
                    f.write("```\n")

            return True

        except Exception as e:
            print(f"Ошибка при конвертации {input_path}: {e}")
            return False

    def _read_with_fallback(self, file_path: Path) -> str:
        """
        Читает файл с fallback на разные кодировки

        :param file_path: Путь к файлу
        :return: Содержимое файла или None
        """
        encodings = ['utf-8', 'cp1251', 'windows-1251', 'latin-1']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                print(f"Ошибка чтения файла {file_path} с кодировкой {encoding}: {e}")
                continue

        print(f"Не удалось прочитать файл {file_path} ни с одной из кодировок")
        return None

    def _get_file_type_name(self, extension: str) -> str:
        """Возвращает человекочитаемое название типа файла"""
        type_names = {
            '.txt': 'Текстовый файл',
            '.md': 'Markdown документ',
            '.py': 'Python скрипт',
            '.json': 'JSON данные',
            '.xml': 'XML документ',
            '.avsc': 'Avro Schema',
            '.j2': 'Jinja2 шаблон'
        }
        return type_names.get(extension, 'Текстовый файл')
