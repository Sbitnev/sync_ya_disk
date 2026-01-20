# Руководство по проверке ошибок

Краткое руководство по использованию новой системы логирования для быстрой диагностики проблем.

## Быстрый старт

### 1. Проверить наличие ошибок

```bash
# Самый быстрый способ
python check_errors.py
```

Скрипт покажет:
- Общее количество ошибок
- Типы ошибок с процентами
- Топ-10 проблемных файлов
- Рекомендации по исправлению

### 2. Посмотреть файл с ошибками вручную

**Windows:**
```bash
type logs\errors.log
```

**Linux/Mac:**
```bash
cat logs/errors.log
```

### 3. Найти конкретную ошибку

**Windows:**
```bash
# Найти все ошибки конвертации CSV
findstr "CSV" logs\errors.log

# Найти критические ошибки
findstr "Критическая" logs\errors.log

# Найти ошибки со словом "disk"
findstr /i "disk" logs\errors.log
```

**Linux/Mac:**
```bash
# Найти все ошибки конвертации CSV
grep "CSV" logs/errors.log

# Найти критические ошибки
grep "Критическая" logs/errors.log

# Найти ошибки со словом "disk" (без учета регистра)
grep -i "disk" logs/errors.log
```

---

## Распространенные проблемы

### Проблема 1: "database or disk is full"

**Симптомы:**
```
2026-01-19 21:37:28 | ERROR | Критическая ошибка: database or disk is full
```

**Решение:**
1. Проверить свободное место:
   ```bash
   # Windows
   dir C:\

   # Linux
   df -h
   ```
2. Освободить минимум 50 ГБ
3. Перезапустить синхронизацию - уже скачанные файлы будут пропущены

---

### Проблема 2: Много ошибок конвертации временных файлов

**Симптомы:**
```
2026-01-19 11:28:54 | ERROR | Ошибка конвертации ~WRL1608.tmp: файл не добавлен в БД
2026-01-19 11:29:36 | ERROR | Ошибка конвертации ~WRL3445.tmp: файл не добавлен в БД
```

**Решение:**
Добавить временные файлы в исключения. См. [CODE_IMPROVEMENTS.md](CODE_IMPROVEMENTS.md) раздел 5.

---

### Проблема 3: CSV файлы с ошибкой кодировки

**Симптомы:**
```
2026-01-19 11:43:25 | ERROR | Ошибка конвертации CSV: UTF-16 stream does not start with BOM
```

**Решение:**
Улучшить обработку CSV кодировок. См. [CODE_IMPROVEMENTS.md](CODE_IMPROVEMENTS.md) раздел 2.

---

### Проблема 4: HTTP 400 ошибки

**Симптомы:**
```
2026-01-19 12:41:59 | ERROR | HTTP ошибка 400: Bad Request for url: ...
```

**Причина:**
Имя файла содержит запрещенные символы (`:`, `<`, `>`, и т.д.)

**Решение:**
Добавить санитизацию имен файлов. См. [CODE_IMPROVEMENTS.md](CODE_IMPROVEMENTS.md) раздел 3.

---

### Проблема 5: Ошибки скачивания после 3 попыток

**Симптомы:**
```
2026-01-19 11:31:58 | ERROR | Не удалось скачать файл test.xlsx после 3 попыток
```

**Причины:**
- Нестабильное сетевое соединение
- Таймаут при скачивании больших файлов
- Проблемы на стороне Яндекс.Диска

**Решение:**
1. Проверить интернет-соединение
2. Увеличить количество попыток в конфигурации
3. Добавить экспоненциальную задержку

   См. [CODE_IMPROVEMENTS.md](CODE_IMPROVEMENTS.md) раздел 4.

---

## Полезные команды

### Статистика по ошибкам

**Windows:**
```bash
# Подсчитать общее количество ошибок
powershell -Command "(Get-Content logs\errors.log | Measure-Object -Line).Lines"

# Найти уникальные типы ошибок
powershell -Command "Get-Content logs\errors.log | Select-String 'ERROR' | Select-Object -Unique"
```

**Linux/Mac:**
```bash
# Подсчитать общее количество ошибок
wc -l logs/errors.log

# Найти уникальные типы ошибок
grep "ERROR" logs/errors.log | sort | uniq
```

