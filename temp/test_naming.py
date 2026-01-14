"""
Тестовый скрипт для проверки новой логики именования markdown файлов
"""
from pathlib import Path
from src.converters import WordConverter, PDFConverter
from src import config

def test_naming():
    print("=== ТЕСТ НОВОЙ ЛОГИКИ ИМЕНОВАНИЯ ===\n")

    # Файлы для теста
    test_files = [
        "downloaded_files/Договор и документы/Аптеки Вита. Предварительное предложение.docx",
        "downloaded_files/Договор и документы/Аптеки Вита. Предварительное предложение.pdf",
        "downloaded_files/Договор и документы/Аптеки Вита. Уточненное предложение.docx",
        "downloaded_files/Договор и документы/Аптеки Вита. Уточненное предложение.pdf",
    ]

    word_converter = WordConverter()
    pdf_converter = PDFConverter(max_pages=config.PDF_MAX_PAGES)

    markdown_dir = Path(config.MARKDOWN_OUTPUT_DIR)
    download_dir = Path("downloaded_files")

    for file_path_str in test_files:
        file_path = Path(file_path_str)

        if not file_path.exists():
            print(f"[!] Файл не найден: {file_path}")
            continue

        print(f"\n[*] Обработка: {file_path.name}")

        # Определяем конвертер
        if file_path.suffix.lower() in ['.docx', '.doc']:
            converter = word_converter
        elif file_path.suffix.lower() == '.pdf':
            converter = pdf_converter
        else:
            print(f"    [X] Неподдерживаемый формат")
            continue

        # Формируем путь для markdown файла (новая логика)
        relative_path = file_path.relative_to(download_dir)
        md_filename = relative_path.name + '.md'
        md_path = markdown_dir / relative_path.parent / md_filename

        print(f"    Исходный файл: {file_path.name}")
        print(f"    MD файл будет: {md_path.name}")
        print(f"    Полный путь: {md_path}")

        # Конвертируем
        success = converter.convert_safe(file_path, md_path)

        if success:
            print(f"    [OK] Успешно сконвертирован")
            # Проверяем размер
            md_size = md_path.stat().st_size
            print(f"    Размер MD: {md_size:,} байт")
        else:
            print(f"    [FAIL] Ошибка конвертации")

    print("\n=== РЕЗУЛЬТАТЫ ===\n")

    # Показываем все созданные MD файлы
    md_files = list(markdown_dir.glob("**/*.md"))
    print(f"Всего создано MD файлов: {len(md_files)}\n")

    # Группируем по базовому имени
    from collections import defaultdict
    base_names = defaultdict(list)

    for md_file in md_files:
        # Убираем расширение .md и смотрим на оригинальное имя
        original_name = md_file.stem  # report.docx.md → report.docx
        base_name = Path(original_name).stem  # report.docx → report
        base_names[base_name].append(md_file)

    # Показываем файлы с одинаковыми базовыми именами
    for base_name, files in sorted(base_names.items()):
        if len(files) > 1:
            print(f"[*] Базовое имя: {base_name}")
            for f in files:
                print(f"    - {f.name}")
            print()

if __name__ == "__main__":
    test_naming()
