"""
Конвертер PDF файлов в Markdown
"""
from pathlib import Path
from loguru import logger

from .base import FileConverter


class PDFConverter(FileConverter):
    """
    Конвертер PDF файлов в Markdown

    Использует pdfplumber для извлечения текста
    Каждая страница PDF -> отдельная секция в Markdown
    """

    def __init__(self, max_pages: int = 100):
        """
        :param max_pages: Максимальное количество страниц для обработки
        """
        super().__init__(['.pdf'])
        self.max_pages = max_pages
        self.has_pdfplumber = self._check_pdfplumber()
        self.has_pypdf2 = self._check_pypdf2()

        if not self.has_pdfplumber and not self.has_pypdf2:
            logger.warning("Ни pdfplumber, ни PyPDF2 не найдены. Конвертация PDF недоступна.")

    def _check_pdfplumber(self) -> bool:
        """Проверяет наличие pdfplumber"""
        try:
            import pdfplumber
            return True
        except ImportError:
            return False

    def _check_pypdf2(self) -> bool:
        """Проверяет наличие PyPDF2"""
        try:
            import PyPDF2
            return True
        except ImportError:
            return False

    def convert(self, input_path: Path, output_path: Path) -> bool:
        """
        Конвертирует PDF в Markdown

        :param input_path: Путь к .pdf файлу
        :param output_path: Путь к .md файлу
        :return: True если успешно
        """
        # Используем pdfplumber если доступен (лучшее качество)
        if self.has_pdfplumber:
            return self._convert_with_pdfplumber(input_path, output_path)
        elif self.has_pypdf2:
            return self._convert_with_pypdf2(input_path, output_path)
        else:
            logger.error("Нет доступных библиотек для конвертации PDF")
            return False

    def _convert_with_pdfplumber(self, input_path: Path, output_path: Path) -> bool:
        """
        Конвертация с использованием pdfplumber

        :param input_path: Путь к PDF файлу
        :param output_path: Путь к .md файлу
        :return: True если успешно
        """
        try:
            import pdfplumber

            # Открываем PDF
            with pdfplumber.open(input_path) as pdf:
                total_pages = len(pdf.pages)
                pages_to_process = min(total_pages, self.max_pages)
                is_truncated = total_pages > self.max_pages

                # Создаем метаданные
                metadata = self._create_metadata(input_path, total_pages, is_truncated)

                # Извлекаем текст со всех страниц
                all_content = [metadata]

                for i, page in enumerate(pdf.pages[:pages_to_process], 1):
                    try:
                        # Извлекаем текст
                        text = page.extract_text()

                        if text and text.strip():
                            # Добавляем заголовок страницы
                            page_header = f"\n## Страница {i}\n\n"
                            all_content.append(page_header + text.strip() + "\n")
                        else:
                            # Страница без текста (возможно, только изображения)
                            all_content.append(f"\n## Страница {i}\n\n_Страница не содержит текста или содержит только изображения_\n")

                    except Exception as e:
                        logger.error(f"Ошибка при обработке страницы {i}: {e}")
                        all_content.append(f"\n## Страница {i}\n\n❌ Ошибка при извлечении текста\n")

                # Добавляем примечание о необработанных страницах
                if is_truncated:
                    all_content.append(
                        f"\n---\n\n⚠️ Обработаны первые {self.max_pages} из {total_pages} страниц.\n"
                    )

                # Сохраняем результат
                full_content = "\n".join(all_content)
                with open(output_path, 'w', encoding='utf-8') as md_file:
                    md_file.write(full_content)

                return True

        except Exception as e:
            logger.error(f"Ошибка pdfplumber конвертации {input_path.name}: {e}")
            return False

    def _convert_with_pypdf2(self, input_path: Path, output_path: Path) -> bool:
        """
        Конвертация с использованием PyPDF2 (fallback)

        :param input_path: Путь к PDF файлу
        :param output_path: Путь к .md файлу
        :return: True если успешно
        """
        try:
            import PyPDF2

            # Открываем PDF
            with open(input_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                total_pages = len(pdf_reader.pages)
                pages_to_process = min(total_pages, self.max_pages)
                is_truncated = total_pages > self.max_pages

                # Создаем метаданные
                metadata = self._create_metadata(input_path, total_pages, is_truncated)

                # Извлекаем текст со всех страниц
                all_content = [metadata]

                for i in range(pages_to_process):
                    try:
                        page = pdf_reader.pages[i]
                        text = page.extract_text()

                        if text and text.strip():
                            # Добавляем заголовок страницы
                            page_header = f"\n## Страница {i + 1}\n\n"
                            all_content.append(page_header + text.strip() + "\n")
                        else:
                            all_content.append(f"\n## Страница {i + 1}\n\n_Страница не содержит текста_\n")

                    except Exception as e:
                        logger.error(f"Ошибка при обработке страницы {i + 1}: {e}")
                        all_content.append(f"\n## Страница {i + 1}\n\n❌ Ошибка при извлечении текста\n")

                # Добавляем примечание о необработанных страницах
                if is_truncated:
                    all_content.append(
                        f"\n---\n\n⚠️ Обработаны первые {self.max_pages} из {total_pages} страниц.\n"
                    )

                # Сохраняем результат
                full_content = "\n".join(all_content)
                with open(output_path, 'w', encoding='utf-8') as md_file:
                    md_file.write(full_content)

                return True

        except Exception as e:
            logger.error(f"Ошибка PyPDF2 конвертации {input_path.name}: {e}")
            return False

    def _create_metadata(self, input_path: Path, total_pages: int, truncated: bool) -> str:
        """
        Создает метаданные для markdown файла

        :param input_path: Путь к исходному файлу
        :param total_pages: Количество страниц
        :param truncated: Обрезаны ли страницы
        :return: Строка с метаданными
        """
        metadata = f"""---
source_file: {input_path.name}
original_format: .pdf
total_pages: {total_pages}
pages_truncated: {truncated}
converted_by: PDFConverter
---

# {input_path.stem}

**Тип:** PDF документ
**Страниц:** {total_pages}

"""
        return metadata
