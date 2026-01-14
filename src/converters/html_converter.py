"""
Конвертер HTML файлов в Markdown
"""
from pathlib import Path
from .base import FileConverter


class HTMLConverter(FileConverter):
    """
    Конвертер для HTML файлов
    Поддерживает: .html, .htm
    """

    def __init__(self):
        super().__init__(['.html', '.htm'])
        self.has_html2text = self._check_html2text()
        self.has_beautifulsoup = self._check_beautifulsoup()

    def _check_html2text(self) -> bool:
        """Проверяет доступность html2text"""
        try:
            import html2text
            return True
        except ImportError:
            return False

    def _check_beautifulsoup(self) -> bool:
        """Проверяет доступность BeautifulSoup"""
        try:
            from bs4 import BeautifulSoup
            return True
        except ImportError:
            return False

    def convert(self, input_path: Path, output_path: Path) -> bool:
        """
        Конвертирует HTML в Markdown

        :param input_path: Путь к исходному файлу
        :param output_path: Путь для сохранения markdown файла
        :return: True если конвертация успешна
        """
        if self.has_html2text:
            return self._convert_with_html2text(input_path, output_path)
        elif self.has_beautifulsoup:
            return self._convert_with_beautifulsoup(input_path, output_path)
        else:
            print(f"Для конвертации HTML установите: pip install html2text beautifulsoup4")
            return False

    def _convert_with_html2text(self, input_path: Path, output_path: Path) -> bool:
        """Конвертирует с помощью html2text"""
        import html2text

        try:
            # Читаем HTML
            content = self._read_with_fallback(input_path)
            if content is None:
                return False

            # Создаем директорию для выходного файла
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Настраиваем конвертер
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True  # Игнорируем изображения
            h.body_width = 0  # Не переносим строки

            # Конвертируем
            markdown_content = h.handle(content)

            with open(output_path, 'w', encoding='utf-8') as f:
                # YAML заголовок
                f.write("---\n")
                f.write(f"source_file: {input_path.name}\n")
                f.write(f"original_format: {input_path.suffix.lower()}\n")
                f.write(f"converted_by: HTMLConverter\n")
                f.write(f"method: html2text\n")
                f.write("---\n\n")

                # Заголовок
                f.write(f"# {input_path.stem}\n\n")
                f.write(f"**Тип:** HTML документ\n\n")

                # Содержимое
                f.write(markdown_content)

            return True

        except Exception as e:
            print(f"Ошибка html2text: {e}")
            return False

    def _convert_with_beautifulsoup(self, input_path: Path, output_path: Path) -> bool:
        """Конвертирует с помощью BeautifulSoup (простое извлечение текста)"""
        from bs4 import BeautifulSoup

        try:
            # Читаем HTML
            content = self._read_with_fallback(input_path)
            if content is None:
                return False

            # Парсим HTML
            soup = BeautifulSoup(content, 'html.parser')

            # Удаляем скрипты и стили
            for script in soup(["script", "style"]):
                script.decompose()

            # Извлекаем текст
            text = soup.get_text()

            # Очищаем пустые строки
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            # Создаем директорию для выходного файла
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                # YAML заголовок
                f.write("---\n")
                f.write(f"source_file: {input_path.name}\n")
                f.write(f"original_format: {input_path.suffix.lower()}\n")
                f.write(f"converted_by: HTMLConverter\n")
                f.write(f"method: beautifulsoup\n")
                f.write("---\n\n")

                # Заголовок
                f.write(f"# {input_path.stem}\n\n")
                f.write(f"**Тип:** HTML документ\n\n")

                # Содержимое
                f.write("## Извлеченный текст\n\n")
                f.write(text)

            return True

        except Exception as e:
            print(f"Ошибка BeautifulSoup: {e}")
            return False

    def _read_with_fallback(self, file_path: Path) -> str:
        """Читает файл с fallback на разные кодировки"""
        encodings = ['utf-8', 'cp1251', 'windows-1251', 'latin-1']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception:
                continue

        return None