### Проверка последних ошибок

**Windows:**
```bash
# Последние 20 ошибок
powershell -Command "Get-Content logs\errors.log -Tail 20"

# Ошибки за последний час (приблизительно)
powershell -Command "Get-Content logs\errors.log | Select-Object -Last 100"
```

**Linux/Mac:**
```bash
# Последние 20 ошибок
tail -20 logs/errors.log

# Следить за ошибками в реальном времени
tail -f logs/errors.log
```

### Поиск по дате

**Windows:**
```bash
# Найти ошибки за 19 января
findstr "2026-01-19" logs\errors.log
```

**Linux/Mac:**
```bash
# Найти ошибки за 19 января
grep "2026-01-19" logs/errors.log
```

---

## Анализ трендов

### Проверить рост ошибок

```bash
# Запускайте check_errors.py периодически
python check_errors.py > error_report_$(date +%Y%m%d).txt

# Сравнивайте отчеты
diff error_report_20260119.txt error_report_20260120.txt
```

### Мониторинг в реальном времени

**Linux/Mac:**
```bash
# Следить за новыми ошибками
tail -f logs/errors.log | grep --color "ERROR"
```

**Windows PowerShell:**
```powershell
Get-Content logs\errors.log -Wait -Tail 10
```

---

## Экспорт для анализа

### Экспорт в CSV для Excel

**Windows PowerShell:**
```powershell
# Экспортировать в CSV
Get-Content logs\errors.log |
    Select-String "ERROR" |
    ConvertTo-Csv |
    Out-File errors_export.csv
```

**Linux/Mac:**
```bash
# Простой экспорт
grep "ERROR" logs/errors.log > errors_export.txt
```

---

## Автоматизация проверок

### Ежедневная проверка (Linux/Mac cron)

```bash
# Добавить в crontab (crontab -e)
0 9 * * * cd /path/to/project && python check_errors.py | mail -s "Sync Errors Report" admin@example.com
```

### Ежедневная проверка (Windows Task Scheduler)

1. Открыть Task Scheduler
2. Создать базовую задачу
3. Триггер: Ежедневно в 9:00
4. Действие: Запустить программу
   - Программа: `python`
   - Аргументы: `check_errors.py`
   - Рабочая папка: `C:\path\to\project`

---

## Очистка старых логов

Логи автоматически удаляются после истечения срока хранения:
- `errors.log` - 30 дней
- `warnings.log` - 14 дней
- `sync_ya_disk.log` - 7 дней

### Ручная очистка (если нужно)

**Windows:**
```bash
# Удалить все архивы логов
del logs\*.zip

# Очистить errors.log
type nul > logs\errors.log
```

**Linux/Mac:**
```bash
# Удалить все архивы логов
rm logs/*.zip

# Очистить errors.log
> logs/errors.log
```

---

## Интеграция с мониторингом

### Простой скрипт проверки

Создайте файл `check_critical_errors.sh` (Linux/Mac) или `check_critical_errors.bat` (Windows):

**Linux/Mac:**
```bash
#!/bin/bash
if grep -q "Критическая ошибка" logs/errors.log; then
    echo "ALERT: Critical errors found!"
    exit 1
else
    echo "OK: No critical errors"
    exit 0
fi
```

**Windows:**
```batch
@echo off
findstr /C:"Критическая ошибка" logs\errors.log >nul
if %errorlevel%==0 (
    echo ALERT: Critical errors found!
    exit /b 1
) else (
    echo OK: No critical errors
    exit /b 0
)
```

Используйте в мониторинге (Nagios, Zabbix, etc.)

---

## Получение помощи

Если после анализа ошибок проблема не ясна:

1. Запустите `python check_errors.py` и сохраните вывод
2. Проверьте `logs/warnings.log` на предупреждения перед ошибкой
3. Посмотрите `logs/sync_ya_disk.log` для полного контекста
4. Обратитесь к документации:
   - [SYNC_REPORT_2026_01_19.md](SYNC_REPORT_2026_01_19.md) - анализ ошибок
   - [CODE_IMPROVEMENTS.md](CODE_IMPROVEMENTS.md) - решения проблем
   - [LOGGING.md](LOGGING.md) - полная документация по логам

---

**Последнее обновление**: 20 января 2026
