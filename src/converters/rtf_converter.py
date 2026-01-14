"""
Конвертер RTF файлов в Markdown
"""
from pathlib import Path
from .base import FileConverter


class RTFConverter(FileConverter):
    """
    Конвертер для Rich Text Format файлов
    Поддерживает: .rtf
    """

    def __init__(self):
        super().__init__(['.rtf'])
        self.has_striprtf = self._check_striprtf()
        self.has_pypandoc = self._check_pypandoc()

    def _check_striprtf(self) -> bool:
        """Проверяет доступность striprtf"""
        try:
            from striprtf.striprtf import rtf_to_text
            return True
        except ImportError:
            return False

    def _check_pypandoc(self) -> bool:
        """Проверяет доступность pypandoc"""
        try:
            import pypandoc
            # Проверяем, установлен ли pandoc
            pypandoc.get_pandoc_version()
            return True
        except (ImportError, OSError):
            return False

    def convert(self, input_path: Path, output_path: Path) -> bool:
        """
        Конвертирует RTF в Markdown

        :param input_path: Путь к исходному файлу
        :param output_path: Путь для сохранения markdown файла
        :return: True если конвертация успешна
        """
        if self.has_pypandoc:
            return self._convert_with_pypandoc(input_path, output_path)
        elif self.has_striprtf:
            return self._convert_with_striprtf(input_path, output_path)
        else:
            print(f"Для конвертации RTF установите: pip install striprtf pypandoc")
            return False

    def _convert_with_pypandoc(self, input_path: Path, output_path: Path) -> bool:
        """Конвертирует с помощью pypandoc (лучшее качество)"""
        import pypandoc

        try:
            # Создаем директорию для выходного файла
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Конвертируем напрямую с pypandoc
            markdown_content = pypandoc.convert_file(
                str(input_path),
                'markdown',
                format='rtf',
                extra_args=['--wrap=none']
            )

            with open(output_path, 'w', encoding='utf-8') as f:
                # YAML заголовок
                f.write("---\n")
                f.write(f"source_file: {input_path.name}\n")
                f.write(f"original_format: .rtf\n")
                f.write(f"converted_by: RTFConverter\n")
                f.write(f"method: pypandoc\n")
                f.write("---\n\n")

                # Заголовок
                f.write(f"# {input_path.stem}\n\n")
                f.write(f"**Тип:** Rich Text Format документ\n\n")

                # Содержимое
                f.write(markdown_content)

            return True

        except Exception as e:
            print(f"Ошибка pypandoc: {e}")
            return False

    def _convert_with_striprtf(self, input_path: Path, output_path: Path) -> bool:
        """Конвертирует с помощью striprtf (простое извлечение текста)"""
        from striprtf.striprtf import rtf_to_text

        try:
            # Читаем RTF файл
            with open(input_path, 'r', encoding='utf-8') as f:
                rtf_content = f.read()

            # Извлекаем текст
            text = rtf_to_text(rtf_content)

            # Создаем директорию для выходного файла
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                # YAML заголовок
                f.write("---\n")
                f.write(f"source_file: {input_path.name}\n")
                f.write(f"original_format: .rtf\n")
                f.write(f"converted_by: RTFConverter\n")
                f.write(f"method: striprtf\n")
                f.write("---\n\n")

                # Заголовок
                f.write(f"# {input_path.stem}\n\n")
                f.write(f"**Тип:** Rich Text Format документ\n\n")

                # Содержимое
                f.write("## Извлеченный текст\n\n")
                f.write(text)

            return True

        except Exception as e:
            print(f"Ошибка striprtf: {e}")
            return False
