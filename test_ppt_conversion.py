#!/usr/bin/env python3
"""
Тест конвертации конкретного .ppt файла через LibreOffice
Используйте для диагностики проблем с конвертацией презентаций
"""
import sys
import subprocess
import tempfile
from pathlib import Path


def test_ppt_file(ppt_path: str):
    """
    Тестирует конвертацию конкретного .ppt файла

    :param ppt_path: Путь к .ppt файлу
    """
    ppt_file = Path(ppt_path)

    if not ppt_file.exists():
        print(f"❌ Файл не найден: {ppt_path}")
        return 1

    print("=" * 70)
    print("ТЕСТ КОНВЕРТАЦИИ .PPT ФАЙЛА")
    print("=" * 70)
    print(f"Файл: {ppt_file.name}")
    print(f"Размер: {ppt_file.stat().st_size:,} байт")
    print()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)

        # Создаем профиль LibreOffice
        user_profile_dir = temp_dir_path / 'libreoffice_profile'
        user_profile_dir.mkdir(exist_ok=True)

        print("Запуск LibreOffice для конвертации .ppt -> .pptx...")
        print()

        # Команда конвертации
        command = [
            'soffice',
            '--headless',
            '--convert-to', 'pptx',
            '--outdir', str(temp_dir_path),
            '-env:UserInstallation=file:///' + str(user_profile_dir).replace('\\', '/'),
            str(ppt_file.resolve())
        ]

        print("Команда:")
        print(" ".join(command))
        print()

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=120
            )

            print(f"Код возврата: {result.returncode}")
            print()

            if result.stdout:
                print("Stdout:")
                print(result.stdout)
                print()

            if result.stderr:
                print("Stderr:")
                print(result.stderr)
                print()

            # Проверяем результат
            expected_pptx = temp_dir_path / f"{ppt_file.stem}.pptx"

            print("Поиск результата...")
            print(f"Ожидаемый файл: {expected_pptx}")
            print()

            # Показываем все файлы в temp директории
            all_files = list(temp_dir_path.iterdir())
            print(f"Файлы в temp директории ({len(all_files)}):")
            for f in all_files:
                if f.is_file():
                    print(f"  📄 {f.name} ({f.stat().st_size:,} байт)")
                else:
                    print(f"  📁 {f.name}/")
            print()

            # Проверяем .pptx файлы
            pptx_files = list(temp_dir_path.glob('*.pptx'))

            if expected_pptx.exists():
                print(f"✅ Конвертация УСПЕШНА!")
                print(f"Создан файл: {expected_pptx.name}")
                print(f"Размер: {expected_pptx.stat().st_size:,} байт")
                print()

                # Пробуем открыть через python-pptx
                try:
                    from pptx import Presentation
                    prs = Presentation(expected_pptx)
                    print(f"✅ .pptx файл валиден")
                    print(f"Количество слайдов: {len(prs.slides)}")
                    return 0
                except ImportError:
                    print("⚠️  python-pptx не установлен, не могу проверить валидность")
                    return 0
                except Exception as e:
                    print(f"⚠️  Ошибка при чтении .pptx: {e}")
                    return 0

            elif pptx_files:
                print(f"✅ Конвертация УСПЕШНА (другое имя)")
                for pptx in pptx_files:
                    print(f"Создан файл: {pptx.name}")
                    print(f"Размер: {pptx.stat().st_size:,} байт")
                return 0
            else:
                print("❌ .pptx файл НЕ СОЗДАН")
                print()
                print("Возможные причины:")
                print("  1. Файл .ppt поврежден или в неподдерживаемом формате")
                print("  2. Недостаточно прав доступа")
                print("  3. Проблема с LibreOffice (попробуйте обновить)")
                print("  4. Файл защищен паролем")
                return 1

        except subprocess.TimeoutExpired:
            print("❌ ТАЙМАУТ (>120 секунд)")
            print("Файл слишком большой или LibreOffice завис")
            return 1

        except Exception as e:
            print(f"❌ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
            return 1


def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print("Использование:")
        print(f"  python {sys.argv[0]} <путь_к_ppt_файлу>")
        print()
        print("Пример:")
        print(f"  python {sys.argv[0]} localdata/downloaded_files/presentation.ppt")
        return 1

    ppt_path = sys.argv[1]
    return test_ppt_file(ppt_path)


if __name__ == "__main__":
    sys.exit(main())
