"""
Вспомогательные утилиты для синхронизации
"""


def sanitize_filename(filename):
    """
    Удаляет или заменяет недопустимые символы в имени файла/папки для Windows

    :param filename: Исходное имя файла или папки
    :return: Безопасное имя файла
    """
    invalid_chars = '<>:"/\\|?*'
    sanitized = filename

    for char in invalid_chars:
        if char == '"':
            sanitized = sanitized.replace(char, "'")
        elif char in ['<', '>']:
            sanitized = sanitized.replace('<', '(').replace('>', ')')
        else:
            sanitized = sanitized.replace(char, '_')

    sanitized = sanitized.strip()

    if sanitized.endswith('.') or sanitized.endswith(' '):
        sanitized += '_'

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
    return '/'.join(safe_parts)


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
