# VideoConverter - Транскрибация видео в текст

## Описание

VideoConverter - это модуль для автоматической конвертации видеофайлов в текст (Markdown) через транскрибацию речи с помощью **Yandex SpeechKit API**.

## Как это работает

1. **Извлечение аудио**: ffmpeg извлекает аудиодорожку из видео в формат OGG Opus
2. **Загрузка в S3**: Аудиофайл загружается в Yandex Object Storage (S3)
3. **Транскрибация**: Yandex SpeechKit API преобразует речь в текст
4. **Сохранение**: Результат сохраняется в Markdown файл
5. **Очистка**: Временные файлы удаляются

## Требования

### 1. ffmpeg

VideoConverter использует ffmpeg для извлечения аудио из видео.

**Windows:**
```bash
# Через Chocolatey
choco install ffmpeg

# Или скачайте с https://ffmpeg.org/download.html
# И добавьте в PATH
```

**Linux:**
```bash
sudo apt install ffmpeg  # Ubuntu/Debian
sudo yum install ffmpeg  # CentOS/RHEL
```

**macOS:**
```bash
brew install ffmpeg
```

**Проверка установки:**
```bash
ffmpeg -version
```

### 2. Python зависимости

```bash
pip install boto3 requests
```

### 3. Yandex Cloud credentials

Необходимо настроить доступ к Yandex Cloud:

**Создание API ключей:**

1. Перейдите в [Yandex Cloud Console](https://console.cloud.yandex.ru/)
2. Создайте S3 bucket для хранения аудио
3. Создайте сервисный аккаунт с ролями:
   - `storage.editor` - для S3
   - `ai.speechkit-stt.user` - для SpeechKit
4. Создайте статические ключи доступа для S3
5. Создайте API-ключ для SpeechKit

**Настройка .env файла:**

```env
# S3 для загрузки аудио
YC_S3_KEY_ID=your_s3_key_id
YC_S3_SECRET_KEY=your_s3_secret_key
YC_S3_BUCKET=your-bucket-name

# API ключ для SpeechKit
YC_API_KEY_ID=your_api_key
```

## Настройка

В файле `src/config.py`:

```python
# Включить конвертацию видео
CONVERT_VIDEO_FILES = True  # По умолчанию False

# Максимальный размер видео для транскрибации
VIDEO_MAX_SIZE = 500 * 1024 * 1024  # 500 МБ

# Максимальное время ожидания транскрибации
VIDEO_TRANSCRIPTION_TIMEOUT = 600  # 10 минут

# Удалять оригинальные видео после конвертации
DELETE_ORIGINALS_AFTER_CONVERSION = False  # По умолчанию False
```

## Использование

### Автоматическая конвертация через синхронизацию

После настройки VideoConverter автоматически обрабатывает все видеофайлы при синхронизации:

```bash
python run.py
```

Система:
1. Скачает видео с Яндекс.Диска
2. Автоматически транскрибирует речь
3. Сохранит текст в `localdata/markdown_files/`
4. Опционально удалит оригинал (если `DELETE_ORIGINALS_AFTER_CONVERSION = True`)

### Ручной тест

Для тестирования на конкретном файле:

```bash
python test_video_converter.py
```

### Программное использование

```python
from pathlib import Path
from src.converters import VideoConverter

# Создать конвертер
converter = VideoConverter()

# Конвертировать видео
video_path = Path("video.mp4")
output_path = Path("transcript.md")

if converter.can_convert(video_path):
    success = converter.convert(video_path, output_path)

    if success:
        print(f"Транскрипт сохранен: {output_path}")
```

## Поддерживаемые форматы

VideoConverter поддерживает все видеоформаты из `config.VIDEO_EXTENSIONS`:

- `.mp4`
- `.avi`
- `.mov`
- `.mkv`
- `.webm`
- `.flv`
- `.wmv`
- `.m4v`
- `.mpg`
- `.mpeg`
- `.3gp`
- `.ogv`
- `.vob`
- `.ts`

## Формат выходного файла

Результат транскрибации сохраняется в Markdown:

```markdown
# Транскрипция видео: video.mp4

**Исходный файл:** video.mp4
**Размер:** 42.8 МБ
**Дата транскрибации:** 2026-01-16 12:00:00

---

## Текст

[Транскрибированный текст речи из видео]

---

*Транскрибация выполнена автоматически с помощью Yandex SpeechKit*
```

## Ограничения

1. **Размер файла**: По умолчанию максимум 500 МБ (настраивается)
2. **Время обработки**: ~1-2 минуты на минуту видео
3. **Язык**: По умолчанию русский (настраивается в коде)
4. **Качество**: Зависит от качества аудио в видео
5. **Стоимость**: Yandex SpeechKit - платный сервис

## Стоимость

Yandex SpeechKit тарифицируется за минуты распознанной речи.
Актуальные цены: https://cloud.yandex.ru/docs/speechkit/pricing

## Troubleshooting

### Ошибка: "ffmpeg не найден"

**Решение:** Установите ffmpeg и добавьте его в PATH.

### Ошибка: "Yandex Cloud credentials не настроены"

**Решение:** Проверьте наличие всех ключей в .env файле:
- YC_S3_KEY_ID
- YC_S3_SECRET_KEY
- YC_API_KEY_ID
- YC_S3_BUCKET

### Ошибка: "Видео слишком большое"

**Решение:** Увеличьте `VIDEO_MAX_SIZE` в config.py или уменьшите размер видео.

### Ошибка: "Превышено время ожидания"

**Решение:** Увеличьте `VIDEO_TRANSCRIPTION_TIMEOUT` в config.py.

### Плохое качество транскрибации

**Причины:**
- Плохое качество аудио в видео
- Фоновый шум
- Быстрая речь
- Нерусский язык (по умолчанию настроен русский)

**Решение:** Предварительно обработайте аудио или используйте видео лучшего качества.

## Интеграция с глобальной целью проекта

VideoConverter полностью интегрирован в систему "MD-копии" диска:

1. ✅ Видео скачивается с Яндекс.Диска
2. ✅ Автоматически транскрибируется в текст
3. ✅ Сохраняется в Markdown формате
4. ✅ Оригинал может быть удален (настраивается)
5. ✅ При обновлении видео - MD файл пересоздается

**Результат**: Видео файлы становятся текстовыми файлами, доступными для:
- Полнотекстового поиска
- Индексации
- Хранения в версионировании (Git)
- Экономии места (текст << видео)

## Следующие этапы

См. главный README.md для информации о:
- Этап 2: Обновление логики синхронизации
- Этап 3: Оптимизация для видео файлов
