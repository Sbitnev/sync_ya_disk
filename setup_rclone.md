# Решение: Использование rclone для скачивания всех файлов

## Установка rclone

### Windows:
```bash
# Скачайте с официального сайта
https://rclone.org/downloads/

# Или через Chocolatey
choco install rclone

# Или через Scoop
scoop install rclone
```

## Настройка для Яндекс.Диска

### Вариант 1: Публичная ссылка (простой)

1. Создайте конфигурацию:
```bash
rclone config
```

2. Выберите:
- n (new remote)
- Имя: `yandex_public`
- Storage: `51` (Yandex Disk)
- Client ID: (оставьте пустым)
- Client Secret: (оставьте пустым)
- OAuth Token: (вставьте ваш токен из .env)
- Edit advanced config: n
- Auto config: n

### Вариант 2: Через OAuth (полный доступ)

```bash
rclone config
# n (new)
# yandex
# 51 (yandex)
# [Enter] для Client ID
# [Enter] для Client Secret
# y для auto config
# Откроется браузер для авторизации
```

## Скачивание файлов

### Через публичную ссылку:
```bash
# Синхронизация всей папки
rclone copy yandex_public:/ ./downloaded_files --progress

# Скачать конкретную подпапку
rclone copy "yandex_public:/Юн.Индастриал" "./downloaded_files/Юн.Индастриал" --progress

# Инкрементальная синхронизация
rclone sync yandex_public:/ ./downloaded_files --progress
```

### Полезные флаги:
```bash
--progress              # Показывать прогресс
--transfers=5           # Количество параллельных загрузок
--checkers=8            # Количество проверок
--bwlimit=10M          # Ограничение скорости
--log-file=rclone.log  # Логирование
--dry-run              # Тестовый запуск
```

## Скрипт для автоматизации

Создайте файл `sync_with_rclone.bat`:
```batch
@echo off
echo Starting sync...
rclone sync yandex_public:/ ./downloaded_files ^
    --progress ^
    --transfers=5 ^
    --log-file=rclone.log ^
    --exclude "*.tmp" ^
    --exclude "desktop.ini"

echo Sync completed!
pause
```

## Преимущества rclone:
- ✅ Работает с публичными ссылками
- ✅ Инкрементальная синхронизация
- ✅ Многопоточная загрузка
- ✅ Retry при ошибках
- ✅ Фильтры и исключения
- ✅ Кроссплатформенность
- ✅ Может работать как демон

## Ограничения:
- ⚠️ Может не работать с файлами в подпапках без public_url
- ⚠️ Требует настройки OAuth для полного доступа
