"""
Тестовый скрипт для проверки конвертеров
"""
from pathlib import Path
from src.converters import WordConverter, CSVConverter
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

if __name__ == "__main__":
    test_word_converter()
    test_csv_converter()

    print("\n" + "=" * 70)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 70)
