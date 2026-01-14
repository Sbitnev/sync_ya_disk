"""
Скачивание файла из публичной папки через сохранение на свой диск
"""
import os
import requests
import time
from dotenv import load_dotenv
from pathlib import Path


def save_public_file_to_disk(token, public_key, file_path, disk_path):
    """Сохраняет публичный файл на свой диск"""
    url = "https://cloud-api.yandex.net/v1/disk/public/resources/save-to-disk"
    headers = {"Authorization": f"OAuth {token}"}
    params = {
        "public_key": public_key,
        "path": file_path,
        "save_path": disk_path
    }

    try:
        print(f"Попытка сохранить файл на диск организации...")
        print(f"  Публичный путь: {file_path}")
        print(f"  Целевой путь: {disk_path}")

        response = requests.post(url, headers=headers, params=params)

        if response.status_code == 201:
            print("[OK] Файл сохранен на диск!")
            return True
        elif response.status_code == 202:
            # Операция асинхронная, нужно подождать
            print("[INFO] Операция выполняется асинхронно...")
            data = response.json()
            operation_url = data.get("href")

            if operation_url:
                # Ждем завершения операции
                print("Ожидание завершения операции...")
                for i in range(30):  # Максимум 30 секунд
                    time.sleep(1)
                    op_response = requests.get(operation_url, headers=headers)
                    if op_response.status_code == 200:
                        op_data = op_response.json()
                        status = op_data.get("status")
                        print(f"  Статус: {status}")

                        if status == "success":
                            print("[OK] Файл успешно сохранен!")
                            return True
                        elif status == "failed":
                            print(f"[ERROR] Операция не удалась: {op_data}")
                            return False

                print("[ERROR] Превышено время ожидания")
                return False

            return True
        elif response.status_code == 409:
            print("[INFO] Файл уже существует на диске")
            return True
        elif response.status_code == 403:
            print("[ERROR] Владелец запретил сохранение файлов")
            print(f"Ответ: {response.text}")
            return False
        else:
            print(f"[ERROR] Ошибка сохранения: {response.status_code}")
            print(f"Ответ: {response.text}")
            return False

    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        return False


def download_from_own_disk(token, disk_path, local_path):
    """Скачивает файл со своего диска"""
    url = "https://cloud-api.yandex.net/v1/disk/resources/download"
    headers = {"Authorization": f"OAuth {token}"}
    params = {"path": disk_path}

    try:
        print(f"\nПолучение ссылки на скачивание с собственного диска...")
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            download_url = data.get("href")

            if not download_url:
                print("[ERROR] Не удалось получить ссылку")
                return False

            print(f"Ссылка получена!")
            print(f"Скачивание файла...")

            # Скачиваем файл
            file_response = requests.get(download_url, stream=True)

            if file_response.status_code == 200:
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
                                print(f"\rПрогресс: {progress:.1f}%", end="")

                print(f"\n[OK] Файл успешно скачан!")
                return True
            else:
                print(f"[ERROR] Ошибка скачивания: {file_response.status_code}")
                return False
        else:
            print(f"[ERROR] Ошибка: {response.status_code}")
            print(f"Ответ: {response.text}")
            return False

    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        return False


def delete_from_disk(token, disk_path):
    """Удаляет файл с диска (для очистки)"""
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {"Authorization": f"OAuth {token}"}
    params = {"path": disk_path, "permanently": "true"}

    try:
        requests.delete(url, headers=headers, params=params)
    except Exception:
        pass


def main():
    load_dotenv()
    token = os.getenv("Token")

    if not token:
        print("Токен не найден")
        return

    public_url = "https://disk.yandex.ru/d/_JeaJNmm6UeQVA"
    public_file_path = "/Юн.Индастриал/UInd. Предварительное предложение.docx"
    disk_path = "/temp_download_test/test_file.docx"
    local_path = Path("test_downloads/UInd. Предварительное предложение.docx")

    print("="*80)
    print("СКАЧИВАНИЕ ЧЕРЕЗ СОХРАНЕНИЕ НА ДИСК")
    print("="*80)
    print(f"Метод: Сохранение на диск -> Скачивание с диска")
    print("="*80 + "\n")

    # Шаг 1: Сохраняем файл на свой диск
    saved = save_public_file_to_disk(token, public_url, public_file_path, disk_path)

    if not saved:
        print("\n" + "="*80)
        print("[ERROR] НЕ УДАЛОСЬ СОХРАНИТЬ ФАЙЛ НА ДИСК")
        print("="*80)
        return

    # Шаг 2: Скачиваем с собственного диска
    downloaded = download_from_own_disk(token, disk_path, local_path)

    # Шаг 3: Удаляем временный файл с диска
    if downloaded:
        print(f"\nОчистка: удаление временного файла с диска...")
        delete_from_disk(token, disk_path)

        print("\n" + "="*80)
        print("[OK] ФАЙЛ УСПЕШНО СКАЧАН!")
        print("="*80)
        print(f"Расположение: {local_path.absolute()}")
    else:
        print("\n" + "="*80)
        print("[ERROR] НЕ УДАЛОСЬ СКАЧАТЬ ФАЙЛ")
        print("="*80)


if __name__ == "__main__":
    main()
