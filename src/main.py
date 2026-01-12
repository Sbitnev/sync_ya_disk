import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Устанавливаем кодировку для консоли
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'ignore')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'ignore')

# Загружаем переменные окружения из .env файла
load_dotenv()

# Конфигурация
DOWNLOAD_DIR = "downloaded_files"
METADATA_FILE = "sync_metadata.json"
TOKEN = os.getenv('Token')


class YandexDiskSyncer:
    def __init__(self, public_url, download_dir=DOWNLOAD_DIR):
        """
        Инициализация синхронизатора Яндекс Диска

        :param public_url: Публичная ссылка на Яндекс Диск
        :param download_dir: Директория для скачивания файлов
        """
        self.public_url = public_url
        self.download_dir = Path(download_dir)
        self.metadata_file = Path(METADATA_FILE)
        self.token = TOKEN
        self.metadata = self.load_metadata()

        # Создаем директорию для загрузки, если её нет
        self.download_dir.mkdir(exist_ok=True)

    def load_metadata(self):
        """Загружает метаданные о скачанных файлах"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_metadata(self):
        """Сохраняет метаданные о скачанных файлах"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    def get_public_resources(self, public_key):
        """
        Получает список ресурсов по публичной ссылке

        :param public_key: Публичная ссылка на ресурс
        :return: Данные ресурса
        """
        api_url = "https://cloud-api.yandex.net/v1/disk/public/resources"

        headers = {
            'Authorization': f'OAuth {self.token}'
        }

        params = {
            'public_key': public_key,
            'limit': 1000
        }

        try:
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении ресурсов: {e}")
            return None

    def get_all_files_recursive(self, public_key, relative_path=""):
        """
        Рекурсивно получает все файлы из папки

        :param public_key: Публичная ссылка на ресурс
        :param relative_path: Относительный путь для локального сохранения
        :return: Список всех файлов
        """
        files_list = []

        data = self.get_public_resources(public_key)
        if not data:
            return files_list

        if '_embedded' in data and 'items' in data['_embedded']:
            items = data['_embedded']['items']

            for item in items:
                item_name = item['name']
                item_type = item['type']
                item_path = f"{relative_path}/{item_name}" if relative_path else item_name

                if item_type == 'dir':
                    # Рекурсивно обходим папку используя её public_url
                    print(f"Обход папки: {item_path}")
                    item_public_url = item.get('public_url', '')
                    if item_public_url:
                        nested_files = self.get_all_files_recursive(
                            public_key=item_public_url,
                            relative_path=item_path
                        )
                        files_list.extend(nested_files)
                else:
                    # Добавляем файл в список
                    file_info = {
                        'name': item_name,
                        'path': item_path,
                        'size': item.get('size', 0),
                        'modified': item.get('modified', ''),
                        'md5': item.get('md5', ''),
                        'file': item.get('file', ''),
                        'public_url': item.get('public_url', '')
                    }
                    files_list.append(file_info)

        return files_list

    def download_file(self, file_info):
        """
        Скачивает файл с Яндекс Диска (или создает пустой файл для видео)

        :param file_info: Информация о файле
        :return: True если файл скачан успешно
        """
        # Создаем путь для сохранения файла
        local_path = self.download_dir / file_info['path']
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Проверяем, является ли файл видео
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg']
        file_ext = Path(file_info['name']).suffix.lower()

        if file_ext in video_extensions:
            # Создаем пустой файл для видео
            try:
                local_path.touch()
                print(f"Пропущено (видео, создан пустой файл): {file_info['path']} ({self.format_size(file_info['size'])})")
                return True
            except Exception as e:
                print(f"Ошибка при создании пустого файла {file_info['path']}: {e}")
                return False

        # Для обычных файлов - скачиваем
        # Проверяем, есть ли прямая ссылка на файл
        download_url = file_info.get('file')

        # Если нет прямой ссылки, получаем её через API
        if not download_url:
            download_url = self.get_download_link(file_info.get('public_url', ''))

        if not download_url:
            print(f"Не удалось получить ссылку для скачивания: {file_info['path']}")
            return False

        try:
            # Скачиваем файл
            response = requests.get(download_url, stream=True)
            response.raise_for_status()

            # Сохраняем файл
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"Скачан: {file_info['path']} ({self.format_size(file_info['size'])})")
            return True

        except requests.exceptions.RequestException as e:
            print(f"Ошибка при скачивании файла {file_info['path']}: {e}")
            return False

    def get_download_link(self, public_url):
        """
        Получает прямую ссылку на скачивание файла

        :param public_url: Публичная ссылка на файл
        :return: URL для скачивания
        """
        if not public_url:
            return None

        api_url = "https://cloud-api.yandex.net/v1/disk/public/resources/download"

        headers = {
            'Authorization': f'OAuth {self.token}'
        }

        params = {
            'public_key': public_url
        }

        try:
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('href')
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении ссылки на скачивание: {e}")
            return None

    def should_download(self, file_info):
        """
        Проверяет, нужно ли скачивать файл

        :param file_info: Информация о файле
        :return: True если файл нужно скачать
        """
        file_path = file_info['path']
        local_path = self.download_dir / file_path

        # Если файл не существует локально, скачиваем
        if not local_path.exists():
            return True

        # Если нет метаданных о файле, скачиваем
        if file_path not in self.metadata:
            return True

        old_metadata = self.metadata[file_path]

        # Сравниваем по дате модификации
        if old_metadata.get('modified') != file_info['modified']:
            return True

        # Сравниваем по размеру
        if old_metadata.get('size') != file_info['size']:
            return True

        # Сравниваем по MD5 (если доступен)
        if file_info.get('md5') and old_metadata.get('md5') != file_info['md5']:
            return True

        return False

    def sync(self):
        """
        Основная функция синхронизации
        """
        print(f"Начало синхронизации с: {self.public_url}")
        print(f"Директория для скачивания: {self.download_dir.absolute()}\n")

        # Получаем список всех файлов
        print("Получение списка файлов...")
        all_files = self.get_all_files_recursive(self.public_url)

        if not all_files:
            print("Файлы не найдены или произошла ошибка")
            return

        print(f"\nНайдено файлов: {len(all_files)}\n")

        # Статистика
        downloaded_count = 0
        updated_count = 0
        skipped_count = 0
        video_count = 0

        # Обрабатываем каждый файл
        for file_info in all_files:
            # Проверяем, является ли файл видео
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg']
            file_ext = Path(file_info['name']).suffix.lower()
            is_video = file_ext in video_extensions

            if self.should_download(file_info):
                # Определяем, это новый файл или обновление
                is_new = file_info['path'] not in self.metadata

                if self.download_file(file_info):
                    # Обновляем метаданные
                    self.metadata[file_info['path']] = {
                        'size': file_info['size'],
                        'modified': file_info['modified'],
                        'md5': file_info['md5'],
                        'last_sync': datetime.now().isoformat(),
                        'is_video': is_video
                    }

                    if is_video:
                        video_count += 1
                    elif is_new:
                        downloaded_count += 1
                    else:
                        updated_count += 1
            else:
                skipped_count += 1
                print(f"Пропущен (не изменен): {file_info['path']}")

        # Сохраняем метаданные
        self.save_metadata()

        # Итоговая статистика
        print(f"\n{'='*60}")
        print(f"Синхронизация завершена!")
        print(f"{'='*60}")
        print(f"Новых файлов скачано: {downloaded_count}")
        print(f"Обновленных файлов: {updated_count}")
        print(f"Видео (созданы пустые файлы): {video_count}")
        print(f"Пропущено (без изменений): {skipped_count}")
        print(f"Всего файлов: {len(all_files)}")

    @staticmethod
    def format_size(size):
        """Форматирует размер файла в читаемый вид"""
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} ТБ"


def main():
    """Главная функция"""
    if not TOKEN:
        print("Ошибка: токен не найден в .env файле")
        return

    # Публичная ссылка на Яндекс Диск
    public_url = "https://disk.yandex.ru/d/_JeaJNmm6UeQVA"

    # Создаем синхронизатор и запускаем синхронизацию
    syncer = YandexDiskSyncer(public_url)
    syncer.sync()


if __name__ == "__main__":
    main()
