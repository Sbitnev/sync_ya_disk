"""
Скачивание файла из публичной папки с помощью библиотеки yadisk
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
    file_path = "/Юн.Индастриал/UInd. Предварительное предложение.docx"
    local_path = Path("test_downloads/UInd. Предварительное предложение.docx")

    print("="*80)
    print("СКАЧИВАНИЕ С ПОМОЩЬЮ БИБЛИОТЕКИ YADISK")
    print("="*80)

    # Создаём клиент с токеном
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

    # Попытка 1: Прямое скачивание публичного файла
    print("Попытка 1: Прямое скачивание публичного файла...")
    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Скачиваем напрямую из публичной папки
        y.download_public(public_url + file_path, str(local_path))

        print(f"[OK] Файл успешно скачан!")
        print(f"Расположение: {local_path.absolute()}")
        return

    except yadisk.exceptions.ForbiddenError:
        print("[ERROR] Доступ запрещен - владелец не разрешает прямое скачивание\n")
    except yadisk.exceptions.PathNotFoundError:
        print("[ERROR] Файл не найден\n")
    except Exception as e:
        print(f"[ERROR] Ошибка: {e}\n")

    # Попытка 2: Сохранение на диск и скачивание
    print("Попытка 2: Сохранение на диск организации...")
    disk_path = "/temp_download_test/test_file.docx"

    try:
        # Сохраняем публичный ресурс на свой диск
        y.save_to_disk(public_url, name=file_path, path=disk_path)
        print(f"[OK] Файл сохранен на диск: {disk_path}")

        # Скачиваем с собственного диска
        print("Скачивание с собственного диска...")
        y.download(disk_path, str(local_path))

        print(f"[OK] Файл успешно скачан!")
        print(f"Расположение: {local_path.absolute()}")

        # Удаляем временный файл
        print("Удаление временного файла...")
        y.remove(disk_path, permanently=True)

    except yadisk.exceptions.ForbiddenError:
        print("[ERROR] Владелец запретил сохранение на другие диски")
    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")

    # Попытка 3: Получение ссылки на скачивание
    print("\nПопытка 3: Получение публичной ссылки на скачивание...")
    try:
        link = y.get_public_download_link(public_url + file_path)
        print(f"[OK] Получена ссылка: {link}")
        print("Попробуйте скачать файл по этой ссылке вручную через браузер")

    except yadisk.exceptions.ForbiddenError:
        print("[ERROR] Получение ссылки запрещено")
    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")

    print("\n" + "="*80)
    print("ИТОГ: Скачивание не удалось")
    print("="*80)
    print("Владелец публичной папки установил ограничения:")
    print("  - Запрещено прямое скачивание файлов")
    print("  - Запрещено сохранение на другие диски")
    print("\nВозможные решения:")
    print("  1. Попросить владельца снять ограничения")
    print("  2. Попросить владельца предоставить прямой доступ к папке")
    print("  3. Скачать файлы вручную через веб-интерфейс")


if __name__ == "__main__":
    main()
