"""
Главная точка входа для синхронизации личной папки пользователя с Яндекс.Диска
"""
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# Устанавливаем кодировку для консоли Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'ignore')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'ignore')

# Загружаем переменные окружения
load_dotenv()

# Импортируем модули проекта
from . import config
from .token_manager import TokenManager
from .syncer import YandexDiskUserSyncer


def setup_logging():
    """Настройка логирования"""
    logger.remove()

    # Логирование в консоль
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
        colorize=True
    )

    # Создаем директорию для логов
    config.LOGS_DIR.mkdir(exist_ok=True)

    # Логирование всех событий в основной файл
    logger.add(
        config.LOGS_DIR / "sync_ya_disk.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip"
    )

    # Отдельный файл только для ошибок (ERROR и выше)
    logger.add(
        config.LOGS_DIR / "errors.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="ERROR",
        rotation="5 MB",
        retention="30 days",
        compression="zip"
    )

    # Отдельный файл для предупреждений и выше (WARNING, ERROR, CRITICAL)
    logger.add(
        config.LOGS_DIR / "warnings.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="WARNING",
        rotation="5 MB",
        retention="14 days",
        compression="zip"
    )


def apply_migrations():
    """Применяет миграции Alembic к БД"""
    try:
        project_root = Path(__file__).parent.parent

        # Создаем директорию для БД если её нет
        db_dir = config.METADATA_DB_PATH.parent
        db_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Применение миграций базы данных...")

        # Используем API Alembic напрямую
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config(str(project_root / "alembic.ini"))
        command.upgrade(alembic_cfg, "head")

        logger.success("Миграции успешно применены")
        return True

    except Exception as e:
        logger.error(f"Ошибка при применении миграций: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


def main():
    """Главная функция"""
    # Настройка логирования
    setup_logging()

    # Применение миграций БД
    if not apply_migrations():
        logger.error("Не удалось применить миграции базы данных")
        logger.error("Проверьте логи выше для деталей ошибки")
        return 1

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

    # Создаем синхронизатор и запускаем синхронизацию
    try:
        syncer = YandexDiskUserSyncer(
            token_manager=token_manager,
            remote_folder_path=config.REMOTE_FOLDER_PATH,
            download_dir=config.DOWNLOAD_DIR
        )

        syncer.sync()
        return 0

    except KeyboardInterrupt:
        logger.warning("Синхронизация прервана пользователем")
        return 130
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
