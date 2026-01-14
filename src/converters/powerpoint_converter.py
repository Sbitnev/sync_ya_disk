"""
Конвертер PowerPoint презентаций в Markdown
"""
from pathlib import Path
from .base import FileConverter


class PowerPointConverter(FileConverter):
    """
    Конвертер для PowerPoint презентаций
    Поддерживает: .pptx, .ppt
    """

    def __init__(self):
        super().__init__(['.pptx', '.ppt'])
        self.has_pptx = self._check_pptx()

    def _check_pptx(self) -> bool:
        """Проверяет доступность python-pptx"""
        try:
            import pptx
            return True
        except ImportError:
            return False

    def convert(self, input_path: Path, output_path: Path) -> bool:
        """
        Конвертирует PowerPoint в Markdown

        :param input_path: Путь к исходному файлу
        :param output_path: Путь для сохранения markdown файла
        :return: True если конвертация успешна
        """
        if not self.has_pptx:
            print(f"python-pptx не установлен. Установите: pip install python-pptx")
            return False

        # .ppt требует конвертации в .pptx, пока не поддерживается
        if input_path.suffix.lower() == '.ppt':
            print(f"Формат .ppt не поддерживается напрямую. Требуется конвертация в .pptx")
            return False

        try:
            return self._convert_with_pptx(input_path, output_path)
        except Exception as e:
            print(f"Ошибка при конвертации {input_path}: {e}")
            return False

    def _convert_with_pptx(self, input_path: Path, output_path: Path) -> bool:
        """Конвертирует с помощью python-pptx"""
        from pptx import Presentation

        try:
            # Открываем презентацию
            prs = Presentation(input_path)

            # Создаем директорию для выходного файла
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                # YAML заголовок
                f.write("---\n")
                f.write(f"source_file: {input_path.name}\n")
                f.write(f"original_format: {input_path.suffix.lower()}\n")
                f.write(f"total_slides: {len(prs.slides)}\n")
                f.write(f"converted_by: PowerPointConverter\n")
                f.write("---\n\n")

                # Заголовок
                f.write(f"# {input_path.stem}\n\n")
                f.write(f"**Тип:** PowerPoint презентация\n")
                f.write(f"**Слайдов:** {len(prs.slides)}\n\n")

                # Обрабатываем каждый слайд
                for i, slide in enumerate(prs.slides, 1):
                    f.write(f"\n## Слайд {i}\n\n")

                    # Извлекаем текст из слайда
                    slide_text = []

                    for shape in slide.shapes:
                        if hasattr(shape, "text") and shape.text:
                            text = shape.text.strip()
                            if text:
                                slide_text.append(text)

                    if slide_text:
                        for text in slide_text:
                            # Определяем, является ли текст заголовком (обычно первый текст)
                            if text == slide_text[0] and len(text) < 100:
                                f.write(f"### {text}\n\n")
                            else:
                                f.write(f"{text}\n\n")
                    else:
                        f.write("*(Слайд без текста)*\n\n")

                    # Если есть заметки докладчика
                    if slide.has_notes_slide:
                        notes = slide.notes_slide.notes_text_frame.text.strip()
                        if notes:
                            f.write(f"**Заметки докладчика:**\n\n")
                            f.write(f"> {notes}\n\n")

            return True

        except Exception as e:
            print(f"Ошибка python-pptx: {e}")
            return False
