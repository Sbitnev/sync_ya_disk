#!/usr/bin/env python3
"""
Скрипт диагностики LibreOffice для конвертации .ppt/.doc файлов
Запустите на сервере для проверки установки и работоспособности
"""
import os
import sys
import platform
import subprocess
import tempfile
from pathlib import Path


def check_system_info():
    """Проверяет информацию о системе"""
    print("=" * 70)
    print("ИНФОРМАЦИЯ О СИСТЕМЕ")
    print("=" * 70)
    print(f"Операционная система: {platform.system()}")
    print(f"Версия ОС: {platform.release()}")
    print(f"Архитектура: {platform.machine()}")
    print(f"Python версия: {sys.version}")
    print()


def check_libreoffice_installed():
    """Проверяет, установлен ли LibreOffice"""
    print("=" * 70)
    print("ПРОВЕРКА УСТАНОВКИ LIBREOFFICE")
    print("=" * 70)

    found_commands = []

    # Проверка для Windows
    if platform.system() == 'Windows':
        possible_paths = [
            r'C:\Program Files\LibreOffice\program\soffice.exe',
            r'C:\Program Files (x86)\LibreOffice\program\soffice.exe',
        ]

        for path in possible_paths:
            if os.path.exists(path):
                print(f"✅ LibreOffice найден: {path}")
                found_commands.append(path)
            else:
                print(f"❌ Не найден: {path}")

    # Проверка для Linux/macOS через PATH
    commands = ['soffice', 'libreoffice', 'loffice']

    for cmd in commands:
        try:
            result = subprocess.run(
                ['which', cmd] if platform.system() != 'Windows' else ['where', cmd],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                path = result.stdout.strip()
                print(f"✅ {cmd} найден: {path}")
                found_commands.append(cmd)
            else:
                print(f"❌ {cmd} не найден в PATH")
        except Exception as e:
            print(f"❌ Ошибка проверки {cmd}: {e}")

    print()
    return found_commands


def check_libreoffice_version(command):
    """Проверяет версию LibreOffice"""
    print("=" * 70)
    print("ВЕРСИЯ LIBREOFFICE")
    print("=" * 70)

    try:
        result = subprocess.run(
            [command, '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print(f"✅ Версия LibreOffice:")
            print(result.stdout)
            return True
        else:
            print(f"❌ Не удалось получить версию")
            if result.stderr:
                print(f"Ошибка: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Таймаут при получении версии")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def check_headless_mode(command):
    """Проверяет работу LibreOffice в headless режиме"""
    print("=" * 70)
    print("ПРОВЕРКА HEADLESS РЕЖИМА")
    print("=" * 70)

    try:
        result = subprocess.run(
            [command, '--headless', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print("✅ Headless режим работает")
            return True
        else:
            print("❌ Headless режим не работает")
            if result.stderr:
                print(f"Ошибка: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Таймаут headless режима")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def test_conversion(command):
    """Тестирует реальную конвертацию файла"""
    print("=" * 70)
    print("ТЕСТ КОНВЕРТАЦИИ")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)

        # Создаем простой текстовый файл для теста
        test_file = temp_dir_path / "test.txt"
        with open(test_file, 'w') as f:
            f.write("Test file for LibreOffice conversion\n")

        print(f"Создан тестовый файл: {test_file}")

        # Пробуем конвертировать в PDF
        try:
            user_profile_dir = temp_dir_path / 'libreoffice_profile'
            user_profile_dir.mkdir(exist_ok=True)

            result = subprocess.run(
                [
                    command,
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', str(temp_dir_path),
                    '-env:UserInstallation=file:///' + str(user_profile_dir).replace('\\', '/'),
                    str(test_file)
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            print(f"Код возврата: {result.returncode}")

            if result.stdout:
                print(f"Stdout:\n{result.stdout}")

            if result.stderr:
                print(f"Stderr:\n{result.stderr}")

            # Проверяем, создан ли PDF
            pdf_file = temp_dir_path / "test.pdf"
            if pdf_file.exists():
                print(f"✅ Конвертация успешна! Создан файл: {pdf_file}")
                print(f"Размер файла: {pdf_file.stat().st_size} байт")
                return True
            else:
                print(f"❌ PDF файл не создан")

                # Показываем все файлы в директории
                files = list(temp_dir_path.iterdir())
                print(f"Файлы в temp директории: {[f.name for f in files]}")
                return False

        except subprocess.TimeoutExpired:
            print("❌ Таймаут при конвертации")
            return False
        except Exception as e:
            print(f"❌ Ошибка конвертации: {e}")
            import traceback
            traceback.print_exc()
            return False


def check_dependencies():
    """Проверяет зависимости для LibreOffice на Linux"""
    print("=" * 70)
    print("ПРОВЕРКА ЗАВИСИМОСТЕЙ (Linux)")
    print("=" * 70)

    if platform.system() != 'Linux':
        print("Пропущено (не Linux система)")
        print()
        return

    # Проверка X11 библиотек (нужны для headless режима)
    x11_libs = ['libX11.so.6', 'libXrender.so.1', 'libXext.so.6']

    for lib in x11_libs:
        try:
            result = subprocess.run(
                ['ldconfig', '-p'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if lib in result.stdout:
                print(f"✅ {lib} установлена")
            else:
                print(f"❌ {lib} не найдена (может потребоваться для headless)")
        except Exception as e:
            print(f"⚠️  Не удалось проверить {lib}: {e}")

    print()


def print_recommendations():
    """Выводит рекомендации по установке"""
    print("=" * 70)
    print("РЕКОМЕНДАЦИИ ПО УСТАНОВКЕ")
    print("=" * 70)

    if platform.system() == 'Linux':
        print("Для установки LibreOffice на Ubuntu/Debian:")
        print("  sudo apt-get update")
        print("  sudo apt-get install -y libreoffice-writer libreoffice-impress")
        print()
        print("Для headless режима также установите:")
        print("  sudo apt-get install -y libreoffice-common")
        print("  sudo apt-get install -y libx11-6 libxrender1 libxext6")
        print()

    elif platform.system() == 'Windows':
        print("Скачайте LibreOffice для Windows:")
        print("  https://www.libreoffice.org/download/download/")
        print()
        print("Или через winget:")
        print("  winget install TheDocumentFoundation.LibreOffice")
        print()

    elif platform.system() == 'Darwin':  # macOS
        print("Установите LibreOffice через Homebrew:")
        print("  brew install --cask libreoffice")
        print()


def main():
    """Главная функция"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "ДИАГНОСТИКА LIBREOFFICE" + " " * 30 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    # Проверка системы
    check_system_info()

    # Проверка установки
    found_commands = check_libreoffice_installed()

    if not found_commands:
        print("❌ LibreOffice НЕ НАЙДЕН на этой системе\n")
        print_recommendations()
        return 1

    # Берем первую найденную команду
    command = found_commands[0]
    print(f"Используем команду: {command}\n")

    # Проверка версии
    version_ok = check_libreoffice_version(command)

    # Проверка headless режима
    headless_ok = check_headless_mode(command)

    # Проверка зависимостей
    check_dependencies()

    # Тест конвертации
    if version_ok and headless_ok:
        conversion_ok = test_conversion(command)
    else:
        conversion_ok = False
        print("Пропущен тест конвертации (предыдущие проверки не прошли)\n")

    # Итоги
    print("=" * 70)
    print("ИТОГИ")
    print("=" * 70)
    print(f"LibreOffice установлен: {'✅ Да' if found_commands else '❌ Нет'}")
    print(f"Версия доступна: {'✅ Да' if version_ok else '❌ Нет'}")
    print(f"Headless режим: {'✅ Работает' if headless_ok else '❌ Не работает'}")
    print(f"Конвертация файлов: {'✅ Работает' if conversion_ok else '❌ Не работает'}")
    print()

    if conversion_ok:
        print("🎉 LibreOffice настроен корректно и готов к использованию!")
        return 0
    else:
        print("⚠️  LibreOffice требует дополнительной настройки")
        print()
        print_recommendations()
        return 1


if __name__ == "__main__":
    sys.exit(main())
