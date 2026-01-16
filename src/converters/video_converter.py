"""
Конвертер видео файлов в текст (Markdown) через транскрибацию
"""
import os
import time
import boto3
import requests
import subprocess
from pathlib import Path
from loguru import logger

from .base import FileConverter
from .. import config


class VideoConverter(FileConverter):
    """
    Конвертер видео файлов в Markdown через транскрибацию аудио

    Использует Yandex SpeechKit для преобразования речи в текст
    """

    def __init__(self):
        super().__init__(supported_extensions=config.VIDEO_EXTENSIONS)

        # Конфигурация Yandex Cloud
        self.yc_s3_key_id = os.getenv("YC_S3_KEY_ID")
        self.yc_s3_secret_key = os.getenv("YC_S3_SECRET_KEY")
        self.yc_api_key = os.getenv("YC_API_SECRET_KEY")  # API Key для SpeechKit (исправлено)
        self.s3_bucket = os.getenv("YC_S3_BUCKET", "imprice-speech-kit")

        if not all([self.yc_s3_key_id, self.yc_s3_secret_key, self.yc_api_key]):
            logger.warning(
                "Yandex Cloud credentials не полностью настроены. "
                "VideoConverter не будет работать без YC_S3_KEY_ID, YC_S3_SECRET_KEY, YC_API_KEY_ID"
            )

        # S3 клиент для загрузки аудио
        self.s3_client = None
        if self.yc_s3_key_id and self.yc_s3_secret_key:
            try:
                self.s3_client = boto3.client(
                    's3',
                    endpoint_url='https://storage.yandexcloud.net',
                    aws_access_key_id=self.yc_s3_key_id,
                    aws_secret_access_key=self.yc_s3_secret_key,
                    region_name='ru-central1'
                )
            except Exception as e:
                logger.warning(f"Не удалось инициализировать S3 клиент: {e}")

    def can_convert(self, file_path: Path) -> bool:
        """Проверяет возможность конвертации"""
        # Базовая проверка расширения
        if not super().can_convert(file_path):
            return False

        # Проверка размера файла
        if not file_path.exists():
            return False

        file_size = file_path.stat().st_size
        max_size = getattr(config, 'VIDEO_MAX_SIZE', 500 * 1024 * 1024)

        if file_size > max_size:
            logger.warning(
                f"Видео {file_path.name} слишком большое ({file_size / 1024 / 1024:.1f} МБ) "
                f"для транскрибации (лимит: {max_size / 1024 / 1024:.1f} МБ)"
            )
            return False

        # Проверка наличия credentials
        if not self.s3_client or not self.yc_api_key:
            logger.error("Yandex Cloud credentials не настроены")
            return False

        # Проверка наличия ffmpeg
        if not self._check_ffmpeg():
            logger.error("ffmpeg не найден. Установите ffmpeg для работы VideoConverter")
            return False

        return True

    def _check_ffmpeg(self) -> bool:
        """Проверяет наличие ffmpeg"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def convert(self, input_path: Path, output_path: Path) -> bool:
        """
        Конвертирует видео в текст через транскрибацию

        :param input_path: Путь к видео файлу
        :param output_path: Путь к .md файлу
        :return: True если успешно
        """
        audio_path = None
        try:
            logger.info(f"Начало транскрибации видео: {input_path.name}")

            # 1. Извлечь аудио из видео
            audio_path = self._extract_audio(input_path)
            if not audio_path:
                return False

            # 2. Загрузить аудио в S3
            s3_uri = self._upload_to_s3(audio_path)
            if not s3_uri:
                return False

            # 3. Запустить транскрибацию
            operation_id = self._start_recognition(s3_uri)
            if not operation_id:
                return False

            # 4. Ожидание завершения
            timeout = getattr(config, 'VIDEO_TRANSCRIPTION_TIMEOUT', 600)
            result = self._wait_for_completion(operation_id, max_wait=timeout)

            if not result:
                return False

            # 5. Форматировать результат
            transcript_text = self._format_transcript(result)

            if not transcript_text:
                logger.error(f"Не удалось извлечь текст из результата транскрибации")
                return False

            # 6. Сохранить в Markdown
            self._save_markdown(output_path, input_path, transcript_text)

            logger.success(f"Видео успешно транскрибировано: {input_path.name}")
            return True

        except Exception as e:
            logger.error(f"Ошибка при транскрибации видео {input_path.name}: {e}")
            return False

        finally:
            # Удаляем временный аудио файл
            if audio_path and audio_path.exists():
                try:
                    audio_path.unlink()
                    logger.debug(f"Временный аудио файл удален: {audio_path.name}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить временный файл {audio_path}: {e}")

    def _extract_audio(self, video_path: Path) -> Path:
        """Извлекает аудио из видео с помощью ffmpeg"""
        try:
            # Создаем временный файл для аудио
            audio_path = video_path.parent / f"{video_path.stem}_temp.ogg"

            logger.info(f"Извлечение аудио из видео: {video_path.name}")

            # Команда ffmpeg для извлечения аудио
            command = [
                'ffmpeg',
                '-i', str(video_path),
                '-vn',  # Без видео
                '-ac', '2',  # Стерео
                '-ar', '16000',  # 16 kHz
                '-c:a', 'libopus',  # Кодек Opus
                '-y',  # Перезаписать если существует
                str(audio_path)
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )

            if audio_path.exists():
                logger.success(f"Аудио извлечено: {audio_path.name}")
                return audio_path
            else:
                logger.error("Файл аудио не был создан")
                return None

        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка ffmpeg: {e.stderr}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при извлечении аудио: {e}")
            return None

    def _upload_to_s3(self, audio_path: Path) -> str:
        """Загружает аудио в S3 bucket"""
        try:
            # Генерируем уникальное имя файла
            timestamp = int(time.time())
            s3_key = f"audio/{timestamp}_{audio_path.name}"

            logger.info(f"Загрузка аудио в S3: {s3_key}")

            self.s3_client.upload_file(
                str(audio_path),
                self.s3_bucket,
                s3_key
            )

            # Формируем URI для SpeechKit
            s3_uri = f"https://storage.yandexcloud.net/{self.s3_bucket}/{s3_key}"
            logger.success(f"Аудио загружено в S3: {s3_uri}")
            return s3_uri

        except Exception as e:
            logger.error(f"Ошибка при загрузке в S3: {e}")
            return None

    def _start_recognition(self, audio_uri: str) -> str:
        """Запускает задачу транскрибации"""
        try:
            url = "https://transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize"

            headers = {
                "Authorization": f"Api-Key {self.yc_api_key}"
            }

            data = {
                "config": {
                    "specification": {
                        "languageCode": "ru-RU",
                        "model": "general",
                        "audioEncoding": "OGG_OPUS",
                        "sampleRateHertz": 16000,
                        "audioChannelCount": 2  # Стерео
                    }
                },
                "audio": {
                    "uri": audio_uri
                }
            }

            logger.info(f"Запуск транскрибации: {audio_uri}")

            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()

            result = response.json()
            operation_id = result['id']

            logger.info(f"Операция запущена: {operation_id}")
            return operation_id

        except Exception as e:
            logger.error(f"Ошибка при запуске транскрибации: {e}")
            return None

    def _wait_for_completion(self, operation_id: str, max_wait: int = 600) -> dict:
        """Ожидает завершения транскрибации"""
        url = f"https://operation.api.cloud.yandex.net/operations/{operation_id}"
        headers = {"Authorization": f"Api-Key {self.yc_api_key}"}

        start_time = time.time()
        check_interval = 10  # секунд

        logger.info(f"Ожидание завершения транскрибации (max {max_wait}с)...")

        while time.time() - start_time < max_wait:
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()

                result = response.json()

                if result.get('done'):
                    if 'error' in result:
                        logger.error(f"Ошибка транскрибации: {result['error']}")
                        return None

                    logger.success("Транскрибация завершена")
                    return result.get('response', {})

                elapsed = int(time.time() - start_time)
                logger.debug(f"Транскрибация в процессе... ({elapsed}с)")
                time.sleep(check_interval)

            except Exception as e:
                logger.error(f"Ошибка при проверке статуса: {e}")
                time.sleep(check_interval)

        logger.error(f"Превышено время ожидания ({max_wait}с)")
        return None

    def _format_transcript(self, recognition_result: dict) -> str:
        """Форматирует результат распознавания в текст"""
        try:
            chunks = recognition_result.get('chunks', [])

            if not chunks:
                return ""

            text_parts = []
            for chunk in chunks:
                alternatives = chunk.get('alternatives', [])
                if alternatives:
                    text_parts.append(alternatives[0].get('text', ''))

            return ' '.join(text_parts)

        except Exception as e:
            logger.error(f"Ошибка при форматировании транскрипта: {e}")
            return ""

    def _save_markdown(self, output_path: Path, input_path: Path, text: str):
        """Сохраняет транскрипт в Markdown формате"""
        # Формируем красивый Markdown
        markdown_content = f"""# Транскрипция видео: {input_path.name}

**Исходный файл:** {input_path.name}
**Размер:** {input_path.stat().st_size / 1024 / 1024:.1f} МБ
**Дата транскрибации:** {time.strftime('%Y-%m-%d %H:%M:%S')}

---

## Текст

{text}

---

*Транскрибация выполнена автоматически с помощью Yandex SpeechKit*
"""

        # Создаем директорию если нужно
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Сохраняем
        output_path.write_text(markdown_content, encoding='utf-8')

        logger.info(f"Транскрипт сохранен: {output_path}")
