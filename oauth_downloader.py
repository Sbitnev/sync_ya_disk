"""
Скачивание файлов через OAuth авторизацию
Требует создания приложения на OAuth.yandex.ru
"""
import os
import sys
from pathlib import Path
import yadisk
from tqdm import tqdm

# ИНСТРУКЦИЯ ПО НАСТРОЙКЕ:
#
# 1. Создайте приложение на https://oauth.yandex.ru/client/new
#    - Название: любое (например "Disk Sync")
#    - Платформа: Веб-сервисы
#    - Callback URL: https://oauth.yandex.ru/verification_code
#    - Права: cloud_api:disk.read, cloud_api:disk.write
#
# 2. Получите CLIENT_ID и CLIENT_SECRET
#
# 3. Добавьте в .env:
#    YA_CLIENT_ID=ваш_client_id
#    YA_CLIENT_SECRET=ваш_client_secret
#
# 4. Первый запуск сгенерирует OAuth токен


def get_oauth_token(client_id, client_secret):
    """Получает OAuth токен через браузер"""
    y = yadisk.YaDisk(client_id, client_secret)

    url = y.get_code_url()

    print("=" * 80)
    print("ПЕРВИЧНАЯ АВТОРИЗАЦИЯ")
    print("=" * 80)
    print(f"\n1. Откройте эту ссылку в браузере:\n   {url}\n")
    print("2. Разрешите доступ приложению")
    print("3. Скопируйте код подтверждения\n")

    code = input("Введите код подтверждения: ").strip()

    try:
        response = y.get_token(code)
        token = response.access_token
        print(f"\n✓ Токен получен!")
        print(f"  Сохраните его в .env: YA_OAUTH_TOKEN={token}")
        return token
    except Exception as e:
        print(f"\n✗ Ошибка получения токена: {e}")
        return None


def download_public_folder(y, public_url, save_to_folder):
    """
    Сохраняет публичную папку на свой диск, затем скачивает
    """
    save_path = Path(save_to_folder)
    save_path.mkdir(parents=True, exist_ok=True)

    print(f"\nПопытка сохранить публичную папку на ваш диск...")

    try:
        # Сохраняем публичную папку к себе на диск
        disk_path = f"disk:/YaDisk_Sync/{Path(save_to_folder).name}"

        # Проверяем, не сохранена ли уже
        if y.exists(disk_path):
            print(f"Папка уже существует на диске: {disk_path}")
        else:
            y.save_to_disk(public_url, path=disk_path)
            print(f"✓ Папка сохранена на ваш диск: {disk_path}")

        # Теперь скачиваем с вашего диска
        print(f"\nНачинаем скачивание...")
        download_from_disk(y, disk_path, save_path)

    except yadisk.exceptions.ForbiddenError:
        print("✗ Владелец запретил сохранение папки на другие диски")
        return False
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False

    return True


def download_from_disk(y, disk_path, local_path):
    """Рекурсивно скачивает папку со своего диска"""
    local_path = Path(local_path)

    try:
        # Получаем содержимое папки
        items = list(y.listdir(disk_path))

        for item in items:
            item_local_path = local_path / item.name
            item_disk_path = f"{disk_path}/{item.name}"

            if item.type == "dir":
                # Рекурсивно обрабатываем подпапку
                item_local_path.mkdir(parents=True, exist_ok=True)
                download_from_disk(y, item_disk_path, item_local_path)
            else:
                # Скачиваем файл
                print(f"  Скачивание: {item.name} ({format_size(item.size)})")

                with tqdm(total=item.size, unit='B', unit_scale=True, desc=item.name[:30]) as pbar:
                    def callback(monitor):
                        pbar.update(monitor.bytes_read - pbar.n)

                    y.download(item_disk_path, item_local_path, progress=callback)

    except Exception as e:
        print(f"Ошибка при скачивании {disk_path}: {e}")


def format_size(size):
    """Форматирует размер"""
    for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} ТБ"


def main():
    from dotenv import load_dotenv
    load_dotenv()

    CLIENT_ID = os.getenv('YA_CLIENT_ID')
    CLIENT_SECRET = os.getenv('YA_CLIENT_SECRET')
    OAUTH_TOKEN = os.getenv('YA_OAUTH_TOKEN')

    if not CLIENT_ID or not CLIENT_SECRET:
        print("ОШИБКА: Не найдены YA_CLIENT_ID или YA_CLIENT_SECRET в .env")
        print("\nСм. инструкцию в начале файла oauth_downloader.py")
        return

    # Получаем или создаём токен
    if not OAUTH_TOKEN:
        OAUTH_TOKEN = get_oauth_token(CLIENT_ID, CLIENT_SECRET)
        if not OAUTH_TOKEN:
            return

    # Создаём клиент
    y = yadisk.YaDisk(CLIENT_ID, CLIENT_SECRET, OAUTH_TOKEN)

    # Проверяем токен
    try:
        if not y.check_token():
            print("ОШИБКА: Токен недействителен")
            return
    except Exception as e:
        print(f"ОШИБКА проверки токена: {e}")
        return

    print("\n✓ Авторизация успешна")

    # URL для скачивания
    PUBLIC_URL = "https://disk.yandex.ru/d/_JeaJNmm6UeQVA"
    OUTPUT_DIR = "oauth_downloads"

    print(f"\nСкачивание: {PUBLIC_URL}")
    print(f"Сохранение в: {OUTPUT_DIR}")

    success = download_public_folder(y, PUBLIC_URL, OUTPUT_DIR)

    if success:
        print(f"\n✓ Скачивание завершено!")
        print(f"  Файлы в: {Path(OUTPUT_DIR).absolute()}")
    else:
        print(f"\n✗ Не удалось скачать файлы")


if __name__ == "__main__":
    main()
