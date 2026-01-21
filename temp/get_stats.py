"""
Скрипт для получения статистики по типам файлов в папке "/Клиенты" на Яндекс.Диске
"""
import sys
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv
from loguru import logger

# Загружаем переменные окружения
load_dotenv()

# Импортируем модули проекта
from src import config
from src.token_manager import TokenManager
from src.syncer import YandexDiskUserSyncer
from src.utils import format_size


def setup_logging():
    """Настройка логирования"""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
        colorize=True
    )


def get_file_statistics(syncer: YandexDiskUserSyncer):
    """
    Получает статистику по типам файлов

    :param syncer: Инициализированный синхронизатор
    :return: Словарь со статистикой
    """
    logger.info("=" * 80)
    logger.info(f"ПОЛУЧЕНИЕ СТАТИСТИКИ ПО ПАПКЕ: {config.REMOTE_FOLDER_PATH}")
    logger.info("=" * 80)

    # Получаем список всех файлов
    logger.info("Получение списка файлов с Яндекс.Диска...")
    folders_set = set()
    all_files = syncer.get_all_files_recursive(config.REMOTE_FOLDER_PATH, folders_set=folders_set)

    if not all_files:
        logger.warning("Файлы не найдены")
        return None

    logger.success(f"Найдено файлов: {len(all_files)}")
    logger.success(f"Найдено папок: {len(folders_set)}")

    # Подсчитываем статистику по типам файлов
    logger.info("\nАнализ типов файлов...")

    stats_by_extension = defaultdict(lambda: {
        'count': 0,
        'total_size': 0,
        'files': []
    })

    total_size = 0
    total_count = 0

    for file_info in all_files:
        file_path = file_info['path']
        file_size = file_info['size']

        # Определяем расширение файла
        file_ext = Path(file_path).suffix.lower()
        if not file_ext:
            file_ext = "(без расширения)"

        # Обновляем статистику
        stats_by_extension[file_ext]['count'] += 1
        stats_by_extension[file_ext]['total_size'] += file_size
        stats_by_extension[file_ext]['files'].append({
            'path': file_path,
            'size': file_size
        })

        total_size += file_size
        total_count += 1

    return {
        'by_extension': dict(stats_by_extension),
        'total_size': total_size,
        'total_count': total_count
    }


def print_statistics(stats: dict):
    """
    Выводит статистику в читаемом виде

    :param stats: Словарь со статистикой
    """
    if not stats:
        return

    logger.info("\n" + "=" * 80)
    logger.info("СТАТИСТИКА ПО ТИПАМ ФАЙЛОВ")
    logger.info("=" * 80)

    # Сортируем по размеру (по убыванию)
    sorted_extensions = sorted(
        stats['by_extension'].items(),
        key=lambda x: x[1]['total_size'],
        reverse=True
    )

    # Выводим заголовок таблицы
    logger.info(f"{'№':<4} {'Тип файла':<20} {'Количество':<15} {'Размер':<20} {'% от общего':<15}")
    logger.info("-" * 80)

    # Выводим данные по каждому типу
    for idx, (ext, data) in enumerate(sorted_extensions, 1):
        count = data['count']
        total_size = data['total_size']
        percentage = (total_size / stats['total_size'] * 100) if stats['total_size'] > 0 else 0

        logger.info(
            f"{idx:<4} {ext:<20} {count:<15} {format_size(total_size):<20} {percentage:>6.2f}%"
        )

    # Итоговая статистика
    logger.info("-" * 80)
    logger.info(f"{'':24} ИТОГО: {stats['total_count']:<15} {format_size(stats['total_size']):<20} 100.00%")
    logger.info("=" * 80)

    # Топ-10 самых больших типов файлов
    logger.info("\nТОП-10 ТИПОВ ФАЙЛОВ ПО ОБЪЕМУ:")
    logger.info("-" * 80)

    top_10 = sorted_extensions[:10]
    for idx, (ext, data) in enumerate(top_10, 1):
        percentage = (data['total_size'] / stats['total_size'] * 100) if stats['total_size'] > 0 else 0
        logger.info(
            f"{idx}. {ext:<15} - {format_size(data['total_size']):<15} ({percentage:.2f}%) - {data['count']} файлов"
        )

    logger.info("=" * 80)


def save_detailed_report(stats: dict, output_file: str = "file_statistics.txt"):
    """
    Сохраняет подробный отчет в файл

    :param stats: Словарь со статистикой
    :param output_file: Путь к файлу для сохранения
    """
    if not stats:
        return

    output_path = Path(output_file)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("ПОДРОБНАЯ СТАТИСТИКА ПО ТИПАМ ФАЙЛОВ\n")
        f.write(f"Папка: {config.REMOTE_FOLDER_PATH}\n")
        f.write("=" * 80 + "\n\n")

        # Сортируем по размеру (по убыванию)
        sorted_extensions = sorted(
            stats['by_extension'].items(),
            key=lambda x: x[1]['total_size'],
            reverse=True
        )

        # Выводим данные по каждому типу
        for idx, (ext, data) in enumerate(sorted_extensions, 1):
            count = data['count']
            total_size = data['total_size']
            percentage = (total_size / stats['total_size'] * 100) if stats['total_size'] > 0 else 0

            f.write(f"\n{idx}. {ext}\n")
            f.write(f"   Количество файлов: {count}\n")
            f.write(f"   Общий размер: {format_size(total_size)} ({percentage:.2f}%)\n")

            # Топ-5 самых больших файлов этого типа
            top_files = sorted(data['files'], key=lambda x: x['size'], reverse=True)[:5]
            if top_files:
                f.write(f"   Топ-5 самых больших файлов:\n")
                for file_idx, file_data in enumerate(top_files, 1):
                    f.write(f"      {file_idx}. {file_data['path']} - {format_size(file_data['size'])}\n")

            f.write("\n")

        # Итоговая статистика
        f.write("-" * 80 + "\n")
        f.write(f"ИТОГО:\n")
        f.write(f"   Всего файлов: {stats['total_count']}\n")
        f.write(f"   Общий размер: {format_size(stats['total_size'])}\n")
        f.write("=" * 80 + "\n")

    logger.success(f"Подробный отчет сохранен в: {output_path.absolute()}")


def main():
    """Главная функция"""
    setup_logging()

    # Валидация конфигурации
    try:
        config.validate_config()
    except ValueError as e:
        logger.error(str(e))
        return 1

    # Создаем менеджер токенов
    logger.info("Инициализация менеджера токенов...")
    try:
        token_manager = TokenManager(
            client_id=config.CLIENT_ID,
            client_secret=config.CLIENT_SECRET,
            user_id=config.USER_ID,
            token_lifetime=config.TOKEN_LIFETIME,
            refresh_before=config.TOKEN_REFRESH_BEFORE
        )
    except Exception as e:
        logger.error(f"Ошибка при создании менеджера токенов: {e}")
        return 1

    # Создаем синхронизатор (только для доступа к API, не запускаем синхронизацию)
    try:
        syncer = YandexDiskUserSyncer(
            token_manager=token_manager,
            remote_folder_path=config.REMOTE_FOLDER_PATH,
            download_dir=config.DOWNLOAD_DIR
        )

        # Получаем статистику
        stats = get_file_statistics(syncer)

        if stats:
            # Выводим статистику
            print_statistics(stats)

            # Сохраняем подробный отчет
            save_detailed_report(stats, "file_statistics.txt")

        return 0

    except KeyboardInterrupt:
        logger.warning("Прервано пользователем")
        return 130
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
