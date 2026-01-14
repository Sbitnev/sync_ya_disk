"""
Тестовый скрипт для проверки конвертеров
"""
from pathlib import Path
from src.converters import WordConverter, CSVConverter, ExcelConverter, PDFConverter
from src import config

def test_word_converter():
    """Тест конвертации Word документов"""
    print("=" * 70)
    print("ТЕСТ WORD CONVERTER")
    print("=" * 70)

    converter = WordConverter()
    input_dir = Path("downloaded_files")
    output_dir = Path(config.MARKDOWN_OUTPUT_DIR)
    output_dir.mkdir(exist_ok=True)

    # Находим все .docx файлы
    docx_files = list(input_dir.glob("*.docx"))
    print(f"Найдено .docx файлов: {len(docx_files)}")

    for docx_file in docx_files:
        print(f"\nКонвертация: {docx_file.name}")
        output_file = output_dir / docx_file.with_suffix('.md').name

        success = converter.convert_safe(docx_file, output_file)
        if success:
            print(f"[OK] Успешно: {output_file}")
            # Показываем первые 500 символов
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"Размер: {len(content)} символов")
                print(f"Превью:")
                print(content[:500])
                print("...")
        else:
            print(f"[FAIL] Ошибка при конвертации {docx_file.name}")

def test_csv_converter():
    """Тест конвертации CSV файлов"""
    print("\n" + "=" * 70)
    print("ТЕСТ CSV CONVERTER")
    print("=" * 70)

    converter = CSVConverter()
    input_dir = Path("downloaded_files")
    output_dir = Path(config.MARKDOWN_OUTPUT_DIR)
    output_dir.mkdir(exist_ok=True)

    # Находим все .csv файлы
    csv_files = list(input_dir.rglob("*.csv"))
    print(f"Найдено .csv файлов: {len(csv_files)}")

    for csv_file in csv_files:
        print(f"\nКонвертация: {csv_file.name}")
        output_file = output_dir / csv_file.with_suffix('.md').name

        success = converter.convert_safe(csv_file, output_file)
        if success:
            print(f"[OK] Успешно: {output_file}")
            # Показываем первые 500 символов
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"Размер: {len(content)} символов")
                print(f"Превью:")
                print(content[:500])
                print("...")
        else:
            print(f"[FAIL] Ошибка при конвертации {csv_file.name}")

def test_excel_converter():
    """Тест конвертации Excel файлов"""
    print("\n" + "=" * 70)
    print("ТЕСТ EXCEL CONVERTER")
    print("=" * 70)

    converter = ExcelConverter(
        max_rows=config.EXCEL_MAX_ROWS,
        max_columns=config.EXCEL_MAX_COLUMNS,
        sheets_limit=config.EXCEL_MAX_SHEETS
    )
    input_dir = Path("downloaded_files")
    output_dir = Path(config.MARKDOWN_OUTPUT_DIR)
    output_dir.mkdir(exist_ok=True)

    # Находим все Excel файлы
    excel_patterns = ['*.xlsx', '*.xls', '*.xlsm', '*.xlsb']
    excel_files = []
    for pattern in excel_patterns:
        excel_files.extend(input_dir.rglob(pattern))

    print(f"Найдено Excel файлов: {len(excel_files)}")

    for excel_file in excel_files[:3]:  # Тестируем только первые 3
        print(f"\nКонвертация: {excel_file.name}")
        output_file = output_dir / excel_file.with_suffix('.md').name

        success = converter.convert_safe(excel_file, output_file)
        if success:
            print(f"[OK] Успешно: {output_file}")
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"Размер: {len(content)} символов")
                print(f"Превью:")
                print(content[:500])
                print("...")
        else:
            print(f"[FAIL] Ошибка при конвертации {excel_file.name}")

def test_pdf_converter():
    """Тест конвертации PDF файлов"""
    print("\n" + "=" * 70)
    print("ТЕСТ PDF CONVERTER")
    print("=" * 70)

    converter = PDFConverter(max_pages=config.PDF_MAX_PAGES)
    input_dir = Path("downloaded_files")
    output_dir = Path(config.MARKDOWN_OUTPUT_DIR)
    output_dir.mkdir(exist_ok=True)

    # Находим все .pdf файлы
    pdf_files = list(input_dir.rglob("*.pdf"))
    print(f"Найдено .pdf файлов: {len(pdf_files)}")

    for pdf_file in pdf_files[:2]:  # Тестируем только первые 2
        print(f"\nКонвертация: {pdf_file.name}")
        output_file = output_dir / pdf_file.with_suffix('.md').name

        success = converter.convert_safe(pdf_file, output_file)
        if success:
            print(f"[OK] Успешно: {output_file}")
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"Размер: {len(content)} символов")
                print(f"Превью:")
                print(content[:500])
                print("...")
        else:
            print(f"[FAIL] Ошибка при конвертации {pdf_file.name}")

if __name__ == "__main__":
    test_word_converter()
    test_csv_converter()
    test_excel_converter()
    test_pdf_converter()

    print("\n" + "=" * 70)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 70)
