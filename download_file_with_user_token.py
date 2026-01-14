"""
Скачивание файла из папки Клиенты с использованием токена пользователя
"""
import os
import requests
from pathlib import Path
from dotenv import load_dotenv


def download_file_from_disk(token, file_path, local_path):
    """Скачивает файл с диска пользователя"""
    # Шаг 1: Получаем ссылку на скачивание
    url = "https://cloud-api.yandex.net/v1/disk/resources/download"
    headers = {"Authorization": f"OAuth {token}"}
    params = {"path": file_path}

    try:
        print(f"Получение ссылки на скачивание...")
        print(f"Файл: {file_path}")

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            download_url = data.get("href")

            if not download_url:
                print("[ERROR] Не удалось получить ссылку")
                return False

            print(f"[OK] Ссылка получена!")

            # Шаг 2: Скачиваем файл
            print(f"Скачивание файла...")

            file_response = requests.get(download_url, stream=True)

            if file_response.status_code == 200:
                local_path = Path(local_path)
                local_path.parent.mkdir(parents=True, exist_ok=True)

                total_size = int(file_response.headers.get('content-length', 0))
                downloaded = 0

                with open(local_path, 'wb') as f:
                    for chunk in file_response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                print(f"\rПрогресс: {progress:.1f}% ({downloaded / 1024 / 1024:.2f} МБ / {total_size / 1024 / 1024:.2f} МБ)", end="")

                print(f"\n[OK] Файл успешно скачан!")
                print(f"Сохранен в: {local_path.absolute()}")
                print(f"Размер: {local_path.stat().st_size / 1024 / 1024:.2f} МБ")
                return True
            else:
                print(f"[ERROR] Ошибка скачивания: {file_response.status_code}")
                return False
        else:
            print(f"[ERROR] Ошибка получения ссылки: {response.status_code}")
            print(f"Ответ: {response.text}")
            return False

    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def list_folder_contents(token, folder_path):
    """Выводит содержимое папки"""
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {"Authorization": f"OAuth {token}"}
    params = {
        "path": folder_path,
        "limit": 100,
        "fields": "_embedded.items.name,_embedded.items.type,_embedded.items.size,_embedded.items.path"
    }

    try:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            items = data.get("_embedded", {}).get("items", [])

            print(f"\nСодержимое папки: {folder_path}")
            print(f"Всего элементов: {len(items)}\n")

            for i, item in enumerate(items, 1):
                item_type = "[DIR]" if item.get("type") == "dir" else "[FILE]"
                name = item.get("name")
                size = item.get("size", 0)

                size_str = f"{size / 1024 / 1024:.2f} МБ" if item.get("type") == "file" else ""

                print(f"{i}. {item_type} {name} {size_str}")

            return items
        else:
            print(f"[ERROR] Ошибка: {response.status_code}")
            print(f"Ответ: {response.text}")
            return []

    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        return []


def main():
    load_dotenv()

    # Используем полученный токен
    token = "2.1130000057842996.997486.1768381487.1768377887976.1.0.11609667.BSFzzc69Js6_ATwI.E98i9pzJ3MdPQcY7o23pdFoLvgwPKSyzcwj_QFeIg91zeNfXtZyIMijTGQJArg.cm377ZoGRhNjmX04cOlvgw"

    # Путь к папке и файлу
    folder_path = "/Клиенты/Юн.Индастриал"
    file_name = "UInd. Предварительное предложение.docx"
    file_path = f"{folder_path}/{file_name}"
    local_path = f"downloads/{file_name}"

    print("="*80)
    print("СКАЧИВАНИЕ ФАЙЛА С ЛИЧНОГО ДИСКА ПОЛЬЗОВАТЕЛЯ")
    print("="*80)
    print(f"Пользователь: tn@imprice.ai")
    print(f"Папка: {folder_path}")
    print(f"Файл: {file_name}")
    print("="*80 + "\n")

    # Показываем содержимое папки
    items = list_folder_contents(token, folder_path)

    # Ищем нужный файл
    target_file = None
    for item in items:
        if item.get("name") == file_name:
            target_file = item
            break

    if not target_file:
        print(f"\n[ERROR] Файл '{file_name}' не найден в папке")
        print("Доступные файлы:")
        for item in items:
            if item.get("type") == "file":
                print(f"  - {item.get('name')}")
        return

    print(f"\n[OK] Файл найден!")
    print(f"Размер: {target_file.get('size', 0) / 1024 / 1024:.2f} МБ")
    print()

    # Скачиваем файл
    success = download_file_from_disk(token, file_path, local_path)

    if success:
        print("\n" + "="*80)
        print("[OK] СКАЧИВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        print("="*80)


if __name__ == "__main__":
    main()
