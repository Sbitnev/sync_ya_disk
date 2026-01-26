"""
Скрипт запуска выгрузки всех файлов в stash/
"""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    # Определяем путь к интерпретатору Python в venv
    if sys.platform == 'win32':
        python_exe = Path('.venv') / 'Scripts' / 'python.exe'
    else:
        python_exe = Path('.venv') / 'bin' / 'python'

    if not python_exe.exists():
        print(f"Ошибка: виртуальное окружение не найдено: {python_exe}")
        sys.exit(1)

    # Запускаем скрипт выгрузки
    subprocess.run([str(python_exe), 'download_all_to_stash.py'])
