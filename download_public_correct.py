"""
Правильное скачивание файла из публичной папки
"""
import os
import yadisk
from dotenv import load_dotenv
from pathlib import Path


def main():
    load_dotenv()
    token = os.getenv("Token")

    if not token:
        print("Токен не найден")
        return

    public_url = "https://disk.yandex.ru/d/_JeaJNmm6UeQVA"
    local_path = Path("test_downloads/UInd. Предварительное предложение.docx")

    print("="*80)
    print("СКАЧИВАНИЕ ФАЙЛА ИЗ ПУБЛИЧНОЙ ПАПКИ")
    print("="*80)

    # Создаём клиент
    y = yadisk.YaDisk(token=token)

    # Проверяем токен
    try:
        if not y.check_token():
            print("[ERROR] Токен недействителен")
            return
        print("[OK] Токен валиден\n")
    except Exception as e:
        print(f"[ERROR] Ошибка проверки токена: {e}")
        return

    # Получаем информацию о публичной папке
    print("Получение информации о публичной папке...")
    try:
        pub_resource = y.get_public_meta(public_url)
        print(f"[OK] Папка найдена: {pub_resource.name}")
        print(f"     Тип: {pub_resource.type}")
        print(f"     Владелец: {pub_resource.owner.login if pub_resource.owner else 'Неизвестно'}")
    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        return

    # Ищем подпапку
    print("\nПоиск подпапки 'Юн.Индастриал'...")
    try:
        # Получаем список элементов в корне
        items = list(y.public_listdir(public_url, limit=1000))

        target_folder = None
        for item in items:
            if item.type == "dir" and item.name == "Юн.Индастриал":
                target_folder = item
                break

        if not target_folder:
            print("[ERROR] Подпапка не найдена")
            return

        print(f"[OK] Подпапка найдена: {target_folder.path}")

        # Получаем файлы в подпапке
        print(f"\nПолучение списка файлов в подпапке...")
        folder_public_key = target_folder.public_key or public_url
        folder_path = target_folder.path

        # Получаем список файлов в подпапке
        files = list(y.public_listdir(folder_public_key, path=folder_path, limit=1000))

        print(f"[OK] Найдено файлов: {len([f for f in files if f.type == 'file'])}")

        # Ищем нужный файл
        target_file = None
        for file_item in files:
            if file_item.name == "UInd. Предварительное предложение.docx":
                target_file = file_item
                break

        if not target_file:
            print("[ERROR] Файл не найден")
            print("Доступные файлы:")
            for f in files[:10]:
                if f.type == "file":
                    print(f"  - {f.name}")
            return

        print(f"[OK] Файл найден: {target_file.name}")
        print(f"     Размер: {target_file.size / 1024 / 1024:.2f} МБ")

        # Скачиваем файл
        print(f"\nПопытка скачать файл...")
        local_path.parent.mkdir(parents=True, exist_ok=True)

        file_public_key = target_file.public_key or folder_public_key
        file_path = target_file.path

        y.download_public(file_public_key, str(local_path), path=file_path)

        print(f"[OK] Файл успешно скачан!")
        print(f"Расположение: {local_path.absolute()}")
        print(f"Размер: {local_path.stat().st_size / 1024 / 1024:.2f} МБ")

    except yadisk.exceptions.ForbiddenError as e:
        print(f"[ERROR] Доступ запрещен: {e}")
        print("\nВладелец папки запретил скачивание файлов.")
    except yadisk.exceptions.PathNotFoundError as e:
        print(f"[ERROR] Путь не найден: {e}")
    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
