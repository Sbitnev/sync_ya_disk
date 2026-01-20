"""
Вспомогательные утилиты для синхронизации
"""
import re


def sanitize_filename(filename):
    """
    Удаляет или заменяет недопустимые символы в имени файла/папки для Windows

    :param filename: Исходное имя файла или папки
    :return: Безопасное имя файла
    """
    # Список зарезервированных имен в Windows
    RESERVED_NAMES = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }

    # Недопустимые символы в именах файлов Windows
    invalid_chars = '<>:"/\\|?*'
    sanitized = filename

    # Заменяем недопустимые символы
    for char in invalid_chars:
        if char == '"':
            sanitized = sanitized.replace(char, "'")
        elif char in ['<', '>']:
            sanitized = sanitized.replace('<', '(').replace('>', ')')
        else:
            sanitized = sanitized.replace(char, '_')

    # Удаляем управляющие символы (ASCII 0-31)
    sanitized = re.sub(r'[\x00-\x1f]', '', sanitized)

    # Убираем пробелы в начале и конце
    sanitized = sanitized.strip()

    # Убираем точки и пробелы в конце (запрещено в Windows)
    sanitized = sanitized.rstrip('. ')

    # Если имя пустое после очистки, используем fallback
    if not sanitized:
        sanitized = 'unnamed'

    # Проверяем на зарезервированные имена Windows
    name_upper = sanitized.upper()
    # Проверяем как с расширением, так и без
    name_without_ext = name_upper.split('.')[0] if '.' in name_upper else name_upper

    if name_without_ext in RESERVED_NAMES:
        sanitized = f"_{sanitized}"

    # Ограничиваем длину имени файла (Windows limit: 255 символов для имени файла)
    if len(sanitized) > 200:  # Оставляем запас для расширений
        # Сохраняем расширение если есть
        if '.' in sanitized:
            name, ext = sanitized.rsplit('.', 1)
            sanitized = name[:200-len(ext)-1] + '.' + ext
        else:
            sanitized = sanitized[:200]

    return sanitized


def sanitize_path(path):
    """
    Санитизирует полный путь, обрабатывая каждый компонент отдельно

    :param path: Путь с возможно недопустимыми символами
    :return: Безопасный путь
    """
    if not path:
        return path

    parts = path.split('/')
    safe_parts = [sanitize_filename(part) for part in parts if part]
    result_path = '/'.join(safe_parts)

    # Предупреждаем о длинных путях (Windows limit: 260 символов)
    # Оставляем запас для префикса пути localdata/downloaded_files/
    if len(result_path) > 200:
        # Можно логировать предупреждение, но не обрезаем - пусть Path сам обработает
        # logger.warning(f"Длинный путь ({len(result_path)} символов): {result_path[:50]}...")
        pass

    return result_path


def format_size(size):
    """
    Форматирует размер файла в читаемый вид

    :param size: Размер в байтах
    :return: Строка с размером в читаемом формате
    """
    for unit in ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} ПБ"
